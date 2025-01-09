import asyncio
import math
from datetime import datetime
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException
from config import my_api_key, my_secret_key

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
        if 'orderListId' in order and order['orderListId'] > -1:  # Checks if it's part of an OCO
            try:
                await client.cancel_order(symbol=symbol, orderId=order['orderId'])
                print(f"\nOCO Order canceled: Order ID: \033[1;32m{order['orderId']}\033[0m")
            except BinanceAPIException as e:
                print(f"\nFailed to cancel OCO order \033[1;31m{order['orderId']}: {e}\033[0m")

async def main():
    client = await AsyncClient.create(api_key, api_secret, testnet=True)
    bsm = BinanceSocketManager(client)
    symbol = 'BTCUSDT'
    symbol_info = await client.get_symbol_info(symbol)
    tick_size = float([f['tickSize'] for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'][0])

    order_count = 0

    await cancel_all_oco_orders(client, symbol)
    saldo_inicial_usdt = await get_usdt_balance(client)
    saldo_inicial_usdt = round(saldo_inicial_usdt, 2)
    print(f"\nInitial USDT Balance: \033[1;33m {saldo_inicial_usdt} \033[0m")
    quantia_usdt_investimento_inicial = float(input("Enter the initial USDT amount:\033[1;33m "))

    async with bsm.user_socket() as um:
        while True:
            order_count += 1
            saldo_atual_usdt = await get_usdt_balance(client)
            quantia_usdt_para_investir = min(quantia_usdt_investimento_inicial, saldo_atual_usdt)
            if quantia_usdt_para_investir > saldo_atual_usdt:
                print("Insufficient balance for the current investment.")
                continue

            compra = await client.order_market_buy(symbol=symbol, quoteOrderQty=quantia_usdt_para_investir)
            executed_qty = float(compra['executedQty'])
            timestamp = datetime.now().strftime("%d/%m/%Y at %H:%M:%S")
            price_rounded = round(float(compra['fills'][0]['price']), 2)
            print(f"\n\033[1;36m({order_count:02d})\033[0m Purchased: Coin: \033[1;32m{symbol}\033[0m, Coin Qty: \033[1;32m{executed_qty}\033[0m, Price: \033[1;34m{price_rounded}\033[0m \033[1;36m({timestamp})\033[0m")

            lucro_alvo = adjust_price_to_tick_size(float(compra['fills'][0]['price']) * 1.0030, tick_size)
            stop_loss = adjust_price_to_tick_size(float(compra['fills'][0]['price']) * 0.9980, tick_size)
            stop_limit = stop_loss - 100 * tick_size
            
            # Adicionamos um novo parâmetro no início do seu main para definir o número máximo de tentativas
            max_attempts = 3  # Número máximo de tentativas para colocar a ordem OCO

            # Dentro do loop async with bsm.user_socket() as um:, após a compra ser efetuada, modificamos a parte que coloca a ordem OCO
            attempt = 0
            while attempt < max_attempts:
                try:
                    oco_order = await client.create_oco_order(
                        symbol=symbol,
                        side="SELL",
                        quantity="{:.6f}".format(executed_qty),
                        price="{:.2f}".format(lucro_alvo),
                        stopPrice="{:.2f}".format(stop_loss),
                        stopLimitPrice="{:.2f}".format(stop_limit),
                        stopLimitTimeInForce='GTC'
                    )
                    print(f"OCO Order placed: Profit: \033[1;32m{lucro_alvo:.2f}\033[0m, Stop Price: \033[1;31m{stop_loss:.2f}\033[0m, Stop Limit: \033[1;31m{stop_limit:.2f}\033[0m")
                    break  # Sai do loop se a ordem for colocada com sucesso
                except BinanceAPIException as e:
                    print(f"Attempt {attempt + 1}: Error placing OCO order: \033[31m{e}\033[0m")
                    if attempt < max_attempts - 1:  # Verifica se mais tentativas serão feitas
                        print("Waiting 3 seconds before retrying...")
                        await asyncio.sleep(2)  # Espera 3 segundos antes da próxima tentativa
                attempt += 1

            # Se após max_attempts ainda tivermos erro, você pode decidir o que fazer a seguir. Pode optar por parar a execução ou apenas continuar e tentar novamente na próxima iteração do loop principal.

            # Await OCO order completion
            while True:
                msg = await um.recv()
                if msg['e'] == 'listStatus' and msg['s'] == symbol and msg['g'] == oco_order['orderListId']:
                    if msg['l'] == 'ALL_DONE':
                        print(f"OCO Order completed. Preparing...")
                        saldo_atual_usdt = await get_usdt_balance(client)
                        saldo_atual_usdt = round(saldo_atual_usdt, 2)
                        print(f"\nCurrent USDT Balance: \033[1;33m{saldo_atual_usdt}\033[0m")
                        break

            await asyncio.sleep(2)  # Short pause before the next iteration

    await client.close_connection()
    
if __name__ == "__main__":
    asyncio.run(main())