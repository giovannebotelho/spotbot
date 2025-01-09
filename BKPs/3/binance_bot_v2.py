import asyncio
import math
from datetime import datetime
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException
from config import my_api_key, my_secret_key
from collections import deque
import numpy as np
import pandas as pd

api_key = my_api_key
api_secret = my_secret_key

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

async def get_order_book(client, symbol, depth=4):
    order_book = await client.get_order_book(symbol=symbol, limit=depth)
    return order_book

def calculate_sell_pressure(order_book):
    total_asks = sum(float(ask[1]) for ask in order_book['asks'])
    total_bids = sum(float(bid[1]) for bid in order_book['bids'])
    total = total_asks + total_bids
    return total_asks / total if total > 0 else 0

sell_pressure_history = deque(maxlen=9)

async def calculate_moving_average_sell_pressure(client, symbol, depth=4):
    order_book = await get_order_book(client, symbol, depth)
    sell_pressure = calculate_sell_pressure(order_book)
    sell_pressure_history.append(sell_pressure)
    return sum(sell_pressure_history) / len(sell_pressure_history)

async def should_place_order(client, symbol, SELL_PRESSURE_THRESHOLD = 0.70):
    avg_sell_pressure = await calculate_moving_average_sell_pressure(client, symbol)
    
    msg = f"High average sell pressure detected: \033[1;31m{avg_sell_pressure:.2f}\033[0m. Waiting before placing the order..."
    
    if avg_sell_pressure < SELL_PRESSURE_THRESHOLD:
        print(f"\r{' ' * len(msg)}", end='')
        return True
    else:
        # Limpa a linha anterior
        print(f"\r{' ' * len(msg)}", end='')
        # Espera um breve momento antes de imprimir a nova mensagem
        await asyncio.sleep(0.2)
        # Imprime a nova mensagem
        print(f"\r{msg}", end='', flush=True)
        await asyncio.sleep(2)
            
def escolher_simbolo():
    while True:
        print("\nEscolha o símbolo preferido ou digite manualmente:")
        print('1 - BTC/USDT')
        print('2 - DOGE/USDT')
        print('3 - SOL/USDT')
        print('4 - Outra')
        
        try:
            symbol_input = int(input(": "))
        except ValueError:
            print("\nPor favor, digite um número.")
            continue

        if symbol_input == 1:
            return 'BTCUSDT'
        elif symbol_input == 2:
            return 'DOGEUSDT'
        elif symbol_input == 3:
            return 'SOLUSDT'
        elif symbol_input == 4:
            escolha_alternativa = input("\nDigite a moeda requerida no formato (Ex.: BTCUSDT): ")
            return escolha_alternativa.upper()  # Garante que o texto será maiúsculo
        else:
            print("\nDigite uma opção válida.")
            
async def adjust_and_place_oco_order(client, symbol, quantity, tick_size, min_price_move):
    max_attempts = 3
    for attempt in range(max_attempts):
        order_book = await get_order_book(client, symbol)
        current_price = float(order_book['asks'][0][0])

        if current_price < 1:
            lucro_multiplier = 1.01
            stop_loss_multiplier = 0.99
        else:
            lucro_multiplier = 1.0025
            stop_loss_multiplier = 0.9985

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
            if symbol == "DOGEUSDT":
                print(f"OCO Order placed. ID: \033[1;34m{order_list_id}\033[0m. Profit: \033[1;32m{lucro_alvo:.4f}\033[0m, Stop Price: \033[1;31m{stop_loss:.4f}\033[0m, Stop Limit: \033[1;31m{stop_limit:.4f}\033[0m")
            else:
                print(f"OCO Order placed. ID: \033[1;34m{order_list_id}\033[0m. Profit: \033[1;32m{lucro_alvo:.2f}\033[0m, Stop Price: \033[1;31m{stop_loss:.2f}\033[0m, Stop Limit: \033[1;31m{stop_limit:.2f}\033[0m")
            return oco_order
        except BinanceAPIException as e:
            print(f"\nAttempt \033[1;31m{attempt + 1}\033[0m: Error placing OCO order: {e}")
            if attempt < max_attempts - 1:
                print("\nAdjusting prices and retrying...")
                await asyncio.sleep(2)  # Breve pausa antes de tentar novamente

    print("\n\033[1;31mFailed\033[0m to place OCO order after several attempts.")
    return None

def calculate_rsi(closes, period=14):
    deltas = np.diff(closes)
    gain = np.where(deltas > 0, deltas, 0)
    loss = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.average(gain[-period:])
    avg_loss = np.average(loss[-period:])

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

async def get_closes(client, symbol, interval='5m', limit=10):
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    closes = [float(kline[4]) for kline in klines]
    return closes

def calculate_macd(closes, slow=26, fast=12, signal=9):
    """Calcula o MACD e a linha de sinal usando pandas."""
    closes_series = pd.Series(closes)
    ema_fast = closes_series.ewm(span=fast, adjust=False).mean()
    ema_slow = closes_series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]

def calculate_bollinger_bands(closes, period=10, num_std=2):    
    closes_series = pd.Series(closes)
    ma = closes_series.rolling(window=period).mean()
    std = closes_series.rolling(window=period).std()
    
    upper_band = ma + (std * num_std)
    lower_band = ma - (std * num_std)
    
    return lower_band.iloc[-1], ma.iloc[-1], upper_band.iloc[-1]

async def main():
    client = await AsyncClient.create(api_key, api_secret, testnet=True)
    bsm = BinanceSocketManager(client)
    
    symbol = escolher_simbolo()
    closes = await get_closes(client, symbol)
    print(f"\nVocê escolheu: \033[1;33m{symbol}\033[0m")
    
    rsi = calculate_rsi(closes)
    print(f"\nCurrent RSI for {symbol}: \033[1;33m{rsi:.1f}\033[0m")
    
    macd_current, signal_line_current = calculate_macd(closes)
    print(f"Current MACD for {symbol}: \033[1;33m{macd_current:.2f}\033[0m, Signal line: \033[1;33m{signal_line_current:.2f}\033[0m")
    
    lower_band, middle_band, upper_band = calculate_bollinger_bands(closes)
    print(f"Bollinger Bands for {symbol}: Lower: \033[1;31m{lower_band:.2f}\033[0m, Middle: \033[1;33m{middle_band:.2f}\033[0m, Upper: \033[1;32m{upper_band:.2f}\033[0m")
    
    symbol_info = await client.get_symbol_info(symbol)
    
    tick_size = float([f['tickSize'] for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'][0])
    min_price_move = float([f['minPrice'] for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'][0])

    order_count = 0

    await cancel_all_oco_orders(client, symbol)
    
    saldo_inicial_usdt = await get_usdt_balance(client)
    print(f"\nInitial USDT Balance: \033[1;33m{saldo_inicial_usdt:.2f}\033[0m")
    
    quantia_usdt_investimento_inicial = float(input("Enter the initial USDT amount:\033[1;33m "))
    print("\033[1;33m\033[0m")

    async with bsm.user_socket() as um:
        while True:
            saldo_atual_usdt = await get_usdt_balance(client)  # Obter saldo atual antes de cada tentativa de compra
            if saldo_atual_usdt < quantia_usdt_investimento_inicial:
                print("\nInsufficient balance for the current investment. Exiting...")
                break  # Encerra o loop se o saldo for insuficiente para a compra

            if await should_place_order(client, symbol):
                
                closes = await get_closes(client, symbol)  # Atualiza os dados de fechamento
                rsi = calculate_rsi(closes)
                macd_current, signal_line_current = calculate_macd(closes)
                lower_band, middle_band, upper_band = calculate_bollinger_bands(closes)
                        
                
                if rsi < 25 and macd_current > signal_line_current and closes[-1] < lower_band:
                    print(f"\nRSI is \033[1;32m{rsi:.1f}\033[0m, considering buying {symbol}. MACD \033[1;32mabove Signal Line, buy\033[0m signal. \033[1;32mBollinger Bands opport. buy\033[0m found.")
            
                    order_count += 1
                    
                    compra = await client.order_market_buy(symbol=symbol, quoteOrderQty=quantia_usdt_investimento_inicial)
                    executed_qty = float(compra['executedQty'])
                    price = float(compra['fills'][0]['price'])
                    timestamp = datetime.now().strftime("%d/%m/%Y at %H:%M:%S")
                    price_rounded = round(price, 4) if price < 1 else round(price, 2)
                    
                    print(f"\n\033[1;36m({order_count:02d})\033[0m Purchased: Coin: \033[1;32m{symbol}\033[0m, Coin Qty: \033[1;32m{executed_qty}\033[0m, Price: \033[1;34m{price_rounded}\033[0m \033[1;36m({timestamp})\033[0m\n")
                    pass    
                    
                    while True:
                        
                        closes = await get_closes(client, symbol)  # Atualiza os dados de fechamento
                        rsi = calculate_rsi(closes)
                        macd_current, signal_line_current = calculate_macd(closes)
                        lower_band, middle_band, upper_band = calculate_bollinger_bands(closes)
                        
                        if rsi > 65 and macd_current < signal_line_current and closes[-1] > upper_band:                            
                            print(f"\nRSI is \033[1;31m{rsi:.1f}\033[0m, considering selling {symbol}. MACD \033[1;31mbelow Signal Line, sell\033[0m signal. \033[1;31mBollinger Bands opport. sell\033[0m found.\n")
                            
                            oco_order = await adjust_and_place_oco_order(client, symbol, executed_qty, tick_size, min_price_move)
                            
                            # Await OCO order completion
                            while True:
                                msg = await um.recv()
                                if msg['e'] == 'listStatus' and msg['s'] == symbol and msg['g'] == oco_order['orderListId']:
                                    if msg['l'] == 'ALL_DONE':
                                        print(f"\nOCO Order completed. Preparing...")
                                        saldo_atual_usdt = await get_usdt_balance(client)
                                        saldo_atual_usdt = round(saldo_atual_usdt, 2)
                                        print(f"Current USDT Balance: \033[1;33m{saldo_atual_usdt}\033[0m")
                                        break
                            break
                        else:
                            msg = "Waiting for selling conditions..."
                            # Limpa a linha anterior
                            print(f"\r{' ' * len(msg)}", end='')
                            # Espera um breve momento antes de imprimir a nova mensagem
                            await asyncio.sleep(0.2)
                            # Imprime a nova mensagem
                            print(f"\r{msg}", end='', flush=True)
                            await asyncio.sleep(2.5)
                            continue
                            
                if rsi > 65 or macd_current < signal_line_current or closes[-1] > upper_band:
                    msg = f"Signals indicates potential \033[1;31msell\033[0m for {symbol}, Waiting for buying conditions. RSI is \033[1;31m{rsi:.1f}\033[0m."
                    # Limpa a linha anterior
                    print(f"\r{' ' * len(msg)}", end='')
                    # Espera um breve momento antes de imprimir a nova mensagem
                    await asyncio.sleep(0.2)
                    # Imprime a nova mensagem
                    print(f"\r{msg}", end='', flush=True)
                    await asyncio.sleep(2.5)
                    continue
                else:
                    msg = f"\033[1;33mNo clear buy or sell conditions\033[0m signal for {symbol}."
                    # Limpa a linha anterior
                    print(f"\r{' ' * len(msg)}", end='')
                    # Espera um breve momento antes de imprimir a nova mensagem
                    await asyncio.sleep(0.2)
                    # Imprime a nova mensagem
                    print(f"\r{msg}", end='', flush=True)
                    await asyncio.sleep(2.5)
                    continue

            await asyncio.sleep(2)  # Short pause before checking for new orders or balance updates

    await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main())