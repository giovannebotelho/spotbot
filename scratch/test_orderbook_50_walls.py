import asyncio
import sys
sys.path.insert(0, '.')
from binance import AsyncClient as BinanceAsyncClient
from config.settings import API_KEYS
from services.binance_client import get_order_book
from core.indicators import detect_orderbook_whale_walls

async def test_live_orderbook_walls():
    key = API_KEYS.get('mainnet', {}).get('key', '')
    secret = API_KEYS.get('mainnet', {}).get('secret', '')
    client = await BinanceAsyncClient.create(key, secret)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT']
    print("==================================================")
    print("TESTE EM TEMPO REAL: LIVRO 50 DEPTH & MUROS DE BALEIAS")
    print("==================================================")
    try:
        for sym in symbols:
            ob = await get_order_book(client, sym, depth=50)
            ticker = await client.get_symbol_ticker(symbol=sym)
            cur_price = float(ticker['price'])
            raw_tp = cur_price * 1.04
            raw_sl = cur_price * 0.98
            
            adj_tp, adj_sl, wall_detected, wall_info = detect_orderbook_whale_walls(
                ob, cur_price, raw_tp, raw_sl
            )
            
            print(f"\nPar: {sym} | Preco Atual: ${cur_price:.4f}")
            print(f"  - TP Padrao (+4%): ${raw_tp:.4f}")
            if wall_detected and wall_info:
                print(f"  - [DETECCAO DE BALEIA]: Muro de Venda em ${wall_info['wall_price']:.4f} (${wall_info['wall_usdt']:,.0f} USDT)")
                print(f"  - TP Ajustado (Protecao): ${adj_tp:.4f} (Antecipado para evitar a baleia)")
            else:
                print("  - Nenhum muro de venda massivo detectado abaixo do TP. TP mantido normalmente.")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_live_orderbook_walls())
