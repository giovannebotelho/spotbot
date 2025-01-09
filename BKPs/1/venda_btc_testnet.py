import asyncio
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from config import my_api_key, my_secret_key

api_key = my_api_key
api_secret = my_secret_key

async def sell_all_btc_for_usdt(client, symbol='BTCUSDT'):
    try:
        # Obtém o saldo de BTC disponível
        btc_balance = await client.get_asset_balance(asset='BTC')
        btc_quantity = btc_balance['free']
        print(f"Saldo disponível de BTC: {btc_quantity} BTC")

        # Se houver saldo disponível, executa uma ordem de venda a mercado
        if float(btc_quantity) > 0:
            sell_order = await client.order_market_sell(
                symbol=symbol,
                quantity=btc_quantity
            )
            print("Ordem de venda executada:", sell_order)
        else:
            print("Saldo insuficiente de BTC para vender.")
    except BinanceAPIException as e:
        print(f"Erro ao executar ordem de venda: {e}")

async def main():
    # Conecta ao cliente da Binance na testnet
    client = await AsyncClient.create(api_key, api_secret, testnet=True)
    
    # Executa a venda de todo BTC por USDT
    await sell_all_btc_for_usdt(client)

    # Fecha a conexão com o cliente
    await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main())