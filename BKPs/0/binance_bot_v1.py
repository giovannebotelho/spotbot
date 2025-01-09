import time
import math  # Importando math para cálculos
from binance.client import Client
from config import my_api_key, my_secret_key

api_key = my_api_key
api_secret = my_secret_key

# Inicializando o cliente da Binance para a testnet
client = Client(api_key, api_secret, testnet=True)

def fetch_current_price(symbol):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

def adjust_quantity_based_on_lot_size(usd_amount, price, symbol_info):
    step_size = float([f['stepSize'] for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'][0])
    quantity = usd_amount / price
    quantity = math.floor(quantity / step_size) * step_size
    return quantity

def place_order(symbol, quantity, side):
    if side.upper() == 'BUY':
        order = client.order_market_buy(symbol=symbol, quantity=quantity)
    elif side.upper() == 'SELL':
        order = client.order_market_sell(symbol=symbol, quantity=quantity)
    else:
        return None
    return order

# Exemplo de operação de trading
symbol = 'BTCUSDT'
usd_amount = 100  # Montante em USDT que deseja usar para comprar BTC

btc_price = fetch_current_price(symbol)
print(f"Preço atual de {symbol}: {btc_price} USDT")

symbol_info = client.get_symbol_info(symbol)
btc_quantity = adjust_quantity_based_on_lot_size(usd_amount, btc_price, symbol_info)
print(f"Quantidade de {symbol.split('USDT')[0]} ajustada para compra: {btc_quantity}")

# Executando compra
buy_order = place_order(symbol, btc_quantity, 'BUY')
if buy_order:
    print("Compra executada com sucesso:", buy_order)
    # Simula uma espera antes de vender para simplificar o exemplo
    time.sleep(10)
    
    # Define um preço-alvo para venda baseado em um ganho de 0.3%
    target_price = btc_price * 1.003
    print(f"Preço alvo para venda: {target_price} USDT")
    
    # Verifica se atingiu o preço-alvo e executa venda
    current_price = fetch_current_price(symbol)
    if current_price >= target_price:
        print(f"Atendido preço alvo de venda: {current_price} USDT")
        sell_order = place_order(symbol, btc_quantity, 'SELL')
        if sell_order:
            print("Venda executada com sucesso:", sell_order)
else:
    print("Erro ao executar compra")