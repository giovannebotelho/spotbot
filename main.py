import asyncio
# import winsound
import os
import pandas as pd
from datetime import datetime, timedelta
from binance import BinanceSocketManager
from binance import AsyncClient as BinanceAsyncClient
from binance.exceptions import BinanceAPIException

from config import API_KEYS, TELEGRAM_CONFIG, TRADING_CONFIG, RSI_CONFIG, TRAILING_STOP_CONFIG
from pre_start import escolher_simbolo, cancel_all_oco_orders
from binance_api import extract_closes, extract_volumes, get_usdt_balance, get_order_details, get_klines, get_bnb_price
from trading_functions import calculate_rsi, calculate_macd, calculate_bollinger_bands, check_trend, check_candle_patterns, calculate_vwap, get_candle_details, calculate_ema, is_market_downward
from decision import should_place_order, should_buy, should_sell, adjust_and_place_oco_order, get_min_notional
from post_trade import process_order_details, log_and_notify_results, create_data_row, save_to_csv
from telegram_integration import send_telegram_message
from telegram_bot import TelegramBot

# Seleciona o ambiente com base na variável de ambiente
environment = os.getenv("BOT_ENVIRONMENT", "mainnet")  # Valor padrão: mainnet

if environment == "mainnet":
    api_key = API_KEYS['mainnet']['key']
    api_secret = API_KEYS['mainnet']['secret']
elif environment == "testnet":
    api_key = API_KEYS['testnet_spot']['key']
    api_secret = API_KEYS['testnet_spot']['secret']
else:
    raise ValueError(f"Ambiente inválido: {environment}")

# Variáveis globais
quantia_usdt_investimento_inicial = None
symbol = None

limit_order_id = None
stop_order_id = None

SHORT_PAUSE = 600  # Alterado para 600 segundos (10 minutos)
LONG_PAUSE = 3600  # Mantido em 3600 segundos (1 hora)

stop_loss_count = 0
last_stop_loss_time = None
block_active = False
pause_end_time = None

MAX_RESTARTS = 3
restart_attempts = 0

# Adicionando a variável global para o tempo da última operação
last_operation_time = None

# Global flag to control the bot loop
bot_running = True

# Shared status for Telegram Bot
bot_status_data = {
    "rsi": 0,
    "price": 0,
    "symbol": "",
    "action": "Iniciando...",
    "trend": "N/A"

}

# New: Shared Market Data for Dashboard (Charts)
shared_market_data = {
    "klines": [],     # List of [time, open, close, low, high]
    "dates": [],      # List of timestamps
    "bb_upper": [],
    "bb_lower": [],
    "bb_middle": [],
    "ema200": []
}

def remove_ansi_codes(text):
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

async def check_stop_losses(current_time, log=print):
    global stop_loss_count, last_stop_loss_time, block_active, pause_end_time

    # Se houver uma pausa longa ativa e chegamos ao tempo de fim da pausa
    if block_active and current_time > pause_end_time:
        block_active = False
        pause_end_time = None
        # Não zera o stop_loss_count aqui

    # Verifica se o último stop loss foi há menos de 15 minutos (900 segundos)
    if last_stop_loss_time and (current_time - last_stop_loss_time) < timedelta(seconds=900):
        # Se sim, e se já houve pelo menos um stop loss antes (stop_loss_count > 0),
        # temos 2 ou mais stop losses em menos de 15 minutos
        if stop_loss_count > 1:
            # Pausa longa (1 hora) e reseta o contador
            log("🚨 Mais de 1 stop loss detectado dentro de 15 minutos. Bloqueando o bot por 1 hora.\n")
            message = "🚨 Mais de 1 stop loss detectado dentro de 15 minutos. Bloqueando o bot por 1 hora."
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))

            pause_end_time = current_time + timedelta(seconds=LONG_PAUSE)
            block_active = True
            stop_loss_count = 0  # Reseta o contador após a pausa longa
            last_stop_loss_time = current_time  # Atualiza o último stop loss

            await asyncio.sleep(LONG_PAUSE)
            log("\n ✅️ Voltando a operar após pausa de 1 hora.")
            message = "✅️ Voltando a operar após pausa de 1 hora."
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
            return  # Importante: retorna da função após a pausa longa
    else:
        # Se não houve stop loss recente (mais de 15 minutos), reseta o contador
        stop_loss_count = 0

    # Se chegou aqui, significa que não houve pausa longa
    if stop_loss_count == 1:
        # Primeiro stop loss, então incrementa o contador
        stop_loss_count += 1
        # Pausa curta (10 minutos)
        log("🚨 Stop loss detectado. Pausando o bot por 10 minutos.")
        message = "🚨 Stop loss detectado. Pausando o bot por 10 minutos."
        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))

        pause_end_time = current_time + timedelta(seconds=SHORT_PAUSE)
        last_stop_loss_time = current_time  # Atualiza o último stop loss

        await asyncio.sleep(SHORT_PAUSE)
        log("\n ✅️ Voltando a operar após pausa de 10 minutos.\n")
        message = "✅️ Voltando a operar após pausa de 10 minutos."
        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
   
async def check_rsi_reset(symbol, log=print):
    global last_operation_time
    
    # Using RSI_CONFIG dictionary directly
    
    if last_operation_time and (datetime.now() - last_operation_time) > timedelta(seconds=6*60*60):
        # Verifica se os níveis de RSI dinâmicos são iguais aos níveis padrão
        current_levels = [RSI_CONFIG['dynamic_low'][i] for i in range(6)]
        default_levels = [RSI_CONFIG['levels'][i] for i in range(6)] # Assuming 'levels' holds the defaults (rsi_low_level_X)
        
        # Wait, in config.py 'levels' holds rsi_low_level_0...5
        # So we compare dynamic_low with levels
        
        if current_levels == default_levels:
            log(f"\n⏳ Níveis de RSI já estão em Standard para {symbol}.\n")
            message = f"⏳ Níveis de RSI já estão em Standard para <b>{symbol}</b>."
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        else:
            # Atualiza os níveis de RSI dinâmicos para os valores padrão
            for i in range(6):
                RSI_CONFIG['dynamic_low'][i] = RSI_CONFIG['levels'][i]
                
            log(f"\n⏳ Níveis de RSI resetados para {symbol} devido à inatividade.")
            message = f"⏳ Níveis de RSI resetados para <b>{symbol}</b> devido à inatividade."
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))

        last_operation_time = datetime.now()  # Atualiza para evitar reset em loop

async def get_account_balances():
    """Fetches BNB and USDT balances for the UI."""
    try:
        client = await BinanceAsyncClient.create(api_key, api_secret)
        bnb_balance = await client.get_asset_balance(asset='BNB')
        bnb_balance_free = float(bnb_balance['free'])
        bnb_price_usdt = await get_bnb_price(client)
        bnb_balance_usdt = bnb_balance_free * bnb_price_usdt
        
        usdt_balance = await get_usdt_balance(client)
        
        await client.close_connection()
        return {
            'bnb': bnb_balance_free,
            'bnb_usdt': bnb_balance_usdt,
            'usdt': usdt_balance
        }
    except Exception as e:
        print(f"Erro ao buscar saldos: {e}")
        return None

async def run_bot(log_callback=None, investment_amount=None, selected_symbol=None, status_callback=None):
    global restart_attempts, quantia_usdt_investimento_inicial
    global limit_order_id, stop_order_id
    global stop_loss_count, last_stop_loss_time, block_active, pause_end_time
    global last_operation_time, bot_running
    
    bot_running = True

    def log(msg, end='\n', flush=False):
        if log_callback:
            log_callback(msg)
        else:
            print(msg, end=end, flush=flush)

    def status(msg):
        if status_callback:
            status_callback(msg)
        # Also update global status for Telegram
        bot_status_data['action'] = remove_ansi_codes(msg)

    # Telegram Command Handler
    async def handle_telegram_command(command):
        global bot_running
        cmd = command.split()[0].lower()
        
        if cmd == '/start':
            return "🤖 O bot já está rodando!"
        
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
            try:
                usdt = await get_usdt_balance(client)
                bnb = await client.get_asset_balance(asset='BNB')
                bnb_free = float(bnb['free'])
                
                # Calculate BNB value in USDT
                bnb_price = await get_bnb_price(client)
                bnb_usdt = bnb_free * bnb_price
                
                return f"💰 <b>Saldos</b>\nUSDT: <b>${usdt:.2f}</b>\nBNB: <b>{bnb_free:.4f} (~${bnb_usdt:.2f})</b>"
            except Exception as e:
                return f"Erro ao buscar saldo: {e}"
        
        elif cmd == '/ajuda':
            return (
                "📚 <b>Comandos Disponíveis</b>\n"
                "/status - Ver preço, RSI e ação atual\n"
                "/saldo - Ver saldo em USDT e BNB\n"
                "/stop - Parar o bot\n"
                "/ajuda - Ver esta mensagem"
            )
            
        return "❓ Comando não reconhecido. Tente /ajuda."

    # Start Telegram Bot Task
    if TELEGRAM_CONFIG['bot_token']:
        tg_bot = TelegramBot(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], handle_telegram_command)
        asyncio.create_task(tg_bot.start())
    else:
        log("⚠️ Token do Telegram não configurado. Comandos desativados.")


    # Inicializações
    total_difference = 0
    total_difference_liquid = 0
    gemini_response = None
    order_count = 0
    saldo_inicial_usdt = 0 # Initialize
    
    log("\n🚀 \033[5;33mBot iniciado!\033[0m 🚀\n")
    message = "<b>🚀 Bot iniciado! 🚀</b>"
    asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
    
    # synchronize_time()  # Removed as per user request
    
    # Initialize Database and Migrate if needed
    from database import DatabaseManager
    try:
        db = DatabaseManager()
        db.create_tables()
        db.migrate_from_csv()
    except Exception as e:
        log(f"⚠️ Erro ao inicializar banco de dados: {e}")

    await asyncio.sleep(1)
    try:
        client = await BinanceAsyncClient.create(api_key, api_secret)
        # Inicializa o BSM fora do loop, mas não abre o socket ainda
        bsm = BinanceSocketManager(client)
        
        # Obter e mostrar saldo de BNB
        bnb_balance = await client.get_asset_balance(asset='BNB')
        bnb_balance_free = float(bnb_balance['free'])
        bnb_price_usdt = await get_bnb_price(client)
        bnb_balance_usdt = bnb_balance_free * bnb_price_usdt
        
        log(f"💰 Saldo BNB: \033[1;33m{bnb_balance_free:.4f}\033[0m (~${bnb_balance_usdt:.2f})")
        message = f"💰 Saldo BNB: <b>{bnb_balance_free:.4f}</b> (~${bnb_balance_usdt:.2f})"
        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))

        # Obter saldo inicial de USDT
        saldo_inicial_usdt = await get_usdt_balance(client)
        log(f"💰 Saldo USDT disponível: \033[1;32m${saldo_inicial_usdt:.2f}\033[0m")
        message = f"💰 Saldo USDT disponível: <b>${saldo_inicial_usdt:.2f}</b>"
        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))

        # Input do valor a investir
        if investment_amount is not None:
             if str(investment_amount).strip() == '100%':
                 quantia_usdt_investimento_inicial = saldo_inicial_usdt
             else:
                 try:
                     quantia_usdt_investimento_inicial = float(investment_amount)
                     if quantia_usdt_investimento_inicial > saldo_inicial_usdt:
                         log(f"⚠️ Valor solicitado maior que o saldo. Ajustando para o saldo total: ${saldo_inicial_usdt:.2f}")
                         quantia_usdt_investimento_inicial = saldo_inicial_usdt
                 except ValueError:
                     log("❌ Valor de investimento inválido. Usando saldo total.")
                     quantia_usdt_investimento_inicial = saldo_inicial_usdt
        else:
            while True:
                print("\nQuanto você quer investir em USDT? (Digite o valor ou '100%' para tudo)")
                user_input = input("Valor: ").strip()
                
                if user_input == '100%':
                    quantia_usdt_investimento_inicial = saldo_inicial_usdt
                    break
                else:
                    try:
                        amount = float(user_input)
                        if 0 < amount <= saldo_inicial_usdt:
                            quantia_usdt_investimento_inicial = amount
                            break
                        else:
                            print(f"❌ Valor inválido. Digite um valor entre 0 e {saldo_inicial_usdt:.2f}")
                    except ValueError:
                        print("❌ Entrada inválida. Digite um número ou '100%'.")
        
        log(f"\n✅ Valor definido para investimento: \033[1;32m${quantia_usdt_investimento_inicial:.2f}\033[0m")
        message = f"✅ Valor definido para investimento: <b>${quantia_usdt_investimento_inicial:.2f}</b>"
        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        
        # Escolher símbolo
        global symbol
        if selected_symbol:
            symbol = selected_symbol
            log(f"\n🪙 Símbolo selecionado via Dashboard: {symbol}")
            message = f"🪙 Símbolo selecionado via Dashboard: <b>{symbol}</b>"
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        else:
            symbol = escolher_simbolo()
        
        # Cancelar ordens abertas
        await cancel_all_oco_orders(client, symbol)
        
        # Obter precisão do símbolo
        symbol_info = await client.get_symbol_info(symbol)
        tick_size = float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'PRICE_FILTER')['tickSize'])
        min_price_move = tick_size # Assuming min_price_move is tick_size
        quote_precision = int(symbol_info['quoteAssetPrecision'])

        # Loop principal
        while bot_running:
            # Fetch klines once per iteration
            try:
                klines = await get_klines(client, symbol, TRADING_CONFIG['interval'], TRADING_CONFIG['limit'])
                if not klines:
                    log("Erro ao obter klines, tentando novamente...")
                    await asyncio.sleep(5)
                    continue
            except Exception as e:
                log(f"Erro ao obter klines: {e}")
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

            # --- Populating Shared Data for Dashboard (Moved) ---
            try:
                chart_limit = 50
                if len(klines) > chart_limit:
                    recent_klines = klines[-chart_limit:]
                    
                    shared_market_data['dates'] = [datetime.fromtimestamp(int(k[0])/1000).strftime('%H:%M') for k in recent_klines]
                    # ECharts Candle: [Open, Close, Low, High]
                    shared_market_data['klines'] = [[float(k[1]), float(k[4]), float(k[3]), float(k[2])] for k in recent_klines]
                    # Volume: [Value]
                    shared_market_data['volumes'] = [float(k[5]) for k in recent_klines]
                    
                    s_closes = pd.Series(closes)
                    
                    r = s_closes.rolling(window=20)
                    ma = r.mean()
                    std = r.std()
                    upper = ma + (2 * std)
                    lower = ma - (2 * std)
                    s_ema200 = s_closes.ewm(span=200, adjust=False).mean()

                    shared_market_data['bb_upper'] = upper.tail(chart_limit).fillna(0).tolist()
                    shared_market_data['bb_middle'] = ma.tail(chart_limit).fillna(0).tolist()
                    shared_market_data['bb_lower'] = lower.tail(chart_limit).fillna(0).tolist()
                    shared_market_data['ema200'] = s_ema200.tail(chart_limit).fillna(0).tolist()
            except Exception as e:
                pass
                # print(f"DEBUG: Error updating shared data: {e}")
            # ---------------------------------------------
            
            # Update Telegram Status Data
            bot_status_data['symbol'] = symbol
            bot_status_data['price'] = closes[-1]
            bot_status_data['rsi'] = rsi
            bot_status_data['trend'] = "Alta" if check_trend(klines) else "Baixa/Neutro"
            
            # ... (prints unchanged) ...
            msg_rsi = f"📊 RSI Atual para {symbol}: \033[1;33m{rsi:.1f}\033[0m"
            status(msg_rsi)
            await asyncio.sleep(0.6)
            # log("\033[2K\r", end='') # Avoid clearing line in logs for now, or handle differently
            await asyncio.sleep(0.15)
            
            if symbol == "ADAUSDT" or symbol == "DOGEUSDT":
                msg_macd = f"📊 MACD Atual para {symbol}: \033[1;33m{macd_current:.4f}\033[0m, Linha de sinal: \033[1;33m{signal_line_current:.4f}\033[0m"
            else:
                msg_macd = f"📊 MACD Atual para {symbol}: \033[1;33m{macd_current:.2f}\033[0m, Linha de sinal: \033[1;33m{signal_line_current:.2f}\033[0m"
            status(msg_macd)
            await asyncio.sleep(0.6)
            # log("\033[2K\r", end='')
            await asyncio.sleep(0.15)
            
            if symbol == "ADAUSDT" or symbol == "DOGEUSDT":
                msg_bb = f"📊 Bandas de Bollinger para {symbol}: Inferior: \033[1;31m${lower_band:.4f}\033[0m, Média: \033[1;33m${middle_band:.4f}\033[0m, Superior: \033[1;32m${upper_band:.4f}\033[0m"
            else:
               msg_bb = f"📊 Bandas de Bollinger para {symbol}: Inferior: \033[1;31m${lower_band:.2f}\033[0m, Média: \033[1;33m${middle_band:.2f}\033[0m, Superior: \033[1;32m${upper_band:.2f}\033[0m"
            status(msg_bb)
            await asyncio.sleep(0.6)
            # log("\033[2K\r", end='')
            await asyncio.sleep(0.15)
            
            msg_vwap = f"📊 VWAP Atual para {symbol}: \033[1;33m{vwap:.2f}\033[0m"
            status(msg_vwap)
            await asyncio.sleep(0.6)
            # log("\033[2K\r", end='')
            await asyncio.sleep(0.15)

            if volumes_series.iloc[-1] > volume_ma * (1 + TRADING_CONFIG['volume_avg'] / 100):
                msg = f"⚠️ Alto volume detectado, possível \033[1;33mvolatilidade de mercado\033[0m. Operação suspensa."
                status(msg)
                await asyncio.sleep(0.6)
                # log("\033[2K\r", end='')
                await asyncio.sleep(0.15)
                continue
                
            # Pass klines to functions
            trend_is_up = check_trend(klines) # Sync call now
            candle_patterns = check_candle_patterns(klines) # Sync call now
            
            market_downward = is_market_downward(klines) # Sync call now
            
            await check_rsi_reset(symbol, log=log)
            
            # Pass klines to should_buy
            if await should_place_order(client, symbol, status_callback=status) and not market_downward:
                
                candle_details = get_candle_details(klines) # Sync call now
                if candle_details:
                    candle_open = candle_details['open']
                    candle_high = candle_details['high']
                    candle_low = candle_details['low']
                    candle_close = candle_details['close']
                    candle_volume = candle_details['volume']
                    amplitude = ((candle_high - candle_low) / candle_open) * 100 if candle_open !=0 else 0
                else:
                    candle_open = 0
                    candle_high = 0
                    candle_low = 0
                    candle_close = 0
                    candle_volume = 0
                    amplitude = 0
                    
                # Calculate variation 24h
                try:
                    if len(klines) >= 25:
                        price_24h_ago = float(klines[-25][4])
                        candle_variation = ((candle_close - candle_open) / candle_open) * 100 if candle_open != 0 else 0
                        
                        ema7 = calculate_ema(closes, 7)
                        ema15 = calculate_ema(closes, 15)
                        ema25 = calculate_ema(closes, 25)
                        ema50 = calculate_ema(closes, 50)
                        ema100 = calculate_ema(closes, 100)
                        ema200 = calculate_ema(closes, 200)

                        # --- Populating Shared Data for Dashboard ---
                        # MOVED TO MAIN LOOP SCOPE
                        pass
                        # ---------------------------------------------
                    else:
                        price_24h_ago = 0
                        candle_variation = 0
                        ema7 = 0
                        ema15 = 0
                        ema25 = 0
                        ema50 = 0
                        ema100 = 0
                        ema200 = 0
                    
                    price_now = closes[-1] if closes else 0
                    variation_24h = ((price_now - price_24h_ago) / price_24h_ago) * 100 if price_24h_ago != 0 else 0
                
                except Exception as e:
                    price_24h_ago = 0
                    variation_24h = 0
                    candle_variation = 0
                    ema7 = 0
                    ema15 = 0
                    ema25 = 0
                    ema50 = 0
                    ema100 = 0
                    ema200 = 0
                    log(f"\nErro ao calcular variação de 24h: {e}")
                
                # Pass klines to should_buy
                buy_result = await should_buy(rsi, trend_is_up, macd_current, signal_line_current, closes[-1], lower_band, middle_band, upper_band, vwap, candle_patterns, candle_open, candle_high, 
                                              candle_low, candle_close, candle_volume, variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, client, symbol, klines)
                
                # Update shared data with Gemini Insight if available
                if buy_result.get('gemini_analysis'):
                     insight = buy_result['gemini_analysis']
                     shared_market_data['gemini_insight'] = insight
                     
                     shared_market_data['gemini_insight'] = insight
                     
                     # Restore log message for Gemini Buy Signal
                     if insight.get('signal'):
                         log(f"🟢 Sinal de \033[1;32m{insight.get('signal')}\033[0m recebido do Gemini ({insight.get('confidence', 'N/A')})...")
                
                if buy_result["buy"]:
                    executed_condition = buy_result["message"]
                    
                    log("### ------------------------- ###")
                    log(f"🟢 RSI: \033[1;32m{rsi:.1f}\033[0m, \033[1;32msinal de compra\033[0m encontrado!")
                    ticker = await client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                    if current_price < 1:
                        log(f"\nPreço Atual: 📈 \033[1;33m${current_price:.4f}\033[0m\n")
                    else:
                        log(f"\nPreço Atual: 📈 \033[1;33m${current_price:.2f}\033[0m\n")
                    
                    # Check Minimum Notional
                    min_notional = get_min_notional(symbol_info)
                    if quantia_usdt_investimento_inicial < min_notional:
                        log(f"⚠️ Saldo insuficiente (${quantia_usdt_investimento_inicial:.2f}) para o mínimo exigido pela Binance (${min_notional}). Operação cancelada.")
                        message = f"⚠️ <b>Saldo insuficiente</b> (${quantia_usdt_investimento_inicial:.2f}) para o mínimo exigido (${min_notional}). Operação cancelada."
                        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
                        await asyncio.sleep(5)
                        continue

                    # Start socket context ONLY when buying
                    async with bsm.user_socket() as um:
                        order_count += 1
                        
                        compra = await client.order_market_buy(symbol=symbol, quoteOrderQty=round(quantia_usdt_investimento_inicial, quote_precision))
                        executed_qty = float(compra['executedQty'])
                        price = float(compra['fills'][0]['price'])
                        timestamp = datetime.now().strftime("%d/%m/%Y at %H:%M:%S")
                        price_rounded = round(price, 4) if price < 1 else round(price, 2)
                        
                        log(f"✅️ \033[1;36m({order_count:02d})\033[0m Comprado: Moeda: \033[1;33m{symbol}\033[0m, Quantidade da Moeda: \033[1;33m{executed_qty}\033[0m, Preço: \033[1;33m${price_rounded}\033[0m \033[1;36m({timestamp})\033[0m\n")
                        # winsound.Beep(800, 1500) # Purchased: Coin.
                        message = f"✅️ ({order_count:02d}) <b>Comprado</b>: Moeda: <b>{symbol}</b>, Quantidade da Moeda: <b>{executed_qty}</b>, Preço: <b>${price_rounded} ({timestamp})</b>"
                        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
                        purchase_timestamp = timestamp
                        
                        log(executed_condition)
                        
                        if candle_patterns:
                            if len(candle_patterns) == 1:
                                log(f"\nPadrões de candle: {candle_patterns[0]}")
                            else:
                                log(f"\nPadrões de candle: {', '.join(candle_patterns)}")
                        else:
                            log("\nPadrões de candle: Nenhum encontrado")
                            
                        # Recalculate details for log (using same klines is fine, or fetch new? Using same is safer/faster)
                        candle_details = get_candle_details(klines)
                        if candle_details:
                            candle_open = candle_details['open']
                            candle_high = candle_details['high']
                            candle_low = candle_details['low']
                            candle_close = candle_details['close']
                            candle_volume = candle_details['volume']
                            amplitude = ((candle_high - candle_low) / candle_open) * 100 if candle_open !=0 else 0
                        else:
                            candle_open = 0
                            candle_high = 0
                            candle_low = 0
                            candle_close = 0
                            candle_volume = 0
                            amplitude = 0
                            
                        # Variation 24h (using klines)
                        try:
                            if len(klines) >= 25:
                                price_24h = float(klines[-25][4])
                                variation_24h = ((current_price - price_24h) / price_24h) * 100
                            else:
                                price_24h = 0
                                variation_24h = 0
                        except Exception as e:
                            price_24h = 0
                            variation_24h = 0
                            log(f"\nErro ao buscar dados para variação de 24h: {e}")

                        ema7 = calculate_ema(closes, 7)
                        ema15 = calculate_ema(closes, 15)
                        ema25 = calculate_ema(closes, 25)
                        ema50 = calculate_ema(closes, 50)
                        ema100 = calculate_ema(closes, 100)
                        ema200 = calculate_ema(closes, 200)
                        
                        candle_variation = ((candle_close - candle_open) / candle_open) * 100 if candle_open != 0 else 0
                        
                        macd_current, signal_line_current = calculate_macd(closes)
                        lower_band, middle_band, upper_band = calculate_bollinger_bands(closes)
                        
                        gemini_response = buy_result.get("gemini_response")
                                    
                        oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit = await adjust_and_place_oco_order(client, symbol, executed_qty, tick_size, min_price_move, klines)
                        
                        last_operation_time = datetime.now()
                        
                        # Await OCO order completion
                        highest_price = price
                        current_stop_loss = stop_loss
                        
                        while True:
                            try:
                                # Reduced timeout for frequent price checks
                                msg = await asyncio.wait_for(um.recv(), timeout=5) 
                            except asyncio.TimeoutError:
                                # UX: Update Status & Heartbeat
                                try:
                                    ticker = await client.get_symbol_ticker(symbol=symbol)
                                    cur_price = float(ticker['price'])
                                    status(f"⏳ Monitorando OCO... Preço: ${cur_price:.2f}")
                                    
                                    # Log heartbeat every ~60s (12 * 5s)
                                    if not hasattr(log, 'heartbeat_counter'): log.heartbeat_counter = 0
                                    log.heartbeat_counter += 1
                                    if log.heartbeat_counter >= 12:
                                        log(f"⏱️ Aguardando alvo ou stop... Preço: ${cur_price:.2f}")
                                        log.heartbeat_counter = 0
                                except Exception:
                                    pass
                                    
                                # Check for Trailing Stop
                                if TRAILING_STOP_CONFIG['enabled']:
                                    try:
                                        ticker = await client.get_symbol_ticker(symbol=symbol)
                                        current_market_price = float(ticker['price'])
                                        
                                        # Update highest price
                                        if current_market_price > highest_price:
                                            highest_price = current_market_price
                                            
                                        # Activation check
                                        activation_price = price * (1 + TRAILING_STOP_CONFIG['activation_percent'])
                                        if highest_price > activation_price:
                                            # Calculate new stop loss
                                            new_stop_loss = highest_price * (1 - TRAILING_STOP_CONFIG['callback_percent'])
                                            
                                            # Adjust to tick size
                                            new_stop_loss = adjust_price_to_tick_size(new_stop_loss, tick_size)
                                            
                                            # Check if new stop is higher than current (with some buffer to avoid spam)
                                            if new_stop_loss > current_stop_loss * 1.001:
                                                log(f"🔄 Trailing Stop: Preço subiu para ${highest_price:.4f}. Movendo Stop de ${current_stop_loss:.4f} para ${new_stop_loss:.4f}")
                                                
                                                # Cancel current OCO
                                                try:
                                                    await client.cancel_order(symbol=symbol, orderListId=oco_order['orderListId'])
                                                    log("❌ Ordem OCO antiga cancelada.")
                                                    
                                                    # Place NEW OCO
                                                    # Keep original Take Profit (lucro_alvo) or adjust? 
                                                    # Let's keep original TP for now to ensure target hit.
                                                    # BUT if new_stop_loss is >= lucro_alvo, we have a problem.
                                                    # If price is that high, maybe we should just let it ride or close?
                                                    # For now, assume TP is far enough. If not, we might need to move TP up too.
                                                    
                                                    stop_limit = new_stop_loss * 0.999
                                                    stop_limit = adjust_price_to_tick_size(stop_limit, tick_size)
                                                    
                                                    # Re-create OCO
                                                    oco_order = await client.create_oco_order(
                                                        symbol=symbol,
                                                        side='SELL',
                                                        quantity=quantity,
                                                        price=f"{lucro_alvo:.{get_precision(tick_size)}f}",
                                                        stopPrice=f"{new_stop_loss:.{get_precision(tick_size)}f}",
                                                        stopLimitPrice=f"{stop_limit:.{get_precision(tick_size)}f}",
                                                        stopLimitTimeInForce='GTC'
                                                    )
                                                    
                                                    order_list_id = oco_order.get('orderListId', 'N/A')
                                                    limit_order_id = oco_order['orders'][1]['orderId']
                                                    stop_order_id = oco_order['orders'][0]['orderId']
                                                    current_stop_loss = new_stop_loss
                                                    
                                                    log(f"✅ Nova OCO colocada (Trailing). ID: {order_list_id}. Novo Stop: ${new_stop_loss:.4f}")
                                                    message = f"🔄 <b>Trailing Stop</b>: Novo Stop em <b>${new_stop_loss:.4f}</b>"
                                                    asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
                                                    
                                                except Exception as e:
                                                    log(f"⚠️ Erro ao atualizar Trailing Stop: {e}")
                                    except Exception as e:
                                        log(f"⚠️ Erro no loop do Trailing Stop: {e}")

                                continue # Keep waiting

                            if msg.get('e') == 'listStatus' and msg.get('s') == symbol and msg.get('g') == oco_order['orderListId']:
                                if 'ALL_DONE' in msg.get('l'):
                                    limit_order_details = await get_order_details(client, symbol, limit_order_id)
                                    stop_order_details = await get_order_details(client, symbol, stop_order_id)

                                    symbol, order_result, trade_result, novo_saldo_usdt, oco_timestamp, fee, trade_result_liquid = await process_order_details(symbol, client, limit_order_details, 
                                                                                                                                                                stop_order_details, price, executed_qty, 
                                                                                                                                                                quantia_usdt_investimento_inicial)

                                    saldo_atual_usdt = novo_saldo_usdt
                                    total_difference += trade_result
                                    total_difference_liquid += trade_result_liquid
                                    quantia_usdt_investimento_inicial = saldo_atual_usdt
                                    
                                    bnb_balance = await client.get_asset_balance(asset='BNB')
                                    bnb_balance = float(bnb_balance['free'])
                                    bnb_price_usdt = await get_bnb_price(client)
                                    bnb_balance_usdt = bnb_balance * bnb_price_usdt
                                    
                                    if order_result:
                                        log_and_notify_results(order_result, symbol, trade_result, total_difference, oco_timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_usdt)
                                        
                                        data_row = create_data_row(order_count, saldo_inicial_usdt, quantia_usdt_investimento_inicial, symbol,
                                                                    executed_qty, price_rounded, purchase_timestamp, lucro_alvo, stop_loss, stop_limit,
                                                                    order_result, oco_timestamp, trade_result, total_difference, saldo_atual_usdt,
                                                                    rsi, executed_condition, vwap, candle_open, candle_high, candle_low, candle_close, candle_volume, 
                                                                    variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, candle_patterns, TRADING_CONFIG['volume_avg'], 
                                                                    amplitude, macd_current, signal_line_current, lower_band, middle_band, upper_band, trend_is_up, fee, trade_result_liquid,
                                                                    total_difference_liquid, gemini_response, bnb_balance_usdt)
                                        save_to_csv(data_row)
                                    
                                        log(f"Saldo atual investido em USDT: \033[1;36m${quantia_usdt_investimento_inicial:.2f}\033[0m\n")
                                        message_2 = f'Saldo atual investido em USDT: <b>${quantia_usdt_investimento_inicial:.2f}</b>'
                                        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message_2)
                                        
                                        last_operation_time = datetime.now()
                                        
                                        await asyncio.sleep(0.2)
                                        
                                        if stop_order_details['status'] == 'FILLED':
                                            stop_loss_count += 1
                                            last_stop_loss_time = datetime.now()
                                            await check_stop_losses(last_stop_loss_time, log=log)
                                        elif limit_order_details['status'] == 'FILLED':
                                            stop_loss_count = 0
                                            last_stop_loss_time = None

                                        break
                            
                elif should_sell(rsi, trend_is_up, macd_current, signal_line_current, closes[-1], lower_band, vwap):
                    ticker = await client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                    if current_price < 1:
                        current_price = round(current_price, 4)
                    else:
                        current_price = round(current_price, 2)
                    msg = f"🔴 Os sinais indicam condições potenciais de \033[1;31mvenda\033[0m para {symbol}. RSI: \033[1;31m{rsi:.1f}\033[0m, Preço Atual: \033[1;33m${current_price}\033[0m"
                    status(msg)
                    await asyncio.sleep(0.6)
                    # log("\033[2K\r", end='')
                    await asyncio.sleep(0.15)
                    continue
                else:
                    ticker = await client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                    if current_price < 1:
                        current_price = round(current_price, 4)
                    else:
                        current_price = round(current_price, 2)
                    msg = f"🟡 \033[1;33mSem sinais claros de compra ou venda\033[0m para {symbol}. RSI: \033[1;33m{rsi:.1f}\033[0m, Preço Atual: \033[1;33m${current_price}\033[0m"
                    status(msg)
                    await asyncio.sleep(0.6)
                    # log("\033[2K\r", end='')
                    await asyncio.sleep(0.15)
                    continue

            await asyncio.sleep(0.5)

        await client.close_connection()

    except asyncio.CancelledError:
        log("\n🛑 Bot parado pelo usuário.")
        message = "🛑 Bot parado pelo usuário."
        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        await client.close_connection()
        return
            
    except BinanceAPIException as e:
            log(f"Erro BinanceAPI: {e}")
            exit()
        
    except Exception as e:
        if not bot_running: # If stopped, don't restart
            return

        if restart_attempts < MAX_RESTARTS:
            restart_attempts += 1
            log(f"\n⚠  Erro inesperado: {e}, reiniciando o bot após 5 segundos...")
            message = f"⚠ Erro inesperado: <b>{e}</b>, reiniciando o bot após 5 segundos..."
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
            await asyncio.sleep(5) # Adicionado tempo de espera
            await run_bot(log_callback, investment_amount, selected_symbol)
        else:
            log("\n🚨  Número máximo de tentativas de reinício atingido. O bot será desligado.")
            message = "🚨 <b>Número máximo</b> de tentativas de reinício atingido. O bot será desligado."
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
            exit()

if __name__ == "__main__":
    asyncio.run(run_bot())
