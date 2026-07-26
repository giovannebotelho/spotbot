import asyncio
import sys
sys.path.insert(0, '.')
from binance import AsyncClient as BinanceAsyncClient
from services.binance_client import get_order_book
from core.indicators import calculate_orderbook_imbalance

async def test_orderbook():
    print("Testing Orderbook Imbalance Scanner on live Binance Spot API...")
    client = await BinanceAsyncClient.create()
    try:
        for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
            ob = await get_order_book(client, sym, depth=20)
            ratio, bids_vol, asks_vol, wall, msg = calculate_orderbook_imbalance(ob)
            print(f"[{sym}] Bids Vol: {bids_vol:.2f} | Asks Vol: {asks_vol:.2f} | Imbalance Ratio: {ratio:.2f}x | Whale Wall: {wall} | Msg: {msg}")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_orderbook())
