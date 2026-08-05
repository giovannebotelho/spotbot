import asyncio
import datetime as dt_module
from config.settings import TELEGRAM_CONFIG, TRADING_CONFIG, TIMEZONE
from services.binance_client import get_futures_order_details, cancel_futures_order, get_bnb_price
from core.post_trade import create_data_row, save_to_csv
from services.telegram_notifier import send_telegram_message
from services.gemini_ai import generate_post_trade_synthesis
from utils.formatting import format_price

async def monitor_futures_lifecycle(
    client, bsm, symbol, position_side, entry_price, executed_qty, 
    tp_order_id, sl_order_id, tp_price, sl_price, db, 
    active_futures_positions, bot_futures_status_data, log=print, status=print
):
    """
    Monitora uma posição de futuros aberta.
    position_side: 'LONG' ou 'SHORT'
    """
    log(f"🛡️ Iniciando monitoramento de Futuros para {symbol} ({position_side})")
    
    use_ws_monitoring = True
    highest_price = entry_price
    lowest_price = entry_price
    
    async def check_and_handle_closure():
        try:
            pos_info = await client.futures_position_information(symbol=symbol)
            is_manually_closed = pos_info and float(pos_info[0]['positionAmt']) == 0.0
            
            tp_details = await get_futures_order_details(client, symbol, tp_order_id)
            sl_details = await get_futures_order_details(client, symbol, sl_order_id)
            
            if tp_details['status'] in ['FILLED'] or sl_details['status'] in ['FILLED'] or is_manually_closed:
                if is_manually_closed and tp_details['status'] != 'FILLED' and sl_details['status'] != 'FILLED':
                    log(f"⚠️ Posição de {symbol} foi fechada manualmente ou externamente!")
                    await close_futures_position(client, symbol, 'SELL' if position_side == 'LONG' else 'BUY', 0, tp_order_id, sl_order_id, log)
                    exit_price = float(bot_futures_status_data.get('price', entry_price))
                else:
                    log(f"🎯 Posição de Futuros fechada! TP: {tp_details['status']}, SL: {sl_details['status']}")
                    
                    if tp_details['status'] == 'FILLED':
                        await close_futures_position(client, symbol, 'SELL' if position_side == 'LONG' else 'BUY', 0, None, sl_order_id, log)
                        exit_price = float(tp_details.get('avgPrice', tp_details.get('actualPrice', 0))) if float(tp_details.get('avgPrice', tp_details.get('actualPrice', 0))) > 0 else float(tp_details.get('stopPrice', tp_details.get('triggerPrice', 0)))
                    else:
                        await close_futures_position(client, symbol, 'SELL' if position_side == 'LONG' else 'BUY', 0, tp_order_id, None, log)
                        exit_price = float(sl_details.get('avgPrice', sl_details.get('actualPrice', 0))) if float(sl_details.get('avgPrice', sl_details.get('actualPrice', 0))) > 0 else float(sl_details.get('stopPrice', sl_details.get('triggerPrice', 0)))

                realized_pnl = None
                try:
                    # Tenta puxar o PnL exato e preço de saída direto da Binance
                    recent_trades = await client.futures_account_trades(symbol=symbol, limit=10)
                    if recent_trades:
                        # Pega as últimas execuções que não têm realizedPnl zero
                        closing_trades = [t for t in recent_trades if float(t.get('realizedPnl', 0)) != 0]
                        if closing_trades:
                            realized_pnl = sum(float(t['realizedPnl']) for t in closing_trades[-3:])
                            # Opcional: ajustar o exit_price com base na última trade
                            exit_price = float(closing_trades[-1]['price'])
                except Exception as api_err:
                    log(f"Aviso ao buscar PnL real de {symbol}: {api_err}")

                await register_futures_trade(client, db, symbol, position_side, entry_price, exit_price, executed_qty, log, realized_pnl)
                return True
        except Exception as e:
            log(f"⚠️ Erro na verificação de posição: {e}")
        return False
    
    
    async def closure_checker():
        while True:
            await asyncio.sleep(5)
            if await check_and_handle_closure():
                break

    checker_task = asyncio.create_task(closure_checker())
    
    async def ws_loop():
        try:
            # WebSocket connection para klines/trades (Futuros)
            async with bsm.aggtrade_futures_socket(symbol=symbol.lower()) as ts:
                while True:
                    try:
                        msg = await asyncio.wait_for(ts.recv(), timeout=10.0)
                        
                        if 'p' in msg:
                            cur_price = float(msg['p'])
                            
                            if position_side == 'LONG':
                                if cur_price > highest_price:
                                    highest_price = cur_price
                            else:
                                if cur_price < lowest_price:
                                    lowest_price = cur_price
                                    
                            bot_futures_status_data['price'] = cur_price
                            
                            # Lógica de Trailing Stop Lock para Futuros
                            if position_side == 'LONG':
                                tp_distance = tp_price - entry_price
                                trigger_price = entry_price + (tp_distance * 0.75)
                                if highest_price >= trigger_price and cur_price < highest_price * 0.998:
                                    log(f"🔒 Trailing Lock Acionado (LONG)! Vendendo a mercado...")
                                    await close_futures_position(client, symbol, 'SELL', executed_qty, tp_order_id, sl_order_id, log)
                                    await register_futures_trade(client, db, symbol, 'LONG', entry_price, cur_price, executed_qty, log)
                                    checker_task.cancel()
                                    break
                            else:
                                # SHORT
                                tp_distance = entry_price - tp_price
                                trigger_price = entry_price - (tp_distance * 0.75)
                                if lowest_price <= trigger_price and cur_price > lowest_price * 1.002:
                                    log(f"🔒 Trailing Lock Acionado (SHORT)! Comprando a mercado...")
                                    await close_futures_position(client, symbol, 'BUY', executed_qty, tp_order_id, sl_order_id, log)
                                    await register_futures_trade(client, db, symbol, 'SHORT', entry_price, cur_price, executed_qty, log)
                                    checker_task.cancel()
                                    break
                    except asyncio.TimeoutError:
                        continue # Apenas continua esperando, sem falhar
        except Exception as ws_err:
            log(f"⚠️ WS Instável em Futuros para {symbol} ({ws_err}). Somente REST Polling ativo.")

    ws_task = asyncio.create_task(ws_loop())
    
    # Aguarda o checker finalizar (indica que a posição foi fechada por TP, SL ou manual)
    try:
        await checker_task
    except asyncio.CancelledError:
        pass
        
    ws_task.cancel()

    # Cleanup Global
    active_futures_positions.pop(symbol, None)
    bot_futures_status_data['active_symbols'] = list(active_futures_positions.keys())
    return

async def close_futures_position(client, symbol, side, qty, tp_order, sl_order, log):
    """Fecha a posição a mercado e cancela ordens orfãs."""
    if tp_order:
        try:
            await cancel_futures_order(client, symbol, tp_order)
        except: pass
    if sl_order:
        try:
            await cancel_futures_order(client, symbol, sl_order)
        except: pass
    
    if qty > 0:
        try:
            await client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=qty, reduceOnly='true')
        except Exception as e:
            if "ReduceOnly" not in str(e) and "-2022" not in str(e):
                log(f"⚠️ Erro ao fechar posição a mercado: {e}")

async def register_futures_trade(client, db, symbol, direction, entry, exit, qty, log, realized_pnl=None):
    """Registra o trade no DB e avisa no Telegram."""
    if realized_pnl is not None:
        gross_pnl = realized_pnl
    else:
        gross_pnl = (exit - entry) * qty if direction == 'LONG' else (entry - exit) * qty
        
    log(f"📈 Trade Futuros Concluído ({direction}): PnL Bruto = ${gross_pnl:.2f}")
    
    if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
        emoji = "🟢" if gross_pnl > 0 else "🔴"
        await send_telegram_message(
            TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
            f"{emoji} <b>TRADE FUTUROS FINALIZADO</b>\n\n"
            f"🪙 Par: <b>{symbol}</b> ({direction})\n"
            f"📥 Entrada: {format_price(entry)}\n"
            f"📤 Saída: {format_price(exit)}\n"
            f"💰 PnL Bruto: <b>${gross_pnl:.2f}</b>"
        )
    
    if db:
        data = {
            "Símbolo": symbol,
            "Preço de Compra": entry,
            "Quantidade de Moeda": qty,
            "Meta de Lucro OCO": exit,
            "Data/Hora da Compra": dt_module.datetime.now(TIMEZONE).strftime("%d/%m/%Y at %H:%M:%S"),
            "Data/Hora OCO": dt_module.datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M:%S"),
            "Resultado da Ordem OCO": "profit" if gross_pnl > 0 else "loss",
            "Resultado Parcial da Transação": gross_pnl,
            "Resultado Parcial da Transação Líquido": gross_pnl * 0.96,
            "Resultado Total Bruto": gross_pnl,
            "Resultado Total Liquido": gross_pnl * 0.96, # desconto de taxa ficticio
            "market_type": "FUTURES",
            "direction": direction,
            "margin_type": "ISOLATED",
            "leverage": 20
        }
        db.add_trade(data)
