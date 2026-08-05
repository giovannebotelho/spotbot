import asyncio
import datetime as dt_module
from config.settings import TELEGRAM_CONFIG, TRADING_CONFIG, TIMEZONE
from services.binance_client import get_futures_order_details, get_bnb_price
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
    
    try:
        # WebSocket connection para klines/trades ou user data
        async with bsm.trade_socket(symbol=symbol.lower()) as ts:
            async for msg in ts:
                if 'p' in msg:
                    cur_price = float(msg['p'])
                    
                    if position_side == 'LONG':
                        if cur_price > highest_price:
                            highest_price = cur_price
                    else:
                        if cur_price < lowest_price:
                            lowest_price = cur_price
                            
                    bot_futures_status_data['price'] = cur_price
                    
                    # Verificação assíncrona periódica do status das ordens condicionais (REST Polling Híbrido)
                    # No futuro, podemos usar o User Data Stream para ser 100% WS
                    
                    # Como WS de trades é muito rápido, podemos ter um gargalo. 
                    # Vamos fazer um break condicional se as ordens sumiram (preenchidas)
                    
                    # Para simplificar na v1, deixaremos o polling principal resolver o fechamento, 
                    # e o WS apenas para atualizar o preço em tempo real e o Trailing Stop Lock.
                    
                    # Lógica de Trailing Stop Lock para Futuros
                    if position_side == 'LONG':
                        tp_distance = tp_price - entry_price
                        trigger_price = entry_price + (tp_distance * 0.75)
                        if highest_price >= trigger_price and cur_price < highest_price * 0.998:
                            log(f"🔒 Trailing Lock Acionado (LONG)! Vendendo a mercado...")
                            await close_futures_position(client, symbol, 'SELL', executed_qty, tp_order_id, sl_order_id, log)
                            await register_futures_trade(client, db, symbol, 'LONG', entry_price, cur_price, executed_qty, log)
                            break
                    else:
                        # SHORT
                        tp_distance = entry_price - tp_price
                        trigger_price = entry_price - (tp_distance * 0.75)
                        if lowest_price <= trigger_price and cur_price > lowest_price * 1.002:
                            log(f"🔒 Trailing Lock Acionado (SHORT)! Comprando a mercado...")
                            await close_futures_position(client, symbol, 'BUY', executed_qty, tp_order_id, sl_order_id, log)
                            await register_futures_trade(client, db, symbol, 'SHORT', entry_price, cur_price, executed_qty, log)
                            break

    except Exception as ws_err:
        use_ws_monitoring = False
        log(f"⚠️ WS Instável em Futuros ({ws_err}). Alternando para REST Polling.")

    if not use_ws_monitoring:
        while True:
            await asyncio.sleep(3)
            try:
                tp_details = await get_futures_order_details(client, symbol, tp_order_id)
                sl_details = await get_futures_order_details(client, symbol, sl_order_id)
                
                if tp_details['status'] in ['FILLED', 'CANCELED'] or sl_details['status'] in ['FILLED', 'CANCELED']:
                    log(f"🎯 Posição de Futuros fechada! TP: {tp_details['status']}, SL: {sl_details['status']}")
                    
                    # Cancel the other orphan order
                    if tp_details['status'] == 'FILLED':
                        try:
                            await client.futures_cancel_order(symbol=symbol, orderId=sl_order_id)
                        except: pass
                        exit_price = float(tp_details['avgPrice']) if float(tp_details.get('avgPrice', 0)) > 0 else float(tp_details['stopPrice'])
                    else:
                        try:
                            await client.futures_cancel_order(symbol=symbol, orderId=tp_order_id)
                        except: pass
                        exit_price = float(sl_details['avgPrice']) if float(sl_details.get('avgPrice', 0)) > 0 else float(sl_details['stopPrice'])

                    await register_futures_trade(client, db, symbol, position_side, entry_price, exit_price, executed_qty, log)
                    break
                    
            except Exception as poll_err:
                log(f"⚠️ Polling Futuros Erro: {poll_err}")

    # Cleanup Global
    active_futures_positions.pop(symbol, None)
    bot_futures_status_data['active_symbols'] = list(active_futures_positions.keys())
    return

async def close_futures_position(client, symbol, side, qty, tp_order, sl_order, log):
    """Fecha a posição a mercado e cancela ordens orfãs."""
    try:
        await client.futures_cancel_order(symbol=symbol, orderId=tp_order)
    except: pass
    try:
        await client.futures_cancel_order(symbol=symbol, orderId=sl_order)
    except: pass
    
    try:
        await client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=qty, reduceOnly='true')
    except Exception as e:
        log(f"⚠️ Erro ao fechar posição a mercado: {e}")

async def register_futures_trade(client, db, symbol, direction, entry, exit, qty, log):
    """Registra o trade no DB e avisa no Telegram."""
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
        # Simplificação para inserir na mesma tabela
        data = {
            "Símbolo": symbol,
            "Preço de Compra": entry,
            "Quantidade de Moeda": qty,
            "Meta de Lucro OCO": exit,
            "Data/Hora da Compra": dt_module.datetime.now(TIMEZONE).strftime("%d/%m/%Y at %H:%M:%S"),
            "Resultado Total Bruto": gross_pnl,
            "Resultado Total Liquido": gross_pnl * 0.96, # desconto de taxa ficticio, ideal calcular real
            "market_type": "FUTURES",
            "direction": direction,
            "margin_type": "ISOLATED",
            "leverage": 20 # placeholder, pass this properly later
        }
        try:
            db.add_trade(data)
        except Exception as e:
            log(f"Erro ao salvar BD Futuros: {e}")
