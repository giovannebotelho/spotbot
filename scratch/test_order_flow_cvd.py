import asyncio
import sys
sys.path.insert(0, '.')
from binance import AsyncClient as BinanceAsyncClient
from config.settings import API_KEYS
from services.binance_client import get_recent_trades_cvd
from core.indicators import calculate_cvd_trend

async def test_live_cvd():
    key = API_KEYS.get('mainnet', {}).get('key', '')
    secret = API_KEYS.get('mainnet', {}).get('secret', '')
    client = await BinanceAsyncClient.create(key, secret)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT']
    print("==================================================")
    print("TESTE EM TEMPO REAL: ORDER FLOW CUMULATIVE VOLUME DELTA (CVD)")
    print("==================================================")
    try:
        for sym in symbols:
            trades = await get_recent_trades_cvd(client, sym, limit=500)
            cvd_usdt, buy_ratio, is_bullish = calculate_cvd_trend(trades)
            status_str = "AGRESSAO COMPRADORA (BULLISH)" if is_bullish else "NEUTRO / VENDEDOR"
            
            print(f"\nPar: {sym} | Status Tape Reading: {status_str}")
            print(f"  - CVD Acumulado (500 trades): ${cvd_usdt:+,.2f} USDT")
            print(f"  - Porcentagem de Compras a Mercado: {buy_ratio:.1f}%")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_live_cvd())
