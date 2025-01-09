import asyncio
from binance import AsyncClient, BinanceSocketManager

from config import my_api_key, my_secret_key

async def print_balance(client, asset='BTC'):
    """Função assíncrona para imprimir o saldo de um ativo."""
    balance = await client.get_asset_balance(asset=asset)
    print(f"Saldo de {asset}: {balance['free']} disponível")

async def place_order_async(client, symbol, quantity, side):
    """Função assíncrona para enviar uma ordem."""
    if side.upper() == 'BUY':
        order = await client.order_market_buy(symbol=symbol, quantity=quantity)
    elif side.upper() == 'SELL':
        order = await client.order_market_sell(symbol=symbol, quantity=quantity)
    else:
        return None
    return order

async def btc_trade_history(client, msg):
    """Define como lidar com a mensagem recebida."""
    if msg['e'] == 'error':
        print(msg['m'])
    else:
        print(f"Mensagem recebida: {msg}")
        # Aqui, você poderia incluir lógica baseada nas mensagens recebidas,
        # como decidir quando comprar ou vender.

async def main(api_key, api_secret):
    client = await AsyncClient.create(api_key, api_secret, testnet=True)
    bsm = BinanceSocketManager(client)
    
    # Imprime o saldo inicial
    await print_balance(client, 'BTC')

    async with bsm.trade_socket('BTCUSDT') as stream:
        while True:
            msg = await stream.recv()
            await btc_trade_history(client, msg)

    # Fechando a conexão
    await client.close_connection()

if __name__ == "__main__":
    api_key = my_api_key
    api_secret = my_secret_key
    asyncio.run(main(api_key, api_secret))