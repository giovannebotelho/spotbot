import pytest
import pandas as pd
from core.indicators import calculate_rsi, calculate_bollinger_bands, calculate_ema

def test_calculate_rsi():
    # Cria uma série de preços com tendência clara de alta
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0]
    rsi = calculate_rsi(closes, period=14)
    # Com apenas altas, o RSI deve estar muito alto (próximo de 100)
    assert rsi is not None
    assert rsi > 70.0

def test_calculate_bollinger_bands():
    # Preços estáticos
    closes = [100.0] * 20
    lower, middle, upper = calculate_bollinger_bands(closes, period=20, std_dev=2.0)
    assert middle == 100.0
    # Desvio padrão de constantes é 0
    assert upper == 100.0
    assert lower == 100.0

    # Preços variando
    closes_var = [100.0, 105.0, 95.0, 110.0, 90.0] * 4 # 20 periodos
    l, m, u = calculate_bollinger_bands(closes_var, period=20, std_dev=2.0)
    assert m == 100.0
    assert u > m
    assert l < m

def test_calculate_ema():
    closes = [100.0, 100.0, 100.0, 100.0, 100.0]
    ema = calculate_ema(closes, period=5)
    assert ema == 100.0
