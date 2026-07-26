import asyncio
import os
import time
import math
import pandas as pd
from datetime import datetime, timedelta
from binance import BinanceSocketManager
from binance import AsyncClient as BinanceAsyncClient
from binance.exceptions import BinanceAPIException

from config.settings import API_KEYS, TELEGRAM_CONFIG, TRADING_CONFIG, RSI_CONFIG, TRAILING_STOP_CONFIG, SCANNER_CONFIG, TOP_20_SYMBOLS
from services.binance_client import extract_closes, extract_volumes, get_usdt_balance, get_order_details, get_klines, get_bnb_price, get_multi_klines
from core.indicators import (
    calculate_rsi, calculate_macd, calculate_bollinger_bands, check_trend, check_candle_patterns,
    calculate_vwap, get_candle_details, calculate_ema, is_market_downward, calculate_relative_strength_rank
)
from core.decision import should_place_order, should_buy, should_sell, adjust_and_place_oco_order, get_min_notional, adjust_price_to_tick_size, get_precision, calculate_dynamic_position_slots
from core.post_trade import process_order_details, log_and_notify_results, create_data_row, save_to_csv
from services.telegram_notifier import send_telegram_message, send_telegram_document, TelegramBot
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
bot_status_data = {
    "rsi": 0, "price": 0, "symbol": "", "action": "Iniciando...", "trend": "N/A", "target_asset": "BTCUSDT"
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
        await sync_binance_time(client, log=lambda m: None)
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
            return (
                f"⚡ <b>STATUS DO SPOTBOT PRO</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Modo</b>: {bot_status_data['symbol']}\n"
                f"🪙 <b>Foco Atual</b>: <b>{target_asset}</b>\n"
                f"💵 <b>Preço</b>: <b>${bot_status_data['price']:.2f}</b>\n"
                f"📊 <b>RSI</b>: <b>{bot_status_data['rsi']:.1f}</b>\n"
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
                
                return (
                    f"💰 <b>SALDOS & POSIÇÕES DA CARTEIRA</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"💵 <b>USDT Disponível</b>: <b>${usdt:.2f}</b>\n"
                    f"🪙 <b>Saldo BNB</b>: <b>{bnb_free:.4f} BNB</b> (~${bnb_free*bnb_price:.2f})\n"
                    f"📈 <b>Lucro Acumulado</b>: <b>${acc_pnl:.2f} USDT</b>\n"
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

        elif cmd == '/ajuda':
            return (
                "📚 <b>COMANDOS DISPONÍVEIS (SPOTBOT PRO)</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "/status - Exibe o ativo em foco, RSI e status do robô\n"
                "/saldo - Exibe saldos USDT, BNB e cálculo de slots\n"
                "/top20 ou /scanner - Varre a força relativa dos Top 20 ativos\n"
                "/lucro ou /perf - Exibe o lucro total líquido acumulado\n"
                "/relatorio ou /pdf - Gera e envia o Relatório Executivo em PDF\n"
                "/stop - Pausa a execução remota com segurança\n"
                "/cancel ou /abort - Interrupção imediata de emergência (CTRL+C)\n"
                "/ajuda - Exibe esta mensagem de ajuda"
            )
        return "❓ Comando não reconhecido. Digite /ajuda para ver as opções."

    if TELEGRAM_CONFIG.get('bot_token'):
        tg_bot = TelegramBot(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], handle_telegram_command)
        asyncio.create_task(tg_bot.start())

    total_difference = 0
    total_difference_liquid = 0
    gemini_response = None
    order_count = 0

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
        
        await cancel_all_oco_orders(client, symbol)
        
        symbol_info = await client.get_symbol_info(symbol)
        tick_size = float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'PRICE_FILTER')['tickSize'])
        quote_precision = int(symbol_info['quoteAssetPrecision'])

        last_sync_hour = datetime.now().hour
        last_pdf_sent_day = None

        while bot_running:
            try:
                current_dt = datetime.now()
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

                usdt_balance = await get_usdt_balance(client)
                
                db_stats = db.get_stats()
                acc_pnl = db_stats['total_net_profit']
                slots, slot_value = calculate_dynamic_position_slots(usdt_balance, accumulated_net_profit=acc_pnl)

                active_target_symbol = symbol
                if is_scanner_mode:
                    status("⚡ Scanner 2.0 avaliando Força Relativa (RS vs BTC) dos Top 20 Criptoativos...")
                    multi_klines = await get_multi_klines(client, TOP_20_SYMBOLS, TRADING_CONFIG['interval'], TRADING_CONFIG['limit'])
                    ranked_assets = calculate_relative_strength_rank(multi_klines)
                    if ranked_assets:
                        active_target_symbol = ranked_assets[0]['symbol']
                        shared_market_data['scanner_results'] = ranked_assets

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
                    
                    if buy_result.get('gemini_analysis'):
                         shared_market_data['gemini_insight'] = buy_result['gemini_analysis']

                    if buy_result["buy"]:
                        executed_condition = buy_result["message"]
                        log(f"🟢 Sinal de COMPRA em {active_target_symbol}! Condição: {executed_condition}")
                        
                        target_symbol_info = await client.get_symbol_info(active_target_symbol)
                        min_notional = get_min_notional(target_symbol_info)
                        
                        pos_multiplier = buy_result.get('position_multiplier', 1.0)
                        safe_usdt_limit = math.floor(usdt_balance * 0.99 * 100) / 100.0
                        order_val_usdt = max(min_notional, min(safe_usdt_limit, round(slot_value * pos_multiplier, 2)))

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
                                f"💰 Valor: <b>${order_val_usdt:.2f} USDT</b> (Juros Compostos Ativo)"
                            ))

                        order_count += 1
                        compra = await client.order_market_buy(symbol=active_target_symbol, quoteOrderQty=round(order_val_usdt, quote_precision))
                        executed_qty = float(compra['executedQty'])
                        price = float(compra['fills'][0]['price'])
                        timestamp = datetime.now().strftime("%d/%m/%Y at %H:%M:%S")
                        
                        log(f"✅️ ({order_count:02d}) Comprado: {active_target_symbol} - Qtd: {executed_qty} - Preço: ${price:.4f}")
                        purchase_timestamp = timestamp
                        gemini_response = buy_result.get("gemini_response")

                        oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit = await adjust_and_place_oco_order(client, active_target_symbol, executed_qty, tick_size, tick_size, klines)
                        last_operation_time = datetime.now()

                        highest_price = price
                        current_stop_loss = stop_loss
                        partial_take_done = False

                        # Loop Resiliente de Monitoramento da Ordem (WebSocket com Fallback automático para REST Polling)
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
                                            
                                            profit_pct = (cur_price - price) / price

                                            if profit_pct >= 0.015 and not partial_take_done:
                                                try:
                                                    step_size = float(next(f for f in target_symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')['stepSize'])
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
                                                        
                                                        oco_order = await client.create_oco_order(
                                                            symbol=active_target_symbol, side='SELL', quantity=rem_qty,
                                                            price=f"{lucro_alvo:.{get_precision(tick_size)}f}",
                                                            stopPrice=f"{be_stop:.{get_precision(tick_size)}f}",
                                                            stopLimitPrice=f"{be_limit:.{get_precision(tick_size)}f}",
                                                            stopLimitTimeInForce='GTC'
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
                                                        oco_order = await client.create_oco_order(
                                                            symbol=active_target_symbol, side='SELL', quantity=executed_qty if not partial_take_done else rem_qty,
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
                                                log_and_notify_results(order_result, active_target_symbol, trade_result, total_difference, oco_timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_free * bnb_price)
                                                data_row = create_data_row(
                                                    order_count, saldo_inicial_usdt, novo_saldo_usdt, active_target_symbol,
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
                        except Exception as ws_err:
                            use_ws_monitoring = False
                            log(f"⚠️ Conexão WebSocket instável ({ws_err}). Alternando automaticamente para monitoramento de ordem por REST Polling...")

                        # Robust Fallback REST Polling se o WebSocket instabilizar
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
                                            log_and_notify_results(order_result, active_target_symbol, trade_result, total_difference, oco_timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_free * bnb_price)
                                            data_row = create_data_row(
                                                order_count, saldo_inicial_usdt, novo_saldo_usdt, active_target_symbol,
                                                executed_qty, price, purchase_timestamp, lucro_alvo, stop_loss, stop_limit,
                                                order_result, oco_timestamp, trade_result, total_difference, novo_saldo_usdt,
                                                rsi, executed_condition, vwap, candle_open, candle_high, candle_low, candle_close, candle_volume, 
                                                variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, candle_patterns, TRADING_CONFIG['volume_avg'], 
                                                amplitude, macd_current, signal_line_current, lower_band, middle_band, upper_band, trend_is_up, fee, trade_result_liquid,
                                                total_difference_liquid, gemini_response, bnb_balance_free * bnb_price
                                            )
                                            save_to_csv(data_row)
                                            break
                                except Exception as poll_err:
                                    status(f"⚠️ Polling de Ordem: {poll_err}")
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
        if client:
            await client.close_connection()
