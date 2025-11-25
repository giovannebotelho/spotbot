from config import TRADING_CONFIG

async def get_usdt_balance(client):
    """
    Obtém o saldo disponível de USDT na conta do cliente.
    Args:
        client (BinanceAsyncClient): O cliente conectado à API da Binance.
    Returns:
        float: O saldo de USDT disponível.
    """
    balance = await client.get_asset_balance(asset='USDT')
    return float(balance['free'])

async def get_order_book(client, symbol, depth=None):
    """
    Recupera o livro de ofertas (order book) para um símbolo específico com a profundidade definida.
    Args:
        client (BinanceAsyncClient): O cliente conectado à API da Binance.
        symbol (str): O símbolo de trading (ex.: 'BTCUSDT').
        depth (int): A profundidade do livro de ofertas a ser recuperada.
    Returns:
        dict: O livro de ofertas contendo 'asks' e 'bids'.
    """
    if depth is None:
        depth = TRADING_CONFIG['depth']
    order_book = await client.get_order_book(symbol=symbol, limit=depth)
    return order_book

async def get_order_details(client, symbol, order_id):
    """
    Obtém detalhes de uma ordem específica por ID.
    Args:
        client (BinanceAsyncClient): O cliente conectado à API da Binance.
        symbol (str): O símbolo de trading.
        order_id (str): O ID da ordem.
    Returns:
        dict: Detalhes da ordem.
    """
    order_details = await client.get_order(symbol=symbol, orderId=order_id)
    return order_details

def extract_closes(klines):
    """
    Extrai os preços de fechamento de uma lista de velas.
    Args:
        klines (list): Lista de velas (klines).
    Returns:
        list: Uma lista dos preços de fechamento das velas.
    """
    return [float(kline[4]) for kline in klines]

def extract_volumes(klines):
    """
    Extrai os volumes de uma lista de velas.
    Args:
        klines (list): Lista de velas (klines).
    Returns:
        list: Uma lista dos volumes de cada vela.
    """
    return [float(kline[5]) for kline in klines]

async def get_klines(client, symbol, interval, limit):
    """
    Obtém as informações completas de velas para um símbolo específico.
    Args:
        client (BinanceAsyncClient): O cliente conectado à API da Binance.
        symbol (str): O símbolo de trading.
        interval (str): O intervalo das velas.
         limit (int): O número de velas a ser recuperado.
    Returns:
       list: Os detalhes de vela do ativo (lista de velas, cada vela tem open, close, high, low, volume)
    """
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    return klines

async def get_bnb_price(client):
    """
    Obtém o preço atual de BNB em USDT.
    """
    ticker = await client.get_symbol_ticker(symbol="BNBUSDT")
    return float(ticker['price'])
