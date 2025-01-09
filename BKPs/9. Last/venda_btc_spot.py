import asyncio
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from config import real_api_key, real_secret_key

api_key = real_api_key
api_secret = real_secret_key

async def sell_coin_for_usdt(client, coin, symbol):
    try:
        # Obtém o saldo disponível da moeda
        balance = await client.get_asset_balance(asset=coin)
        quantity = balance['free']
        print(f"Saldo disponível de {coin}: {quantity} {coin}")

        # Se houver saldo disponível, executa uma ordem de venda a mercado
        if float(quantity) > 0:
            sell_order = await client.order_market_sell(
                symbol=symbol,
                quantity=quantity
            )
            print(f"Ordem de venda executada para {symbol}:", sell_order)
        else:
            print(f"Saldo insuficiente de {coin} para vender.")
    except BinanceAPIException as e:
        print(f"Erro ao executar ordem de venda para {symbol}: {e}")

async def main():
    # Conecta ao cliente da Binance na testnet
    client = await AsyncClient.create(api_key, api_secret)
    
    # Executa a venda de todo BTC, SOL, e DOGE por USDT
    await sell_coin_for_usdt(client, 'BTC', 'BTCUSDT')
    # await sell_coin_for_usdt(client, 'SOL', 'SOLUSDT')
    # await sell_coin_for_usdt(client, 'DOGE', 'DOGEUSDT')

    # Fecha a conexão com o cliente
    await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main())