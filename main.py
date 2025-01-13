import asyncio
import winsound
import os
import pandas as pd
from datetime import datetime, timedelta
from binance import BinanceSocketManager
from binance import AsyncClient as BinanceAsyncClient
from binance.exceptions import BinanceAPIException

from config import bot_token, chat_id, mainnet_api_key, mainnet_secret_key, testnetspot_api_key, testnetspot_secret_key
from config import volume_avg, dynamic_rsi_low_0, dynamic_rsi_low_1, dynamic_rsi_low_2, dynamic_rsi_low_3
from config import interval, limit
from pre_start import synchronize_time, escolher_simbolo, cancel_all_oco_orders
from binance_api import get_closes, get_usdt_balance, get_volumes, get_order_details, get_klines
from trading_functions import calculate_rsi, calculate_macd, calculate_bollinger_bands, check_trend, check_candle_patterns, calculate_vwap, get_candle_details, calculate_ema, is_market_downward
from decision import should_place_order, should_buy, should_sell, adjust_and_place_oco_order, adjust_rsi_levels
from post_trade import process_order_details, log_and_notify_results, create_data_row, save_to_excel
from telegram_integration import send_telegram_message

# Seleciona o ambiente com base na variável de ambiente
environment = os.getenv("BOT_ENVIRONMENT", "mainnet")  # Valor padrão: mainnet

if environment == "mainnet":
    api_key = mainnet_api_key
    api_secret = mainnet_secret_key
elif environment == "testnet":
    api_key = testnetspot_api_key
    api_secret = testnetspot_secret_key
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

async def check_stop_losses(current_time):
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
            print("\n 🚨 Mais de 1 stop loss detectado dentro de 15 minutos. Bloqueando o bot por 1 hora.\n")
            message = "🚨 Mais de 1 stop loss detectado dentro de 15 minutos. Bloqueando o bot por 1 hora."
            send_telegram_message(bot_token, chat_id, message)

            pause_end_time = current_time + timedelta(seconds=LONG_PAUSE)
            block_active = True
            stop_loss_count = 0  # Reseta o contador após a pausa longa
            last_stop_loss_time = current_time  # Atualiza o último stop loss

            await asyncio.sleep(LONG_PAUSE)
            print("\n ✅️ Voltando a operar após pausa de 1 hora.")
            message = "✅️ Voltando a operar após pausa de 1 hora."
            send_telegram_message(bot_token, chat_id, message)
            adjust_rsi_levels('stop loss')  # Reduz ainda mais os níveis de RSI após pausa longa
            return  # Importante: retorna da função após a pausa longa
    else:
        # Se não houve stop loss recente (mais de 15 minutos), reseta o contador
        stop_loss_count = 0

    # Se chegou aqui, significa que não houve pausa longa
    if stop_loss_count == 1:
        # Primeiro stop loss, então incrementa o contador
        stop_loss_count += 1
        # Pausa curta (10 minutos)
        print("\n 🚨 Stop loss detectado. Pausando o bot por 10 minutos.")
        message = "🚨 Stop loss detectado. Pausando o bot por 10 minutos."
        send_telegram_message(bot_token, chat_id, message)

        pause_end_time = current_time + timedelta(seconds=SHORT_PAUSE)
        last_stop_loss_time = current_time  # Atualiza o último stop loss

        await asyncio.sleep(SHORT_PAUSE)
        print("\n ✅️ Voltando a operar após pausa de 10 minutos.\n")
        message = "✅️ Voltando a operar após pausa de 10 minutos."
        send_telegram_message(bot_token, chat_id, message)
        adjust_rsi_levels('stop loss')  # Reduz os níveis de RSI após a pausa
   
async def check_rsi_reset(symbol):
    global last_operation_time
    
    # Removendo a importação das variáveis locais e importanto as globais
    global dynamic_rsi_low_0, dynamic_rsi_low_1, dynamic_rsi_low_2, dynamic_rsi_low_3
    from config import rsi_low_level_0, rsi_low_level_1, rsi_low_level_2, rsi_low_level_3

    if last_operation_time and (datetime.now() - last_operation_time) > timedelta(seconds=7200):
        # Verifica se os níveis de RSI dinâmicos são iguais aos níveis padrão
        if dynamic_rsi_low_0 == rsi_low_level_0 and \
           dynamic_rsi_low_1 == rsi_low_level_1 and \
           dynamic_rsi_low_2 == rsi_low_level_2 and \
           dynamic_rsi_low_3 == rsi_low_level_3:
            print(f"\n⏳ Níveis de RSI já estão em Standard para {symbol}.")
            message = f"⏳ Níveis de RSI já estão em Standard para <b>{symbol}</b>."
            send_telegram_message(bot_token, chat_id, message)
        else:
            # Atualiza os níveis de RSI dinâmicos para os valores padrão
            dynamic_rsi_low_0 = rsi_low_level_0
            dynamic_rsi_low_1 = rsi_low_level_1
            dynamic_rsi_low_2 = rsi_low_level_2
            dynamic_rsi_low_3 = rsi_low_level_3
            print(f"\n⏳ Níveis de RSI resetados para {symbol} devido à inatividade.")
            message = f"⏳ Níveis de RSI resetados para <b>{symbol}</b> devido à inatividade."
            send_telegram_message(bot_token, chat_id, message)

        last_operation_time = datetime.now()  # Atualiza para evitar reset em loop

async def run_bot():
    global restart_attempts, quantia_usdt_investimento_inicial
    global limit_order_id, stop_order_id
    global stop_loss_count, last_stop_loss_time, block_active, pause_end_time
    global last_operation_time
    
    # Inicializações
    total_difference = 0
    
    print("\n🚀 \033[5;33mBot iniciado!\033[0m 🚀\n")
    message = "<b>🚀 Bot iniciado! 🚀</b>"
    send_telegram_message(bot_token, chat_id, message)
    
    synchronize_time()  # Sincroniza o tempo antes de começar
    await asyncio.sleep(1)
    try:
        client = await BinanceAsyncClient.create(api_key, api_secret)
        bsm = BinanceSocketManager(client)
        
        print("\n💸 \033[1;4;34mSeja bem-vindo(a) ao Gio Binance Bot - Spot Trading\033[0m 🤖")
        message = "<b><u>💸 Seja bem-vindo(a) ao Gio Binance Bot - Spot Trading🤖</u></b>"
        send_telegram_message(bot_token, chat_id, message)
        
        global symbol
        if symbol is None:
            symbol = escolher_simbolo()
            closes = await get_closes(client, symbol)
            print(f"\nVocê escolheu: 🪙 \033[1;33m{symbol}\033[0m")
            message = f"Você escolheu: 🪙 <b>${symbol}</b>"
            send_telegram_message(bot_token, chat_id, message)
        else:
            symbol = symbol  # Aqui, garantimos que o valor global seja usado
            closes = await get_closes(client, symbol)
            print(f"\nUsando símbolo salvo: 🪙 \033[1;33m{symbol}\033[0m")
            message = f"Usando símbolo salvo: 🪙 <b>{symbol}</b>"
            send_telegram_message(bot_token, chat_id, message)
        
        ticker = await client.get_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])
        if current_price < 1:
            print(f"\nPreço Atual: 📈 \033[1;33m${current_price:.4f}\033[0m")
            message = f"Preço Atual: 📈 <b>${current_price:.4f}</b>"
        else:
            print(f"\nPreço Atual: 📈 \033[1;33m${current_price:.2f}\033[0m")
            message = f"Preço Atual: 📈 <b>${current_price:.2f}</b>"
        
        send_telegram_message(bot_token, chat_id, message)
        
        rsi = calculate_rsi(closes)
        
        print(f"\n📊 RSI Inicial para {symbol}: \033[1;33m{rsi:.1f}\033[0m")
        
        symbol_info = await client.get_symbol_info(symbol)
        quote_precision = int(symbol_info['baseAssetPrecision'])
        
        tick_size = float([f['tickSize'] for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'][0])
        min_price_move = float([f['minPrice'] for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'][0])

        order_count = 0

        await cancel_all_oco_orders(client, symbol)
        
        saldo_inicial_usdt = await get_usdt_balance(client)
        saldo_atual_usdt = saldo_inicial_usdt  # Começa com o saldo inicial
        print(f"\nSaldo Inicial em USDT: 💰 \033[1;36m${saldo_inicial_usdt:.2f}\033[0m")
        message = f"\nSaldo Inicial em USDT: 💰 <b>${saldo_inicial_usdt:.2f}</b>"
        send_telegram_message(bot_token, chat_id, message)
        
        last_operation_time = datetime.now() # Inicializa o tempo da última operação
        
        while True:            
            if quantia_usdt_investimento_inicial is None:
                try:
                    quantia_usdt_investimento_inicial = float(input("Digite o valor inicial em USDT: 💰\033[1;36m $"))
                    print("\033[0m")
                except ValueError:
                    print("\033[0m")
                    print("🚫 Entrada inválida. Por favor, insira um número válido.\n")
                    continue  # Solicita novamente se a entrada não for um número
                if quantia_usdt_investimento_inicial > saldo_inicial_usdt:
                        print("🚫 Saldo insuficiente para o investimento atual.\n")
                        quantia_usdt_investimento_inicial = None
                        continue
                else:
                    message = f"Quantia inicial de USDT investida: 💰 <b>${quantia_usdt_investimento_inicial:.2f}</b>"
                    send_telegram_message(bot_token, chat_id, message)
                    break
            else:
                print(f"\nUsando o valor inicial de USDT salvo: 💰 \033[1;36m${quantia_usdt_investimento_inicial:.2f}\033[0m\n")
                message = f"Usando o valor inicial de USDT salvo: 💰 <b>${quantia_usdt_investimento_inicial:.2f}</b>"
                send_telegram_message(bot_token, chat_id, message)
                break
            
        async with bsm.user_socket() as um:
            macd_current = 0
            signal_line_current = 0
            lower_band = 0
            middle_band = 0
            upper_band = 0
            vwap = 0
            while True:
                closes = await get_closes(client, symbol)
                volumes = await get_volumes(client, symbol) #pega os volumes das velas
                
                rsi = calculate_rsi(closes)
                
                volumes_series = pd.Series(volumes)  # Converte diretamente para uma Series do Pandas
                volume_ma = volumes_series.dropna().rolling(window=8).mean().iloc[-1]
                
                macd_current, signal_line_current = calculate_macd(closes)
                lower_band, middle_band, upper_band = calculate_bollinger_bands(closes)
                
                #Novo indicador
                vwap = calculate_vwap(closes, volumes)
                
                msg_rsi = f"📊 RSI Atual para {symbol}: \033[1;33m{rsi:.1f}\033[0m"
                print(f"\r{msg_rsi}", end='', flush=True)
                await asyncio.sleep(0.4)
                print("\033[2K\r", end='')
                
                await asyncio.sleep(0.15)
                
                if symbol == "ADAUSDT" or symbol == "DOGEUSDT":
                    msg_macd = f"📊 MACD Atual para {symbol}: \033[1;33m{macd_current:.4f}\033[0m, Linha de sinal: \033[1;33m{signal_line_current:.4f}\033[0m"
                else:
                    msg_macd = f"📊 MACD Atual para {symbol}: \033[1;33m{macd_current:.2f}\033[0m, Linha de sinal: \033[1;33m{signal_line_current:.2f}\033[0m"
                print(f"\r{msg_macd}", end='', flush=True)
                await asyncio.sleep(0.4)
                print("\033[2K\r", end='')
                
                await asyncio.sleep(0.15)
                
                if symbol == "ADAUSDT" or symbol == "DOGEUSDT":
                    msg_bb = f"📊 Bandas de Bollinger para {symbol}: Inferior: \033[1;31m${lower_band:.4f}\033[0m, Média: \033[1;33m${middle_band:.4f}\033[0m, Superior: \033[1;32m${upper_band:.4f}\033[0m"
                else:
                   msg_bb = f"📊 Bandas de Bollinger para {symbol}: Inferior: \033[1;31m${lower_band:.2f}\033[0m, Média: \033[1;33m${middle_band:.2f}\033[0m, Superior: \033[1;32m${upper_band:.2f}\033[0m"
                print(f"\r{msg_bb}", end='', flush=True)
                await asyncio.sleep(0.4)
                print("\033[2K\r", end='')
                
                await asyncio.sleep(0.15)
                
                msg_vwap = f"📊 VWAP Atual para {symbol}: \033[1;33m{vwap:.2f}\033[0m"
                print(f"\r{msg_vwap}", end='', flush=True)
                await asyncio.sleep(0.4)
                print("\033[2K\r", end='')
                
                await asyncio.sleep(0.15)

                if volumes_series.iloc[-1] > volume_ma * (1 + volume_avg / 100):
                    msg = f"⚠️ Alto volume detectado, possível \033[1;33mvolatilidade de mercado\033[0m. Operação suspensa."
                    # Imprime a nova mensagem
                    print(f"\r{msg}", end='', flush=True)
                    # Espera um breve momento antes de limpar a linha novamente
                    await asyncio.sleep(0.4)
                    # Limpa a linha anterior
                    print("\033[2K\r", end='')
                    await asyncio.sleep(0.15)
                    continue
                    
                trend_is_up = await check_trend(client, symbol)
                candle_patterns = await check_candle_patterns(client, symbol, interval, limit)  # Chamada da função de padrões de candle
                
                # Verifica se o mercado está em tendência de baixa
                market_downward = await is_market_downward(client, symbol, interval)
                
                #Verifica o tempo desde a ultima operação
                await check_rsi_reset(symbol)
                
                if await should_place_order(client, symbol) and not market_downward:
                    
                    buy_result = should_buy(rsi, trend_is_up, macd_current, signal_line_current, closes[-1], lower_band, vwap, candle_patterns)
                    if buy_result["buy"]:  # Verifica as condições de compra
                        executed_condition = buy_result["message"]  # Atribui a mensagem da condição atendida
                        
                        print("### ------------------------- ###")
                        print(f"🟢 RSI: \033[1;32m{rsi:.1f}\033[0m, \033[1;32msinal de compra\033[0m encontrado!")
                        ticker = await client.get_symbol_ticker(symbol=symbol)
                        current_price = float(ticker['price'])
                        if current_price < 1:
                            print(f"\nPreço Atual: 📈 \033[1;33m${current_price:.4f}\033[0m\n")
                        else:
                            print(f"\nPreço Atual: 📈 \033[1;33m${current_price:.2f}\033[0m\n")
                        
                        order_count += 1
                        
                        compra = await client.order_market_buy(symbol=symbol, quoteOrderQty=round(quantia_usdt_investimento_inicial, quote_precision))
                        executed_qty = float(compra['executedQty'])
                        price = float(compra['fills'][0]['price'])
                        timestamp = datetime.now().strftime("%d/%m/%Y at %H:%M:%S")
                        price_rounded = round(price, 4) if price < 1 else round(price, 2)
                        
                        print(f"✅️ \033[1;36m({order_count:02d})\033[0m Comprado: Moeda: \033[1;33m{symbol}\033[0m, Quantidade da Moeda: \033[1;33m{executed_qty}\033[0m, Preço: \033[1;33m${price_rounded}\033[0m \033[1;36m({timestamp})\033[0m\n")
                        winsound.Beep(800, 1500) # Purchased: Coin.
                        message = f"✅️ ({order_count:02d}) <b>Comprado</b>: Moeda: <b>{symbol}</b>, Quantidade da Moeda: <b>{executed_qty}</b>, Preço: <b>${price_rounded} ({timestamp})</b>"
                        send_telegram_message(bot_token, chat_id, message)
                        purchase_timestamp = timestamp
                        
                        print(executed_condition)
                        
                        if candle_patterns:  # Verifica se a lista não está vazia
                            if len(candle_patterns) == 1:
                                print(f"\nPadrões de candle: {candle_patterns[0]}")  # Imprime apenas o elemento
                            else:
                                print(f"\nPadrões de candle: {', '.join(candle_patterns)}")  # Imprime a lista com elementos separados por vírgula
                        else:
                            print("\nPadrões de candle: Nenhum encontrado")

                        # Busca detalhes da candle da operação para registro em planilha e para ter detalhes das operações
                        candle_details = await get_candle_details(client, symbol, interval, limit)
                        if candle_details:
                            candle_open = candle_details['open']
                            candle_high = candle_details['high']
                            candle_low = candle_details['low']
                            candle_close = candle_details['close']
                            candle_volume = candle_details['volume']
                            # Calcula amplitude
                            amplitude = ((candle_high - candle_low) / candle_open) * 100 if candle_open !=0 else 0
                        else: # Pega esses valores caso a API de erro, pra garantir que o bot não quebre
                            candle_open = 0
                            candle_high = 0
                            candle_low = 0
                            candle_close = 0
                            candle_volume = 0
                            amplitude = 0
                            
                        # Pega o preço do candle de 24h atrás para usar na variação
                        try:
                            klines_24h = await get_klines(client, symbol, interval, 2) #pega o preço de fechamento do candle de 24h atras em ms, e o atual
                            if klines_24h and len(klines_24h) >= 2:  # Para evitar erros do codigo caso ele nao consiga pegar os dados
                                price_24h = float(klines_24h[-2][4]) if klines_24h else 0  # o valor que queremos para usar no calculo é o candle anterior ao atual
                                variation_24h = ((current_price - price_24h) / price_24h) * 100 # calcula variacao percentual de preço nas ultimas 24 horas
                            else:
                                price_24h = 0  # Caso a api de problema ou algo de errado, seta para 0
                                variation_24h = 0 # seta como zero também
                        
                        except Exception as e: # caso de algum erro, os valores devem continuar como 0 pra que o programa não quebre
                            price_24h = 0
                            variation_24h = 0
                            print(f"\nErro ao buscar dados para variação de 24h: {e}")

                        # Calculo das EMAS que queremos que o bot calcule e tenha nos relatorios

                        ema7 = calculate_ema(closes, 7)
                        ema15 = calculate_ema(closes, 15)
                        ema25 = calculate_ema(closes, 25)
                        ema50 = calculate_ema(closes, 50)
                        ema100 = calculate_ema(closes, 100)
                        ema200 = calculate_ema(closes, 200)
                        
                        candle_variation = ((candle_close - candle_open) / candle_open) * 100 if candle_open != 0 else 0 # calculo variacao percentual de preço da vela
                        
                        # Calcula os valores de MACD e Bollinger
                        macd_current, signal_line_current = calculate_macd(closes)
                        lower_band, middle_band, upper_band = calculate_bollinger_bands(closes)
                                 
                        oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit = await adjust_and_place_oco_order(client, symbol, executed_qty, tick_size, min_price_move)
                        
                        # Atualiza o tempo da última operação
                        last_operation_time = datetime.now()
                        
                        # Await OCO order completion
                        while True:
                            msg = await um.recv()
                            if msg.get('e') == 'listStatus' and msg.get('s') == symbol and msg.get('g') == oco_order['orderListId']:
                                if 'ALL_DONE' in msg.get('l'):
                                    # Busca os detalhes das ordens executadas
                                    limit_order_details = await get_order_details(client, symbol, limit_order_id)
                                    stop_order_details = await get_order_details(client, symbol, stop_order_id)
                                    
                                    # Atualize total_difference depois de chamar process_order_details
                                    order_result, trade_result, novo_saldo_usdt, oco_timestamp, fee, trade_result_liquid = await process_order_details(client, limit_order_details, stop_order_details,
                                                                                                                                                 price, executed_qty, quantia_usdt_investimento_inicial)
                                    # Atualiza o saldo atual e a diferença total
                                    saldo_atual_usdt = novo_saldo_usdt
                                    total_difference += trade_result  # Acumula os resultados ao total
                                    quantia_usdt_investimento_inicial = saldo_atual_usdt  # Atualiza o montante para reinvestimento
                                    
                                    if order_result:
                                        # Registra os resultados no log e envia mensagens
                                        log_and_notify_results(order_result, symbol, trade_result, total_difference, oco_timestamp, vwap, fee, trade_result_liquid)
                                        
                                        # Salva resultados na planilha Excel
                                        data_row = create_data_row(order_count, saldo_inicial_usdt, quantia_usdt_investimento_inicial, symbol,
                                                                    executed_qty, price_rounded, purchase_timestamp, lucro_alvo, stop_loss, stop_limit,
                                                                    order_result, oco_timestamp, trade_result, total_difference, saldo_atual_usdt,
                                                                    rsi, executed_condition, vwap, candle_open, candle_high, candle_low, candle_close, candle_volume, 
                                                                    variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, candle_patterns, volume_avg, 
                                                                    amplitude, macd_current, signal_line_current, lower_band, middle_band, upper_band, trend_is_up, fee, trade_result_liquid)
                                        save_to_excel(data_row)
                                    
                                        print(f"Saldo atual investido em USDT: \033[1;36m${quantia_usdt_investimento_inicial:.2f}\033[0m\n")
                                        message_2 = f'Saldo atual investido em USDT: <b>${quantia_usdt_investimento_inicial:.2f}</b>'
                                        send_telegram_message(bot_token, chat_id, message_2)
                                        
                                        last_operation_time = datetime.now()
                                        
                                        await asyncio.sleep(0.2)
                                        
                                        # Verifica o status das ordens para atualizar contadores e gerenciar pausas
                                        if stop_order_details['status'] == 'FILLED':
                                            stop_loss_count += 1
                                            last_stop_loss_time = datetime.now()
                                            await check_stop_losses(last_stop_loss_time)  # Passa o tempo atual para a função de pausa
                                        elif limit_order_details['status'] == 'FILLED':
                                            # Reseta o contador de stop losses se uma ordem de lucro for executada
                                            stop_loss_count = 0
                                            last_stop_loss_time = None

                                        break # Sai do loop após processar os detalhes da ordem
                                
                    elif should_sell(rsi, trend_is_up, macd_current, signal_line_current, closes[-1], lower_band, vwap):
                        ticker = await client.get_symbol_ticker(symbol=symbol)
                        current_price = float(ticker['price'])
                        if current_price < 1:
                            current_price = round(current_price, 4)
                        else:
                            current_price = round(current_price, 2)
                        msg = f"🔴 Os sinais indicam condições potenciais de \033[1;31mvenda\033[0m para {symbol}. RSI: \033[1;31m{rsi:.1f}\033[0m, Preço Atual: \033[1;33m${current_price}\033[0m"
                        # Imprime a nova mensagem
                        print(f"\r{msg}", end='', flush=True)
                        # Espera um breve momento antes de limpar a linha novamente
                        await asyncio.sleep(0.5)
                        # Limpa a linha anterior
                        print("\033[2K\r", end='')
                        await asyncio.sleep(0.2)
                        continue
                    else:
                        ticker = await client.get_symbol_ticker(symbol=symbol)
                        current_price = float(ticker['price'])
                        if current_price < 1:
                            current_price = round(current_price, 4)
                        else:
                            current_price = round(current_price, 2)
                        msg = f"🟡 \033[1;33mSem sinais claros de compra ou venda\033[0m para {symbol}. RSI: \033[1;33m{rsi:.1f}\033[0m, Preço Atual: \033[1;33m${current_price}\033[0m"
                        # Imprime a nova mensagem
                        print(f"\r{msg}", end='', flush=True)
                        # Espera um breve momento antes de limpar a linha novamente
                        await asyncio.sleep(0.5)
                        # Limpa a linha anterior
                        print("\033[2K\r", end='')
                        await asyncio.sleep(0.2)
                        continue

                await asyncio.sleep(0.1)  # Short pause before checking for new orders or balance updates

        await client.close_connection()
            
    except BinanceAPIException as e:
        if restart_attempts < MAX_RESTARTS:
            restart_attempts += 1
            if e.code == -1021:  # Código de erro para timestamp incorreto
                print("\n⚠  Erro de timestamp detectado, tentando reiniciar o bot...")
                message = '⚠ Erro de <b>timestamp</b> detectado, tentando reiniciar o bot...'
                send_telegram_message(bot_token, chat_id, message)
            else:
                print(f"\n⚠  Erro detectado: {e}")
                message = f'⚠ Erro detectado: <b>{e}</b>'
                send_telegram_message(bot_token, chat_id, message)
            print("⏱  Aguardando 5 segundos antes de reiniciar...")
            await asyncio.sleep(2)
            print("♻  Reiniciando o bot...")
            message = "♻ Reiniciando o bot..."
            send_telegram_message(bot_token, chat_id, message)
            await run_bot()  # Tenta reiniciar o bot automaticamente
        else:
            print("\n🚨  Número máximo de tentativas de reinício atingido. O bot será desligado.")
            message = "🚨 <b>Número máximo</b> de tentativas de reinício atingido. O bot será desligado."
            send_telegram_message(bot_token, chat_id, message)
            exit()
        
    except Exception as e:
        if restart_attempts < MAX_RESTARTS:
            restart_attempts += 1
            print(f"\n⚠  Erro inesperado: {e}, reiniciando o bot após 5 segundos...")
            message = f"⚠ Erro inesperado: <b>{e}</b>, reiniciando o bot após 5 segundos..."
            send_telegram_message(bot_token, chat_id, message)
            await asyncio.sleep(5) # Adicionado tempo de espera
            await run_bot()
        else:
            print("\n🚨  Número máximo de tentativas de reinício atingido. O bot será desligado.")
            message = "🚨 <b>Número máximo</b> de tentativas de reinício atingido. O bot será desligado."
            send_telegram_message(bot_token, chat_id, message)
            exit()

if __name__ == "__main__":
    asyncio.run(run_bot())
