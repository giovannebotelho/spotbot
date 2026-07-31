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
        # Check signature of create_oco_order
        import inspect
        print("create_oco_order signature:", inspect.signature(client.create_oco_order))
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_oco())
