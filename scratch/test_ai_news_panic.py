import asyncio
import sys
sys.path.insert(0, '.')
from services.news_scanner import fetch_crypto_news
from services.gemini_ai import analyze_news_sentiment_with_gemini

async def test_live_news_panic():
    symbols = ['BTC', 'ETH', 'SOL', 'AVAX']
    print("==================================================")
    print("TESTE EM TEMPO REAL: SCANNER DE NOTICIAS & SENTIMENTO IA")
    print("==================================================")
    for sym in symbols:
        headlines = await fetch_crypto_news(sym)
        score, is_panic, summary = analyze_news_sentiment_with_gemini(headlines)
        status_str = "PANICO EXTREMO" if is_panic else "ESTAVEL / NEUTRO"
        
        print(f"\nPar: {sym} | Status IA: {status_str} | Score Sentimento: {score}/100")
        print(f"  - Resumo IA: {summary}")
        print("  - Manchetes Recentes:")
        for h in headlines[:3]:
            print(f"    * {h}")

if __name__ == "__main__":
    asyncio.run(test_live_news_panic())
