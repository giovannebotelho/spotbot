def is_hammer(candle):
    open_price, high_price, low_price, close_price = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    candle_body = abs(close_price - open_price)
    candle_high_low = high_price - low_price
    return candle_body <= candle_high_low * 0.3 and min(open_price, close_price) - low_price >= candle_body * 2 and high_price - max(open_price, close_price) <= candle_body * 0.1

def is_shooting_star(candle):
    open_price, high_price, low_price, close_price = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    candle_body = abs(close_price - open_price)
    candle_high_low = high_price - low_price
    return candle_body <= candle_high_low * 0.3 and high_price - max(open_price, close_price) >= candle_body * 2 and min(open_price, close_price) - low_price <= candle_body * 0.1

def is_bullish_engulfing(candle1, candle2):
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    return (close1 < open1) and (close2 > open2) and (close2 > open1) and (open2 < close1)

def is_piercing_line(candle1, candle2):
    open1, low1, close1 = float(candle1[1]), float(candle1[3]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    return (close1 < open1) and (close2 > open1) and (close2 > ((open1 + close1)/2) ) and (open2 < low1)

def is_dark_cloud_cover(candle1, candle2):
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    return (close1 > open1) and (close2 < open2) and (open2 > close1) and (close2 < ((close1+open1) / 2 ))

def is_kicker_bullish(candle1, candle2):
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    return (close1 < open1) and (close2 > open2) and (open2 > close1)

def is_kicker_bearish(candle1, candle2):
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    return (close1 > open1) and (close2 < open2) and (open2 < close1)

def is_long_day(candle):
    open_price, high_price, low_price, close_price = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    candle_body = abs(close_price - open_price)
    candle_high_low = high_price - low_price
    return candle_body >= candle_high_low * 0.7

def is_short_day(candle):
    open_price, high_price, low_price, close_price = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    candle_body = abs(close_price - open_price)
    candle_high_low = high_price - low_price
    return candle_body <= candle_high_low * 0.3

def is_doji(candle):
    open_price, close_price = float(candle[1]), float(candle[4])
    return abs(close_price - open_price) <= 0.001

def is_doji_dragonfly(candle):
    open_price, high_price, close_price = float(candle[1]), float(candle[2]), float(candle[4])
    return abs(close_price - open_price) <= 0.001 and abs(open_price - high_price) <= 0.001

def is_doji_gravestone(candle):
    open_price, low_price, close_price = float(candle[1]), float(candle[3]), float(candle[4])
    return abs(close_price - open_price) <= 0.001 and abs(open_price - low_price) <= 0.001

def is_doji_long_shadows(candle):
    open_price, high_price, low_price, close_price = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    candle_body = abs(close_price - open_price)
    candle_high_low = high_price - low_price
    return candle_body <= candle_high_low * 0.2 and candle_high_low >= candle_body * 5

def is_rising_three_methods(candle1, candle2, candle3, candle4, candle5):
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    open3, close3 = float(candle3[1]), float(candle3[4])
    open4, close4 = float(candle4[1]), float(candle4[4])
    close5 = float(candle5[4])
    if close1 <= open1: return False
    return (close1 > open1) and (open2>close1 and close2<open1) and (open3>close1 and close3<open1) and (open4>close1 and close4<open1) and (close5>close1 and close5 > open1)

def is_falling_three_methods(candle1, candle2, candle3, candle4, candle5):
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    open3, close3 = float(candle3[1]), float(candle3[4])
    open4, close4 = float(candle4[1]), float(candle4[4])
    close5 = float(candle5[4])
    if close1 >= open1: return False
    return (close1 < open1) and (open2<close1 and close2>open1) and (open3<close1 and close3>open1) and (open4<close1 and close4>open1) and (close5 < close1 and close5 < open1)

def is_bullish_and_bearish_strike(candle1, candle2):
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    return (close2 > open2 and open1>close1 and open2>open1) or (close2 < open2 and open1<close1 and open2<open1)

def is_stick_sandwich(candle1, candle2, candle3):
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    open3, close3 = float(candle3[1]), float(candle3[4])
    return (close1 < open1) and (close2 > open2) and (close3 < open3) and abs(close1-close3) <= 0.001 and close2 > close1 and close2 > close3
