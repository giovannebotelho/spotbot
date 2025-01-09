import asyncio
import math
from datetime import datetime
from binance.streams import BinanceSocketManager
from binance import AsyncClient as BinanceAsyncClient
from binance.exceptions import BinanceAPIException
from config import real_api_key, real_secret_key
from collections import deque
import numpy as np
import pandas as pd
import winsound
import requests
import subprocess
import pandas as pd
from pathlib import Path

api_key = real_api_key
api_secret = real_secret_key

bot_token = '6906678051:AAEuNtDgPCtUbXH_KSkG3FPc_LX3RvpIfAg'
chat_id = '6707404308'

global limit_order_id, stop_order_id
limit_order_id = None
stop_order_id = None

quantia_usdt_investimento_inicial = None
symbol = None

def synchronize_time():
    try:
        subprocess.run(['w32tm', '/resync'], check=True)
        print("✅️ Relógio do sistema sincronizado com sucesso.")
        message = "✅️ Relógio do sistema sincronizado com sucesso."
        send_telegram_message(bot_token, chat_id, message)
    except subprocess.CalledProcessError:
        print("🚨 Falha ao sincronizar o relógio do sistema.")
        message = "🚨 Falha ao sincronizar o relógio do sistema."
        send_telegram_message(bot_token, chat_id, message)

async def get_usdt_balance(client):
    balance = await client.get_asset_balance(asset='USDT')
    return float(balance['free'])

def adjust_price_to_tick_size(price, tick_size):
    return math.floor(price / tick_size) * tick_size

async def cancel_all_oco_orders(client, symbol):
    open_orders = await client.get_open_orders(symbol=symbol)
    for order in open_orders:
        if 'orderListId' in order and order['orderListId'] > -1:
            await client.cancel_order(symbol=symbol, orderId=order['orderId'])

async def get_order_book(client, symbol, depth=5): # 🟣🟣
    order_book = await client.get_order_book(symbol=symbol, limit=depth)
    return order_book

def calculate_sell_pressure(order_book):
    total_asks = sum(float(ask[1]) for ask in order_book['asks'])
    total_bids = sum(float(bid[1]) for bid in order_book['bids'])
    total = total_asks + total_bids
    return total_asks / total if total > 0 else 0

sell_pressure_history = deque(maxlen=5) # 🟣🟣

async def calculate_moving_average_sell_pressure(client, symbol, depth=5): # 🟣🟣
    order_book = await get_order_book(client, symbol, depth)
    sell_pressure = calculate_sell_pressure(order_book)
    sell_pressure_history.append(sell_pressure)
    return sum(sell_pressure_history) / len(sell_pressure_history)

async def should_place_order(client, symbol, SELL_PRESSURE_THRESHOLD = 0.75): # 🟣🟣
    avg_sell_pressure = await calculate_moving_average_sell_pressure(client, symbol)
    
    msg = f"⛔ High average sell pressure detected: \033[1;31m{avg_sell_pressure:.2f}\033[0m, Waiting..."
    
    if avg_sell_pressure < SELL_PRESSURE_THRESHOLD:
        print("\033[2K\r", end='')
        return True
    else:
        # Imprime a nova mensagem
        print(f"\r{msg}", end='', flush=True)
        # Espera um breve momento antes de limpar a linha novamente
        await asyncio.sleep(2.2)
        # Limpa a linha anterior
        print("\033[2K\r", end='')
        await asyncio.sleep(0.5)
            
def escolher_simbolo():
    while True:
        print("\n🪙 Escolha o símbolo preferido ou digite manualmente:")
        print('1 - BTC/USDT')
        print('2 - ETH/USDT')
        print('3 - BNB/USDT')
        print('4 - ADA/USDT')
        print('5 - SOL/USDT')
        print('6 - DOGE/USDT')
        print('0 - Outra')
        
        try:
            symbol_input = int(input(": "))
        except ValueError:
            print("\nPor favor, digite um número.")
            continue

        if symbol_input == 1:
            return 'BTCUSDT'
        elif symbol_input == 2:
            return 'ETHUSDT'
        elif symbol_input == 3:
            return 'BNBUSDT'
        elif symbol_input == 4:
            return 'ADAUSDT'
        elif symbol_input == 5:
            return 'SOLUSDT'
        elif symbol_input == 6:
            return 'DOGEUSDT'
        elif symbol_input == 0:
            escolha_alternativa = input("\nDigite a moeda requerida no formato (Ex.: BTCUSDT): ")
            return escolha_alternativa.upper()  # Garante que o texto será maiúsculo
        else:
            print("\n⛔ Digite uma opção válida.")
            
async def adjust_and_place_oco_order(client, symbol, quantity, tick_size, min_price_move):
    max_attempts = 5
    for attempt in range(max_attempts):
        order_book = await get_order_book(client, symbol)
        current_price = float(order_book['asks'][0][0])

        if current_price < 1:
            lucro_multiplier = 1.01 # 🟣🟣
            stop_loss_multiplier = 0.99 # 🟣🟣
        else:
            lucro_multiplier = 1.0021 # 🟣🟣
            stop_loss_multiplier = 0.9988 # 🟣🟣

        lucro_alvo = adjust_price_to_tick_size(current_price * lucro_multiplier, tick_size)
        stop_loss = adjust_price_to_tick_size(current_price * stop_loss_multiplier, tick_size)
        stop_limit = stop_loss - (20 * min_price_move)

        try:
            oco_order = await client.create_oco_order(
                symbol=symbol,
                side="SELL",
                quantity=f"{quantity:.6f}",
                price=f"{lucro_alvo:.2f}",
                stopPrice=f"{stop_loss:.2f}",
                stopLimitPrice=f"{stop_limit:.2f}",
                stopLimitTimeInForce='GTC'
            )
            order_list_id = oco_order.get('orderListId', 'N/A')  # Acessa o ID da ordem OCO, se disponível

            limit_order_id = oco_order['orders'][1]['orderId']
            stop_order_id = oco_order['orders'][0]['orderId']
            
            if symbol == "DOGEUSDT" or symbol == "ADAUSDT":
                print(f"✅️ OCO Order placed. Coin: \033[1;32m{symbol}\033[0m. ID: \033[1;34m{order_list_id}\033[0m. Profit: \033[1;32m${lucro_alvo:.4f}\033[0m, Stop Price: \033[1;31m${stop_loss:.4f}\033[0m, Stop Limit: \033[1;31m${stop_limit:.4f}\033[0m")
                message = f"✅️ OCO Order placed. Coin: <b>{symbol}</b>. ID: <b>{order_list_id}</b>. Profit: <b>${lucro_alvo:.4f}</b>, Stop Price: <b>${stop_loss:.4f}</b>, Stop Limit: <b>${stop_limit:.4f}</b>"
                send_telegram_message(bot_token, chat_id, message)
            else:
                print(f"✅️ OCO Order placed. Coin: \033[1;32m{symbol}\033[0m.  ID: \033[1;34m{order_list_id}\033[0m. Profit: \033[1;32m${lucro_alvo:.2f}\033[0m, Stop Price: \033[1;31m${stop_loss:.2f}\033[0m, Stop Limit: \033[1;31m${stop_limit:.2f}\033[0m")
                message = f"✅️ OCO Order placed. Coin: <b>{symbol}</b>. ID: <b>{order_list_id}</b>. Profit: <b>${lucro_alvo:.2f}</b>, Stop Price: <b>${stop_loss:.2f}</b>, Stop Limit: <b>${stop_limit:.2f}</b>"
                send_telegram_message(bot_token, chat_id, message)
            return oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit
        
        except BinanceAPIException as e:
            print(f"\n🚨 Attempt \033[1;31m{attempt + 1}\033[0m: Error placing OCO order: {e}")
            if attempt < max_attempts - 1:
                print("\n⌛ Adjusting prices and retrying...")
                await asyncio.sleep(2)  # Breve pausa antes de tentar novamente

    print("\n🚨 \033[1;31mFailed\033[0m to place OCO order after several attempts.")
    message = f'<b>🚨 Failed to place OCO order after several attempts</b>, Coin: <b>{symbol}</b>'
    send_telegram_message(bot_token, chat_id, message)
    return None

async def get_order_details(client, symbol, order_id):
    order_details = await client.get_order(symbol=symbol, orderId=order_id)
    return order_details

def calculate_rsi(closes, period=6): # 🟣🟣
    deltas = np.diff(closes)
    gain = np.where(deltas > 0, deltas, 0)
    loss = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.average(gain[-period:])
    avg_loss = np.average(loss[-period:])

    if avg_loss == 0:
        rs = float('inf')  # Definir RS como infinito se avg_loss é 0
    else:
        rs = avg_gain / avg_loss
    
    rsi = 100 - (100 / (1 + rs))
    return rsi

async def get_closes(client, symbol, interval='15m', limit=6): # 🟣🟣
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    closes = [float(kline[4]) for kline in klines]
    return closes

async def get_volumes(client, symbol, interval='15m', limit=12): # 🟣🟣
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    volumes = [float(kline[5]) for kline in klines]  # Volume está na 6ª posição
    return volumes

def calculate_macd(closes, slow=21, fast=12, signal=9): # 🟣🟣
    """Calcula o MACD e a linha de sinal usando pandas."""
    closes_series = pd.Series(closes)
    ema_fast = closes_series.ewm(span=fast, adjust=False).mean()
    ema_slow = closes_series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]

def calculate_bollinger_bands(closes, period=6, num_std=2): # 🟣🟣
    closes_series = pd.Series(closes)
    ma = closes_series.rolling(window=period).mean()
    std = closes_series.rolling(window=period).std()
    
    upper_band = ma + (std * num_std)
    lower_band = ma - (std * num_std)
    
    return lower_band.iloc[-1], ma.iloc[-1], upper_band.iloc[-1]

def send_telegram_message(bot_token, chat_id, message):
    """Envia uma mensagem para um chat do Telegram."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"  # Adiciona esta linha para ativar o modo HTML
    }
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        print(f"🚨 Erro ao enviar mensagem: {e}")
        return None
    
def save_to_excel(data_row):
    filename = "results.xlsx"
    filepath = Path(__file__).parent / filename  # Salva na mesma pasta do script

    # Cria um DataFrame a partir do dicionário data_row
    new_row_df = pd.DataFrame([data_row])

    if filepath.exists():
        # Carrega o DataFrame existente
        df = pd.read_excel(filepath, index_col=0)
        # Usa concat ao invés de append
        df = pd.concat([df, new_row_df], ignore_index=True)
    else:
        df = new_row_df

    df.to_excel(filepath)
    
def calculate_volume_moving_average(volumes, period=12): # 🟣🟣
    return sum(volumes[-period:]) / period

MAX_RESTARTS = 5
restart_attempts = 0

def calculate_trade_result(purchase_price, executed_qty, sell_price):
    """
    Calcula o resultado do trade.
    :param purchase_price: Preço de compra da moeda.
    :param executed_qty: Quantidade executada na compra.
    :param sell_price: Preço de venda da moeda.
    :param is_profit: Booleano, True se foi um profit, False se foi um stop loss.
    :return: Resultado financeiro do trade.
    """
    total_purchase = purchase_price * executed_qty
    total_sell = sell_price * executed_qty
    result = total_sell - total_purchase
    return result

async def run_bot():
    global restart_attempts
    
    print("\n🚀 \033[5;33mBot iniciado!\033[0m 🚀\n")
    message = "<b>🚀 Bot iniciado! 🚀</b>"
    send_telegram_message(bot_token, chat_id, message)
    
    synchronize_time()  # Sincroniza o tempo antes de começar
    await asyncio.sleep(3)
    try:
        client = await BinanceAsyncClient.create(api_key, api_secret)
        bsm = BinanceSocketManager(client)
        
        print("\n💸 \033[1;4;34mSeja bem-vindo(a) ao Gio Binance Bot - v0.1.0\033[0m 🤖")
        message = "<b><u>💸 Seja bem-vindo(a) ao Gio Binance Bot - v0.1.0 🤖</u></b>"
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
            print(f"\nUsing saved symbol: 🪙 \033[1;33m{symbol}\033[0m")
            message = f"Using saved symbol: 🪙 <b>{symbol}</b>"
            send_telegram_message(bot_token, chat_id, message)
        
        ticker = await client.get_symbol_ticker(symbol=symbol)
        current_price = f"{float(ticker['price']):.2f}"
        print(f"\nCurrent Price: 📈 \033[1;33m${current_price}\033[0m")
        message = f"Current Price: 📈 <b>${current_price}</b>"
        send_telegram_message(bot_token, chat_id, message)
        
        rsi = calculate_rsi(closes)
        print(f"\n📊 Current RSI for {symbol}: \033[1;33m{rsi:.1f}\033[0m")
        
        macd_current, signal_line_current = calculate_macd(closes)
        print(f"📊 Current MACD for {symbol}: \033[1;33m{macd_current:.2f}\033[0m, Signal line: \033[1;33m{signal_line_current:.2f}\033[0m")
        
        lower_band, middle_band, upper_band = calculate_bollinger_bands(closes)
        print(f"📊 Bollinger Bands for {symbol}: Lower: \033[1;31m${lower_band:.2f}\033[0m, Middle: \033[1;33m${middle_band:.2f}\033[0m, Upper: \033[1;32m${upper_band:.2f}\033[0m")
        
        symbol_info = await client.get_symbol_info(symbol)
        quote_precision = int(symbol_info['baseAssetPrecision'])
        
        tick_size = float([f['tickSize'] for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'][0])
        min_price_move = float([f['minPrice'] for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'][0])

        order_count = 0

        await cancel_all_oco_orders(client, symbol)
        
        saldo_inicial_usdt = await get_usdt_balance(client)
        print(f"\nInitial USDT Balance: 💰 \033[1;36m${saldo_inicial_usdt:.2f}\033[0m")
        message = f"\nInitial USDT Balance: 💰 <b>${saldo_inicial_usdt:.2f}</b>"
        send_telegram_message(bot_token, chat_id, message)
        
        global quantia_usdt_investimento_inicial
        
        while True:
            if quantia_usdt_investimento_inicial is None:
                try:
                    quantia_usdt_investimento_inicial = float(input("Enter the initial USDT amount: 💰\033[1;36m $"))
                    print("\033[0m")
                except ValueError:
                    print("\033[0m")
                    print("🚫 Invalid input. Please enter a valid number.\n")
                    continue  # Solicita novamente se a entrada não for um número
                if quantia_usdt_investimento_inicial > saldo_inicial_usdt:
                        print("🚫 Insufficient balance for the current investment.\n")
                        quantia_usdt_investimento_inicial = None
                        continue
                else:
                    message = f"Initial USDT amount invested: 💰 <b>${quantia_usdt_investimento_inicial:.2f}</b>"
                    send_telegram_message(bot_token, chat_id, message)
                    break
            else:
                print(f"\nUsing saved initial USDT amount: 💰 \033[1;36m${quantia_usdt_investimento_inicial:.2f}\033[0m\n")
                message = f"Using saved initial USDT amount: 💰 <b>${quantia_usdt_investimento_inicial:.2f}</b>"
                send_telegram_message(bot_token, chat_id, message)
                break
            
        async with bsm.user_socket() as um:
            while True:
                if await should_place_order(client, symbol):
                    closes = await get_closes(client, symbol)  # Atualiza os dados de fechamento
                    
                    rsi = calculate_rsi(closes)
                    
                    volumes = await get_volumes(client, symbol)
                    volumes_series = pd.Series(volumes)  # Converte diretamente para uma Series do Pandas

                    volume_ma = volumes_series.dropna().rolling(window=8).mean().iloc[-1]

                    if volumes_series.iloc[-1] > volume_ma * 1.4: # 🟣🟣
                        msg = f"⚠️ High volume detected, potential \033[1;33mmarket volatility\033[0m. Skipping operating."
                        # Imprime a nova mensagem
                        print(f"\r{msg}", end='', flush=True)
                        # Espera um breve momento antes de limpar a linha novamente
                        await asyncio.sleep(2.2)
                        # Limpa a linha anterior
                        print("\033[2K\r", end='')
                        await asyncio.sleep(0.5)
                        continue
                    macd_current, signal_line_current = calculate_macd(closes)
                    lower_band, middle_band, upper_band = calculate_bollinger_bands(closes)
            
                    if rsi < 30 or (macd_current > signal_line_current and closes[-1] < lower_band): # 🟣🟣
                        print("")
                        print(f"🟢 RSI: \033[1;32m{rsi:.1f}\033[0m, MACD \033[1;32mabove\033[0m Signal Line, Bollinger Bands \033[1;32mbuy\033[0m signal found.")
                        ticker = await client.get_symbol_ticker(symbol=symbol)
                        current_price = f"{float(ticker['price']):.2f}"
                        print(f"\nCurrent Price: 📈 \033[1;33m${current_price}\033[0m\n")
                        
                        order_count += 1
                        
                        compra = await client.order_market_buy(symbol=symbol, quoteOrderQty=round(quantia_usdt_investimento_inicial, quote_precision))
                        executed_qty = float(compra['executedQty'])
                        price = float(compra['fills'][0]['price'])
                        timestamp = datetime.now().strftime("%d/%m/%Y at %H:%M:%S")
                        price_rounded = round(price, 4) if price < 1 else round(price, 2)
                        
                        print(f"✅️ \033[1;36m({order_count:02d})\033[0m Purchased: Coin: \033[1;32m{symbol}\033[0m, Coin Qty: \033[1;32m{executed_qty}\033[0m, Price: \033[1;34m${price_rounded}\033[0m \033[1;36m({timestamp})\033[0m\n")
                        winsound.Beep(800, 1500) # Purchased: Coin.
                        message = f"✅️ ({order_count:02d}) <b>Purchased</b>: Coin: <b>{symbol}</b>, Coin Qty: <b>{executed_qty}</b>, Price: <b>${price_rounded} ({timestamp})</b>"
                        send_telegram_message(bot_token, chat_id, message)
                        purchase_timestamp = timestamp
                                
                        oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit = await adjust_and_place_oco_order(client, symbol, executed_qty, tick_size, min_price_move)
                        
                        # Await OCO order completion
                        while True:
                            msg = await um.recv()
                            if msg.get('e') == 'listStatus' and msg.get('s') == symbol and msg.get('g') == oco_order['orderListId']:
                                if 'ALL_DONE' in msg.get('l'):
                                    # Aqui, você busca os detalhes das ordens e verifica qual foi executada
                                    limit_order_details = await get_order_details(client, symbol, limit_order_id)
                                    stop_order_details = await get_order_details(client, symbol, stop_order_id)

                                    # Verifique qual ordem foi executada baseado no campo 'status'
                                    if limit_order_details['status'] == 'FILLED':
                                        print("")
                                        print(f"✅️ OCO Order completed at \033[1;32mprofit\033[0m, Coin: \033[1;32m{symbol}\033[0m \033[1;36m({timestamp})\033[0m")
                                        winsound.Beep(1200, 1300) # OCO Order completed at profit.
                                        message = f'✅️ OCO Order completed at <b>profit</b>, Coin: <b>{symbol} ({timestamp})</b>'
                                        send_telegram_message(bot_token, chat_id, message)
                                        oco_order_result = 'profit'
                                        oco_timestamp = timestamp
                                        price_sold = float(limit_order_details['price'])
                                        trade_result = calculate_trade_result(price, executed_qty, price_sold)
                                        print(f"\nParcial balance difference: 🟢 \033[1;32m${trade_result:.2f}\033[0m")  # Verde e negrito
                                        message2 = f'Parcial balance difference: 🟢 <b>${trade_result:.2f}</b>' # 🟢
                                        send_telegram_message(bot_token, chat_id, message2)
                                    elif stop_order_details['status'] == 'FILLED':
                                        print("")
                                        print(f"⛔ OCO Order completed at \033[1;31mstop loss\033[0m, Coin: \033[1;31m{symbol}\033[0m \033[1;36m({timestamp})\033[0m")
                                        winsound.Beep(400, 1300) # OCO Order completed at stoploss.
                                        message = f'⛔ OCO Order completed at <b>stop loss</b>, Coin: <b>{symbol} ({timestamp})</b>'
                                        send_telegram_message(bot_token, chat_id, message)
                                        oco_order_result = 'stop loss'
                                        oco_timestamp = timestamp
                                        price_sold = float(stop_order_details['price'])
                                        trade_result = calculate_trade_result(price, executed_qty, price_sold)
                                        print(f"\nParcial balance difference: 🔴 \033[1;31m${trade_result:.2f}\033[0m")  # Vermelho e negrito
                                        message2 = f'Parcial balance difference: 🔴 <b>${trade_result:.2f}</b>' # 🔴
                                        send_telegram_message(bot_token, chat_id, message2)
                                    else:
                                        print("⚠  No detailed orders information available in the message.")
                                        message = f'⚠ <b>No detailed orders information available in the message</b>, Coin: <b>{symbol} ({timestamp})</b>'
                                        send_telegram_message(bot_token, chat_id, message)
                                        
                                    saldo_atual_usdt = await get_usdt_balance(client)
                                    saldo_atual_usdt = round(saldo_atual_usdt, 2)
                                    
                                    total_difference = saldo_atual_usdt - saldo_inicial_usdt
                                    if total_difference > 0:
                                        print(f"Total balance difference: 🟢 \033[1;32m${total_difference:.2f}\033[0m\n")  # Verde e negrito
                                        message2 = f'Total balance difference: 🟢 <b>${total_difference:.2f}</b>' # 🟢
                                        send_telegram_message(bot_token, chat_id, message2)
                                    else:
                                        print(f"Total balance difference: 🔴 \033[1;31m${total_difference:.2f}\033[0m\n")  # Vermelho e negrito
                                        message2 = f'Total balance difference: 🔴 <b>${total_difference:.2f}</b>' # 🔴
                                        send_telegram_message(bot_token, chat_id, message2)
                                    
                                    quantia_usdt_investimento_inicial += trade_result
                                    
                                    print(f"Current invested USDT Balance: 💰 \033[1;36m${quantia_usdt_investimento_inicial:.2f}\033[0m\n")
                                    message = f'Current invested USDT Balance: 💰 <b>${quantia_usdt_investimento_inicial:.2f}</b>'
                                    send_telegram_message(bot_token, chat_id, message)
                                    
                                    data_row = {
                                        "Order Index": f"{order_count:02d}",
                                        "Initial USDT Balance": round(saldo_inicial_usdt,2),
                                        "Initial USDT Invested": round(quantia_usdt_investimento_inicial,2),
                                        "Symbol": symbol,
                                        "Coin Qty": executed_qty,
                                        "Purchase Price": price_rounded,
                                        "Purchase Timestamp": purchase_timestamp,
                                        "OCO Profit Target": lucro_alvo,
                                        "OCO Stop Loss": stop_loss,
                                        "OCO Stop Limit": stop_limit,
                                        "OCO Order Result": oco_order_result,
                                        "OCO Timestamp": oco_timestamp,
                                        "Trade Result" : round(trade_result,2),
                                        "Total Result" : round(total_difference,2),
                                        "Final USDT Balance": round(saldo_atual_usdt,2)
                                    }
                                    
                                    save_to_excel(data_row)
                                    
                                    break                              
                                
                    elif rsi > 70 or (macd_current < signal_line_current and closes[-1] > upper_band): # 🟣🟣
                        ticker = await client.get_symbol_ticker(symbol=symbol)
                        current_price = f"{float(ticker['price']):.2f}"
                        msg = f"⛔ Signals indicates potential \033[1;31msell\033[0m conditions for {symbol}. RSI: \033[1;31m{rsi:.1f}\033[0m, Current Price: \033[1;33m${current_price}\033[0m"
                        # Imprime a nova mensagem
                        print(f"\r{msg}", end='', flush=True)
                        # Espera um breve momento antes de limpar a linha novamente
                        await asyncio.sleep(2.2)
                        # Limpa a linha anterior
                        print("\033[2K\r", end='')
                        await asyncio.sleep(0.5)
                        continue
                    else:
                        ticker = await client.get_symbol_ticker(symbol=symbol)
                        current_price = f"{float(ticker['price']):.2f}"
                        msg = f"🟡 \033[1;33mNo clear buy or sell conditions\033[0m signal for {symbol}. RSI: \033[1;33m{rsi:.1f}\033[0m, Current Price: \033[1;33m${current_price}\033[0m"
                        # Imprime a nova mensagem
                        print(f"\r{msg}", end='', flush=True)
                        # Espera um breve momento antes de limpar a linha novamente
                        await asyncio.sleep(2.2)
                        # Limpa a linha anterior
                        print("\033[2K\r", end='')
                        await asyncio.sleep(0.5)
                        continue

                await asyncio.sleep(0.5)  # Short pause before checking for new orders or balance updates

            await client.close_connection()
            
    except BinanceAPIException as e:
        if restart_attempts < MAX_RESTARTS:
            restart_attempts += 1
            if e.code == -1021:  # Código de erro para timestamp incorreto
                print("⚠  \nErro de timestamp detectado, tentando reiniciar o bot...")
                message = '⚠ Erro de <b>timestamp</b> detectado, tentando reiniciar o bot...'
                send_telegram_message(bot_token, chat_id, message)
            else:
                print(f"⚠  \nErro detectado: {e}")
                message = f'⚠ Erro detectado: <b>{e}</b>'
                send_telegram_message(bot_token, chat_id, message)
            print("⏱  Aguardando 5 segundos antes de reiniciar...")
            await asyncio.sleep(3)
            print("♻  Reiniciando o bot...")
            message = "♻ Reiniciando o bot..."
            send_telegram_message(bot_token, chat_id, message)
            await run_bot()  # Tenta reiniciar o bot automaticamente
        else:
            print("🚨 \nNúmero máximo de tentativas de reinício atingido. O bot será desligado.")
            message = "🚨 <b>Número máximo</b> de tentativas de reinício atingido. O bot será desligado."
            send_telegram_message(bot_token, chat_id, message)
            exit()
        
    except Exception as e:
        if restart_attempts < MAX_RESTARTS:
            restart_attempts += 1
            print(f"⚠  \nErro inesperado: {e}, reiniciando o bot após 5 segundos...")
            message = f"⚠ Erro inesperado: <b>{e}</b>, reiniciando o bot após 5 segundos..."
            send_telegram_message(bot_token, chat_id, message)
            await asyncio.sleep(3)
            await run_bot()
        else:
            print("🚨 \nNúmero máximo de tentativas de reinício atingido. O bot será desligado.")
            message = "🚨 <b>Número máximo</b> de tentativas de reinício atingido. O bot será desligado."
            send_telegram_message(bot_token, chat_id, message)
            exit()

if __name__ == "__main__":
    asyncio.run(run_bot())