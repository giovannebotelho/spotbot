import os
from dotenv import load_dotenv

load_dotenv()  # Carrega as variáveis do arquivo .env

# Binance API Keys for different environments

# Testnet Spot - Chaves de API para a versão de teste de negociação spot em Binance.
testnetspot_api_key = os.getenv("testnetspot_api_key")
testnetspot_secret_key = os.getenv("testnetspot_secret_key")

# Testnet Futures - Chaves de API para a versão de teste de negociação de futuros em Binance.
testnetfut_api_key = os.getenv("testnetfut_api_key")
testnetfut_secret_key = os.getenv("testnetfut_secret_key")

# Mainnet - Chaves de API para a versão principal de negociação em Binance.
mainnet_api_key = os.getenv("mainnet_api_key")
mainnet_secret_key = os.getenv("mainnet_secret_key")

# Telegram - Configurações para integração com o bot do Telegram para notificações.
bot_token = os.getenv("bot_token")
chat_id = os.getenv("chat_id")

# Interval, period and depth configs - Configurações gerais para busca de dados e cálculos.
interval = '15m'  # Intervalo de tempo para buscar dados de velas (candles).
period = 10       # Período utilizado para cálculos que envolvem médias móveis ou outros indicadores.
num_std = 2       # Número de desvios padrões para cálculo das Bandas de Bollinger.
short_period = 10  # Período curto para cálculos de média móvel em comparações de tendência.
long_period = 15  # Período longo para cálculos de média móvel em comparações de tendência.
limit = 20        # Limite de dados históricos (por exemplo, velas) para recuperar de uma vez.
depth = 10        # Profundidade do livro de ofertas para recuperar em consultas ao order book.
maxlen = 10       # Tamanho máximo para deque usados em médias móveis de pressão de venda.

# Configurações do MACD
macd_fast = 8
macd_slow = 17
macd_signal = 5

# Should buy configs - Configurações para a lógica de decisão de compra.
SELL_PRESSURE_THRESHOLD_1 = 0.6  # Limiar de pressão de venda para decidir sobre colocar uma ordem de compra.

# Configuração inicial de um limiar de volume que pode ser ajustada conforme necessário.
# Verificação condicional que compara o último volume coletado com a média móvel ajustada por um percentual específico (volume_avg).
volume_avg = 35 # 35%

# Configurações de níveis de RSI
lvl0 = 15 # (apenas RSI)
lvl1 = 22 # (RSI+VWAP)
lvl2 = 23 # (RSI+TREND+VWAP)
lvl3 = 24 # (RSI+TREND+VWAP+MACD OU RSI+CANDLE)

rsi_low_level_0 = lvl0 # Limiar para o RSI considerado muito baixo.
rsi_low_level_1 = lvl1 # Limiar para o RSI considerado baixo e considerando o indicador VWAP.
rsi_low_level_2 = lvl2 # Limiar para o RSI considerado médio e considerando tendências de alta e o indicador VWAP.
rsi_low_level_3 = lvl3 # Limiar para o RSI considerado médio-alto considerando tendências de alta, indicador VWAP e MACD ou somente RSI e padrões de Candle.

rsi_min_level_0 = lvl0 - 4
rsi_min_level_1 = lvl1 - 4
rsi_min_level_2 = lvl2 - 4
rsi_min_level_3 = lvl3 - 4

# Configurações dinâmicas de RSI
dynamic_rsi_low_0 = rsi_low_level_0
dynamic_rsi_low_1 = rsi_low_level_1
dynamic_rsi_low_2 = rsi_low_level_2
dynamic_rsi_low_3 = rsi_low_level_3

rsi_high_0 = 70 # Limiar para o RSI considerado alto para decisões de venda.

# Lucro and Stop Loss - Configurações para cálculos de ordens OCO.
# if current_price < 1:
lucro_multiplier_1 = 1.008  # Multiplicador de lucro para preços menores que 1.
stop_loss_multiplier_1 = 0.99  # Multiplicador de stop loss para preços menores que 1.
#else:
lucro_multiplier_2 = 1.003  # Multiplicador de lucro para preços maiores ou iguais a 1.
stop_loss_multiplier_2 = 0.9968  # Multiplicador de stop loss para preços maiores ou iguais a 1.
