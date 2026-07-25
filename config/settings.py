import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env da raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# API Keys Binance & Gemini
API_KEYS = {
    "testnet_spot": {
        "key": os.getenv("testnetspot_api_key", ""),
        "secret": os.getenv("testnetspot_secret_key", "")
    },
    "testnet_futures": {
        "key": os.getenv("testnetfut_api_key", ""),
        "secret": os.getenv("testnetfut_secret_key", "")
    },
    "mainnet": {
        "key": os.getenv("mainnet_api_key", ""),
        "secret": os.getenv("mainnet_secret_key", "")
    },
    "gemini": os.getenv("gemini_api", "")
}

# Configurações do Telegram
TELEGRAM_CONFIG = {
    "bot_token": os.getenv("bot_token", ""),
    "chat_id": os.getenv("chat_id", "")
}

# Configurações do Dashboard Web (NiceGUI)
DASHBOARD_CONFIG = {
    "user": os.getenv("DASHBOARD_USER", "admin"),
    "password": os.getenv("DASHBOARD_PASSWORD", "admin123"),
    "secret_key": os.getenv("DASHBOARD_SECRET_KEY", "spotbot_secured_key_8823"),
    "port": int(os.getenv("PORT", os.getenv("DASHBOARD_PORT", "8080")))
}

# Configurações Globais de Trading
TRADING_CONFIG = {
    "symbol": 'BTCUSDT',
    "interval": '1h',
    "period": 20,
    "num_std": 2,
    "short_period": 12,
    "long_period": 26,
    "limit": 300,
    "depth": 20,
    "maxlen": 20,
    "volume_avg": 50,
    "sell_pressure_threshold": 0.65,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "use_ema_filter": False
}

# Configurações Dinâmicas de RSI
RSI_CONFIG = {
    "levels": {
        0: 20,
        1: 25,
        2: 30,
        3: 35,
        4: 40,
        5: 50
    },
    "high": 70,
    "dynamic_low": {
        0: 20,
        1: 25,
        2: 30,
        3: 35,
        4: 40,
        5: 50
    },
    "min": {
        0: 15,
        1: 20,
        2: 25,
        3: 30,
        4: 35,
        5: 45
    }
}

# Configurações de Ordem OCO (Fixed Percent Multipliers)
OCO_CONFIG = {
    "price_under_1": {
        "profit_multiplier": 1.008,
        "stop_loss_multiplier": 0.99
    },
    "price_over_1": {
        "profit_multiplier": 1.005,
        "stop_loss_multiplier": 0.990
    }
}

# Configurações de Stop baseado em ATR (Average True Range)
ATR_CONFIG = {
    "period": 14,
    "sl_multiplier": 1.5,
    "tp_multiplier": 2.0,
    "use_atr_stop": True
}

# Configurações de Trailing Stop
TRAILING_STOP_CONFIG = {
    "enabled": True,
    "activation_percent": 0.015, # 1.5% lucro para ativar
    "callback_percent": 0.005    # 0.5% recuo do topo dispara o stop
}

# Configurações do Banco de Dados (SQLite Local vs PostgreSQL Nuvem/Railway)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'spotbot.db'}")
