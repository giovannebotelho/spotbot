import asyncio
import sys
sys.path.insert(0, '.')
from binance import AsyncClient as BinanceAsyncClient
from config.settings import API_KEYS
from services.binance_client import get_klines
from core.indicators import calculate_pair_cointegration_zscore

async def test_live_stat_arb():
    key = API_KEYS.get('mainnet', {}).get('key', '')
    secret = API_KEYS.get('mainnet', {}).get('secret', '')
    client = await BinanceAsyncClient.create(key, secret)
    
    symbols = ['AVAXUSDT', 'SOLUSDT', 'ETHUSDT']
    ref_symbol = 'BTCUSDT'
    print("==================================================")
    print("TESTE EM TEMPO REAL: COINTEGRATION PAIR TRADING & Z-SCORE")
    print("==================================================")
    try:
        btc_klines = await get_klines(client, ref_symbol, '15m', 50)
        for sym in symbols:
            alt_klines = await get_klines(client, sym, '15m', 50)
            z_score, is_arb, r_mean, r_std = calculate_pair_cointegration_zscore(alt_klines, btc_klines)
            status_str = "REVERSAO ESTATISTICA (COMPRA)" if is_arb else "DENTRO DO INTERVALO NORMAL"
            
            print(f"\nPar: {sym} vs {ref_symbol} | Status: {status_str}")
            print(f"  - Z-Score Atual: {z_score:+.2f} sigma")
            print(f"  - Razao Media Historica: {r_mean:.6f} | Desvio-Padrao: {r_std:.6f}")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_live_stat_arb())
