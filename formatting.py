# Emojis:
# Alertas e Ações
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

# Formatações:
# Códigos de cores ANSI para terminal
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"  # Reseta a cor para o padrão do terminal

# Formatações de texto ANSI para terminal
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"

# \033[0m

# Formatações HTML para mensagens Telegram
HTML_BOLD = "<b>{}</b>"
HTML_ITALIC = "<i>{}</i>"
HTML_UNDERLINE = "<u>{}</u>"
HTML_STRIKETHROUGH = "<s>{}</s>"
HTML_CODE = "<code>{}</code>"
HTML_CODE_BLOCK = "<pre>{}</pre>"
HTML_LINK = "<a href='{}'>{}</a>"

# Exemplos de uso das formatações
def print_examples():
    print(RED + "Texto em vermelho" + RESET)
    print(GREEN + "Texto em verde" + RESET)
    print(YELLOW + "Texto em amarelo" + RESET)
    print(BLUE + "Texto em azul" + RESET)
    print(MAGENTA + "Texto em magenta" + RESET)
    print(CYAN + "Texto em ciano" + RESET)
    print(BOLD + "Texto Negrito" + RESET)
    print(UNDERLINE + "Texto Sublinhado" + RESET)
    print(BLINK + "Texto Piscante" + RESET)