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

shared_futures_market_data = {
    'dates': [], 'klines': [], 'bb_upper': [], 'bb_lower': [], 'ema200': [], 'volumes': []
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
                    bot_futures_status_data['target_asset'] = rec_symbol
                    
                    try:
                        import pandas as pd
                        import datetime as dt_module
                        from config.settings import TIMEZONE, TRADING_CONFIG
                        from services.binance_client import get_futures_klines
                        klines_raw = await get_futures_klines(client, symbol=rec_symbol, interval=TRADING_CONFIG['interval'], limit=100)
                        if klines_raw:
                            klines_rec = [float(k[4]) for k in klines_raw]
                            dates_rec = [dt_module.datetime.fromtimestamp(float(k[0])/1000).strftime('%H:%M') for k in klines_raw]
                            volumes_rec = [float(k[5]) for k in klines_raw]
                            
                            df_rec = pd.DataFrame({'close': klines_rec})
                            sma20 = df_rec['close'].rolling(window=20).mean()
                            std20 = df_rec['close'].rolling(window=20).std()
                            bb_upper = (sma20 + 2 * std20).where(pd.notnull(sma20), None).tolist()
                            bb_lower = (sma20 - 2 * std20).where(pd.notnull(sma20), None).tolist()
                            ema200 = df_rec['close'].ewm(span=min(200, len(klines_rec)), adjust=False).mean().where(pd.notnull(df_rec['close']), None).tolist()

                            shared_futures_market_data['dates'] = dates_rec
                            shared_futures_market_data['klines'] = [[float(k[1]), float(k[4]), float(k[3]), float(k[2])] for k in klines_raw]
                            shared_futures_market_data['bb_upper'] = bb_upper[-100:]
                            shared_futures_market_data['bb_lower'] = bb_lower[-100:]
                            shared_futures_market_data['ema200'] = ema200[-100:]
                            shared_futures_market_data['volumes'] = volumes_rec
                    except Exception as k_err:
                        log(f"⚠️ Aviso ao carregar klines no State Recovery Futuros: {k_err}")

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
                from config.settings import TRADING_CONFIG
                interval = TRADING_CONFIG['interval']
                klines = await get_futures_klines(client, symbol, interval=interval, limit=100)
                if not klines or len(klines) < 20:
                    continue
                    
                import pandas as pd
                import datetime as dt_module
                
                closes = [float(k[4]) for k in klines]
                dates_rec = [dt_module.datetime.fromtimestamp(float(k[0])/1000).strftime('%H:%M') for k in klines]
                volumes_rec = [float(k[5]) for k in klines]
                
                df_rec = pd.DataFrame({'close': closes})
                sma20 = df_rec['close'].rolling(window=20).mean()
                std20 = df_rec['close'].rolling(window=20).std()
                bb_upper = (sma20 + 2 * std20).where(pd.notnull(sma20), None).tolist()
                bb_lower = (sma20 - 2 * std20).where(pd.notnull(sma20), None).tolist()
                ema200 = df_rec['close'].ewm(span=min(200, len(closes)), adjust=False).mean().where(pd.notnull(df_rec['close']), None).tolist()

                shared_futures_market_data['dates'] = dates_rec
                shared_futures_market_data['klines'] = [[float(k[1]), float(k[4]), float(k[3]), float(k[2])] for k in klines]
                shared_futures_market_data['bb_upper'] = bb_upper[-100:]
                shared_futures_market_data['bb_lower'] = bb_lower[-100:]
                shared_futures_market_data['ema200'] = ema200[-100:]
                shared_futures_market_data['volumes'] = volumes_rec
                
                bot_futures_status_data['target_asset'] = symbol

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
                        
                        # Conditional Orders (10% ROI = 0.5% variação com 20x de alavancagem)
                        if direction == 'LONG':
                            tp_price = entry_price * 1.005
                            sl_price = entry_price * 0.995
                            side_exit = 'SELL'
                        else:
                            tp_price = entry_price * 0.995
                            sl_price = entry_price * 1.005
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
