
# from datetime import datetime, timedelta  <-- keeping date imports as they might be used elsewhere or remove if unused. Checking usage... 
# actually datetime is used in other functions? No, looking at file content:
# line 4: from datetime import datetime, timedelta
# Used in read/write_last_sync_time and synchronize_time.
# Used in cancel_all_oco_orders? No.
# Used in escolher_simbolo? No.
# So I can remove the imports too.

from binance.exceptions import BinanceAPIException

from telegram_integration import send_telegram_message
from config import TELEGRAM_CONFIG

async def cancel_all_oco_orders(client, symbol):
    """
    Cancela todas as ordens OCO abertas para um símbolo específico.
    Args:
        client: Cliente da API do Binance.
        symbol (str): Símbolo de trading para o qual as ordens serão canceladas.
    """
    try:
        open_oco_orders = await client.get_open_oco_orders()  # Obter todas as ordens OCO abertas
        for order_list in open_oco_orders:
            if order_list['symbol'] == symbol:
                order_list_id = order_list['orderListId']
                await client.cancel_order(symbol=symbol, orderListId=order_list_id)
                print(f"Ordem OCO com orderListId {order_list_id} para o símbolo {symbol} cancelada.")

    except BinanceAPIException as e:
        print(f"Erro ao cancelar ordens OCO: {e}")
    except Exception as e:
        print(f"Erro inesperado ao cancelar ordens OCO: {e}")

def escolher_simbolo():
    """
    Permite ao usuário escolher um símbolo de trading através de uma interface interativa no console.
    Se um símbolo estiver definido em TRADING_CONFIG, ele será usado automaticamente.
    Returns:
        str: Símbolo escolhido pelo usuário para trading.
    """
    from config import TRADING_CONFIG
    
    if "symbol" in TRADING_CONFIG and TRADING_CONFIG["symbol"]:
        print(f"\n🪙 Símbolo definido na configuração: {TRADING_CONFIG['symbol']}")
        return TRADING_CONFIG["symbol"]

    while True:
        print("\n🪙 Escolha o símbolo preferido ou digite manualmente:")
        print('1 - BTC/USDT')
        print('2 - ETH/USDT')
        print('3 - BNB/USDT')
        print('4 - ADA/USDT')
        print('5 - SOL/USDT')
        print('0 - Outra')
        
        try:
            symbol_input = int(input(": "))
        except ValueError:
            print("\nPor favor, digite um número.")
            continue

        if symbol_input == 1:
            return 'BTCUSDT'
        elif symbol_input == 2:
            return 'ETHUSDT'
        elif symbol_input == 3:
            return 'BNBUSDT'
        elif symbol_input == 4:
            return 'ADAUSDT'
        elif symbol_input == 5:
            return 'SOLUSDT'
        elif symbol_input == 0:
            escolha_alternativa = input("\nDigite a moeda requerida no formato (Ex.: BTCUSDT): ")
            return escolha_alternativa.upper()  # Garante que o texto será maiúsculo
        else:
            print("\n⛔ Digite uma opção válida.")
