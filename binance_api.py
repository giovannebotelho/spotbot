from config import interval, depth, limit

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

async def get_order_book(client, symbol, depth=depth): # 🟣🟣
    """
    Recupera o livro de ofertas (order book) para um símbolo específico com a profundidade definida.
    Args:
        client (BinanceAsyncClient): O cliente conectado à API da Binance.
        symbol (str): O símbolo de trading (ex.: 'BTCUSDT').
        depth (int): A profundidade do livro de ofertas a ser recuperada.
    Returns:
        dict: O livro de ofertas contendo 'asks' e 'bids'.
    """
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

async def get_closes(client, symbol, interval=interval, limit=limit): # 🟣🟣
    """
    Obtém os preços de fechamento de velas para um símbolo específico.
    Args:
        client (BinanceAsyncClient): O cliente conectado à API da Binance.
        symbol (str): O símbolo de trading.
        interval (str): O intervalo das velas (ex.: '15m').
        limit (int): O número de velas a ser recuperado.
    Returns:
        list: Uma lista dos preços de fechamento das velas.
    """
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    closes = [float(kline[4]) for kline in klines]
    return closes

async def get_volumes(client, symbol, interval=interval, limit=limit): # 🟣🟣
    """
    Obtém os volumes de trading de velas para um símbolo específico.
    Args:
        client (BinanceAsyncClient): O cliente conectado à API da Binance.
        symbol (str): O símbolo de trading.
        interval (str): O intervalo das velas.
        limit (int): O número de velas a ser recuperado.
    Returns:
        list: Uma lista dos volumes de cada vela.
    """
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    volumes = [float(kline[5]) for kline in klines]  # Volume está na 6ª posição
    return volumes

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
