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

async def get_bnb_price(client):
    """Obtém o preço atual do BNB em USDT."""
    ticker = await client.get_symbol_ticker(symbol="BNBUSDT")
    return float(ticker['price'])
