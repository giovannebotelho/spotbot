import asyncio
import os
import time
import math
import pandas as pd
import datetime as dt_module
from datetime import datetime, timedelta
from binance import BinanceSocketManager
from binance import AsyncClient as BinanceAsyncClient
from binance.exceptions import BinanceAPIException

from config.settings import API_KEYS, TELEGRAM_CONFIG, TRADING_CONFIG, RSI_CONFIG, TRAILING_STOP_CONFIG, SCANNER_CONFIG, TOP_20_SYMBOLS, MAX_CONCURRENT_POSITIONS, RESERVE_FRACTION_FOR_DCA
from services.binance_client import extract_closes, extract_volumes, get_usdt_balance, get_order_details, get_klines, get_bnb_price, get_multi_klines
from core.indicators import (
    calculate_rsi, calculate_macd, calculate_bollinger_bands, check_trend, check_candle_patterns,
    calculate_vwap, get_candle_details, calculate_ema, is_market_downward, calculate_relative_strength_rank,
    calculate_fibonacci_supports
)
from core.decision import (
    should_place_order, should_buy, should_sell, adjust_and_place_oco_order, get_min_notional,
    adjust_price_to_tick_size, get_precision, calculate_dynamic_position_slots, place_safe_oco_sell_order,
    calculate_kelly_position_size
)
from core.post_trade import process_order_details, log_and_notify_results, create_data_row, save_to_csv
from services.telegram_notifier import send_telegram_message, send_telegram_document, TelegramBot
from services.news_scanner import fetch_crypto_news
from services.gemini_ai import analyze_news_sentiment_with_gemini, generate_post_trade_synthesis, auto_tune_risk_profile
from services.database import DatabaseManager
from services.pdf_generator import generate_weekly_telemetry_pdf
from utils.formatting import remove_ansi_codes

environment = os.getenv("BOT_ENVIRONMENT", "mainnet")
if environment == "mainnet":
    api_key = API_KEYS.get('mainnet', {}).get('key', '')
    api_secret = API_KEYS.get('mainnet', {}).get('secret', '')
elif environment == "testnet":
    api_key = API_KEYS.get('testnet_spot', {}).get('key', '')
    api_secret = API_KEYS.get('testnet_spot', {}).get('secret', '')
else:
    api_key = API_KEYS.get('mainnet', {}).get('key', '')
    api_secret = API_KEYS.get('mainnet', {}).get('secret', '')

bot_running = True
active_positions = {}

bot_status_data = {
    "rsi": 0, "price": 0, "symbol": "", "action": "Iniciando...", "trend": "N/A", "target_asset": "BTCUSDT",
    "active_symbols": [], "active_positions": active_positions
}
shared_market_data = {
    "klines": [], "dates": [], "bb_upper": [], "bb_lower": [], "bb_middle": [], "ema200": [], "volumes": [], "scanner_results": []
}

SHORT_PAUSE = 600
LONG_PAUSE = 3600
stop_loss_count = 0
last_stop_loss_time = None
block_active = False
pause_end_time = None
MAX_RESTARTS = 3
restart_attempts = 0
last_operation_time = None

async def sync_binance_time(client, log=print):
    try:
        res = await client.get_server_time()
        server_time = res['serverTime']
        local_time = int(time.time() * 1000)
        time_offset = server_time - local_time
        client.TIME_OFFSET = time_offset
        log(f"⏱️ Relógio sincronizado com a Binance! (Offset: {time_offset}ms)")
    except Exception as e:
        log(f"⚠️ Aviso ao sincronizar relógio com a Binance: {e}")

async def cancel_all_oco_orders(client, symbol):
    try:
        open_oco_orders = await client.get_open_oco_orders()
        for order_list in open_oco_orders:
            if order_list['symbol'] == symbol:
                order_list_id = order_list['orderListId']
                await client.cancel_order(symbol=symbol, orderListId=order_list_id)
                print(f"Ordem OCO ID {order_list_id} cancelada para {symbol}.")
    except Exception as e:
        print(f"Aviso ao cancelar ordens OCO: {e}")

async def check_stop_losses(current_time, log=print):
    global stop_loss_count, last_stop_loss_time, block_active, pause_end_time
    if block_active and current_time > pause_end_time:
        block_active = False
        pause_end_time = None

    if last_stop_loss_time and (current_time - last_stop_loss_time) < timedelta(seconds=900):
        if stop_loss_count > 1:
            log("🚨 Mais de 1 stop loss detectado em 15min. Pausando robô por 1 hora.\n")
            message = "🚨 Mais de 1 stop loss detectado em 15min. Pausando robô por 1 hora."
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))

            pause_end_time = current_time + timedelta(seconds=LONG_PAUSE)
            block_active = True
            stop_loss_count = 0
            last_stop_loss_time = current_time
            await asyncio.sleep(LONG_PAUSE)
            log("\n ✅ Voltando a operar após pausa de 1 hora.")
            return
    else:
        stop_loss_count = 0

    if stop_loss_count == 1:
        stop_loss_count += 1
        log("🚨 Stop loss detectado. Pausando por 10 minutos.")
        message = "🚨 Stop loss detectado. Pausando por 10 minutos."
        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        pause_end_time = current_time + timedelta(seconds=SHORT_PAUSE)
        last_stop_loss_time = current_time
        await asyncio.sleep(SHORT_PAUSE)

async def check_rsi_reset(symbol, log=print):
    global last_operation_time
    if last_operation_time and (dt_module.datetime.now() - last_operation_time) > timedelta(seconds=6*60*60):
        current_levels = [RSI_CONFIG['dynamic_low'][i] for i in range(6)]
        default_levels = [RSI_CONFIG['levels'][i] for i in range(6)]
        
        if current_levels != default_levels:
            for i in range(6):
                RSI_CONFIG['dynamic_low'][i] = RSI_CONFIG['levels'][i]
            log(f"\n⏳ Níveis de RSI resetados para {symbol} por inatividade.")
        last_operation_time = dt_module.datetime.now()

_cached_balances = {'bnb': 0.0, 'bnb_usdt': 0.0, 'usdt': 0.0}
_last_balance_time = 0
_balance_client = None

async def get_account_balances():
    global _cached_balances, _last_balance_time, _balance_client
    if not api_key or not api_secret:
        return {'bnb': 0.0, 'bnb_usdt': 0.0, 'usdt': 0.0}
    
    now = time.time()
    if now - _last_balance_time < 10.0 and _cached_balances['usdt'] > 0:
        return _cached_balances

    try:
        if _balance_client is None:
            _balance_client = await BinanceAsyncClient.create(api_key, api_secret)
            await sync_binance_time(_balance_client, log=lambda m: None)

        bnb_balance = await _balance_client.get_asset_balance(asset='BNB')
        bnb_balance_free = float(bnb_balance['free'])
        bnb_price_usdt = await get_bnb_price(_balance_client)
        bnb_balance_usdt = bnb_balance_free * bnb_price_usdt
        usdt_balance = await get_usdt_balance(_balance_client)

        _cached_balances = {
            'bnb': bnb_balance_free, 'bnb_usdt': bnb_balance_usdt, 'usdt': usdt_balance
        }
        _last_balance_time = now
        return _cached_balances
    except Exception as e:
        err_msg = str(e) if str(e).strip() else repr(e)
        print(f"⚠️ Aviso ao buscar saldos ({type(e).__name__}): {err_msg}")
        if _balance_client:
            try:
                await _balance_client.close_connection()
            except Exception:
                pass
            _balance_client = None
        return _cached_balances

async def monitor_oco_lifecycle(
    client, bsm, active_target_symbol, oco_order, limit_order_id, stop_order_id,
    price, executed_qty, order_val_usdt, lucro_alvo, stop_loss, target_symbol_info,
    tick_size, step_size, log, status, saldo_inicial_usdt, order_count, purchase_timestamp,
    executed_condition, rsi, vwap, candle_open, candle_high, candle_low, candle_close,
    candle_volume, variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100,
    ema200, candle_patterns, amplitude, macd_current, signal_line_current, lower_band,
    middle_band, upper_band, trend_is_up, gemini_response, db
):
    global stop_loss_count, last_stop_loss_time
    total_difference = 0
    total_difference_liquid = 0
    highest_price = price
    current_stop_loss = stop_loss
    partial_take_done = False
    dca_done = False

    active_positions[active_target_symbol] = {
        'tp': lucro_alvo,
        'sl': stop_loss,
        'entry': price,
        'qty': executed_qty,
        'val': order_val_usdt
    }
    bot_status_data['active_symbols'] = list(active_positions.keys())
    bot_status_data['target_asset'] = active_target_symbol
    bot_status_data['price'] = price
    bot_status_data['tp_price'] = lucro_alvo
    bot_status_data['sl_price'] = stop_loss
    bot_status_data['entry_price'] = price

    use_ws_monitoring = True
    try:
        async with bsm.user_socket() as um:
            while True:
                try:
                    msg = await asyncio.wait_for(um.recv(), timeout=5)
                except asyncio.TimeoutError:
                    try:
                        cur_price = float((await client.get_symbol_ticker(symbol=active_target_symbol))['price'])
                        status(f"⏳ Monitorando OCO ({active_target_symbol})... Preço: ${cur_price:.2f}")
                        
                        profit_pct = (cur_price - price) / price if price > 0 else 0

                        # FASE 1 (v5.0): Smart Recovery DCA em Suporte de Fibonacci para Flash Dumps
                        if not dca_done and not partial_take_done and cur_price < price * 0.988:
                            try:
                                klines_dca = await get_klines(client, active_target_symbol, '15m', 50)
                                fib_618, fib_786, _, _ = calculate_fibonacci_supports(klines_dca)
                                
                                if cur_price <= fib_618 * 1.002 or cur_price <= fib_786 * 1.002:
                                    usdt_avail = await get_usdt_balance(client)
                                    min_not = get_min_notional(target_symbol_info)
                                    dca_val_usdt = max(min_not, min(usdt_avail * 0.98, order_val_usdt * 0.5))
                                    
                                    if usdt_avail >= min_not and dca_val_usdt >= min_not:
                                        await client.cancel_order(symbol=active_target_symbol, orderListId=oco_order['orderListId'])
                                        dca_buy = await client.order_market_buy(symbol=active_target_symbol, quoteOrderQty=round(dca_val_usdt, 2))
                                        dca_qty = float(dca_buy['executedQty'])
                                        dca_price = float(dca_buy['fills'][0]['price'])
                                        
                                        total_qty = executed_qty + dca_qty
                                        new_pm = ((executed_qty * price) + (dca_qty * dca_price)) / total_qty
                                        
                                        log(f"🧪 \033[1;36mSmart Recovery DCA Executado\033[0m em \033[1;33m{active_target_symbol}\033[0m no Suporte de Fibonacci 61.8% (${dca_price:.4f})!")
                                        log(f"📉 Preço Médio ajustado de ${price:.4f} para \033[1;32m${new_pm:.4f}\033[0m! Re-posicionando TP/SL de recuperação...")
                                        
                                        prec_p = get_precision(tick_size)
                                        prec_q = get_precision(step_size)
                                        prec_qty_val = round(math.floor(total_qty / step_size) * step_size, prec_q)
                                        
                                        new_tp = adjust_price_to_tick_size(new_pm * 1.008, tick_size)
                                        new_sl = adjust_price_to_tick_size(new_pm * 0.985, tick_size)
                                        new_sl_limit = adjust_price_to_tick_size(new_sl * 0.999, tick_size)
                                        
                                        oco_order = await place_safe_oco_sell_order(
                                            client, active_target_symbol, prec_qty_val, new_tp, new_sl, new_sl_limit, prec_p, prec_q
                                        )
                                        limit_order_id = oco_order['orders'][1]['orderId']
                                        stop_order_id = oco_order['orders'][0]['orderId']
                                        
                                        price = new_pm
                                        executed_qty = prec_qty_val
                                        lucro_alvo = new_tp
                                        stop_loss = new_sl
                                        current_stop_loss = new_sl
                                        dca_done = True
                                        
                                        if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                                            asyncio.create_task(send_telegram_message(
                                                TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                                f"🧪 <b>Smart Recovery DCA Executado!</b>\n\n"
                                                f"🪙 Par: <b>{active_target_symbol}</b>\n"
                                                f"📉 Recompra efetuada no Suporte Fibonacci 61.8% (<b>${dca_price:.4f}</b>)\n"
                                                f"🎯 <b>Novo Preço Médio: ${new_pm:.4f}</b>\n"
                                                f"🛡️ Take Profit de recuperação ajustado para <b>${new_tp:.4f} (+0.8%)</b>!"
                                            ))
                            except Exception as e_dca:
                                log(f"Aviso no Smart Recovery DCA: {e_dca}")

                        if profit_pct >= 0.015 and not partial_take_done:
                            try:
                                prec_qty = get_precision(step_size)
                                half_qty = round(math.floor((executed_qty * 0.5) / step_size) * step_size, prec_qty)
                                rem_qty = round(executed_qty - half_qty, prec_qty)

                                if half_qty > 0 and rem_qty > 0:
                                    await client.cancel_order(symbol=active_target_symbol, orderListId=oco_order['orderListId'])
                                    venda_parcial = await client.order_market_sell(symbol=active_target_symbol, quantity=half_qty)
                                    p_price = float(venda_parcial['fills'][0]['price'])
                                    
                                    log(f"💰 Scalp Locking: Venda parcial de 50% executada em {active_target_symbol} a ${p_price:.4f}! (+{profit_pct*100:.2f}%)")
                                    
                                    be_stop = adjust_price_to_tick_size(price, tick_size)
                                    be_limit = adjust_price_to_tick_size(price * 0.999, tick_size)
                                    prec_p = get_precision(tick_size)
                                    prec_q = get_precision(step_size)
                                    
                                    oco_order = await place_safe_oco_sell_order(
                                        client, active_target_symbol, rem_qty, lucro_alvo, be_stop, be_limit, prec_p, prec_q
                                    )
                                    limit_order_id = oco_order['orders'][1]['orderId']
                                    stop_order_id = oco_order['orders'][0]['orderId']
                                    current_stop_loss = be_stop
                                    partial_take_done = True

                                    if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                                        asyncio.create_task(send_telegram_message(
                                            TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                            f"💰 <b>Scalp Locking (+1.5% Lucro Garantido)!</b>\n\n"
                                            f"🪙 Par: <b>{active_target_symbol}</b>\n"
                                            f"🎯 50% da posição vendida a <b>${p_price:.2f}</b>!\n"
                                            f"🛡️ 50% restante protegido no <b>Breakeven (Zero a Zero em ${price:.2f})</b>!"
                                        ))
                            except Exception as e_partial:
                                log(f"Aviso ao executar Scalp Locking: {e_partial}")

                        if TRAILING_STOP_CONFIG['enabled'] and cur_price > highest_price:
                            highest_price = cur_price
                            if highest_price > price * (1 + TRAILING_STOP_CONFIG['activation_percent']):
                                new_stop = adjust_price_to_tick_size(highest_price * (1 - TRAILING_STOP_CONFIG['callback_percent']), tick_size)
                                if new_stop > current_stop_loss * 1.001:
                                    log(f"🔄 Trailing Stop acionado! Movendo stop para ${new_stop:.4f}")
                                    await client.cancel_order(symbol=active_target_symbol, orderListId=oco_order['orderListId'])
                                    new_stop_limit = adjust_price_to_tick_size(new_stop * 0.999, tick_size)
                                    prec_p = get_precision(tick_size)
                                    prec_q = get_precision(step_size)
                                    qty_to_sell = executed_qty if not partial_take_done else rem_qty
                                    
                                    oco_order = await place_safe_oco_sell_order(
                                        client, active_target_symbol, qty_to_sell, lucro_alvo, new_stop, new_stop_limit, prec_p, prec_q
                                    )
                                    limit_order_id = oco_order['orders'][1]['orderId']
                                    stop_order_id = oco_order['orders'][0]['orderId']
                                    current_stop_loss = new_stop
                    except Exception:
                        pass
                    continue

                if msg.get('e') == 'listStatus' and msg.get('s') == active_target_symbol and msg.get('g') == oco_order['orderListId']:
                    if 'ALL_DONE' in msg.get('l'):
                        limit_details = await get_order_details(client, active_target_symbol, limit_order_id)
                        stop_details = await get_order_details(client, active_target_symbol, stop_order_id)

                        active_target_symbol, order_result, trade_result, novo_saldo_usdt, oco_timestamp, fee, trade_result_liquid = await process_order_details(
                            active_target_symbol, client, limit_details, stop_details, price, executed_qty, order_val_usdt
                        )

                        total_difference += trade_result
                        total_difference_liquid += trade_result_liquid
                        
                        bnb_balance_free = float((await client.get_asset_balance(asset='BNB'))['free'])
                        bnb_price = await get_bnb_price(client)
                        
                        if order_result:
                            log_and_notify_results(order_result, active_target_symbol, trade_result, total_difference, oco_timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_free * bnb_price, log=log)
                            
                            # FASE 3: Síntese Pós-Trade via IA Gemini
                            try:
                                cur_exit_price = lucro_alvo if (order_result and "TAKE" in str(order_result).upper()) else stop_loss
                                post_synthesis = generate_post_trade_synthesis(active_target_symbol, order_result, price, cur_exit_price, trade_result_liquid)
                                log(f"🧠 \033[1;36mAnálise Pós-Trade (IA Gemini)\033[0m: {post_synthesis}")
                                if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                                    asyncio.create_task(send_telegram_message(
                                        TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                        f"🧠 <b>ANÁLISE PÓS-TRADE (IA GEMINI)</b>\n\n"
                                        f"🪙 Par: <b>{active_target_symbol}</b>\n"
                                        f"📝 Resumo IA: <i>{post_synthesis}</i>"
                                    ))
                            except Exception as ai_post_err:
                                log(f"⚠️ Aviso na análise pós-trade IA Gemini: {ai_post_err}")
                            data_row = create_data_row(
                                order_count, saldo_inicial_usdt, novo_saldo_usdt, active_target_symbol,
                                executed_qty, price, purchase_timestamp, lucro_alvo, stop_loss, stop_loss,
                                order_result, oco_timestamp, trade_result, total_difference, novo_saldo_usdt,
                                rsi, executed_condition, vwap, candle_open, candle_high, candle_low, candle_close, candle_volume, 
                                variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, candle_patterns, TRADING_CONFIG['volume_avg'], 
                                amplitude, macd_current, signal_line_current, lower_band, middle_band, upper_band, trend_is_up, fee, trade_result_liquid,
                                total_difference_liquid, gemini_response, bnb_balance_free * bnb_price
                            )
                            save_to_csv(data_row)
                            if db:
                                try:
                                    db.add_trade(data_row)
                                except Exception as db_save_err:
                                    log(f"⚠️ Erro ao registrar trade no banco de dados: {db_save_err}")
                            
                            if stop_details['status'] == 'FILLED':
                                stop_loss_count += 1
                                last_stop_loss_time = dt_module.datetime.now()
                                await check_stop_losses(last_stop_loss_time, log=log)
                            else:
                                stop_loss_count = 0
                            active_positions.pop(active_target_symbol, None)
                            bot_status_data['active_symbols'] = list(active_positions.keys())
                            if bot_status_data.get('target_asset') == active_target_symbol:
                                bot_status_data['tp_price'] = 0.0
                                bot_status_data['sl_price'] = 0.0
                                bot_status_data['entry_price'] = 0.0
                            return
    except Exception as ws_err:
        use_ws_monitoring = False
        log(f"⚠️ Conexão WebSocket instável ({ws_err}). Alternando automaticamente para monitoramento de ordem por REST Polling...")

    # Fallback REST Polling se o WebSocket instabilizar
    if not use_ws_monitoring:
        while True:
            await asyncio.sleep(3)
            try:
                limit_details = await get_order_details(client, active_target_symbol, limit_order_id)
                stop_details = await get_order_details(client, active_target_symbol, stop_order_id)

                if limit_details['status'] in ['FILLED', 'CANCELED'] or stop_details['status'] in ['FILLED', 'CANCELED']:
                    active_target_symbol, order_result, trade_result, novo_saldo_usdt, oco_timestamp, fee, trade_result_liquid = await process_order_details(
                        active_target_symbol, client, limit_details, stop_details, price, executed_qty, order_val_usdt
                    )

                    total_difference += trade_result
                    total_difference_liquid += trade_result_liquid
                    
                    bnb_balance_free = float((await client.get_asset_balance(asset='BNB'))['free'])
                    bnb_price = await get_bnb_price(client)
                    
                    if order_result:
                        log_and_notify_results(order_result, active_target_symbol, trade_result, total_difference, oco_timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_free * bnb_price, log=log)
                        data_row = create_data_row(
                            order_count, saldo_inicial_usdt, novo_saldo_usdt, active_target_symbol,
                            executed_qty, price, purchase_timestamp, lucro_alvo, stop_loss, stop_loss,
                            order_result, oco_timestamp, trade_result, total_difference, novo_saldo_usdt,
                            rsi, executed_condition, vwap, candle_open, candle_high, candle_low, candle_close, candle_volume, 
                            variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, candle_patterns, TRADING_CONFIG['volume_avg'], 
                            amplitude, macd_current, signal_line_current, lower_band, middle_band, upper_band, trend_is_up, fee, trade_result_liquid,
                            total_difference_liquid, gemini_response, bnb_balance_free * bnb_price
                        )
                        save_to_csv(data_row)
                        if db:
                            try:
                                db.add_trade(data_row)
                            except Exception as db_save_err:
                                log(f"⚠️ Erro ao registrar trade no banco de dados: {db_save_err}")
                        
                        if stop_details['status'] == 'FILLED':
                            stop_loss_count += 1
                            last_stop_loss_time = dt_module.datetime.now()
                            await check_stop_losses(last_stop_loss_time, log=log)
                        else:
                            stop_loss_count = 0
                        active_positions.pop(active_target_symbol, None)
                        bot_status_data['active_symbols'] = list(active_positions.keys())
                        if bot_status_data.get('target_asset') == active_target_symbol:
                            bot_status_data['tp_price'] = 0.0
                            bot_status_data['sl_price'] = 0.0
                            bot_status_data['entry_price'] = 0.0
                        return
            except Exception as poll_err:
                status(f"⚠️ Polling de Ordem: {poll_err}")

async def panic_sell_position(symbol, client_instance=None):
    """
    FASE 1 (v6.0): Panic Sell / Encerramento a Mercado de Posição Ativa.
    Cancela a ordem OCO na Binance, executa venda a mercado imediatamente,
    calcula o PnL final e grava o trade no PostgreSQL.
    Funciona inclusive para posições recuperadas via State Recovery!
    """
    global active_positions, bot_status_data
    symbol = symbol.strip().upper()
    log_msg = f"🚨 \033[1;31mPANIC SELL\033[0m: Iniciando encerramento de emergência para {symbol}..."
    print(log_msg)
    
    cli = client_instance or globals().get('client')
    if not cli:
        try:
            cli = await BinanceAsyncClient.create(api_key, api_secret)
            await sync_binance_time(cli, log=lambda m: None)
        except Exception as e:
            return False, f"Erro ao conectar com a Binance: {e}"

    try:
        # 1. Cancela ordens OCO abertas para o simbolo
        open_ocos = await cli.get_open_oco_orders()
        for oco in open_ocos:
            if oco['symbol'] == symbol:
                try:
                    await cli.cancel_order(symbol=symbol, orderListId=oco['orderListId'])
                except Exception as c_err:
                    print(f"⚠️ Aviso ao cancelar OCO de {symbol}: {c_err}")

        # 2. Obtem quantidade livre e vende a mercado
        asset_name = symbol.replace("USDT", "")
        bal = await cli.get_asset_balance(asset=asset_name)
        free_qty = float(bal['free']) if bal else 0.0

        info = await cli.get_symbol_info(symbol)
        step_size = float(next(f for f in info['filters'] if f['filterType'] == 'LOT_SIZE')['stepSize'])
        precision_qty = get_precision(step_size)
        sell_qty = round(math.floor(free_qty / step_size) * step_size, precision_qty)

        if sell_qty <= 0:
            active_positions.pop(symbol, None)
            bot_status_data['active_symbols'] = list(active_positions.keys())
            return False, f"Saldo insuficiente de {asset_name} para efetuar venda a mercado."

        sell_order = await cli.order_market_sell(symbol=symbol, quantity=sell_qty)
        executed_qty = float(sell_order.get('executedQty', sell_qty))
        sell_price = float(sell_order['fills'][0]['price']) if sell_order.get('fills') else float((await cli.get_symbol_ticker(symbol=symbol))['price'])

        pos_info = active_positions.get(symbol, {})
        entry_price = pos_info.get('entry', sell_price)
        trade_result = (sell_price - entry_price) * executed_qty
        trade_result_liquid = trade_result * 0.999 # Desconto de taxa estimado

        timestamp = dt_module.datetime.now().strftime("%d/%m/%Y at %H:%M:%S")

        # 3. Salva no banco de dados PostgreSQL/SQLite
        db_mgr = DatabaseManager()
        usdt_bal = await get_usdt_balance(cli)
        data_row = create_data_row(
            1, usdt_bal, usdt_bal, symbol, executed_qty, entry_price, timestamp,
            pos_info.get('tp', 0.0), pos_info.get('sl', 0.0), pos_info.get('sl', 0.0),
            "PANIC SELL (Encerramento Manual)", timestamp, trade_result, trade_result, usdt_bal,
            0, "Panic Sell executado via Dashboard", 0, sell_price, sell_price, sell_price, sell_price, 0,
            0, 0, 0, 0, 0, 0, 0, 0, [], 0, 0, 0, 0, 0, 0, True, 0.001, trade_result_liquid,
            trade_result_liquid, "Encerramento manual a mercado efetuado pelo usuário", 0
        )
        save_to_csv(data_row)
        try:
            db_mgr.add_trade(data_row)
        except Exception as db_err:
            print(f"⚠️ Erro ao registrar Panic Sell no banco: {db_err}")

        # 4. Remove de active_positions
        active_positions.pop(symbol, None)
        bot_status_data['active_symbols'] = list(active_positions.keys())
        if bot_status_data.get('target_asset') == symbol:
            bot_status_data['tp_price'] = 0.0
            bot_status_data['sl_price'] = 0.0
            bot_status_data['entry_price'] = 0.0

        if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
            asyncio.create_task(send_telegram_message(
                TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                f"🚨 <b>PANIC SELL EXECUTADO!</b>\n\n"
                f"🪙 Par: <b>{symbol}</b>\n"
                f"💵 Preço de Venda: <b>${sell_price:.4f}</b>\n"
                f"📊 PnL: <b>${trade_result_liquid:+.2f} USDT</b>"
            ))

        return True, f"Panic Sell de {symbol} executado a mercado com sucesso por ${sell_price:.4f}!"
    except Exception as err:
        return False, f"Falha no Panic Sell de {symbol}: {err}"

async def run_bot(log_callback=None, investment_amount=None, selected_symbol=None, status_callback=None):
    global restart_attempts, bot_running, last_operation_time, stop_loss_count, last_stop_loss_time
    bot_running = True

    def log(msg, end='\n', flush=False):
        print(msg, end=end, flush=flush)
        if log_callback: log_callback(msg)

    def status(msg):
        if status_callback: status_callback(msg)
        bot_status_data['action'] = remove_ansi_codes(msg)

    if not api_key or not api_secret:
        log("⚠️ ATENÇÃO: As chaves da API Binance não estão preenchidas no .env.")
        status("⚠️ Chaves API ausentes no .env")
        return

    db = DatabaseManager()

    async def handle_telegram_command(command):
        global bot_running
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()

        if cmd == '/start':
            return "🤖 <b>SpotBot Pro está ativo e monitorando o mercado!</b>"
        
        elif cmd == '/stop':
            bot_running = False
            return "🛑 <b>Comando recebido. Parando o bot com segurança...</b>"

        elif cmd in ['/cancel', '/abort', '/cancelar']:
            bot_running = False
            return "🚨 <b>INTERRUPÇÃO DE EMERGÊNCIA (CANCEL/CTRL+C)! Operações e conexões paralisadas imediatamente.</b>"
        
        elif cmd == '/status':
            target_asset = bot_status_data.get('target_asset', 'BTCUSDT')
            mtf_sc = bot_status_data.get('mtf_score', 80)
            return (
                f"⚡ <b>STATUS DO SPOTBOT PRO v4.0 (QUANT)</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Modo</b>: {bot_status_data['symbol']}\n"
                f"🪙 <b>Foco Atual</b>: <b>{target_asset}</b>\n"
                f"💵 <b>Preço</b>: <b>${bot_status_data['price']:.2f}</b>\n"
                f"📊 <b>RSI</b>: <b>{bot_status_data['rsi']:.1f}</b>\n"
                f"📐 <b>Confluência MTF (4H+1H+15M)</b>: <b>{mtf_sc}%</b> 🟢\n"
                f"📈 <b>Tendência 4h</b>: <b>{bot_status_data['trend']}</b>\n"
                f"⚡ <b>Estado</b>: <i>{bot_status_data['action']}</i>"
            )
        
        elif cmd == '/saldo':
            c = None
            try:
                c = await BinanceAsyncClient.create(api_key, api_secret)
                await sync_binance_time(c, log=lambda m: None)
                usdt = await get_usdt_balance(c)
                bnb = await c.get_asset_balance(asset='BNB')
                bnb_free = float(bnb['free'])
                bnb_price = await get_bnb_price(c)
                
                db_stats = db.get_stats()
                acc_pnl = db_stats['total_net_profit']
                slots, val_slot = calculate_dynamic_position_slots(usdt, accumulated_net_profit=acc_pnl)
                kelly_val, kelly_pct, is_k_active = calculate_kelly_position_size(db, usdt)
                kelly_str = f"${kelly_val:.2f} USDT ({kelly_pct*100:.1f}% Half-Kelly)" if is_k_active else f"${val_slot:.2f} USDT (Padrão)"
                
                return (
                    f"💰 <b>SALDOS & POSIÇÕES DA CARTEIRA</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"💵 <b>USDT Disponível</b>: <b>${usdt:.2f}</b>\n"
                    f"🪙 <b>Saldo BNB</b>: <b>{bnb_free:.4f} BNB</b> (~${bnb_free*bnb_price:.2f})\n"
                    f"📈 <b>Lucro Acumulado</b>: <b>${acc_pnl:.2f} USDT</b>\n"
                    f"🏆 <b>Lote Kelly Criterion</b>: <b>{kelly_str}</b>\n"
                    f"❄️ <i>Motor de Juros Compostos (Snowball) Ativo!</i>\n\n"
                    f"🎰 <b>Slots Calculados</b>: <b>{slots} posições</b> de <b>${val_slot:.2f} USDT</b> cada."
                )
            except Exception as e:
                return f"Erro ao buscar saldo: {e}"
            finally:
                if c: await c.close_connection()

        elif cmd in ['/top20', '/scanner']:
            c = None
            try:
                c = await BinanceAsyncClient.create(api_key, api_secret)
                await sync_binance_time(c, log=lambda m: None)
                multi_klines = await get_multi_klines(c, TOP_20_SYMBOLS, TRADING_CONFIG['interval'], 50)
                ranked_assets = calculate_relative_strength_rank(multi_klines)
                
                lines = [f"🔥 <b>TOP 5 FORÇA RELATIVA & MOMENTUM (SCANNER 2.0)</b>\n━━━━━━━━━━━━━━━━━━━"]
                for item in ranked_assets[:5]:
                    sym = item['symbol']
                    prc = item['price']
                    rsi_v = item['rsi']
                    rs_v = item['rs_ratio']
                    emoji = "🟢" if rsi_v <= 35 else ("🟡" if rsi_v <= 50 else "⚪")
                    lines.append(f"{emoji} <b>{sym}</b>: ${prc:.2f} | RS: <b>{rs_v:+.1f}%</b> | RSI: <b>{rsi_v:.1f}</b>")
                
                return "\n".join(lines)
            except Exception as e:
                return f"Erro ao buscar scanner: {e}"
            finally:
                if c: await c.close_connection()

        elif cmd in ['/lucro', '/perf']:
            try:
                stats = db.get_stats()
                return (
                    f"📈 <b>PERFORMANCE ACUMULADA</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"💰 <b>Lucro Líquido Total</b>: <b>${stats['total_net_profit']:.2f} USDT</b>\n"
                    f"🎯 <b>Taxa de Vitória</b>: <b>{stats['win_rate']:.1f}%</b>\n"
                    f"📊 <b>Total de Operações</b>: <b>{stats['total_trades']} trades</b>"
                )
            except Exception as e:
                return f"Erro ao ler estatísticas: {e}"

        elif cmd in ['/relatorio', '/pdf']:
            try:
                pdf_path = generate_weekly_telemetry_pdf(db, output_path="docs/Relatorio_Semanal_Telemetria.pdf")
                asyncio.create_task(send_telegram_document(
                    TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                    pdf_path, caption="📊 <b>Relatório Executivo de Telemetria Semanal (PDF) SpotBot Pro v3.0</b>"
                ))
                return "📄 <b>Relatório Executivo em PDF gerado com sucesso! Enviando arquivo no Telegram...</b>"
            except Exception as e:
                return f"Erro ao gerar relatório PDF: {e}"

        elif cmd in ['/ocos', '/ordens', '/posicoes']:
            c = None
            try:
                c = await BinanceAsyncClient.create(api_key, api_secret)
                await sync_binance_time(c, log=lambda m: None)
                open_orders = await c.get_open_orders()
                
                if not open_orders:
                    return "ℹ️ <b>Nenhuma ordem OCO ou posição em aberto no momento.</b>\nO SpotBot Pro está varrendo o mercado em busca de novas oportunidades!"
                
                grouped = {}
                for o in open_orders:
                    sym = o.get('symbol', 'N/A')
                    list_id = o.get('orderListId', -1)
                    key = (sym, list_id)
                    if key not in grouped:
                        grouped[key] = {'symbol': sym, 'tp': 'N/A', 'sl': 'N/A', 'qty': '0'}
                    
                    qty_v = float(o.get('origQty', 0))
                    if qty_v > 0:
                        grouped[key]['qty'] = f"{qty_v:.2f}"
                        
                    o_type = o.get('type', '')
                    if o_type == 'LIMIT_MAKER':
                        price_v = float(o.get('price', 0))
                        if price_v > 0:
                            grouped[key]['tp'] = f"${price_v:.4f}"
                    elif 'STOP' in o_type:
                        stop_v = float(o.get('stopPrice', 0))
                        if stop_v == 0:
                            stop_v = float(o.get('price', 0))
                        if stop_v > 0:
                            grouped[key]['sl'] = f"${stop_v:.4f}"

                lines = ["🎯 <b>ORDENS OCO & POSIÇÕES ATIVAS</b>\n━━━━━━━━━━━━━━━━━━━"]
                for (sym, list_id), data in grouped.items():
                    lines.append(
                        f"🪙 Par: <b>{data['symbol']}</b>\n"
                        f"📦 Quantidade: <b>{data['qty']}</b>\n"
                        f"🟢 Take Profit (TP): <b>{data['tp']}</b> (+4.0%)\n"
                        f"🔴 Stop Loss (SL): <b>{data['sl']}</b> (-2.0%)\n"
                    )
                return "\n".join(lines)
            except Exception as e:
                return f"Erro ao buscar ordens OCO: {e}"
            finally:
                if c: await c.close_connection()

        elif cmd in ['/noticias', '/sentimento', '/news']:
            try:
                target_asset = bot_status_data.get('target_asset', 'BTCUSDT')
                headlines = await fetch_crypto_news(target_asset)
                score, is_panic, summary = analyze_news_sentiment_with_gemini(headlines)
                status_emoji = "🚨 PÂNICO" if is_panic else "🟢 ESTÁVEL"
                
                lines = [
                    f"📰 <b>SENTIMENTO DE MERCADO & NOTÍCIAS (IA)</b>\n━━━━━━━━━━━━━━━━━━━",
                    f"🎯 <b>Status</b>: <b>{status_emoji}</b> | <b>Score IA</b>: <b>{score}/100</b>",
                    f"💡 <b>Análise IA Gemini</b>: <i>{summary}</i>\n",
                    f"<b>Manchetes Recentes (CryptoPanic)</b>:"
                ]
                for h in headlines[:4]:
                    lines.append(f"• <i>{h}</i>")
                return "\n".join(lines)
            except Exception as e:
                return f"Erro ao buscar notícias: {e}"

        elif cmd in ['/ajuda', '/help', '/menu']:
            return (
                "📚 <b>COMANDOS DISPONÍVEIS (SPOTBOT PRO v6.0)</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "📊 /status - Status do ativo em foco, RSI e confluência MTF\n"
                "💰 /saldo - Saldos USDT, BNB e fracionamento de vagas\n"
                "📈 /lucro ou /perf - Lucro líquido acumulado e Win Rate\n"
                "⚡ /posicoes ou /ocos - Ordens OCO e posições ativas\n"
                "📰 /noticias - Sentimento de mercado e notícias CryptoPanic\n"
                "🔥 /top20 ou /scanner - Ranking de Força Relativa do Top 20\n"
                "📄 /relatorio ou /pdf - Gera e envia Relatório Semanal PDF\n"
                "🛑 /stop - Pausa o bot com segurança\n"
                "🚨 /cancel - Interrupção de emergência (CTRL+C)\n"
                "📱 /menu ou /ajuda - Exibe este menu com botões inline"
            )
        return "❓ Comando não reconhecido. Digite /ajuda para ver as opções."

    if TELEGRAM_CONFIG.get('bot_token'):
        tg_bot = TelegramBot(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], handle_telegram_command)
        asyncio.create_task(tg_bot.start())

    log("\n🚀 \033[5;33mBot SpotBot Pro iniciado!\033[0m 🚀\n")
    
    try:
        db.create_tables()
        db.migrate_from_csv()
    except Exception as e:
        log(f"⚠️ Aviso no banco de dados: {e}")

    await asyncio.sleep(1)
    client = None
    try:
        client = await BinanceAsyncClient.create(api_key, api_secret)
        await sync_binance_time(client, log=log)
        bsm = BinanceSocketManager(client)
        
        saldo_inicial_usdt = await get_usdt_balance(client)
        log(f"💰 Saldo USDT disponível: \033[1;32m${saldo_inicial_usdt:.2f}\033[0m")

        is_scanner_mode = False
        if selected_symbol == '⚡ SCANNER TOP 20' or not selected_symbol:
            symbol = "BTCUSDT"
            display_symbol = "⚡ SCANNER TOP 20"
            is_scanner_mode = True
        else:
            symbol = selected_symbol
            display_symbol = selected_symbol

        log(f"🪙 Modo Selecionado: {display_symbol}\n")

        if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
            asyncio.create_task(send_telegram_message(
                TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                f"<b>🚀 Bot SpotBot Pro iniciado! 🚀</b>\n\n"
                f"💰 Saldo USDT disponível: <b>${saldo_inicial_usdt:.2f}</b>\n"
                f"🪙 Modo Selecionado: <b>{display_symbol}</b>"
            ))
        
        # Verificação e Adotação Multi-Posição de Ordens OCO Ativas (State Recovery Engine v4.0)
        open_ocos = await client.get_open_oco_orders()
        if open_ocos:
            log(f"🔄 \033[1;36mState Recovery Engine\033[0m: {len(open_ocos)} ordem(ns) OCO ativa(s) encontrada(s) na Binance!")
            for oco_order in open_ocos[:MAX_CONCURRENT_POSITIONS]:
                active_target_symbol = oco_order['symbol']
                log(f"🛡️ Retomando monitoramento paralelo de \033[1;33m{active_target_symbol}\033[0m sem cancelar a operação...")
                
                if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                    asyncio.create_task(send_telegram_message(
                        TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                        f"🔄 <b>State Recovery Ativado!</b>\n\n"
                        f"🪙 Par: <b>{active_target_symbol}</b>\n"
                        f"🛡️ Ordem OCO recuperada da Binance. Retomando monitoramento de lucro e stop automaticamente!"
                    ))
                
                limit_order_id = oco_order['orders'][1]['orderId']
                stop_order_id = oco_order['orders'][0]['orderId']
                target_symbol_info = await client.get_symbol_info(active_target_symbol)
                tick_size = float(next(f for f in target_symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER')['tickSize'])
                step_size = float(next(f for f in target_symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')['stepSize'])
                
                limit_details = await get_order_details(client, active_target_symbol, limit_order_id)
                stop_details = await get_order_details(client, active_target_symbol, stop_order_id)
                
                executed_qty = float(limit_details.get('origQty', stop_details.get('origQty', 0)))
                lucro_alvo = float(limit_details.get('price', 0))
                stop_loss = float(stop_details.get('stopPrice', stop_details.get('price', 0)))
                
                ticker_cur = await client.get_symbol_ticker(symbol=active_target_symbol)
                price = float(ticker_cur['price'])
                order_val_usdt = round(executed_qty * price, 2)
                purchase_timestamp = dt_module.datetime.now().strftime("%d/%m/%Y at %H:%M:%S")
                active_positions[active_target_symbol] = {
                    'entry': price,
                    'tp': lucro_alvo,
                    'sl': stop_loss,
                    'qty': executed_qty,
                    'time': purchase_timestamp
                }
                bot_status_data['active_symbols'] = list(active_positions.keys())
                bot_status_data['target_asset'] = active_target_symbol
                bot_status_data['price'] = price
                bot_status_data['tp_price'] = lucro_alvo
                bot_status_data['sl_price'] = stop_loss
                bot_status_data['entry_price'] = price

                # Carrega klines e indicadores para popular o gráfico do ativo recuperado
                try:
                    klines_raw = await client.get_klines(symbol=active_target_symbol, interval=TRADING_CONFIG['interval'], limit=100)
                    if klines_raw:
                        klines_rec = [float(k[4]) for k in klines_raw]
                        dates_rec = [dt_module.datetime.fromtimestamp(float(k[0])/1000).strftime('%H:%M') for k in klines_raw]
                        volumes_rec = [float(k[5]) for k in klines_raw]
                        
                        df_rec = pd.DataFrame({'close': klines_rec})
                        sma20 = df_rec['close'].rolling(window=20).mean()
                        std20 = df_rec['close'].rolling(window=20).std()
                        bb_upper = (sma20 + 2 * std20).fillna(0).tolist()
                        bb_lower = (sma20 - 2 * std20).fillna(0).tolist()
                        ema200 = df_rec['close'].ewm(span=min(200, len(klines_rec)), adjust=False).mean().fillna(0).tolist()

                        shared_market_data['dates'] = dates_rec
                        shared_market_data['klines'] = [[float(k[1]), float(k[4]), float(k[3]), float(k[2])] for k in klines_raw]
                        shared_market_data['bb_upper'] = bb_upper
                        shared_market_data['bb_lower'] = bb_lower
                        shared_market_data['ema200'] = ema200
                        shared_market_data['volumes'] = volumes_rec
                except Exception as k_err:
                    log(f"⚠️ Aviso ao carregar klines no State Recovery ({active_target_symbol}): {k_err}")

                # Lança o monitoramento em background para NÃO bloquear o scanner das vagas restantes!
                asyncio.create_task(monitor_oco_lifecycle(
                    client, bsm, active_target_symbol, oco_order, limit_order_id, stop_order_id,
                    price, executed_qty, order_val_usdt, lucro_alvo, stop_loss, target_symbol_info,
                    tick_size, step_size, log, status, saldo_inicial_usdt, 1, purchase_timestamp,
                    "State Recovery (Posição Retomada)", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    [], 0, 0, 0, 0, 0, 0, True, None, db
                ))

        symbol_info = await client.get_symbol_info(symbol)
        tick_size = float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'PRICE_FILTER')['tickSize'])
        quote_precision = int(symbol_info['quoteAssetPrecision'])

        last_sync_hour = dt_module.datetime.now().hour
        last_pdf_sent_day = None
        order_count = 0

        while bot_running:
            try:
                current_dt = dt_module.datetime.now()
                current_hour = current_dt.hour
                
                if current_hour != last_sync_hour:
                    await sync_binance_time(client, log=log)
                    last_sync_hour = current_hour

                if current_dt.weekday() == 6 and current_hour == 20 and last_pdf_sent_day != current_dt.date():
                    last_pdf_sent_day = current_dt.date()
                    try:
                        pdf_path = generate_weekly_telemetry_pdf(db, output_path="docs/Relatorio_Semanal_Telemetria.pdf")
                        if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                            asyncio.create_task(send_telegram_document(
                                TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                pdf_path, caption="📊 <b>Relatório Executivo de Telemetria Semanal (PDF) SpotBot Pro v3.0</b>"
                            ))
                            log("📄 Relatório Semanal em PDF enviado automaticamente para o Telegram!")
                    except Exception as pdf_err:
                        log(f"⚠️ Erro ao gerar PDF automático de domingo: {pdf_err}")

                # FASE 2: Relatório Diário Automático às 23:59
                now_dt = dt_module.datetime.now()
                if now_dt.hour == 23 and now_dt.minute == 59 and globals().get('_last_daily_report_date') != now_dt.date():
                    globals()['_last_daily_report_date'] = now_dt.date()
                    try:
                        d_stats = db.get_daily_stats()
                        if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                            asyncio.create_task(send_telegram_message(
                                TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                f"📊 <b>RELATÓRIO DIÁRIO DE TRADING ({d_stats['date']})</b>\n\n"
                                f"🎯 Operações Executadas: <b>{d_stats['trades']}</b>\n"
                                f"🏆 Vitórias / Derrotas: <b>{d_stats['wins']} Wins / {d_stats['losses']} Losses</b>\n"
                                f"📈 Win Rate do Dia: <b>{d_stats['win_rate']:.1f}%</b>\n"
                                f"💰 PnL Líquido Diário: <b>${d_stats['daily_pnl']:+.2f} USDT</b>\n"
                                f"💵 Saldo Livre Atual: <b>${await get_usdt_balance(client):.2f} USDT</b>"
                            ))
                            log("📄 Relatório Diário enviado automaticamente para o Telegram!")
                    except Exception as r_err:
                        log(f"⚠️ Erro ao gerar relatório diário: {r_err}")

                usdt_balance = await get_usdt_balance(client)
                
                # FASE 2: Daily Circuit Breaker (-5.0% Max Drawdown Diário)
                daily_stats = db.get_daily_stats()
                daily_pnl = daily_stats['daily_pnl']
                circuit_breaker_limit = -abs(max(5.0, usdt_balance * 0.05))
                
                if daily_pnl <= circuit_breaker_limit:
                    status(f"🚨 DAILY CIRCUIT BREAKER ATIVADO ({daily_pnl:+.2f} USDT). Novas compras pausadas por 12h...")
                    if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id') and globals().get('_last_cb_alert') != now_dt.date():
                        globals()['_last_cb_alert'] = now_dt.date()
                        asyncio.create_task(send_telegram_message(
                            TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                            f"🚨 <b>DAILY CIRCUIT BREAKER ATIVADO!</b>\n\n"
                            f"📊 Perda acumulada hoje de <b>${daily_pnl:.2f} USDT</b> atingiu o limite de proteção de -5.0%!\n"
                            f"🛡️ Novas compras pausadas por 12 horas enquanto as ordens OCO ativas continuam sendo monitoradas."
                        ))
                    await asyncio.sleep(600)
                    continue

                if len(active_positions) >= MAX_CONCURRENT_POSITIONS:
                    active_list_str = ", ".join(active_positions.keys())
                    status(f"⏳ Posições Máximas Atingidas ({len(active_positions)}/{MAX_CONCURRENT_POSITIONS}): [{active_list_str}]. Monitorando operações...")
                    await asyncio.sleep(6)
                    continue

                db_stats = db.get_stats()
                acc_pnl = db_stats['total_net_profit']

                # FASE 3: Gemini Auto-Tuning de Perfil de Risco a cada 30 min
                if now_dt.minute % 30 == 0 and globals().get('_last_autotune_min') != now_dt.minute:
                    globals()['_last_autotune_min'] = now_dt.minute
                    try:
                        rec_profile, rec_just = auto_tune_risk_profile("ALTA", db_stats['win_rate'], acc_pnl)
                        from config.settings import RISK_PROFILES
                        import config.settings as setts
                        if rec_profile in RISK_PROFILES and setts.ACTIVE_RISK_PROFILE != rec_profile:
                            setts.ACTIVE_RISK_PROFILE = rec_profile
                            log(f"🧠 \033[1;36mGemini Auto-Tuning\033[0m: Perfil de Risco ajustado para \033[1;32m{rec_profile}\033[0m! ({rec_just})")
                            if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                                asyncio.create_task(send_telegram_message(
                                    TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                    f"🧠 <b>GEMINI AUTO-TUNING DE RISCO</b>\n\n"
                                    f"🎯 Novo Perfil Recomendado: <b>{rec_profile}</b>\n"
                                    f"📝 Justificativa IA: <i>{rec_just}</i>"
                                ))
                    except Exception as at_err:
                        log(f"⚠️ Aviso no Gemini Auto-Tuning: {at_err}")

                slots, slot_value = calculate_dynamic_position_slots(
                    usdt_balance,
                    accumulated_net_profit=acc_pnl,
                    max_concurrent_positions=MAX_CONCURRENT_POSITIONS,
                    reserve_fraction_for_dca=RESERVE_FRACTION_FOR_DCA
                )

                active_target_symbol = symbol
                if is_scanner_mode:
                    status(f"⚡ Scanner 2.0 avaliando Top 20... (Vagas Livres: {MAX_CONCURRENT_POSITIONS - len(active_positions)}/{MAX_CONCURRENT_POSITIONS})")
                    multi_klines = await get_multi_klines(client, TOP_20_SYMBOLS, TRADING_CONFIG['interval'], TRADING_CONFIG['limit'])
                    ranked_assets = calculate_relative_strength_rank(multi_klines)
                    if ranked_assets:
                        available_assets = [a for a in ranked_assets if a['symbol'] not in active_positions]
                        if available_assets:
                            active_target_symbol = available_assets[0]['symbol']
                        else:
                            await asyncio.sleep(5)
                            continue

                bot_status_data['target_asset'] = active_target_symbol

                klines = await get_klines(client, active_target_symbol, TRADING_CONFIG['interval'], TRADING_CONFIG['limit'])
                if not klines:
                    await asyncio.sleep(5)
                    continue
            except BinanceAPIException as api_err:
                if api_err.code == -1021:
                    log("⏱️ Erro de dessincronização detectado. Ressincronizando com a Binance...")
                    await sync_binance_time(client, log=log)
                    await asyncio.sleep(2)
                    continue
                else:
                    log(f"Erro na API Binance: {api_err}")
                    await asyncio.sleep(5)
                    continue
            except Exception as e:
                err_desc = str(e) if str(e).strip() else repr(e)
                log(f"⚠️ Instabilidade ao buscar klines ({type(e).__name__}): {err_desc}")
                await asyncio.sleep(5)
                continue

            closes = extract_closes(klines)
            volumes = extract_volumes(klines)
            rsi = calculate_rsi(closes)
            
            volumes_series = pd.Series(volumes)
            volume_ma = volumes_series.dropna().rolling(window=8).mean().iloc[-1]
            
            macd_current, signal_line_current = calculate_macd(closes)
            lower_band, middle_band, upper_band = calculate_bollinger_bands(closes)
            vwap = calculate_vwap(closes, volumes)

            try:
                chart_limit = 50
                if len(klines) > chart_limit:
                    recent_klines = klines[-chart_limit:]
                    shared_market_data['dates'] = [dt_module.datetime.fromtimestamp(int(k[0])/1000).strftime('%H:%M') for k in recent_klines]
                    shared_market_data['klines'] = [[float(k[1]), float(k[4]), float(k[3]), float(k[2])] for k in recent_klines]
                    shared_market_data['volumes'] = [float(k[5]) for k in recent_klines]
                    
                    s_closes = pd.Series(closes)
                    r = s_closes.rolling(window=20)
                    ma = r.mean()
                    std = r.std()
                    shared_market_data['bb_upper'] = (ma + (2 * std)).tail(chart_limit).fillna(0).tolist()
                    shared_market_data['bb_middle'] = ma.tail(chart_limit).fillna(0).tolist()
                    shared_market_data['bb_lower'] = (ma - (2 * std)).tail(chart_limit).fillna(0).tolist()
                    shared_market_data['ema200'] = s_closes.ewm(span=200, adjust=False).mean().tail(chart_limit).fillna(0).tolist()
            except Exception:
                pass

            bot_status_data['symbol'] = display_symbol
            bot_status_data['price'] = closes[-1]
            bot_status_data['rsi'] = rsi
            bot_status_data['trend'] = "Alta" if check_trend(klines) else "Baixa/Neutro"
            
            status(f"📊 RSI ({active_target_symbol}): {rsi:.1f} | Preço: ${closes[-1]:.2f}")
            
            if volumes_series.iloc[-1] > volume_ma * (1 + TRADING_CONFIG['volume_avg'] / 100):
                status("⚠️ Alto volume detectado (Volatilidade). Operação em espera.")
                await asyncio.sleep(1)
                continue
                
            trend_is_up = check_trend(klines)
            candle_patterns = check_candle_patterns(klines)
            market_downward = is_market_downward(klines)
            
            await check_rsi_reset(active_target_symbol, log=log)
            
            try:
                if await should_place_order(client, active_target_symbol, status_callback=status) and not market_downward:
                    candle_details = get_candle_details(klines)
                    candle_open = candle_details['open'] if candle_details else 0
                    candle_high = candle_details['high'] if candle_details else 0
                    candle_low = candle_details['low'] if candle_details else 0
                    candle_close = candle_details['close'] if candle_details else 0
                    candle_volume = candle_details['volume'] if candle_details else 0
                    amplitude = ((candle_high - candle_low) / candle_open) * 100 if candle_open != 0 else 0
                    
                    try:
                        price_24h_ago = float(klines[-25][4]) if len(klines) >= 25 else closes[-1]
                        variation_24h = ((closes[-1] - price_24h_ago) / price_24h_ago) * 100 if price_24h_ago != 0 else 0
                        candle_variation = ((candle_close - candle_open) / candle_open) * 100 if candle_open != 0 else 0
                    except Exception:
                        variation_24h, candle_variation = 0, 0

                    ema7 = calculate_ema(closes, 7)
                    ema15 = calculate_ema(closes, 15)
                    ema25 = calculate_ema(closes, 25)
                    ema50 = calculate_ema(closes, 50)
                    ema100 = calculate_ema(closes, 100)
                    ema200 = calculate_ema(closes, 200)

                    buy_result = await should_buy(rsi, trend_is_up, macd_current, signal_line_current, closes[-1], lower_band, middle_band, upper_band, vwap, candle_patterns, candle_open, candle_high, 
                                                  candle_low, candle_close, candle_volume, variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, client, active_target_symbol, klines)
                    
                    if buy_result.get('mtf_score'):
                        bot_status_data['mtf_score'] = buy_result['mtf_score']

                    if buy_result.get('gemini_analysis'):
                         shared_market_data['gemini_insight'] = buy_result['gemini_analysis']

                    if buy_result["buy"]:
                        executed_condition = buy_result["message"]
                        log(f"🟢 Sinal de COMPRA em {active_target_symbol}! Condição: {executed_condition}")
                        
                        target_symbol_info = await client.get_symbol_info(active_target_symbol)
                        min_notional = get_min_notional(target_symbol_info)
                        tick_size = float(next(f for f in target_symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER')['tickSize'])
                        step_size = float(next(f for f in target_symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')['stepSize'])
                        
                        pos_multiplier = buy_result.get('position_multiplier', 1.0)
                        safe_usdt_limit = math.floor(usdt_balance * 0.99 * 100) / 100.0
                        
                        # FASE 5 (v5.0): Kelly Criterion Position Sizing Engine
                        k_val, k_pct, is_k_act = calculate_kelly_position_size(db, usdt_balance, default_slot_value=slot_value)
                        target_slot = k_val if is_k_act else slot_value
                        if is_k_act:
                            log(f"🏆 \033[1;36mKelly Criterion Sizing\033[0m: Lote dimensionado em \033[1;32m${target_slot:.2f} USDT\033[0m ({k_pct*100:.1f}% Half-Kelly).")

                        order_val_usdt = max(min_notional, min(safe_usdt_limit, round(target_slot * pos_multiplier, 2)))

                        if usdt_balance < min_notional:
                            log(f"⚠️ Saldo insuficiente (${usdt_balance:.2f}) para o mínimo exigido (${min_notional}).")
                            await asyncio.sleep(5)
                            continue

                        if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                            asyncio.create_task(send_telegram_message(
                                TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                f"🛒 <b>Ordem de COMPRA Executada!</b>\n\n"
                                f"🪙 Par: <b>{active_target_symbol}</b>\n"
                                f"💵 Preço: <b>${closes[-1]:.2f}</b>\n"
                                f"🎯 Motivo: <i>{executed_condition}</i>\n"
                                f"💰 Valor: <b>${order_val_usdt:.2f} USDT</b> (Slot {len(active_positions)+1}/{MAX_CONCURRENT_POSITIONS})"
                            ))

                        order_count += 1
                        compra = await client.order_market_buy(symbol=active_target_symbol, quoteOrderQty=round(order_val_usdt, quote_precision))
                        executed_qty = float(compra['executedQty'])
                        price = float(compra['fills'][0]['price'])
                        timestamp = dt_module.datetime.now().strftime("%d/%m/%Y at %H:%M:%S")
                        
                        log(f"✅️ ({order_count:02d}) Comprado: {active_target_symbol} - Qtd: {executed_qty} - Preço: ${price:.4f}")
                        purchase_timestamp = timestamp
                        gemini_response = buy_result.get("gemini_response")

                        oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit = await adjust_and_place_oco_order(client, active_target_symbol, executed_qty, tick_size, step_size, klines, log=log)
                        if oco_order and TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                            asyncio.create_task(send_telegram_message(
                                TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                f"🎯 <b>Ordem OCO Posicionada!</b>\n\n"
                                f"🪙 Par: <b>{active_target_symbol}</b>\n"
                                f"🟢 Take Profit (TP): <b>${lucro_alvo:.4f}</b> (+4.0%)\n"
                                f"🔴 Stop Loss (SL): <b>${stop_loss:.4f}</b> (-2.0%)"
                            ))
                        last_operation_time = dt_module.datetime.now()

                        # Lança o monitoramento em background para NÃO bloquear o scanner!
                        asyncio.create_task(monitor_oco_lifecycle(
                            client, bsm, active_target_symbol, oco_order, limit_order_id, stop_order_id,
                            price, executed_qty, order_val_usdt, lucro_alvo, stop_loss, target_symbol_info,
                            tick_size, step_size, log, status, saldo_inicial_usdt, order_count, purchase_timestamp,
                            executed_condition, rsi, vwap, candle_open, candle_high, candle_low, candle_close,
                            candle_volume, variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100,
                            ema200, candle_patterns, amplitude, macd_current, signal_line_current, lower_band,
                            middle_band, upper_band, trend_is_up, gemini_response, db
                        ))
            except Exception as trade_exec_err:
                log(f"⚠️ Erro recuperável na execução de ordem: {trade_exec_err}")

            await asyncio.sleep(1)

    except asyncio.CancelledError:
        log("\n🛑 Bot parado pelo usuário.")
        if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
            asyncio.create_task(send_telegram_message(
                TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                "🛑 <b>Bot parado pelo usuário.</b>"
            ))
    except Exception as e:
        log(f"\n⚠️ Erro de execução: {e}")
    finally:
        bot_running = False
        bot_status_data['is_running'] = False
        if client:
            await client.close_connection()
