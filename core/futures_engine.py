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
                    
                    qty = notional / cur_price
                    # Precisão fake (simplificação), na real precisa buscar do exchange_info
                    qty = round(qty, 3) 
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
                            
                        # Precisão de preço fake (simplificação)
                        tp_price = round(tp_price, 4)
                        sl_price = round(sl_price, 4)
                        
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
                            tp_order['orderId'], sl_order['orderId'], tp_price, sl_price, db,
                            active_futures_positions, bot_futures_status_data, log, status
                        ))
                        
                    except Exception as e:
                        log(f"❌ Erro ao abrir posição {direction} em {symbol}: {e}")
                        
            await asyncio.sleep(5)
            
        except Exception as e:
            log(f"⚠️ Erro no Motor de Futuros: {e}")
            await asyncio.sleep(10)
