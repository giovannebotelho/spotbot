import asyncio
import sys
sys.path.insert(0, '.')
from binance import AsyncClient as BinanceAsyncClient
from config.settings import API_KEYS
from services.binance_client import get_multi_timeframe_klines
from core.indicators import calculate_multi_timeframe_confluence

async def test_live_mtf():
    key = API_KEYS.get('mainnet', {}).get('key', '')
    secret = API_KEYS.get('mainnet', {}).get('secret', '')
    client = await BinanceAsyncClient.create(key, secret)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT']
    print("==================================================")
    print("TESTE EM TEMPO REAL: MATRIZ DE CONFLUENCIA 4H+1H+15M")
    print("==================================================")
    try:
        for sym in symbols:
            mtf_data = await get_multi_timeframe_klines(client, sym)
            score, is_confluent, details = calculate_multi_timeframe_confluence(
                mtf_data.get('4h', []),
                mtf_data.get('1h', []),
                mtf_data.get('15m', [])
            )
            status_str = "APROVADO" if is_confluent else "BLOQUEADO"
            print(f"\nPar: {sym} | Status: {status_str} | Score MTF: {score}%")
            for r in details['reasons']:
                print(f"  - {r}")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_live_mtf())
