import numpy as np
import pandas as pd
import asyncio
from collections import deque
from binance.exceptions import BinanceAPIException

from binance_api import get_order_book, get_closes
from patterns import (is_hammer, is_shooting_star, is_bullish_engulfing, is_piercing_line, is_dark_cloud_cover, is_kicker_bullish, is_kicker_bearish, is_long_day, is_short_day, is_doji, is_doji_dragonfly, 
                      is_doji_gravestone, is_doji_long_shadows, is_bullish_and_bearish_strike, is_rising_three_methods, is_falling_three_methods, is_stick_sandwich)
from config import maxlen, depth, period, interval, limit, short_period, long_period, num_std, macd_fast, macd_slow, macd_signal

def calculate_sell_pressure(order_book):
    """
    Calcula a pressão de venda com base na proporção das ordens de venda (asks) sobre o total de ordens no livro de ofertas.
    Args:
        order_book (dict): Livro de ofertas contendo 'asks' e 'bids'.
    Returns:
        float: Porcentagem representando a pressão de venda.
    """
    total_asks = sum(float(ask[1]) for ask in order_book['asks'])
    total_bids = sum(float(bid[1]) for bid in order_book['bids'])
    total = total_asks + total_bids
    return total_asks / total if total > 0 else 0

# Cria um deque para armazenar o histórico de pressão de venda, limitado ao tamanho máximo definido em 'maxlen'.
sell_pressure_history = deque(maxlen=maxlen)

async def calculate_moving_average_sell_pressure(client, symbol, interval=interval, limit=limit, depth=depth):
    """
    Calcula a média móvel da pressão de venda para um símbolo específico.
    Args:
        client: Cliente da API da Binance.
        symbol (str): Símbolo para o qual calcular a pressão de venda.
        depth (int): Profundidade do livro de ofertas a ser considerada.
    Returns:
        float: Média móvel da pressão de venda.
    """
    order_book = await get_order_book(client, symbol, depth=depth)
    sell_pressure = calculate_sell_pressure(order_book)
    sell_pressure_history.append(sell_pressure)
    return sum(sell_pressure_history) / len(sell_pressure_history)

def calculate_rsi(closes, period=period):
    """
    Calcula o Índice de Força Relativa (RSI) para uma lista de preços de fechamento.
    Args:
        closes (list): Lista de preços de fechamento.
        period (int): Número de períodos a considerar para o cálculo.
    Returns:
        float: Valor do RSI.
    """
    deltas = np.diff(closes)
    gain = np.where(deltas > 0, deltas, 0)
    loss = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.average(gain[-period:])
    avg_loss = np.average(loss[-period:])

    if avg_loss == 0:
        rs = float('inf')  # Definir RS como infinito se avg_loss é 0
    else:
        rs = avg_gain / avg_loss
    
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(closes, slow=macd_slow, fast=macd_fast, signal=macd_signal):
    """
    Calcula a Convergência/Divergência da Média Móvel (MACD) e a linha de sinal.
    Args:
        closes (list): Lista de preços de fechamento.
        slow (int): Períodos para a média móvel lenta.
        fast (int): Períodos para a média móvel rápida.
        signal (int): Períodos para a linha de sinal.
    Returns:
        tuple: Valor do MACD e da linha de sinal.
    """
    closes_series = pd.Series(closes)
    ema_fast = closes_series.ewm(span=fast, adjust=False).mean()
    ema_slow = closes_series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]

def calculate_bollinger_bands(closes, period=period, num_std=num_std):
    """
    Calcula as Bandas de Bollinger para uma lista de preços de fechamento.
    Args:
        closes (list): Lista de preços de fechamento.
        period (int): Número de períodos a considerar para as médias móveis.
        num_std (int): Número de desvios padrões para definir as bandas superior e inferior.
    Returns:
        tuple: Banda inferior, média e banda superior.
    """
    closes_series = pd.Series(closes)
    ma = closes_series.rolling(window=period).mean()
    std = closes_series.rolling(window=period).std()
    
    upper_band = ma + (std * num_std)
    lower_band = ma - (std * num_std)
    
    return lower_band.iloc[-1], ma.iloc[-1], upper_band.iloc[-1]

def calculate_volume_moving_average(volumes, period=period):
    """
    Calcula a média móvel do volume de negociação.
    Args:
        volumes (list): Lista de volumes de negociação.
        period (int): Número de períodos a considerar para a média móvel.
    Returns:
        float: Média móvel do volume.
    """
    return sum(volumes[-period:]) / period

def calculate_trade_result(purchase_price, executed_qty, sell_price):
    """
    Calcula o resultado financeiro de uma transação de compra e venda.
    Args:
        purchase_price (float): Preço de compra.
        executed_qty (float): Quantidade executada na compra.
        sell_price (float): Preço de venda.
    Returns:
        float: Resultado financeiro da transação.
    """
    total_purchase = purchase_price * executed_qty
    total_sell = sell_price * executed_qty
    result = total_sell - total_purchase
    return result

def calculate_moving_average(closes, period):
    """
    Calcula a média móvel dos preços de fechamento para um período especificado.
    Args:
        closes (list): Lista de preços de fechamento.
        period (int): Número de períodos a considerar para a média móvel.
    Returns:
        float: Média móvel dos preços de fechamento.
    """
    return sum(closes[-period:]) / period

async def check_trend(client, symbol, interval=interval, short_period=short_period, long_period=long_period):
    """
    Determina a tendência do mercado com base em médias móveis de curto e longo prazo.
    Args:
        client: Cliente da API da Binance.
        symbol (str): Símbolo a ser analisado.
        interval (str): Intervalo de tempo para cada candle.
        short_period (int): Período para a média móvel curta.
        long_period (int): Período para a média móvel longa.
    Returns:
        bool: True se a tendência for de alta, False caso contrário.
    """
    closes = await get_closes(client, symbol, interval, long_period)
    short_ma = calculate_moving_average(closes, short_period)
    long_ma = calculate_moving_average(closes, long_period)
    return short_ma > long_ma  # Retorna True se a tendência for de alta

async def check_candle_patterns(client, symbol, interval=interval, limit=limit):
    """
    Verifica padrões de candles para tomar decisões de compra ou venda.
    Args:
        client: Cliente da API da Binance.
        symbol (str): Símbolo a ser analisado.
    Returns:
        tuple: Decisão ('buy', 'sell', ou None) e mensagem descrevendo o padrão detectado.
    """
    # Obter os últimos candles necessários para análise de padrão
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    
    if not klines or len(klines) < 3: # verifica se existem dados suficientes
        return None # retorna nulo caso não exista dados para verificar

    last_candle = klines[-1]
    second_last_candle = klines[-2]
    third_last_candle = klines[-3]
    fourth_last_candle = klines[-4]
    fifth_last_candle = klines[-5]

    patterns = [] # cria uma lista com todos os padrões encontrados

    if is_hammer(last_candle):
        patterns.append("hammer")
    if is_shooting_star(last_candle):
        patterns.append("shooting_star")
    if is_bullish_engulfing(second_last_candle, last_candle):
        patterns.append("bullish_engulfing")
    if is_piercing_line(second_last_candle, last_candle):
        patterns.append("piercing_line")
    if is_dark_cloud_cover(second_last_candle, last_candle):
        patterns.append("dark_cloud_cover")
    if is_kicker_bullish(second_last_candle, last_candle):
        patterns.append("kicker_bullish")
    if is_kicker_bearish(second_last_candle, last_candle):
        patterns.append("kicker_bearish")
    if is_long_day(last_candle):
        patterns.append("long_day")
    if is_short_day(last_candle):
        patterns.append("short_day")
    if is_doji(last_candle):
        patterns.append("doji")
    if is_doji_dragonfly(last_candle):
        patterns.append("doji_dragonfly")
    if is_doji_gravestone(last_candle):
        patterns.append("doji_gravestone")
    if is_doji_long_shadows(last_candle):
        patterns.append("doji_long_shadows")
    if is_rising_three_methods(fifth_last_candle, fourth_last_candle, third_last_candle, second_last_candle, last_candle):
        patterns.append("rising_three_methods")
    if is_falling_three_methods(fifth_last_candle, fourth_last_candle, third_last_candle, second_last_candle, last_candle):
        patterns.append("falling_three_methods")
    if is_bullish_and_bearish_strike(second_last_candle, last_candle):
        patterns.append("bullish_or_bearish_strike")
    if is_stick_sandwich(third_last_candle,second_last_candle, last_candle):
        patterns.append("stick_sandwich")

    msg = f"🟢 Padrões de candle detectados: {patterns}" if patterns else "🟡 Sem padrões de candle significativos detectados."

    # Imprime a nova mensagem
    print(f"\r{msg}", end='', flush=True)
    # Espera um breve momento antes de limpar a linha novamente
    await asyncio.sleep(0.6)
    # Limpa a linha anterior
    print("\033[2K\r", end='')
    
    return patterns if patterns else None # retorna a lista dos padrões, se houver, ou nenhum, caso não encontre nada

def calculate_vwap(closes, volumes):
    """
    Calcula o Volume Weighted Average Price (VWAP).
    Args:
        closes (list): Lista de preços de fechamento.
        volumes (list): Lista de volumes correspondentes.
    Returns:
        float: Valor do VWAP.
    """
    if not closes or not volumes or len(closes) != len(volumes):
      return np.nan
    
    closes_series = pd.Series(closes)
    volumes_series = pd.Series(volumes)
    
    typical_price = (closes_series + closes_series.shift(1) + closes_series.shift(2)) / 3 # usa um preço típico
    
    cumulative_tp_volume = (typical_price * volumes_series).cumsum()
    cumulative_volume = volumes_series.cumsum()
    
    vwap = cumulative_tp_volume / cumulative_volume
    return vwap.iloc[-1]
    
def calculate_ema(closes, period):
    """Calcula a média móvel exponencial (EMA)."""
    closes_series = pd.Series(closes)
    ema = closes_series.ewm(span=period, adjust=False).mean()
    return ema.iloc[-1]

async def get_candle_details(client, symbol, interval, limit):
    """
    Obtém detalhes da vela para um símbolo específico.
    Args:
        client (BinanceAsyncClient): O cliente conectado à API da Binance.
        symbol (str): O símbolo de trading.
        interval (str): O intervalo das velas (ex.: '15m').
        limit (int): O número de velas a ser recuperado.
    Returns:
        dict: Os detalhes da vela contendo 'open', 'high', 'low', 'close', 'volume'.
    """
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    if klines:
        last_kline = klines[-1]
        return {
            "open": float(last_kline[1]),
            "high": float(last_kline[2]),
            "low": float(last_kline[3]),
            "close": float(last_kline[4]),
            "volume": float(last_kline[5])
        }
    return None

async def is_market_downward(client, symbol, interval, limit=4, high_amplitude_threshold=0.25):
    """
    Verifica se o mercado está em tendência de baixa com base nos últimos candles,
    considerando a amplitude dos candles vermelhos.

    Args:
        client: Cliente da API da Binance.
        symbol (str): Símbolo a ser analisado.
        interval (str): Intervalo de tempo para cada candle.
        limit (int): Número de candles a serem analisados (padrão: 4).
        high_amplitude_threshold (float): Limite de amplitude para considerar um candle
                                          como de alta amplitude (padrão: 0.4%).

    Returns:
        bool: True se o mercado estiver em tendência de baixa, False caso contrário.
    """
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    if not klines or len(klines) < limit:
        return False  # Não há dados suficientes para determinar a tendência

    red_high_amplitude_candles = 0
    for kline in klines:
        open_price, high_price, low_price, close_price = float(kline[1]), float(kline[2]), float(kline[3]), float(kline[4])
        amplitude = (high_price - low_price) / open_price * 100

        if close_price < open_price and amplitude >= high_amplitude_threshold:
            red_high_amplitude_candles += 1

    return red_high_amplitude_candles >= 2

async def calculate_fee(client, symbol, executed_qty, price):
    """
    Calcula a taxa da corretora para uma operação.
    
    Args:
        client: Cliente da API da Binance.
        symbol (str): Símbolo do par de moedas.
        executed_qty (float): Quantidade executada.
        price (float): Preço da ordem.

    Returns:
        float: Valor da taxa.
    """
    try:
        # Verifica se o usuário tem BNB suficiente para cobrir a taxa
        bnb_balance = await client.get_asset_balance(asset='BNB')
        bnb_balance = float(bnb_balance['free'])

        if bnb_balance > 0:
            fee_rate = 0.00075 * 2  # Taxa com desconto para BNB (considerando compra e venda)
        else:
            fee_rate = 0.001 * 2  # Taxa padrão (considerando compra e venda)
        
        # print(f"Dados para calcular a taxa: symbol={symbol}, executed_qty={executed_qty}, price={price}")

        return executed_qty * price * fee_rate
    
    except BinanceAPIException as e:
        print(f"Erro ao obter informações da conta: {e}")
        return 0.0
    except Exception as e:
        print(f"Erro inesperado ao obter informações da conta: {e}")
        return 0.0
