"""
Ponto de exportação legado para configurações.
Delegando para config.settings.
"""
from config.settings import (
    API_KEYS, TELEGRAM_CONFIG, DASHBOARD_CONFIG, TRADING_CONFIG,
    RSI_CONFIG, OCO_CONFIG, ATR_CONFIG, TRAILING_STOP_CONFIG, DATABASE_URL
)
