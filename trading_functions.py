import numpy as np
import pandas as pd
import asyncio
from collections import deque
from binance.exceptions import BinanceAPIException

from binance_api import get_order_book, extract_closes
from patterns import (is_hammer, is_shooting_star, is_bullish_engulfing, is_piercing_line, is_dark_cloud_cover, is_kicker_bullish, is_kicker_bearish, is_long_day, is_short_day, is_doji, is_doji_dragonfly, 
                      is_doji_gravestone, is_doji_long_shadows, is_bullish_and_bearish_strike, is_rising_three_methods, is_falling_three_methods, is_stick_sandwich)
from config import TRADING_CONFIG

# Cria um deque para armazenar o histórico de pressão de venda
sell_pressure_history = deque(maxlen=TRADING_CONFIG['maxlen'])

def calculate_sell_pressure(order_book):
    """
    Calcula a pressão de venda com base na proporção das ordens de venda (asks) sobre o total de ordens no livro de ofertas.
    """
    total_asks = sum(float(ask[1]) for ask in order_book['asks'])
    total_bids = sum(float(bid[1]) for bid in order_book['bids'])
    total = total_asks + total_bids
    return total_asks / total if total > 0 else 0

async def calculate_moving_average_sell_pressure(client, symbol, interval=None, limit=None, depth=None):
    """
    Calcula a média móvel da pressão de venda para um símbolo específico.
    """
    if depth is None:
        depth = TRADING_CONFIG['depth']
        
    order_book = await get_order_book(client, symbol, depth=depth)
    sell_pressure = calculate_sell_pressure(order_book)
    sell_pressure_history.append(sell_pressure)
    return sum(sell_pressure_history) / len(sell_pressure_history)

def calculate_rsi(closes, period=None):
    """
    Calcula o Índice de Força Relativa (RSI).
    """
    if period is None:
        period = TRADING_CONFIG['period']

    deltas = np.diff(closes)
    gain = np.where(deltas > 0, deltas, 0)
    loss = np.where(deltas < 0, -deltas, 0)

    # Wilder's Smoothing
    avg_gain = pd.Series(gain).ewm(alpha=1/period, min_periods=period, adjust=False).mean().iloc[-1]
    avg_loss = pd.Series(loss).ewm(alpha=1/period, min_periods=period, adjust=False).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(closes, slow=None, fast=None, signal=None):
    """
    Calcula MACD.
    """
    if slow is None: slow = TRADING_CONFIG['macd_slow']
    if fast is None: fast = TRADING_CONFIG['macd_fast']
    if signal is None: signal = TRADING_CONFIG['macd_signal']

    closes_series = pd.Series(closes)
    ema_fast = closes_series.ewm(span=fast, adjust=False).mean()
    ema_slow = closes_series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]

def calculate_bollinger_bands(closes, period=None, num_std=None):
    """
    Calcula Bandas de Bollinger.
    """
    if period is None: period = TRADING_CONFIG['period']
    if num_std is None: num_std = TRADING_CONFIG['num_std']

    closes_series = pd.Series(closes)
    ma = closes_series.rolling(window=period).mean()
    std = closes_series.rolling(window=period).std()
    
    upper_band = ma + (std * num_std)
    lower_band = ma - (std * num_std)
    
    return lower_band.iloc[-1], ma.iloc[-1], upper_band.iloc[-1]

def calculate_volume_moving_average(volumes, period=None):
    """
    Calcula média móvel de volume.
    """
    if period is None: period = TRADING_CONFIG['period']
    return sum(volumes[-period:]) / period

def calculate_moving_average(closes, period):
    """
    Calcula média móvel simples.
    """
    return sum(closes[-period:]) / period

def calculate_ema(closes, period):
    """
    Calcula média móvel exponencial.
    """
    return pd.Series(closes).ewm(span=period, adjust=False).mean().iloc[-1]

def check_trend(klines, short_period=None, long_period=None):
    """
    Determina a tendência do mercado.
    """
    if short_period is None: short_period = TRADING_CONFIG['short_period']
    if long_period is None: long_period = TRADING_CONFIG['long_period']

    closes = extract_closes(klines)
    short_ma = calculate_moving_average(closes, short_period)
    long_ma = calculate_moving_average(closes, long_period)
    return short_ma > long_ma

def check_candle_patterns(klines):
    """
    Verifica padrões de candles.
    """
    if not klines or len(klines) < 5:
        return None

    last_candle = klines[-1]
    second_last_candle = klines[-2]
    third_last_candle = klines[-3]
    fourth_last_candle = klines[-4]
    fifth_last_candle = klines[-5]

    patterns = []

    if is_hammer(last_candle): patterns.append("hammer")
    if is_shooting_star(last_candle): patterns.append("shooting_star")
    if is_bullish_engulfing(second_last_candle, last_candle): patterns.append("bullish_engulfing")
    if is_piercing_line(second_last_candle, last_candle): patterns.append("piercing_line")
    if is_dark_cloud_cover(second_last_candle, last_candle): patterns.append("dark_cloud_cover")
    if is_kicker_bullish(second_last_candle, last_candle): patterns.append("kicker_bullish")
    if is_kicker_bearish(second_last_candle, last_candle): patterns.append("kicker_bearish")
    if is_long_day(last_candle): patterns.append("long_day")
    if is_short_day(last_candle): patterns.append("short_day")
    if is_doji(last_candle): patterns.append("doji")
    if is_doji_dragonfly(last_candle): patterns.append("doji_dragonfly")
    if is_doji_gravestone(last_candle): patterns.append("doji_gravestone")
    if is_doji_long_shadows(last_candle): patterns.append("doji_long_shadows")
    if is_rising_three_methods(fifth_last_candle, fourth_last_candle, third_last_candle, second_last_candle, last_candle): patterns.append("rising_three_methods")
    if is_falling_three_methods(fifth_last_candle, fourth_last_candle, third_last_candle, second_last_candle, last_candle): patterns.append("falling_three_methods")
    if is_bullish_and_bearish_strike(second_last_candle, last_candle): patterns.append("bullish_or_bearish_strike")
    if is_stick_sandwich(third_last_candle,second_last_candle, last_candle): patterns.append("stick_sandwich")

    return patterns if patterns else None

def get_candle_details(klines):
    """
    Obtém detalhes da vela.
    """
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

def is_market_downward(klines, limit=4, high_amplitude_threshold=0.25):
    """
    Verifica se o mercado está em tendência de baixa.
    """
    if not klines or len(klines) < limit:
        return False

    recent_klines = klines[-limit:]
    red_high_amplitude_candles = 0
    for kline in recent_klines:
        open_price, high_price, low_price, close_price = float(kline[1]), float(kline[2]), float(kline[3]), float(kline[4])
        amplitude = (high_price - low_price) / open_price * 100

        if close_price < open_price and amplitude >= high_amplitude_threshold:
            red_high_amplitude_candles += 1
    
    if red_high_amplitude_candles >= 2:
        return True
    else:
        return False

def calculate_atr(klines, period=None):
    """
    Calcula o Average True Range (ATR).
    """
    from config import ATR_CONFIG
    if period is None: period = ATR_CONFIG['period']
    
    if not klines or len(klines) < period + 1:
        return 0.0

    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    closes = np.array([float(k[4]) for k in klines])
    
    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])
    
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    tr_series = pd.Series(tr)
    atr = tr_series.ewm(alpha=1/period, min_periods=period, adjust=False).mean().iloc[-1]
    
    return atr

def calculate_vwap(closes, volumes):
    """
    Calcula o Volume Weighted Average Price (VWAP).
    """
    if not closes or not volumes or len(closes) != len(volumes):
      return np.nan
    
    closes_series = pd.Series(closes)
    volumes_series = pd.Series(volumes)
    
    typical_price = (closes_series + closes_series.shift(1) + closes_series.shift(2)) / 3
    
    cumulative_tp_volume = (typical_price * volumes_series).cumsum()
    cumulative_volume = volumes_series.cumsum()
    
    vwap = cumulative_tp_volume / cumulative_volume
    return vwap.iloc[-1]

async def calculate_fee(client, symbol, executed_qty, price):
    """
    Calcula a taxa da corretora.
    """
    try:
        bnb_balance = await client.get_asset_balance(asset='BNB')
        bnb_balance = float(bnb_balance['free'])

        if bnb_balance > 0:
            fee_rate = 0.00075 * 2
        else:
            fee_rate = 0.001 * 2
        
        return executed_qty * price * fee_rate
    
    except BinanceAPIException as e:
        print(f"Erro ao obter informações da conta: {e}")
        return 0.0
    except Exception as e:
        print(f"Erro inesperado ao obter informações da conta: {e}")
        return 0.0

def calculate_trade_result(entry_price, quantity, exit_price):
    """
    Calcula o resultado financeiro de uma operação.
    Args:
        entry_price (float): Preço de entrada.
        quantity (float): Quantidade negociada.
        exit_price (float): Preço de saída.
    Returns:
        float: Resultado financeiro (Lucro ou Prejuízo).
    """
    return (exit_price - entry_price) * quantity
