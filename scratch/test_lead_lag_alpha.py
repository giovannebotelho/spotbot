import asyncio
import sys
sys.path.insert(0, '.')
from binance import AsyncClient as BinanceAsyncClient
from config.settings import API_KEYS
from services.binance_client import get_lead_lag_btc_klines, get_klines
from core.indicators import calculate_lead_lag_alpha

async def test_live_lead_lag():
    key = API_KEYS.get('mainnet', {}).get('key', '')
    secret = API_KEYS.get('mainnet', {}).get('secret', '')
    client = await BinanceAsyncClient.create(key, secret)
    
    symbols = ['AVAXUSDT', 'SOLUSDT', 'ETHUSDT']
    print("==================================================")
    print("TESTE EM TEMPO REAL: CORRELATION LEAD-LAG ALPHA ENGINE")
    print("==================================================")
    try:
        btc_1m = await get_lead_lag_btc_klines(client)
        btc_closes = [float(k[4]) for k in btc_1m]
        btc_change_3m = ((btc_closes[-1] - btc_closes[-3]) / btc_closes[-3]) * 100 if len(btc_closes) >= 3 else 0.0
        
        print(f"BTCUSDT Preco Atual: ${btc_closes[-1]:.2f} | Variacao 3m: {btc_change_3m:+.2f}%")
        
        for sym in symbols:
            alt_1m = await get_klines(client, sym, '1m', 15)
            is_lead, imp_pct, msg = calculate_lead_lag_alpha(btc_1m, alt_1m)
            status_str = "DISPARO DE ANTECIPACAO (LEAD)" if is_lead else "SEM DIVERGENCIA"
            
            print(f"\nPar: {sym} | Status: {status_str}")
            print(f"  - Mensagem: {msg}")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_live_lead_lag())
