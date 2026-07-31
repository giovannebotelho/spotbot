import asyncio
import sys
sys.path.insert(0, '.')
from binance import AsyncClient as BinanceAsyncClient
from config.settings import API_KEYS

async def test_oco():
    key = API_KEYS.get('mainnet', {}).get('key', '')
    secret = API_KEYS.get('mainnet', {}).get('secret', '')
    client = await BinanceAsyncClient.create(key, secret)
    try:
        open_ocos = await client.get_open_oco_orders()
        open_orders = await client.get_open_orders()
        print("OPEN OCOS:", open_ocos)
        print("OPEN ORDERS:", open_orders)
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_oco())
