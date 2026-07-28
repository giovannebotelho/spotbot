import asyncio
import sys
sys.path.insert(0, '.')
from binance import AsyncClient as BinanceAsyncClient
from config.settings import API_KEYS
from services.binance_client import get_klines
from core.indicators import calculate_atr

async def test_live_atr():
    key = API_KEYS.get('mainnet', {}).get('key', '')
    secret = API_KEYS.get('mainnet', {}).get('secret', '')
    client = await BinanceAsyncClient.create(key, secret)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT']
    print("==================================================")
    print("TESTE EM TEMPO REAL: VOLATILIDADE ATR & STOPS DINAMICOS")
    print("==================================================")
    try:
        for sym in symbols:
            klines = await get_klines(client, sym, '15m', 100)
            ticker = await client.get_symbol_ticker(symbol=sym)
            cur_price = float(ticker['price'])
            
            atr_val, atr_pct = calculate_atr(klines, period=14)
            stop_loss_pct = max(0.012, min(0.030, atr_pct * 1.2))
            take_profit_pct = max(0.035, stop_loss_pct * 2.0)
            
            print(f"\nPar: {sym} | Preco Atual: ${cur_price:.4f}")
            print(f"  - ATR (14): ${atr_val:.4f} ({atr_pct*100:.2f}% de volatilidade)")
            print(f"  - Stop Loss Dinamico: -{stop_loss_pct*100:.2f}% (Preco: ${cur_price*(1-stop_loss_pct):.4f})")
            print(f"  - Take Profit Dinamico: +{take_profit_pct*100:.2f}% (Preco: ${cur_price*(1+take_profit_pct):.4f})")
            print(f"  - Relacao Risco/Retorno: 2.0x (Protecao Adaptativa Ativa)")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_live_atr())
