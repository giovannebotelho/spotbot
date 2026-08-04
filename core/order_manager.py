import asyncio
import time
import math
import datetime as dt_module
from config.settings import TELEGRAM_CONFIG, TRADING_CONFIG, TRAILING_STOP_CONFIG, TIMEZONE
from services.binance_client import get_usdt_balance, get_klines, get_bnb_price, get_order_details
from core.indicators import calculate_fibonacci_supports
from core.decision import get_min_notional, adjust_price_to_tick_size, get_precision
from core.post_trade import process_order_details, save_to_csv, create_data_row, log_and_notify_results
from services.telegram_notifier import send_telegram_message
from services.gemini_ai import generate_post_trade_synthesis
from utils.formatting import format_price

async def monitor_oco_lifecycle(
    client, bsm, active_target_symbol, oco_order, limit_order_id, stop_order_id,
    price, executed_qty, order_val_usdt, lucro_alvo, stop_loss, target_symbol_info,
    tick_size, step_size, log, status, saldo_inicial_usdt, order_count, purchase_timestamp,
    executed_condition, rsi, vwap, candle_open, candle_high, candle_low, candle_close,
    candle_volume, variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100,
    ema200, candle_patterns, amplitude, macd_current, signal_line_current, lower_band,
    middle_band, upper_band, trend_is_up, gemini_response, db, confluence_score=0.0, slippage=0.0, active_positions=None, bot_status_data=None, globals_dict=None
):
    
    total_difference = 0
    total_difference_liquid = 0
    highest_price = price
    current_stop_loss = stop_loss
    partial_take_done = False
    dca_done = False
    dca_count = 0

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
                                        await client._delete('orderList', signed=True, data={'symbol': active_target_symbol, 'orderListId': oco_order['orderListId']})
                                        dca_buy = await client.order_market_buy(symbol=active_target_symbol, quoteOrderQty=round(dca_val_usdt, 2))
                                        dca_qty = float(dca_buy['executedQty'])
                                        dca_price = float(dca_buy['fills'][0]['price'])
                                        
                                        total_qty = executed_qty + dca_qty
                                        new_pm = ((executed_qty * price) + (dca_qty * dca_price)) / total_qty
                                        
                                        log(f"🧪 \033[1;36mSmart Recovery DCA Executado\033[0m em \033[1;33m{active_target_symbol}\033[0m no Suporte de Fibonacci 61.8% (${dca_price:.4f})!")
                                        log(f"📉 Preço Médio ajustado de ${price:.4f} para \033[1;32m${new_pm:.4f}\033[0m! Re-posicionando TP/SL de recuperação...")
                                        if db:
                                            db.add_event(active_target_symbol, "DCA", f"Smart Recovery DCA a ${dca_price:.4f}. Preço médio alterado para ${new_pm:.4f}.")
                                        
                                        prec_p = get_precision(tick_size)
                                        prec_q = get_precision(step_size)
                                        prec_qty_val = round(math.floor(total_qty / step_size) * step_size, prec_q)
                                        
                                        new_tp = adjust_price_to_tick_size(new_pm * 1.015, tick_size)
                                        new_sl = adjust_price_to_tick_size(new_pm * 0.975, tick_size)
                                        new_sl_limit = adjust_price_to_tick_size(new_sl * 0.999, tick_size)
                                        
                                        oco_order = await place_safe_oco_sell_order(
                                            client, active_target_symbol, prec_qty_val, new_tp, new_sl, new_sl_limit, prec_p, prec_q
                                        )
                                        limit_order_id = oco_order['orders'][1]['orderId']
                                        stop_order_id = oco_order['orders'][0]['orderId']
                                        
                                        price = new_pm
                                        executed_qty = prec_qty_val
                                        order_val_usdt = round(price * executed_qty, 2)
                                        lucro_alvo = new_tp
                                        stop_loss = new_sl
                                        current_stop_loss = new_sl
                                        dca_done = True
                                        dca_count += 1
                                        
                                        if bot_status_data.get('target_asset') == active_target_symbol:
                                            bot_status_data['entry_price'] = new_pm
                                            bot_status_data['tp_price'] = new_tp
                                            bot_status_data['sl_price'] = new_sl
                                        
                                        if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                                            asyncio.create_task(send_telegram_message(
                                                TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                                f"🧪 <b>Smart Recovery DCA Executado!</b>\n\n"
                                                f"🪙 Par: <b>{active_target_symbol}</b>\n"
                                                f"📉 Recompra efetuada no Suporte Fibonacci 61.8% (<b>{format_price(dca_price)}</b>)\n"
                                                f"🎯 <b>Novo Preço Médio: {format_price(new_pm)}</b>\n"
                                                f"🛡️ Take Profit de recuperação ajustado para <b>{format_price(new_tp)} (+0.8%)</b>!"
                                            ))
                            except Exception as e_dca:
                                log(f"Aviso no Smart Recovery DCA: {e_dca}")

                        if profit_pct >= 0.015 and not partial_take_done:
                            try:
                                prec_qty = get_precision(step_size)
                                half_qty = round(math.floor((executed_qty * 0.5) / step_size) * step_size, prec_qty)
                                rem_qty = round(executed_qty - half_qty, prec_qty)

                                if half_qty > 0 and rem_qty > 0:
                                    await client._delete('orderList', signed=True, data={'symbol': active_target_symbol, 'orderListId': oco_order['orderListId']})
                                    venda_parcial = await client.order_market_sell(symbol=active_target_symbol, quantity=half_qty)
                                    p_price = float(venda_parcial['fills'][0]['price'])
                                    
                                    log(f"💰 Scalp Locking: Venda parcial de 50% executada em {active_target_symbol} a {format_price(p_price)}! (+{profit_pct*100:.2f}%)")
                                    if db:
                                        db.add_event(active_target_symbol, "SCALP_LOCK", f"Venda parcial a {format_price(p_price)} (+{profit_pct*100:.2f}%).")
                                    
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
                                    
                                    if bot_status_data.get('target_asset') == active_target_symbol:
                                        bot_status_data['sl_price'] = be_stop

                                    if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                                        asyncio.create_task(send_telegram_message(
                                            TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                            f"💰 <b>Scalp Locking (+1.5% Lucro Garantido)!</b>\n\n"
                                            f"🪙 Par: <b>{active_target_symbol}</b>\n"
                                            f"🎯 50% da posição vendida a <b>{format_price(p_price)}</b>!\n"
                                            f"🛡️ 50% restante protegido no <b>Breakeven (Zero a Zero em {format_price(price)})</b>!"
                                        ))
                            except Exception as e_partial:
                                log(f"Aviso ao executar Scalp Locking: {e_partial}")

                        # FASE 5: Trailing Profit Lock (Venda a mercado após 75% do TP alvo)
                        if cur_price > highest_price:
                            highest_price = cur_price
                        
                        tp_distance = lucro_alvo - price
                        trigger_price = price + (tp_distance * 0.75)
                        
                        if highest_price >= trigger_price:
                            # Queda de 0.2% em relação ao pico -> Executa Market Sell direto
                            if cur_price < highest_price * 0.998:
                                log(f"🔒 \033[1;36mTrailing Profit Lock Acionado!\033[0m Preço caiu 0.2% do pico ${highest_price:.4f}. Garantindo lucro...")
                                if db:
                                    db.add_event(active_target_symbol, "TRAILING_LOCK", f"Market Sell executado a ${cur_price:.4f} via Trailing Profit Lock")
                                
                                try:
                                    await client._delete('orderList', signed=True, data={'symbol': active_target_symbol, 'orderListId': oco_order['orderListId']})
                                except Exception as e:
                                    log(f"Aviso ao cancelar OCO para Trailing Lock: {e}")
                                
                                qty_to_sell = executed_qty if not partial_take_done else rem_qty
                                prec_qty = get_precision(step_size)
                                qty_to_sell = round(qty_to_sell, prec_qty)
                                
                                # Envia venda a mercado
                                await client.order_market_sell(symbol=active_target_symbol, quantity=qty_to_sell)
                                
                                # Obter detalhes (como se a ordem limit fosse 'FILLED' antecipadamente) para consolidar o PnL
                                limit_details = await get_order_details(client, active_target_symbol, limit_order_id)
                                stop_details = await get_order_details(client, active_target_symbol, stop_order_id)
                                limit_details['status'] = 'FILLED'
                                limit_details['price'] = str(cur_price) # Simulando o preenchimento ao preço de mercado
                                
                                active_target_symbol, order_result, trade_result, novo_saldo_usdt, oco_timestamp, fee, trade_result_liquid = await process_order_details(
                                    active_target_symbol, client, limit_details, stop_details, price, executed_qty, order_val_usdt
                                )
                                
                                total_difference += trade_result
                                total_difference_liquid += trade_result_liquid
                                bnb_balance_free = float((await client.get_asset_balance(asset='BNB'))['free'])
                                bnb_price = await get_bnb_price(client)
                                
                                if order_result:
                                    await log_and_notify_results(order_result, active_target_symbol, trade_result, total_difference, oco_timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_free * bnb_price, log=log)
                                    if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
                                        asyncio.create_task(send_telegram_message(
                                            TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'],
                                            f"🔒 <b>Trailing Profit Lock Acionado!</b>\n\n"
                                            f"🪙 Par: <b>{active_target_symbol}</b>\n"
                                            f"🎯 Lucro garantido via Market Sell em <b>{format_price(cur_price)}</b>!\n"
                                        ))
                                        
                                    try:
                                        cur_exit_price = cur_price
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
                                        total_difference_liquid, gemini_response, bnb_balance_free * bnb_price,
                                        confluence_score, slippage, stop_loss, dca_count, "v6.0"
                                    )
                                    try:
                                        save_to_csv(data_row)
                                    except Exception as csv_err:
                                        log(f"⚠️ Erro ao salvar CSV local: {csv_err}")
                                    if db:
                                        try:
                                            db.add_trade(data_row)
                                        except Exception as db_save_err:
                                            log(f"⚠️ Erro ao registrar trade no banco de dados: {db_save_err}")
                                    
                                    globals_dict['stop_loss_count'] = 0
                                    active_positions.pop(active_target_symbol, None)
                                    bot_status_data['active_symbols'] = list(active_positions.keys())
                                    if bot_status_data.get('target_asset') == active_target_symbol:
                                        bot_status_data['tp_price'] = 0.0
                                        bot_status_data['sl_price'] = 0.0
                                        bot_status_data['entry_price'] = 0.0
                                    return
                    except Exception as tsl_err:
                        log(f"⚠️ Erro ao atualizar Trailing Stop Loss para {active_target_symbol}: {tsl_err}")
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
                            await log_and_notify_results(order_result, active_target_symbol, trade_result, total_difference, oco_timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_free * bnb_price, log=log)
                            
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
                                total_difference_liquid, gemini_response, bnb_balance_free * bnb_price,
                                confluence_score, slippage, stop_loss, dca_count, "v6.0"
                            )
                            try:
                                save_to_csv(data_row)
                            except Exception as csv_err:
                                log(f"⚠️ Erro ao salvar CSV local: {csv_err}")
                            if db:
                                try:
                                    db.add_trade(data_row)
                                except Exception as db_save_err:
                                    log(f"⚠️ Erro ao registrar trade no banco de dados: {db_save_err}")
                            
                            if stop_details['status'] == 'FILLED':
                                globals_dict['stop_loss_count'] += 1
                                globals_dict['last_stop_loss_time'] = dt_module.datetime.now(TIMEZONE)
                                await check_stop_losses(globals_dict['last_stop_loss_time'], log=log)
                            else:
                                globals_dict['stop_loss_count'] = 0
                            active_positions.pop(active_target_symbol, None)
                            bot_status_data['active_symbols'] = list(active_positions.keys())
                            if bot_status_data.get('target_asset') == active_target_symbol:
                                bot_status_data['tp_price'] = 0.0
                                bot_status_data['sl_price'] = 0.0
                                bot_status_data['entry_price'] = 0.0
                            return
    except Exception as ws_err:
        use_ws_monitoring = False
        if "-2035" in str(ws_err) or "already active" in str(ws_err):
            log(f"ℹ️ Monitoramento Multimodal: Posição secundária ({active_target_symbol}) alocada no motor REST Polling.")
        else:
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
                        await log_and_notify_results(order_result, active_target_symbol, trade_result, total_difference, oco_timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_free * bnb_price, log=log)
                        data_row = create_data_row(
                            order_count, saldo_inicial_usdt, novo_saldo_usdt, active_target_symbol,
                            executed_qty, price, purchase_timestamp, lucro_alvo, stop_loss, stop_loss,
                            order_result, oco_timestamp, trade_result, total_difference, novo_saldo_usdt,
                            rsi, executed_condition, vwap, candle_open, candle_high, candle_low, candle_close, candle_volume, 
                            variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, candle_patterns, TRADING_CONFIG['volume_avg'], 
                            amplitude, macd_current, signal_line_current, lower_band, middle_band, upper_band, trend_is_up, fee, trade_result_liquid,
                            total_difference_liquid, gemini_response, bnb_balance_free * bnb_price,
                            confluence_score, slippage, stop_loss, dca_count, "v6.0"
                        )
                        try:
                            save_to_csv(data_row)
                        except Exception as csv_err:
                            log(f"⚠️ Erro ao salvar CSV local: {csv_err}")
                        if db:
                            try:
                                db.add_trade(data_row)
                            except Exception as db_save_err:
                                log(f"⚠️ Erro ao registrar trade no banco de dados: {db_save_err}")
                        
                        if stop_details['status'] == 'FILLED':
                            globals_dict['stop_loss_count'] += 1
                            globals_dict['last_stop_loss_time'] = dt_module.datetime.now(TIMEZONE)
                            await check_stop_losses(globals_dict['last_stop_loss_time'], log=log)
                        else:
                            globals_dict['stop_loss_count'] = 0
                        active_positions.pop(active_target_symbol, None)
                        bot_status_data['active_symbols'] = list(active_positions.keys())
                        if bot_status_data.get('target_asset') == active_target_symbol:
                            bot_status_data['tp_price'] = 0.0
                            bot_status_data['sl_price'] = 0.0
                            bot_status_data['entry_price'] = 0.0
                        return
            except Exception as poll_err:
                status(f"⚠️ Polling de Ordem: {poll_err}")
