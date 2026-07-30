import re

# Emojis para Alertas e Ações
ALERT = "🚨"
STOP = "⛔"
BLOCK = "🚫"
RED_CIRCLE = "🔴"
YELLOW_CIRCLE = "🟡"
WARN = "⚠️"
RECYCLE = "♻"

# Status
CHECK_MARK = "✅️"
GREEN_CIRCLE = "🟢"

# Finanças
MONEY_BAG = "💰"
COIN = "🪙"
ROCKET = "🚀"
CHART_UP = "📈"
CHART = "📊"

# Misc
ROBOT = "🤖"
PURPLE_CIRCLE = "🟣"
HOURGLASS = "⌛"
STOPWATCH = "⏱"

# Códigos de cores ANSI para terminal
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"

# Formatações de texto ANSI
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"

# Formatações HTML para mensagens Telegram
HTML_BOLD = "<b>{}</b>"
HTML_ITALIC = "<i>{}</i>"
HTML_UNDERLINE = "<u>{}</u>"
HTML_STRIKETHROUGH = "<s>{}</s>"
HTML_CODE = "<code>{}</code>"
HTML_CODE_BLOCK = "<pre>{}</pre>"
HTML_LINK = "<a href='{}'>{}</a>"

def remove_ansi_codes(text: str) -> str:
    """Remove códigos de escape ANSI de textos para exibição limpa em UIs e logs."""
    if not text:
        return ""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def format_price(price: float, include_symbol: bool = True) -> str:
    """
    Formata valores de preços considerando moedas normais (ex: BTC, ETH, SOL)
    e meme coins de baixíssimo valor (ex: SHIB, PEPE, BONK, FLOKI) sem zerar decimais.
    """
    if price is None:
        return "$0.00" if include_symbol else "0.00"
    
    try:
        val = float(price)
    except (ValueError, TypeError):
        return str(price)

    prefix = "$" if include_symbol else ""
    
    if abs(val) >= 1.0:
        return f"{prefix}{val:,.2f}"
    elif abs(val) >= 0.001:
        return f"{prefix}{val:.4f}"
    elif abs(val) >= 0.00001:
        return f"{prefix}{val:.6f}"
    else:
        return f"{prefix}{val:.8f}"
