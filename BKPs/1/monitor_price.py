import asyncio
from binance import AsyncClient, BinanceSocketManager
from config import my_api_key, my_secret_key

print("")

async def monitor_btc_price():
    client = await AsyncClient.create(api_key=my_api_key, api_secret=my_secret_key, testnet=True)
    bsm = BinanceSocketManager(client)

    async with bsm.trade_socket('BTCUSDT') as ts:
        while True:
            res = await ts.recv()
            price = float(res['p'])
            # Arredonda o preço para 2 casas decimais antes de exibir
            print(f"\rCurrent BTCUSDT Price: \033[1;32m{price:.2f}\033[0m", end='', flush=True)

async def main():
    await monitor_btc_price()

if __name__ == "__main__":
    asyncio.run(main())