import asyncio
import winsound
import pandas as pd
from datetime import datetime, timedelta
from binance.streams import BinanceSocketManager
from binance import AsyncClient as BinanceAsyncClient
from binance.exceptions import BinanceAPIException

from config import bot_token, chat_id, mainnet_api_key, mainnet_secret_key
from config import rsi_low_level_0, rsi_low_level_1, rsi_low_level_2, rsi_low_level_3, volume_avg
from pre_start import synchronize_time, escolher_simbolo, cancel_all_oco_orders
from binance_api import get_closes, get_usdt_balance, get_volumes, get_order_details
from trading_functions import calculate_rsi, calculate_macd, calculate_bollinger_bands, check_trend, check_candle_patterns, calculate_vwap
from decision import should_place_order, should_buy, should_sell, adjust_and_place_oco_order, adjust_rsi_levels
from post_trade import process_order_details, log_and_notify_results, create_data_row, save_to_excel
from telegram_integration import send_telegram_message
from config import interval, limit #importar interval e limit

api_key = mainnet_api_key
api_secret = mainnet_secret_key

# Variáveis globais
quantia_usdt_investimento_inicial = None
symbol = None

limit_order_id = None
stop_order_id = None

STOP_LOSS_LIMIT = 2
SHORT_PAUSE = 900  # Pausa de 15 minutos (em segundos)
LONG_PAUSE = 3600  # Pausa de 1 hora (em segundos)

stop_loss_count = 0
last_stop_loss_time = None
block_active = False
pause_end_time = None

MAX_RESTARTS = 3
restart_attempts = 0

async def check_stop_losses(current_time):
    global stop_loss_count, last_stop_loss_time, block_active, pause_end_time
    
    # Verificar se estamos após uma pausa e reinicializar o contador se o tempo de pausa acabou
    if pause_end_time and current_time > pause_end_time:
        pause_end_time = None
        stop_loss_count = 0
        block_active = False

    # Verifica se os stop losses ocorreram dentro do intervalo de tempo esperado
    if stop_loss_count >= STOP_LOSS_LIMIT:
        if not block_active:
            # Primeiro bloco de stop losses
            print("\n 🚨 2 stop losses detectados em menos de 10 minutos. Pausando o bot por 15 minutos.")
            message = "🚨 2 stop losses detectados em menos de 10 minutos. Pausando o bot por 15 minutos."
            send_telegram_message(bot_token, chat_id, message)
            block_active = True
            pause_end_time = current_time + timedelta(seconds=SHORT_PAUSE)
            await asyncio.sleep(SHORT_PAUSE)
            print("\n ✅️ Voltando a operar após pausa de 15 minutos.\n")
            message = "✅️ Voltando a operar após pausa de 15 minutos."
            send_telegram_message(bot_token, chat_id, message)
            stop_loss_count = 0
            adjust_rsi_levels('stop loss')  # Reduz os níveis de RSI após a pausa
        else:
            # Segundo bloco de stop losses dentro de 15 minutos
            print("\n 🚨 Mais 2 stop losses detectados dentro de 15 minutos. Bloqueando o bot por 1 hora.\n")
            message = "🚨 Mais 2 stop losses detectados dentro de 15 minutos. Bloqueando o bot por 1 hora."
            send_telegram_message(bot_token, chat_id, message)
            pause_end_time = current_time + timedelta(seconds=LONG_PAUSE)
            await asyncio.sleep(LONG_PAUSE)
            print("\n ✅️ Voltando a operar após pausa de 1 hora.")
            message = "✅️ Voltando a operar após pausa de 1 hora."
            send_telegram_message(bot_token, chat_id, message)
            stop_loss_count = 0
            block_active = False
            adjust_rsi_levels('stop loss')  # Reduz ainda mais os níveis de RSI após pausa longa
        stop_loss_count = 0
    else:
        # Verifica o tempo entre os stop losses para determinar se continua a contar ou reseta
        if current_time - last_stop_loss_time > timedelta(minutes=5):
            stop_loss_count = 0
            last_stop_loss_time = current_time

async def run_bot():
    global restart_attempts, quantia_usdt_investimento_inicial
    global limit_order_id, stop_order_id
    global stop_loss_count, last_stop_loss_time, block_active, pause_end_time
    
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
        
        print(f"\n📊 RSI Atual para {symbol}: \033[1;33m{rsi:.1f}\033[0m")
        
        
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
                
                if symbol == "ADAUSDT" or symbol == "DOGEUSDT":
                    msg_macd = f"📊 MACD Atual para {symbol}: \033[1;33m{macd_current:.4f}\033[0m, Linha de sinal: \033[1;33m{signal_line_current:.4f}\033[0m"
                else:
                    msg_macd = f"📊 MACD Atual para {symbol}: \033[1;33m{macd_current:.2f}\033[0m, Linha de sinal: \033[1;33m{signal_line_current:.2f}\033[0m"
                print(f"\r{msg_macd}", end='', flush=True)
                await asyncio.sleep(0.5)
                print("\033[2K\r", end='')
                
                await asyncio.sleep(0.2)
                
                if symbol == "ADAUSDT" or symbol == "DOGEUSDT":
                    msg_bb = f"📊 Bandas de Bollinger para {symbol}: Inferior: \033[1;31m${lower_band:.4f}\033[0m, Média: \033[1;33m${middle_band:.4f}\033[0m, Superior: \033[1;32m${upper_band:.4f}\033[0m"
                else:
                   msg_bb = f"📊 Bandas de Bollinger para {symbol}: Inferior: \033[1;31m${lower_band:.2f}\033[0m, Média: \033[1;33m${middle_band:.2f}\033[0m, Superior: \033[1;32m${upper_band:.2f}\033[0m"
                print(f"\r{msg_bb}", end='', flush=True)
                await asyncio.sleep(0.5)
                print("\033[2K\r", end='')
                
                await asyncio.sleep(0.2)
                
                msg_vwap = f"📊 VWAP Atual para {symbol}: \033[1;33m{vwap:.2f}\033[0m"
                print(f"\r{msg_vwap}", end='', flush=True)
                await asyncio.sleep(0.5)
                print("\033[2K\r", end='')
                
                await asyncio.sleep(0.2)

                if volumes_series.iloc[-1] > volume_ma * (1 + volume_avg / 100):
                    msg = f"⚠️ Alto volume detectado, possível \033[1;33mvolatilidade de mercado\033[0m. Operação suspensa."
                    # Imprime a nova mensagem
                    print(f"\r{msg}", end='', flush=True)
                    # Espera um breve momento antes de limpar a linha novamente
                    await asyncio.sleep(0.5)
                    # Limpa a linha anterior
                    print("\033[2K\r", end='')
                    await asyncio.sleep(0.2)
                    continue
                    
                trend_is_up = await check_trend(client, symbol)
                candle_decision = await check_candle_patterns(client, symbol, interval, limit)  # Chamada da função de padrões de candle

                if await should_place_order(client, symbol):
                   
                    if should_buy(rsi, trend_is_up, candle_decision, macd_current, signal_line_current, closes[-1], lower_band, vwap):
                        
                        print("### ------------------------- ###")
                        print(f"🟢 RSI: \033[1;32m{rsi:.1f}\033[0m, MACD \033[1;32macima\033[0m da Linha de Sinal, Bandas de Bollinger \033[1;32msinal de compra\033[0m encontrado.")
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
                        
                        # Pega qual condição acionou a compra, passando os parametros e alterando o valor da variável executed_condition com a resposta
                        executed_condition = should_buy(rsi, trend_is_up, candle_decision, macd_current, signal_line_current, closes[-1], lower_band, vwap)
                                
                        oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit = await adjust_and_place_oco_order(client, symbol, executed_qty, tick_size, min_price_move)
                        
                        # Await OCO order completion
                        while True:
                            msg = await um.recv()
                            if msg.get('e') == 'listStatus' and msg.get('s') == symbol and msg.get('g') == oco_order['orderListId']:
                                if 'ALL_DONE' in msg.get('l'):
                                    # Busca os detalhes das ordens executadas
                                    limit_order_details = await get_order_details(client, symbol, limit_order_id)
                                    stop_order_details = await get_order_details(client, symbol, stop_order_id)
                                    
                                    # Atualize total_difference depois de chamar process_order_details
                                    order_result, trade_result, novo_saldo_usdt, oco_timestamp = process_order_details(limit_order_details, stop_order_details, price, executed_qty, quantia_usdt_investimento_inicial)
                                    # Atualiza o saldo atual e a diferença total
                                    saldo_atual_usdt = novo_saldo_usdt
                                    total_difference += trade_result  # Acumula os resultados ao total
                                    quantia_usdt_investimento_inicial = saldo_atual_usdt  # Atualiza o montante para reinvestimento
                                    
                                    if order_result:
                                        # Registra os resultados no log e envia mensagens
                                        log_and_notify_results(order_result, symbol, trade_result, total_difference, oco_timestamp, vwap)
                                        
                                        # Salva resultados na planilha Excel
                                        data_row = create_data_row(order_count, saldo_inicial_usdt, quantia_usdt_investimento_inicial, symbol, 
                                                                        executed_qty, price_rounded, purchase_timestamp, lucro_alvo, stop_loss, stop_limit, 
                                                                        order_result, oco_timestamp, trade_result, total_difference, saldo_atual_usdt, 
                                                                        rsi, executed_condition, vwap)
                                        save_to_excel(data_row)
                                    
                                        print(f"Saldo atual investido em USDT: \033[1;36m${quantia_usdt_investimento_inicial:.2f}\033[0m\n")
                                        message_2 = f'Saldo atual investido em USDT: <b>${quantia_usdt_investimento_inicial:.2f}</b>'
                                        send_telegram_message(bot_token, chat_id, message_2)
                                        
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

                                        break  # Sai do loop após processar os detalhes da ordem
                                
                    elif should_sell(rsi, trend_is_up, candle_decision, macd_current, signal_line_current, closes[-1], lower_band, vwap):
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
            await asyncio.sleep(2)
            await run_bot()
        else:
            print("\n🚨  Número máximo de tentativas de reinício atingido. O bot será desligado.")
            message = "🚨 <b>Número máximo</b> de tentativas de reinício atingido. O bot será desligado."
            send_telegram_message(bot_token, chat_id, message)
            exit()

if __name__ == "__main__":
    asyncio.run(run_bot())

'''O main.py é a peça central de seu bot de trading, agindo como o executor principal que lida com a lógica do ciclo de vida completo das operações de trading, 
desde a inicialização até o encerramento da sessão, incluindo a manipulação de exceções. Aqui está uma explicação dos principais componentes e funções definidos no arquivo:

1. Importações e Configurações Globais:
* Importa módulos necessários como asyncio para operações assíncronas e winsound para alertas sonoros.
* Utiliza módulos específicos para interagir com a API da Binance e gerenciar mensagens do Telegram.
* Define chaves API para a Binance e tokens para o bot do Telegram.

2. Inicialização do Bot:
* Define uma função run_bot assíncrona que encapsula toda a lógica operacional do bot.
* Sincroniza o relógio do sistema para evitar problemas de timestamp com a API da Binance.
* Inicia uma sessão de cliente com a Binance e configura o gerenciador de sockets para ouvir eventos de ordens.

3. Seleção do Símbolo de Trading e Configuração Inicial:
* Permite ao usuário escolher o símbolo para trading ou usa um valor pré-definido.
* Obtém o saldo inicial em USDT e configura variáveis globais como o saldo atual e o investimento inicial.

4. Monitoramento e Decisão de Trading:
* Em um loop, o bot verifica continuamente se deve colocar ordens baseado em análises de indicadores técnicos como RSI, MACD e Bandas de Bollinger.
* Decide sobre compras ou vendas com base nos sinais de trading derivados de padrões de velas e condições de mercado.

5. Gestão de Ordens e Execução:
* Coloca ordens OCO (One Cancels the Other) com base nos preços calculados para tomar lucro e parar perdas.
* Monitora o status das ordens e processa os resultados para atualizar o saldo.

6. Registro e Notificação de Resultados:
* Registra os resultados das operações, como lucro ou perda, e notifica o usuário através de mensagens do Telegram.
* Salva detalhes do trade em uma planilha Excel para futura referência.

7. Gerenciamento de Exceções e Reinício:
* Lida com exceções específicas da API da Binance e erros inesperados, tentando reiniciar o bot automaticamente se não exceder o limite máximo de reinícios.
* Se todos os esforços falharem, encerra o bot e notifica o usuário.

8. Encerramento e Limpeza:
* Fecha a conexão com a API da Binance e termina a sessão de maneira limpa.

9. Execução do Bot:
* Inicializa e executa o bot chamando a função run_bot dentro do bloco if __name__ == "__main__": para garantir que o script só execute quando não importado como um módulo.

*** Este script serve como o núcleo operacional do bot, integrando todas as funções e módulos para uma operação de trading automática e eficaz.'''
