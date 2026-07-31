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
        # Test calling legacy endpoint vs orderList/oco
        print("Testing legacy /order/oco endpoint...")
        params = {
            'symbol': 'BTCUSDT',
            'side': 'SELL',
            'quantity': '0.001',
            'price': '100000',
            'stopPrice': '50000',
            'stopLimitPrice': '49900',
            'stopLimitTimeInForce': 'GTC'
        }
        try:
            res = await client._post("order/oco", True, data=params)
            print("Legacy /order/oco response:", res)
        except Exception as e:
            print("Legacy /order/oco error:", e)

    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_oco())
