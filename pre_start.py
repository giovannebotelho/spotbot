import os
import subprocess

from datetime import datetime, timedelta
from binance.exceptions import BinanceAPIException

from telegram_integration import send_telegram_message
from config import TELEGRAM_CONFIG

sync_file_path = 'last_sync_time.txt'

def read_last_sync_time():
    """
    Lê o último momento de sincronização do relógio do sistema a partir de um arquivo.
    Returns:
        datetime: A última data de sincronização, se disponível.
    """
    if os.path.exists(sync_file_path):
        with open(sync_file_path, 'r') as file:
            last_sync_time_str = file.read().strip()
            if last_sync_time_str:
                return datetime.fromisoformat(last_sync_time_str)
    return None

def write_last_sync_time():
    """
    Grava a data e hora atual no arquivo como a última vez que o relógio foi sincronizado.
    """
    with open(sync_file_path, 'w') as file:
        file.write(datetime.now().isoformat())

def synchronize_time():
    """
    Sincroniza o relógio do sistema com um servidor de tempo para garantir que o tempo está correto,
    essencial para operações de trading que dependem de timing preciso.
    """
    last_sync_time = read_last_sync_time()
    if last_sync_time is None or datetime.now() - last_sync_time > timedelta(days=3):
        try:
            subprocess.run(['w32tm', '/resync'], check=True)
            print("✅️ Relógio do sistema sincronizado com sucesso.")
            message = "✅️ Relógio do sistema sincronizado com sucesso."
            send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)
            write_last_sync_time()  # Atualiza a última data de sincronização no arquivo
        except subprocess.CalledProcessError:
            print("🚨 Falha ao sincronizar o relógio do sistema.")
            message = "🚨 Falha ao sincronizar o relógio do sistema."
            send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)
    else:
        print("🟡 Sincronização de relógio não necessária. Última feita há menos de 3 dias.")

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
                await client.cancel_order_list(symbol=symbol, orderListId=order_list_id)
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
