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

sell_pressure_history = deque(maxlen=TRADING_CONFIG.get('maxlen', 10))

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
        depth = TRADING_CONFIG.get('depth', 20)
        
    order_book = await get_order_book(client, symbol, depth=depth)
    sell_pressure = calculate_sell_pressure(order_book)
    sell_pressure_history.append(sell_pressure)
    return sum(sell_pressure_history) / len(sell_pressure_history)

def calculate_rsi(closes, period=None):
    if period is None:
        period = TRADING_CONFIG.get('period', 14)

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
    if slow is None: slow = TRADING_CONFIG.get('macd_slow', 26)
    if fast is None: fast = TRADING_CONFIG.get('macd_fast', 12)
    if signal is None: signal = TRADING_CONFIG.get('macd_signal', 9)

    closes_series = pd.Series(closes)
    ema_fast = closes_series.ewm(span=fast, adjust=False).mean()
    ema_slow = closes_series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]

def calculate_bollinger_bands(closes, period=None, num_std=None):
    if period is None: period = TRADING_CONFIG.get('period', 14)
    if num_std is None: num_std = TRADING_CONFIG.get('num_std', 2.0)

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
    if period is None: period = ATR_CONFIG.get('period', 14)
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

def calculate_hurst_exponent(closes, max_lag=20):
    """
    Calcula o Expoente de Hurst para determinar a dinâmica do mercado:
      - H < 0.45: Reversão à Média (Range Bound / Consolidação)
      - 0.45 <= H <= 0.55: Movimento Aleatório (Random Walk)
      - H > 0.55: Tendência Persistente (Trending)
    """
    if len(closes) < 50:
        return 0.50
    
    closes_arr = np.array(closes)
    lags = range(2, min(max_lag, len(closes_arr) // 4))
    tau = [np.sqrt(np.std(np.subtract(closes_arr[lag:], closes_arr[:-lag]))) for lag in lags]
    
    if len(tau) < 2 or np.all(tau[0] == tau):
        return 0.50

    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    hurst = poly[0] * 2.0
    return float(np.clip(hurst, 0.0, 1.0))

def detect_market_regime(klines):
    """
    Classifica o Regime de Mercado Atual:
      - REGIME_CRASH_PANIC: Se houver queda brusca (> 3.5% em 24h)
      - REGIME_BULL_TREND: Se Hurst > 0.55 e Preço > EMA50 > EMA200
      - REGIME_RANGE_BOUND: Se Hurst < 0.48 (Reversão à média ativada)
      - REGIME_NEUTRAL: Mercado equilibrado
    """
    closes = extract_closes(klines)
    if len(closes) < 50:
        return "REGIME_RANGE_BOUND", 0.45

    first_price = closes[-24] if len(closes) >= 24 else closes[0]
    price_change_24h = ((closes[-1] - first_price) / first_price) * 100
    
    if price_change_24h < -3.5:
        return "REGIME_CRASH_PANIC", 0.30

    hurst = calculate_hurst_exponent(closes)
    ema50 = calculate_ema(closes, 50)
    ema200 = calculate_ema(closes, 200)

    if hurst > 0.55 and closes[-1] > ema50 and ema50 > ema200:
        return "REGIME_BULL_TREND", hurst
    elif hurst < 0.48:
        return "REGIME_RANGE_BOUND", hurst
    else:
        return "REGIME_NEUTRAL", hurst

def detect_liquidity_sweep(klines):
    """
    Fase 2: Detecta Varredura de Liquidez Institucional (Smart Money Concepts - SMC):
    Identifica quando a vela espeta abaixo da mínima das últimas 24 horas (capturando stop losses)
    e fecha acima do suporte com rejeição em vela (hammer/pinbar) e pico de volume.
    """
    if not klines or len(klines) < 25:
        return False, ""

    lows_24h = [float(k[3]) for k in klines[-25:-1]]
    low_24h = min(lows_24h)

    last_candle = klines[-1]
    open_p = float(last_candle[1])
    high_p = float(last_candle[2])
    low_p = float(last_candle[3])
    close_p = float(last_candle[4])
    vol = float(last_candle[5])

    volumes = [float(k[5]) for k in klines[-20:]]
    avg_vol = np.mean(volumes)

    swept_below = low_p < low_24h
    closed_above = close_p > low_24h or close_p > open_p

    body = abs(close_p - open_p)
    lower_wick = min(open_p, close_p) - low_p
    strong_rejection = lower_wick > (body * 1.2)

    volume_surge = vol >= (avg_vol * 1.3)

    if swept_below and closed_above and (strong_rejection or volume_surge):
        return True, "Varredura de Liquidez SMC (Rejeição de Mínima 24h + Volume)"

    return False, ""

def calculate_relative_strength_rank(multi_klines):
    """
    Fase 3: Ranker de Força Relativa e Momentum (Relative Strength vs BTC).
    Calcula a Força Relativa de cada altcoin contra o BTCUSDT e combina com RSI e ADX.
    Retorna uma lista ordenada com os melhores criptoativos para operar no momento.
    """
    if not multi_klines:
        return []

    btc_klines = multi_klines.get('BTCUSDT', [])
    btc_return_24h = 0.0
    if btc_klines and len(btc_klines) >= 25:
        b_closes = extract_closes(btc_klines)
        b_start = b_closes[-25]
        b_end = b_closes[-1]
        btc_return_24h = ((b_end - b_start) / b_start) * 100 if b_start > 0 else 0.0

    ranked_assets = []
    for symbol, klines in multi_klines.items():
        if not klines or len(klines) < 25:
            continue

        closes = extract_closes(klines)
        start_p = closes[-25]
        end_p = closes[-1]
        asset_return_24h = ((end_p - start_p) / start_p) * 100 if start_p > 0 else 0.0

        rs_ratio = asset_return_24h - btc_return_24h
        rsi_val = calculate_rsi(closes)
        adx_val = calculate_adx(klines)

        combined_score = (rs_ratio * 0.4) + ((100 - rsi_val) * 0.4) + (adx_val * 0.2)

        ranked_assets.append({
            'symbol': symbol,
            'price': end_p,
            'return_24h': asset_return_24h,
            'rs_ratio': rs_ratio,
            'rsi': rsi_val,
            'adx': adx_val,
            'score': combined_score
        })

    ranked_assets.sort(key=lambda x: x['score'], reverse=True)
    return ranked_assets

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
    if not klines or len(klines) < 5:
        return []

    c1 = klines[-1]
    c2 = klines[-2]
    c3 = klines[-3]
    c4 = klines[-4]
    c5 = klines[-5]

    patterns = []
    if is_hammer(c1): patterns.append("Hammer")
    if is_shooting_star(c1): patterns.append("Shooting Star")
    if is_bullish_engulfing(c2, c1): patterns.append("Bullish Engulfing")
    if is_piercing_line(c2, c1): patterns.append("Piercing Line")
    if is_dark_cloud_cover(c2, c1): patterns.append("Dark Cloud Cover")
    if is_kicker_bullish(c2, c1): patterns.append("Bullish Kicker")
    if is_kicker_bearish(c2, c1): patterns.append("Bearish Kicker")
    if is_long_day(c1): patterns.append("Long Day")
    if is_short_day(c1): patterns.append("Short Day")
    if is_doji(c1): patterns.append("Doji")
    if is_doji_dragonfly(c1): patterns.append("Dragonfly Doji")
    if is_doji_gravestone(c1): patterns.append("Gravestone Doji")
    if is_doji_long_shadows(c1): patterns.append("Long Legged Doji")
    if is_bullish_and_bearish_strike(c2, c1): patterns.append("Three Line Strike")
    if is_rising_three_methods(c5, c4, c3, c2, c1): patterns.append("Rising Three Methods")
    if is_falling_three_methods(c5, c4, c3, c2, c1): patterns.append("Falling Three Methods")
    if is_stick_sandwich(c3, c2, c1): patterns.append("Stick Sandwich")

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
