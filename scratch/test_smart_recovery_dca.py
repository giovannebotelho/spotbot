import asyncio
import sys
sys.path.insert(0, '.')
from binance import AsyncClient as BinanceAsyncClient
from config.settings import API_KEYS
from services.binance_client import get_klines
from core.indicators import calculate_fibonacci_supports

async def test_live_fib_dca():
    key = API_KEYS.get('mainnet', {}).get('key', '')
    secret = API_KEYS.get('mainnet', {}).get('secret', '')
    client = await BinanceAsyncClient.create(key, secret)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT']
    print("==================================================")
    print("TESTE EM TEMPO REAL: SMART RECOVERY DCA & FIBONACCI SUPPORTS")
    print("==================================================")
    try:
        for sym in symbols:
            klines = await get_klines(client, sym, '15m', 50)
            ticker = await client.get_symbol_ticker(symbol=sym)
            cur_price = float(ticker['price'])
            
            fib_618, fib_786, swing_high, swing_low = calculate_fibonacci_supports(klines)
            
            print(f"\nPar: {sym} | Preco Atual: ${cur_price:.4f}")
            print(f"  - Swing High: ${swing_high:.4f} | Swing Low: ${swing_low:.4f}")
            print(f"  - Suporte Fibonacci 61.8%: ${fib_618:.4f} (Zona de Recompra DCA 1)")
            print(f"  - Suporte Fibonacci 78.6%: ${fib_786:.4f} (Zona de Recompra DCA 2)")
            
            dist_618 = ((cur_price - fib_618) / cur_price) * 100
            print(f"  - Distancia ate Suporte DCA (61.8%): {dist_618:.2f}%")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_live_fib_dca())
