import asyncio
import os
import pandas as pd
from datetime import datetime, timedelta
from binance import BinanceSocketManager
from binance import AsyncClient as BinanceAsyncClient

from config.settings import API_KEYS, TELEGRAM_CONFIG, TRADING_CONFIG, RSI_CONFIG, TRAILING_STOP_CONFIG
from services.binance_client import extract_closes, extract_volumes, get_usdt_balance, get_order_details, get_klines, get_bnb_price
from core.indicators import (
    calculate_rsi, calculate_macd, calculate_bollinger_bands, check_trend, check_candle_patterns,
    calculate_vwap, get_candle_details, calculate_ema, is_market_downward
)
from core.decision import should_place_order, should_buy, should_sell, adjust_and_place_oco_order, get_min_notional, adjust_price_to_tick_size, get_precision
from core.post_trade import process_order_details, log_and_notify_results, create_data_row, save_to_csv
from services.telegram_notifier import send_telegram_message, TelegramBot
from services.database import DatabaseManager
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
bot_status_data = {
    "rsi": 0, "price": 0, "symbol": "", "action": "Iniciando...", "trend": "N/A"
}
shared_market_data = {
    "klines": [], "dates": [], "bb_upper": [], "bb_lower": [], "bb_middle": [], "ema200": [], "volumes": []
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
    if last_operation_time and (datetime.now() - last_operation_time) > timedelta(seconds=6*60*60):
        current_levels = [RSI_CONFIG['dynamic_low'][i] for i in range(6)]
        default_levels = [RSI_CONFIG['levels'][i] for i in range(6)]
        
        if current_levels != default_levels:
            for i in range(6):
                RSI_CONFIG['dynamic_low'][i] = RSI_CONFIG['levels'][i]
            log(f"\n⏳ Níveis de RSI resetados para {symbol} por inatividade.")
        last_operation_time = datetime.now()

async def get_account_balances():
    if not api_key or not api_secret:
        return {'bnb': 0.0, 'bnb_usdt': 0.0, 'usdt': 0.0}
    client = None
    try:
        client = await BinanceAsyncClient.create(api_key, api_secret)
        bnb_balance = await client.get_asset_balance(asset='BNB')
        bnb_balance_free = float(bnb_balance['free'])
        bnb_price_usdt = await get_bnb_price(client)
        bnb_balance_usdt = bnb_balance_free * bnb_price_usdt
        usdt_balance = await get_usdt_balance(client)
        return {
            'bnb': bnb_balance_free, 'bnb_usdt': bnb_balance_usdt, 'usdt': usdt_balance
        }
    except Exception as e:
        print(f"Aviso ao buscar saldos: {e}")
        return {'bnb': 0.0, 'bnb_usdt': 0.0, 'usdt': 0.0}
    finally:
        if client:
            await client.close_connection()

async def run_bot(log_callback=None, investment_amount=None, selected_symbol=None, status_callback=None):
    global restart_attempts, bot_running, last_operation_time, stop_loss_count, last_stop_loss_time
    bot_running = True

    def log(msg, end='\n', flush=False):
        if log_callback: log_callback(msg)
        else: print(msg, end=end, flush=flush)

    def status(msg):
        if status_callback: status_callback(msg)
        bot_status_data['action'] = remove_ansi_codes(msg)

    if not api_key or not api_secret:
        log("⚠️ ATENÇÃO: As chaves da API Binance (mainnet_api_key e mainnet_secret_key) não estão preenchidas no arquivo .env.")
        log("👉 Por favor, edite o arquivo .env com suas chaves reais da Binance para conectar ao mercado ao vivo.")
        status("⚠️ Chaves API ausentes no .env")
        return

    async def handle_telegram_command(command):
        global bot_running
        cmd = command.split()[0].lower()
        if cmd == '/start': return "🤖 O bot já está rodando!"
        elif cmd == '/stop':
            bot_running = False
            return "🛑 Comando recebido. Parando o bot..."
        elif cmd == '/status':
            return (
                f"📊 <b>Status do Bot</b>\n"
                f"Moeda: <b>{bot_status_data['symbol']}</b>\n"
                f"Preço: <b>${bot_status_data['price']:.2f}</b>\n"
                f"RSI: <b>{bot_status_data['rsi']:.2f}</b>\n"
                f"Tendência: <b>{bot_status_data['trend']}</b>\n"
                f"Ação: {bot_status_data['action']}"
            )
        elif cmd == '/saldo':
            c = None
            try:
                c = await BinanceAsyncClient.create(api_key, api_secret)
                usdt = await get_usdt_balance(c)
                bnb = await c.get_asset_balance(asset='BNB')
                bnb_free = float(bnb['free'])
                bnb_price = await get_bnb_price(c)
                return f"💰 <b>Saldos</b>\nUSDT: <b>${usdt:.2f}</b>\nBNB: <b>{bnb_free:.4f} (~${bnb_free*bnb_price:.2f})</b>"
            except Exception as e:
                return f"Erro ao buscar saldo: {e}"
            finally:
                if c: await c.close_connection()
        elif cmd == '/ajuda':
            return "📚 <b>Comandos</b>: /status, /saldo, /stop, /ajuda"
        return "❓ Comando não reconhecido."

    if TELEGRAM_CONFIG.get('bot_token'):
        tg_bot = TelegramBot(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], handle_telegram_command)
        asyncio.create_task(tg_bot.start())

    total_difference = 0
    total_difference_liquid = 0
    gemini_response = None
    order_count = 0

    log("\n🚀 \033[5;33mBot SpotBot Pro iniciado!\033[0m 🚀\n")
    if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], "<b>🚀 Bot SpotBot Pro iniciado! 🚀</b>"))
    
    try:
        db = DatabaseManager()
        db.create_tables()
        db.migrate_from_csv()
    except Exception as e:
        log(f"⚠️ Aviso no banco de dados: {e}")

    await asyncio.sleep(1)
    client = None
    try:
        client = await BinanceAsyncClient.create(api_key, api_secret)
        bsm = BinanceSocketManager(client)
        
        bnb_balance = await client.get_asset_balance(asset='BNB')
        bnb_balance_free = float(bnb_balance['free'])
        bnb_price_usdt = await get_bnb_price(client)
        bnb_balance_usdt = bnb_balance_free * bnb_price_usdt
        
        saldo_inicial_usdt = await get_usdt_balance(client)
        log(f"💰 Saldo USDT disponível: \033[1;32m${saldo_inicial_usdt:.2f}\033[0m")

        if investment_amount is not None:
             if str(investment_amount).strip() == '100%':
                 quantia_usdt_investimento_inicial = saldo_inicial_usdt
             else:
                 try:
                     quantia_usdt_investimento_inicial = min(float(investment_amount), saldo_inicial_usdt)
                 except ValueError:
                     quantia_usdt_investimento_inicial = saldo_inicial_usdt
        else:
            quantia_usdt_investimento_inicial = saldo_inicial_usdt
        
        symbol = selected_symbol or TRADING_CONFIG.get("symbol", "BTCUSDT")
        log(f"\n🪙 Símbolo selecionado: {symbol}")
        
        await cancel_all_oco_orders(client, symbol)
        
        symbol_info = await client.get_symbol_info(symbol)
        tick_size = float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'PRICE_FILTER')['tickSize'])
        quote_precision = int(symbol_info['quoteAssetPrecision'])

        while bot_running:
            try:
                klines = await get_klines(client, symbol, TRADING_CONFIG['interval'], TRADING_CONFIG['limit'])
                if not klines:
                    await asyncio.sleep(5)
                    continue
            except Exception as e:
                log(f"Erro ao buscar klines: {e}")
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
                    shared_market_data['dates'] = [datetime.fromtimestamp(int(k[0])/1000).strftime('%H:%M') for k in recent_klines]
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

            bot_status_data['symbol'] = symbol
            bot_status_data['price'] = closes[-1]
            bot_status_data['rsi'] = rsi
            bot_status_data['trend'] = "Alta" if check_trend(klines) else "Baixa/Neutro"
            
            status(f"📊 RSI Atual ({symbol}): {rsi:.1f} | Preço: ${closes[-1]:.2f}")
            
            if volumes_series.iloc[-1] > volume_ma * (1 + TRADING_CONFIG['volume_avg'] / 100):
                status("⚠️ Alto volume detectado (Volatilidade). Operação em espera.")
                await asyncio.sleep(1)
                continue
                
            trend_is_up = check_trend(klines)
            candle_patterns = check_candle_patterns(klines)
            market_downward = is_market_downward(klines)
            
            await check_rsi_reset(symbol, log=log)
            
            if await should_place_order(client, symbol, status_callback=status) and not market_downward:
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
                                              candle_low, candle_close, candle_volume, variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, client, symbol, klines)
                
                if buy_result.get('gemini_analysis'):
                     shared_market_data['gemini_insight'] = buy_result['gemini_analysis']

                if buy_result["buy"]:
                    executed_condition = buy_result["message"]
                    log(f"🟢 Sinal de COMPRA ativado! Condição: {executed_condition}")
                    
                    min_notional = get_min_notional(symbol_info)
                    if quantia_usdt_investimento_inicial < min_notional:
                        log(f"⚠️ Saldo insuficiente (${quantia_usdt_investimento_inicial:.2f}) para o mínimo exigido (${min_notional}).")
                        await asyncio.sleep(5)
                        continue

                    async with bsm.user_socket() as um:
                        order_count += 1
                        compra = await client.order_market_buy(symbol=symbol, quoteOrderQty=round(quantia_usdt_investimento_inicial, quote_precision))
                        executed_qty = float(compra['executedQty'])
                        price = float(compra['fills'][0]['price'])
                        timestamp = datetime.now().strftime("%d/%m/%Y at %H:%M:%S")
                        
                        log(f"✅️ ({order_count:02d}) Comprado: {symbol} - Quantidade: {executed_qty} - Preço: ${price:.4f}")
                        purchase_timestamp = timestamp
                        gemini_response = buy_result.get("gemini_response")

                        oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit = await adjust_and_place_oco_order(client, symbol, executed_qty, tick_size, tick_size, klines)
                        last_operation_time = datetime.now()

                        highest_price = price
                        current_stop_loss = stop_loss

                        while True:
                            try:
                                msg = await asyncio.wait_for(um.recv(), timeout=5)
                            except asyncio.TimeoutError:
                                try:
                                    cur_price = float((await client.get_symbol_ticker(symbol=symbol))['price'])
                                    status(f"⏳ Monitorando OCO... Preço Atual: ${cur_price:.2f}")
                                    
                                    if TRAILING_STOP_CONFIG['enabled'] and cur_price > highest_price:
                                        highest_price = cur_price
                                        if highest_price > price * (1 + TRAILING_STOP_CONFIG['activation_percent']):
                                            new_stop = adjust_price_to_tick_size(highest_price * (1 - TRAILING_STOP_CONFIG['callback_percent']), tick_size)
                                            if new_stop > current_stop_loss * 1.001:
                                                log(f"🔄 Trailing Stop acionado! Movendo stop para ${new_stop:.4f}")
                                                await client.cancel_order(symbol=symbol, orderListId=oco_order['orderListId'])
                                                new_stop_limit = adjust_price_to_tick_size(new_stop * 0.999, tick_size)
                                                oco_order = await client.create_oco_order(
                                                    symbol=symbol, side='SELL', quantity=executed_qty,
                                                    price=f"{lucro_alvo:.{get_precision(tick_size)}f}",
                                                    stopPrice=f"{new_stop:.{get_precision(tick_size)}f}",
                                                    stopLimitPrice=f"{new_stop_limit:.{get_precision(tick_size)}f}",
                                                    stopLimitTimeInForce='GTC'
                                                )
                                                limit_order_id = oco_order['orders'][1]['orderId']
                                                stop_order_id = oco_order['orders'][0]['orderId']
                                                current_stop_loss = new_stop
                                except Exception:
                                    pass
                                continue

                            if msg.get('e') == 'listStatus' and msg.get('s') == symbol and msg.get('g') == oco_order['orderListId']:
                                if 'ALL_DONE' in msg.get('l'):
                                    limit_details = await get_order_details(client, symbol, limit_order_id)
                                    stop_details = await get_order_details(client, symbol, stop_order_id)

                                    symbol, order_result, trade_result, novo_saldo_usdt, oco_timestamp, fee, trade_result_liquid = await process_order_details(
                                        symbol, client, limit_details, stop_details, price, executed_qty, quantia_usdt_investimento_inicial
                                    )

                                    total_difference += trade_result
                                    total_difference_liquid += trade_result_liquid
                                    quantia_usdt_investimento_inicial = novo_saldo_usdt
                                    
                                    bnb_balance_free = float((await client.get_asset_balance(asset='BNB'))['free'])
                                    bnb_price = await get_bnb_price(client)
                                    
                                    if order_result:
                                        log_and_notify_results(order_result, symbol, trade_result, total_difference, oco_timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_free * bnb_price)
                                        data_row = create_data_row(
                                            order_count, saldo_inicial_usdt, quantia_usdt_investimento_inicial, symbol,
                                            executed_qty, price, purchase_timestamp, lucro_alvo, stop_loss, stop_limit,
                                            order_result, oco_timestamp, trade_result, total_difference, novo_saldo_usdt,
                                            rsi, executed_condition, vwap, candle_open, candle_high, candle_low, candle_close, candle_volume, 
                                            variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, candle_patterns, TRADING_CONFIG['volume_avg'], 
                                            amplitude, macd_current, signal_line_current, lower_band, middle_band, upper_band, trend_is_up, fee, trade_result_liquid,
                                            total_difference_liquid, gemini_response, bnb_balance_free * bnb_price
                                        )
                                        save_to_csv(data_row)
                                        
                                        if stop_details['status'] == 'FILLED':
                                            stop_loss_count += 1
                                            last_stop_loss_time = datetime.now()
                                            await check_stop_losses(last_stop_loss_time, log=log)
                                        else:
                                            stop_loss_count = 0
                                        break

            await asyncio.sleep(1)

    except asyncio.CancelledError:
        log("\n🛑 Bot parado pelo usuário.")
    except Exception as e:
        log(f"\n⚠️ Erro de execução: {e}")
    finally:
        if client:
            await client.close_connection()
