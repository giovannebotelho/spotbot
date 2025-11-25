import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
API_KEYS = {
    "testnet_spot": {
        "key": os.getenv("testnetspot_api_key"),
        "secret": os.getenv("testnetspot_secret_key")
    },
    "testnet_futures": {
        "key": os.getenv("testnetfut_api_key"),
        "secret": os.getenv("testnetfut_secret_key")
    },
    "mainnet": {
        "key": os.getenv("mainnet_api_key"),
        "secret": os.getenv("mainnet_secret_key")
    },
    "gemini": os.getenv("gemini_api")
}

# Telegram Config
TELEGRAM_CONFIG = {
    "bot_token": os.getenv("bot_token"),
    "chat_id": os.getenv("chat_id")
}

# General Trading Configuration
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
    "macd_signal": 9
}

# RSI Configuration
RSI_CONFIG = {
    "levels": {
        0: 20,
        1: 25,
        2: 30,
        3: 35,
        4: 40,
        5: 45
    },
    "high": 70,
    "dynamic_low": {
        0: 20,
        1: 25,
        2: 30,
        3: 35,
        4: 40,
        5: 45
    },
    "min": {
        0: 14, # 20 - 6
        1: 19, # 25 - 6
        2: 24, # 30 - 6
        3: 29, # 35 - 6
        4: 34, # 40 - 6
        5: 39  # 45 - 6
    }
}

# OCO Order Configuration
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

# ATR Configuration
ATR_CONFIG = {
    "period": 14,
    "sl_multiplier": 2.0,
    "tp_multiplier": 3.0,
    "use_atr_stop": True
}

# Trailing Stop Configuration
TRAILING_STOP_CONFIG = {
    "enabled": True,
    "activation_percent": 0.015, # 1.5% profit to activate
    "callback_percent": 0.005    # 0.5% drop from peak triggers stop
}

# Backward compatibility (to be removed after refactoring other files)
# ... (I will NOT add backward compatibility variables here to force myself to update other files)

