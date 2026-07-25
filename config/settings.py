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
    "use_ema_filter": False,
    "adx_period": 14,
    "min_adx": 20.0
}

# Perfis de Risco Selecionáveis
RISK_PROFILES = {
    "Conservador": {"rsi_threshold": 22, "adx_min": 25.0, "risk_percent": 1.0},
    "Moderado": {"rsi_threshold": 30, "adx_min": 20.0, "risk_percent": 2.0},
    "Agressivo": {"rsi_threshold": 35, "adx_min": 15.0, "risk_percent": 3.0}
}
ACTIVE_RISK_PROFILE = "Moderado"
PAPER_TRADING = False

# Configurações Dinâmicas de RSI
RSI_CONFIG = {
    "levels": {0: 18, 1: 20, 2: 22, 3: 25, 4: 28, 5: 30},
    "high": 70,
    "dynamic_low": {0: 18, 1: 20, 2: 22, 3: 25, 4: 28, 5: 30},
    "min": {0: 12, 1: 15, 2: 18, 3: 20, 4: 22, 5: 25}
}

# Configurações de Ordens OCO (Lucro & Stop)
OCO_CONFIG = {
    "target_profit_percent": 0.025,  # 2.5% Lucro Alvo
    "stop_loss_percent": 0.015,       # 1.5% Stop Loss
    "stop_limit_buffer": 0.002        # 0.2% Buffer para execução do Stop
}

# Configurações de Stop baseado em Volatilidade (ATR)
ATR_CONFIG = {
    "period": 14,
    "sl_multiplier": 2.0,
    "tp_multiplier": 3.0,
    "use_atr_stop": True
}

# Configurações de Trailing Stop Móvel
TRAILING_STOP_CONFIG = {
    "enabled": True,
    "activation_percent": 0.015,   # Ativa o trailing quando o lucro atinge +1.5%
    "callback_percent": 0.008       # Recua o stop se o preço cair 0.8% da máxima
}

# Banco de Dados Híbrido
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///spotbot.db")
