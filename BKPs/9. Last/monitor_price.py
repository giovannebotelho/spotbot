import asyncio
from binance import AsyncClient, BinanceSocketManager
from config import my_api_key, my_secret_key

# Dicionário para armazenar os preços mais recentes
current_prices = {}

async def monitor_price(symbol, prices_dict):
    client = await AsyncClient.create(api_key=my_api_key, api_secret=my_secret_key, testnet=True)
    bsm = BinanceSocketManager(client)

    async with bsm.trade_socket(symbol) as ts:
        while True:
            res = await ts.recv()
            price = float(res['p'])
            prices_dict[symbol] = price  # Atualiza o preço no dicionário

async def print_prices(prices_dict):
    while True:
        # Limpa a tela
        print("\033[H\033[J", end="")
        for symbol, price in prices_dict.items():
            # Substitui 'USDT' por '' para remover do símbolo
            symbol_without_usdt = symbol.replace("USDT", "")
            # Aplica formatação específica com base no símbolo
            if symbol == 'DOGEUSDT':
                formatted_price = f"{price:.4f}"  # 4 casas decimais para DOGE
            elif symbol == 'ADAUSDT':
                formatted_price = f"{price:.3f}"  # 4 casas decimais para DOGE
            else:
                formatted_price = f"{price:.2f}"  # 2 casas decimais para BTC e SOL
            print(f"🪙 \033[1m{symbol_without_usdt}\033[0m: 💲\033[1;32m{formatted_price}\033[0m")
        await asyncio.sleep(0.6)  # Atualiza a tela a cada segundo

async def main():
    # Inicia a corotina de impressão
    printer_task = asyncio.create_task(print_prices(current_prices))

    # Inicia corotinas para monitorar cada símbolo
    monitor_tasks = [
        asyncio.create_task(monitor_price('BTCUSDT', current_prices)),
        asyncio.create_task(monitor_price('ETHUSDT', current_prices)),
        asyncio.create_task(monitor_price('BNBUSDT', current_prices)),
        asyncio.create_task(monitor_price('ADAUSDT', current_prices)),
        asyncio.create_task(monitor_price('SOLUSDT', current_prices)),
        asyncio.create_task(monitor_price('DOGEUSDT', current_prices)),
    ]

    await asyncio.gather(*monitor_tasks)
    await printer_task

if __name__ == "__main__":
    asyncio.run(main())