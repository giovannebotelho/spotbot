import asyncio
from config.settings import TELEGRAM_CONFIG, TIMEZONE
from services.binance_client import (
    setup_futures_margin, place_futures_order, place_futures_conditional_order,
    get_futures_usdt_balance, get_futures_klines
)
from core.decision import get_precision
from core.indicators import calculate_rsi
from core.futures_order_manager import monitor_futures_lifecycle
from services.telegram_notifier import send_telegram_message

bot_futures_running = False
active_futures_positions = {}
bot_futures_status_data = {
    "price": 0, "symbol": "", "action": "Aguardando...", "target_asset": "BTCUSDT",
    "active_symbols": [], "active_positions": active_futures_positions
}

async def run_futures_bot(client, bsm, db, log=print, status=print):
    global bot_futures_running, active_futures_positions, bot_futures_status_data
    bot_futures_running = True
    log("🚀 Iniciando Motor de Futuros (HedgeFund Edition)...")
    
    symbols_to_scan = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'AVAXUSDT']
    
    try:
        exchange_info = await client.futures_exchange_info()
        symbols_info = {s['symbol']: s for s in exchange_info['symbols']}
    except Exception as e:
        log(f"⚠️ Erro ao buscar futures_exchange_info: {e}")
        symbols_info = {}
        
    try:
        positions = await client.futures_position_information()
        active = [p for p in positions if float(p['positionAmt']) != 0]
        if active:
            log(f"🔄 \033[1;36mState Recovery Engine\033[0m: {len(active)} posição(ões) de Futuros ativa(s) encontrada(s)!")
            for p in active:
                rec_symbol = p['symbol']
                qty = float(p['positionAmt'])
                entry_price = float(p['entryPrice'])
                direction = 'LONG' if qty > 0 else 'SHORT'
                qty = abs(qty)
                
                algo_open = await client.futures_get_open_algo_orders(symbol=rec_symbol)
                tp_order = next((o for o in algo_open if o['orderType'] == 'TAKE_PROFIT_MARKET'), None)
                sl_order = next((o for o in algo_open if o['orderType'] == 'STOP_MARKET'), None)
                
                tp_price = float(tp_order['triggerPrice']) if tp_order else (entry_price * 1.03 if direction == 'LONG' else entry_price * 0.97)
                sl_price = float(sl_order['triggerPrice']) if sl_order else (entry_price * 0.98 if direction == 'LONG' else entry_price * 1.02)
                
                if tp_order and sl_order:
                    active_futures_positions[rec_symbol] = {
                        'entry': entry_price, 'tp': tp_price, 'sl': sl_price, 'direction': direction
                    }
                    bot_futures_status_data['active_symbols'] = list(active_futures_positions.keys())
                    log(f"🛡️ Retomando monitoramento de \033[1;33m{rec_symbol}\033[0m sem cancelar a operação...")
                    asyncio.create_task(monitor_futures_lifecycle(
                        client, bsm, rec_symbol, direction, entry_price, qty,
                        tp_order.get('algoId'), sl_order.get('algoId'), tp_price, sl_price, db,
                        active_futures_positions, bot_futures_status_data, log, status
                    ))
                    if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                        asyncio.create_task(send_telegram_message(
                            TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                            f"🔄 <b>FUTURES State Recovery Ativado!</b>\n\n"
                            f"🪙 Par: <b>{rec_symbol}</b> ({direction})\n"
                            f"🛡️ Posição adotada da nuvem para monitoramento ativo!"
                        ))
                else:
                    log(f"⚠️ Posição órfã em {rec_symbol} sem Stop Loss! Recomenda-se fechar manualmente.")
    except Exception as e:
        log(f"⚠️ Erro no State Recovery do Futuros: {e}")

    
    while bot_futures_running:
        try:
            if len(active_futures_positions) >= 3:
                status("⏳ Limite de 3 posições simultâneas atingido no Futuros.")
                await asyncio.sleep(10)
                continue
                
            for symbol in symbols_to_scan:
                if symbol in active_futures_positions:
                    continue
                    
                status(f"🔍 [FUTUROS] Analisando {symbol}...")
                
                # Setup alavancagem 20x Isolada
                await setup_futures_margin(client, symbol, leverage=20, margin_type='ISOLATED')
                
                # Fetch Klines 15m
                klines = await get_futures_klines(client, symbol, interval='15m', limit=100)
                if not klines or len(klines) < 20:
                    continue
                    
                closes = [float(k[4]) for k in klines]
                cur_price = closes[-1]
                rsi = calculate_rsi(closes)
                
                direction = None
                if rsi < 30:
                    direction = 'LONG'
                elif rsi > 70:
                    direction = 'SHORT'
                    
                if direction:
                    log(f"🚨 [FUTUROS] Oportunidade {direction} detectada em {symbol} (RSI: {rsi:.1f})")
                    
                    usdt_balance = await get_futures_usdt_balance(client)
                    if usdt_balance < 10:
                        log(f"⚠️ Saldo insuficiente no Futuros: ${usdt_balance:.2f}. Necessário mínimo de $10.")
                        await asyncio.sleep(30)
                        break
                        
                    # Usa $10 dólares de margem por trade (com 20x = $200 de posição)
                    margin_usdt = 10.0 
                    leverage = 20
                    notional = margin_usdt * leverage
                    
                    # Dinamicamente buscar a precisão do ativo
                    info = symbols_info.get(symbol, {})
                    qty_precision = 3
                    price_precision = 4
                    if info:
                        for f in info.get('filters', []):
                            if f['filterType'] == 'LOT_SIZE':
                                qty_precision = get_precision(float(f['stepSize']))
                            if f['filterType'] == 'PRICE_FILTER':
                                price_precision = get_precision(float(f['tickSize']))
                                
                    qty = round(notional / cur_price, qty_precision)
                    if qty <= 0: continue
                    
                    try:
                        # Market Entry
                        side_entry = 'BUY' if direction == 'LONG' else 'SELL'
                        entry_order = await place_futures_order(client, symbol, side_entry, 'MARKET', qty)
                        
                        entry_price = float(entry_order.get('avgPrice', cur_price))
                        if entry_price == 0.0: entry_price = cur_price
                        
                        # Conditional Orders (TP 3%, SL 2%)
                        if direction == 'LONG':
                            tp_price = entry_price * 1.03
                            sl_price = entry_price * 0.98
                            side_exit = 'SELL'
                        else:
                            tp_price = entry_price * 0.97
                            sl_price = entry_price * 1.02
                            side_exit = 'BUY'
                            
                        # Usando a precisão real da exchange
                        tp_price = round(tp_price, price_precision)
                        sl_price = round(sl_price, price_precision)
                        
                        tp_order = await place_futures_conditional_order(client, symbol, side_exit, 'TAKE_PROFIT_MARKET', qty, tp_price)
                        sl_order = await place_futures_conditional_order(client, symbol, side_exit, 'STOP_MARKET', qty, sl_price)
                        
                        active_futures_positions[symbol] = {
                            'entry': entry_price, 'tp': tp_price, 'sl': sl_price, 'direction': direction
                        }
                        bot_futures_status_data['active_symbols'] = list(active_futures_positions.keys())
                        
                        log(f"✅ [FUTUROS] Posição {direction} aberta em {symbol} a ${entry_price:.4f} (TP: ${tp_price}, SL: ${sl_price})")
                        
                        # Inicia Monitoramento Lifecycle
                        asyncio.create_task(monitor_futures_lifecycle(
                            client, bsm, symbol, direction, entry_price, qty,
                            tp_order.get('orderId') or tp_order.get('algoId'),
                            sl_order.get('orderId') or sl_order.get('algoId'),
                            tp_price, sl_price, db,
                            active_futures_positions, bot_futures_status_data, log, status
                        ))
                        
                    except Exception as e:
                        log(f"❌ Erro ao abrir posição {direction} em {symbol}: {e}")
                        
            await asyncio.sleep(5)
            
        except Exception as e:
            log(f"⚠️ Erro no Motor de Futuros: {e}")
            await asyncio.sleep(10)

async def panic_sell_futures_position(client, symbol, qty=0, log=print):
    """Fecha imediatamente a posição de futuros (Panic Sell) e limpa ordens condicionais."""
    if symbol not in active_futures_positions:
        return False, "Nenhuma posição aberta neste par."
    
    pos_data = active_futures_positions[symbol]
    direction = pos_data['direction']
    close_side = 'SELL' if direction == 'LONG' else 'BUY'
    
    try:
        # Tenta pegar ordens em aberto para cancelar
        open_orders = await client.futures_get_open_orders(symbol=symbol)
        for order in open_orders:
            try:
                await client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
            except: pass
            
        # O qty não é armazenado localmente para simplificar no dicionário
        # precisaremos buscar a quantidade exata da posição aberta se qty=0
        if qty == 0:
            positions = await client.futures_position_information(symbol=symbol)
            for p in positions:
                if float(p['positionAmt']) != 0:
                    qty = abs(float(p['positionAmt']))
                    break
        
        if qty > 0:
            await client.futures_create_order(symbol=symbol, side=close_side, type='MARKET', quantity=qty, reduceOnly='true')
            
        active_futures_positions.pop(symbol, None)
        bot_futures_status_data['active_symbols'] = list(active_futures_positions.keys())
        log(f"🔥 PANIC SELL FUTUROS: {symbol} liquidado a mercado!")
        return True, f"Posição de Futuros em {symbol} liquidada a mercado."
    except Exception as e:
        log(f"Erro no Panic Sell Futuros: {e}")
        return False, str(e)
