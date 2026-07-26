import asyncio
import sys
sys.path.insert(0, '.')
from services.binance_client import get_futures_analytics
from core.indicators import analyze_futures_squeeze_potential

async def test_futures():
    print("Testing Futures Analytics on live Binance Futures API...")
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "PEPEUSDT"]:
        data = await get_futures_analytics(sym)
        is_sq, msg = analyze_futures_squeeze_potential(data, smc_sweep_active=True)
        print(f"[{sym}] Funding Rate: {data['funding_rate_pct']:.4f}% | Open Interest: {data['open_interest']:.2f} | Short Heavy: {data['is_short_heavy']} | Setup: {msg}")

if __name__ == "__main__":
    asyncio.run(test_futures())
