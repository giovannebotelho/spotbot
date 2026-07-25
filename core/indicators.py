import numpy as np
import pandas as pd
from collections import deque
from binance.exceptions import BinanceAPIException
from services.binance_client import get_order_book, extract_closes
from core.patterns import (
    is_hammer, is_shooting_star, is_bullish_engulfing, is_piercing_line, is_dark_cloud_cover,
    is_kicker_bullish, is_kicker_bearish, is_long_day, is_short_day, is_doji, is_doji_dragonfly,
    is_doji_gravestone, is_doji_long_shadows, is_bullish_and_bearish_strike, is_rising_three_methods,
    is_falling_three_methods, is_stick_sandwich
)
from config.settings import TRADING_CONFIG, ATR_CONFIG

sell_pressure_history = deque(maxlen=TRADING_CONFIG['maxlen'])

def calculate_trade_result(buy_price, quantity, sell_price):
    return (sell_price - buy_price) * quantity

async def calculate_fee(client, symbol, quantity, sell_price, fee_rate=0.001):
    total_val = sell_price * quantity
    return total_val * fee_rate

def calculate_sell_pressure(order_book):
    total_asks = sum(float(ask[1]) for ask in order_book['asks'])
    total_bids = sum(float(bid[1]) for bid in order_book['bids'])
    total = total_asks + total_bids
    return total_asks / total if total > 0 else 0

async def calculate_moving_average_sell_pressure(client, symbol, interval=None, limit=None, depth=None):
    if depth is None:
        depth = TRADING_CONFIG['depth']
        
    order_book = await get_order_book(client, symbol, depth=depth)
    sell_pressure = calculate_sell_pressure(order_book)
    sell_pressure_history.append(sell_pressure)
    return sum(sell_pressure_history) / len(sell_pressure_history)

def calculate_rsi(closes, period=None):
    if period is None:
        period = TRADING_CONFIG['period']

    deltas = np.diff(closes)
    gain = np.where(deltas > 0, deltas, 0)
    loss = np.where(deltas < 0, -deltas, 0)

    avg_gain = pd.Series(gain).ewm(alpha=1/period, min_periods=period, adjust=False).mean().iloc[-1]
    avg_loss = pd.Series(loss).ewm(alpha=1/period, min_periods=period, adjust=False).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(closes, slow=None, fast=None, signal=None):
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
    if period is None: period = TRADING_CONFIG['period']
    if num_std is None: num_std = TRADING_CONFIG['num_std']

    closes_series = pd.Series(closes)
    rolling_mean = closes_series.rolling(window=period).mean()
    rolling_std = closes_series.rolling(window=period).std()

    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    return lower_band.iloc[-1], rolling_mean.iloc[-1], upper_band.iloc[-1]

def calculate_vwap(closes, volumes):
    cumulative_pv = np.cumsum(np.array(closes) * np.array(volumes))
    cumulative_v = np.cumsum(volumes)
    vwap = cumulative_pv / cumulative_v
    return vwap[-1]

def calculate_ema(closes, period):
    closes_series = pd.Series(closes)
    ema = closes_series.ewm(span=period, adjust=False).mean()
    return ema.iloc[-1]

def calculate_atr(klines, period=None):
    if period is None: period = ATR_CONFIG['period']
    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    closes = np.array([float(k[4]) for k in klines])

    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])

    tr = np.maximum(np.maximum(tr1, tr2), tr3)
    atr = pd.Series(tr).ewm(alpha=1/period, min_periods=period, adjust=False).mean().iloc[-1]
    return atr

def calculate_adx(klines, period=14):
    """Calcula o ADX (Average Directional Index) para medir força da tendência."""
    if len(klines) < period + 1:
        return 0.0

    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    closes = np.array([float(k[4]) for k in klines])

    up_move = highs[1:] - highs[:-1]
    down_move = lows[:-1] - lows[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])
    tr = np.maximum(np.maximum(tr1, tr2), tr3)

    tr_smoothed = pd.Series(tr).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    plus_dm_smoothed = pd.Series(plus_dm).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    minus_dm_smoothed = pd.Series(minus_dm).ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    plus_di = 100 * (plus_dm_smoothed / tr_smoothed)
    minus_di = 100 * (minus_dm_smoothed / tr_smoothed)

    sum_di = plus_di + minus_di
    dx = 100 * (np.abs(plus_di - minus_di) / np.where(sum_di == 0, 1, sum_di))

    adx = pd.Series(dx).ewm(alpha=1/period, min_periods=period, adjust=False).mean().iloc[-1]
    return float(adx)

def check_trend(klines):
    closes = extract_closes(klines)
    ema200 = calculate_ema(closes, 200)
    return closes[-1] > ema200

def is_market_downward(klines, period=24):
    closes = extract_closes(klines)
    if len(closes) < period: return False
    
    first_price = closes[-period]
    last_price = closes[-1]
    price_change = ((last_price - first_price) / first_price) * 100
    
    ema50 = calculate_ema(closes, 50)
    ema200 = calculate_ema(closes, 200)
    
    return price_change < -2.0 and closes[-1] < ema50 and ema50 < ema200

def check_candle_patterns(klines):
    opens = [float(k[1]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    closes = [float(k[4]) for k in klines]

    patterns = []
    if is_hammer(opens, highs, lows, closes): patterns.append("Hammer")
    if is_shooting_star(opens, highs, lows, closes): patterns.append("Shooting Star")
    if is_bullish_engulfing(opens, highs, lows, closes): patterns.append("Bullish Engulfing")
    if is_piercing_line(opens, highs, lows, closes): patterns.append("Piercing Line")
    if is_dark_cloud_cover(opens, highs, lows, closes): patterns.append("Dark Cloud Cover")
    if is_kicker_bullish(opens, highs, lows, closes): patterns.append("Bullish Kicker")
    if is_kicker_bearish(opens, highs, lows, closes): patterns.append("Bearish Kicker")
    if is_long_day(opens, highs, lows, closes): patterns.append("Long Day")
    if is_short_day(opens, highs, lows, closes): patterns.append("Short Day")
    if is_doji(opens, highs, lows, closes): patterns.append("Doji")
    if is_doji_dragonfly(opens, highs, lows, closes): patterns.append("Dragonfly Doji")
    if is_doji_gravestone(opens, highs, lows, closes): patterns.append("Gravestone Doji")
    if is_doji_long_shadows(opens, highs, lows, closes): patterns.append("Long Legged Doji")
    if is_bullish_and_bearish_strike(opens, highs, lows, closes): patterns.append("Three Line Strike")
    if is_rising_three_methods(opens, highs, lows, closes): patterns.append("Rising Three Methods")
    if is_falling_three_methods(opens, highs, lows, closes): patterns.append("Falling Three Methods")
    if is_stick_sandwich(opens, highs, lows, closes): patterns.append("Stick Sandwich")

    return patterns

def get_candle_details(klines):
    if not klines: return None
    last_candle = klines[-1]
    return {
        'open': float(last_candle[1]),
        'high': float(last_candle[2]),
        'low': float(last_candle[3]),
        'close': float(last_candle[4]),
        'volume': float(last_candle[5]),
    }
