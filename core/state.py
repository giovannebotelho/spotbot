"""
Gerenciador de Estado Global do SpotBot Pro.
Centraliza as variáveis mutáveis que antes ficavam no engine.py.
"""

bot_running = False
active_positions = {}
active_monitoring_tasks = []
_last_autotune_time = 0

bot_status_data = {
    "rsi": 0, 
    "price": 0, 
    "symbol": "", 
    "action": "Iniciando...", 
    "trend": "N/A", 
    "target_asset": "BTCUSDT",
    "active_symbols": [], 
    "active_positions": active_positions
}

shared_market_data = {
    "klines": [], 
    "dates": [], 
    "bb_upper": [], 
    "bb_lower": [], 
    "bb_middle": [], 
    "ema200": [], 
    "volumes": [], 
    "scanner_results": [],
    "gemini_insight": None
}

SHORT_PAUSE = 600
LONG_PAUSE = 3600
stop_loss_count = 0
last_stop_loss_time = None
block_active = False
pause_end_time = None
MAX_RESTARTS = 3
restart_attempts = 0
last_operation_time = None
