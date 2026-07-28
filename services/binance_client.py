import asyncio
import aiohttp
from config.settings import TRADING_CONFIG

async def get_usdt_balance(client):
    """Obtém o saldo disponível de USDT na conta do cliente."""
    balance = await client.get_asset_balance(asset='USDT')
    return float(balance['free'])

async def get_order_book(client, symbol, depth=None):
    """Recupera o livro de ofertas (order book) para um símbolo com a profundidade solicitada."""
    if depth is None:
        depth = TRADING_CONFIG['depth']
    order_book = await client.get_order_book(symbol=symbol, limit=depth)
    return order_book

async def get_order_details(client, symbol, order_id):
    """Obtém detalhes de uma ordem específica pelo ID."""
    order_details = await client.get_order(symbol=symbol, orderId=order_id)
    return order_details

def extract_closes(klines):
    """Extrai os preços de fechamento de uma lista de velas."""
    return [float(kline[4]) for kline in klines]

def extract_volumes(klines):
    """Extrai os volumes de uma lista de velas."""
    return [float(kline[5]) for kline in klines]

async def get_klines(client, symbol, interval, limit):
    """Obtém as velas (klines) para um símbolo específico."""
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    return klines

async def get_multi_klines(client, symbols, interval, limit):
    """Obtém klines em lote de forma assíncrona para múltiplos símbolos."""
    async def fetch(sym):
        try:
            res = await client.get_klines(symbol=sym, interval=interval, limit=limit)
            return sym, res
        except Exception:
            return sym, []

    tasks = [fetch(s) for s in symbols]
    results = await asyncio.gather(*tasks)
    return dict(results)

async def get_bnb_price(client):
    """Obtém o preço atual do BNB em USDT."""
    ticker = await client.get_symbol_ticker(symbol="BNBUSDT")
    return float(ticker['price'])

async def get_futures_analytics(symbol):
    """
    Obtém métricas de Derivativos (Futures Funding Rate & Open Interest) da Binance em tempo real.
    Permite detectar potenciais setups de Short Squeeze quando o Funding Rate está significativamente negativo.
    """
    url_funding = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
    url_oi = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
    
    funding_rate = 0.0
    open_interest = 0.0
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url_funding, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    funding_rate = float(data.get('lastFundingRate', 0.0))

            async with session.get(url_oi, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    open_interest = float(data.get('openInterest', 0.0))
    except Exception as e:
        pass

    return {
        'symbol': symbol,
        'funding_rate': funding_rate,
        'funding_rate_pct': funding_rate * 100.0,
        'open_interest': open_interest,
        'is_short_heavy': funding_rate < -0.0001 # Funding Rate < -0.01%
    }

async def get_multi_timeframe_klines(client, symbol):
    """
    Obtém em paralelo ultra-rápido as klines de 3 horizontes de tempo (4h, 1h, 15m)
    para o cálculo da Matriz de Confluência Multi-Timeframe (v4.0).
    """
    async def fetch(tf, limit):
        try:
            return await client.get_klines(symbol=symbol, interval=tf, limit=limit)
        except Exception:
            return []

    res_4h, res_1h, res_15m = await asyncio.gather(
        fetch('4h', 100),
        fetch('1h', 100),
        fetch('15m', 100)
    )
    return {
        '4h': res_4h,
        '1h': res_1h,
        '15m': res_15m
    }

async def get_lead_lag_btc_klines(client):
    """
    FASE 2 (v5.0): Obtém as últimas velas de 1m do BTCUSDT em tempo real
    para o cálculo do Motor de Antecipação (Lead-Lag Alpha Engine).
    """
    try:
        return await client.get_klines(symbol="BTCUSDT", interval="1m", limit=15)
    except Exception:
        return []
