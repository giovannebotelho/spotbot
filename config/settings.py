import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

API_KEYS = {
    'mainnet': {
        'key': os.getenv('mainnet_api_key', ''),
        'secret': os.getenv('mainnet_secret_key', ''),
    },
    'testnet_spot': {
        'key': os.getenv('testnet_spot_api_key', ''),
        'secret': os.getenv('testnet_spot_secret_key', ''),
    }
}

TELEGRAM_CONFIG = {
    'bot_token': os.getenv('bot_token', ''),
    'chat_id': os.getenv('chat_id', '')
}

DASHBOARD_CONFIG = {
    'user': os.getenv('DASHBOARD_USER', 'admin'),
    'password': os.getenv('DASHBOARD_PASSWORD', 'admin123'),
    'port': int(os.getenv('PORT', '8080')),
    'secret_key': os.getenv('SECRET_KEY', 'spotbot_secret_key_change_me')
}

DB_CONFIG = {
    'url': os.getenv('DATABASE_URL', 'sqlite:///spotbot.db')
}
DATABASE_URL = DB_CONFIG['url']

TOP_20_SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'NEARUSDT',
    'DOTUSDT', 'MATICUSDT', 'SHIBUSDT', 'LTCUSDT', 'UNIUSDT',
    'APTUSDT', 'SUIUSDT', 'PEPEUSDT', 'FETUSDT', 'RENDERUSDT'
]

SCANNER_CONFIG = {
    'enabled': True,
    'top_symbols': TOP_20_SYMBOLS,
    'min_order_usdt': 10.0,
    'macro_interval': '4h',
    'default_micro_interval': '1h',
    'scalping_micro_interval': '15m',
    'adaptive_interval': True
}

TRADING_CONFIG = {
    'symbol': 'BTCUSDT',
    'interval': '1h',
    'limit': 300,
    'depth': 20,
    'maxlen': 10,
    'period': 14,
    'num_std': 2.0,
    'volume_avg': 50,
    'adx_period': 14,
    'min_adx': 20.0,
    'sell_pressure_threshold': 0.65
}

RISK_PROFILES = {
    'Conservador': {
        'rsi_threshold': 22,
        'adx_min': 25.0,
        'risk_percent': 1.0
    },
    'Moderado': {
        'rsi_threshold': 30,
        'adx_min': 20.0,
        'risk_percent': 2.0
    },
    'Agressivo': {
        'rsi_threshold': 35,
        'adx_min': 15.0,
        'risk_percent': 3.0
    }
}

ACTIVE_RISK_PROFILE = 'Moderado'
PAPER_TRADING = False

RSI_CONFIG = {
    'levels': [25, 23, 20, 18, 15, 12],
    'dynamic_low': [25, 23, 20, 18, 15, 12]
}

ATR_CONFIG = {
    'period': 14,
    'tp_multiplier': 2.0,
    'sl_multiplier': 1.5
}

OCO_CONFIG = {
    'target_profit_percent': 0.025,
    'stop_loss_percent': 0.02,
    'stop_limit_buffer': 0.005
}

OCO_ORDER_CONFIG = {
    'lucro_alvo_percent': 2.5,
    'stop_loss_percent': 2.0,
}

TRAILING_STOP_CONFIG = {
    'enabled': True,
    'activation_percent': 0.015,
    'callback_percent': 0.008,
}
