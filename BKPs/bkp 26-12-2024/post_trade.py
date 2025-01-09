from datetime import datetime
from pathlib import Path
import pandas as pd

from trading_functions import calculate_trade_result
from telegram_integration import send_telegram_message
from config import bot_token, chat_id

from decision import adjust_rsi_levels

def process_order_details(limit_order_details, stop_order_details, price, executed_qty, quantia_usdt_investimento_inicial):
    """
    Analisa os resultados das ordens OCO e atualiza o saldo baseado nos resultados das ordens de lucro ou stop loss.
    Também ajusta dinamicamente os níveis de RSI com base nos resultados das ordens.
    Args:
        limit_order_details (dict): Detalhes da ordem limite da OCO.
        stop_order_details (dict): Detalhes da ordem de stop da OCO.
        price (float): Preço de compra inicial.
        executed_qty (float): Quantidade da moeda comprada.
        quantia_usdt_investimento_inicial (float): Quantidade inicial de USDT investida.
    Returns:
        tuple: Resultado da ordem, resultado financeiro, saldo atualizado e timestamp da ordem.
    """
    if limit_order_details['status'] == 'FILLED':
        oco_order_result = 'profit'
        price_sold = float(limit_order_details['price'])
        adjust_rsi_levels('profit')  # Aumenta níveis de RSI após lucro
    elif stop_order_details['status'] == 'FILLED':
        oco_order_result = 'stop loss'
        price_sold = float(stop_order_details['price'])
        adjust_rsi_levels('stop loss')  # Reduz níveis de RSI após stop loss
    else:
        oco_order_result = None  # Não houve ordem preenchida
        price_sold = 0

    # Só processa o resultado do trade se houve uma ordem preenchida
    if oco_order_result is not None:
        trade_result = calculate_trade_result(price, executed_qty, price_sold)
        novo_saldo_usdt = quantia_usdt_investimento_inicial + trade_result
    else:
        trade_result = 0
        novo_saldo_usdt = quantia_usdt_investimento_inicial  # Mantém o saldo atual se não houve ordem preenchida

    oco_timestamp = datetime.now().strftime("%d/%m/%Y at %H:%M:%S") if oco_order_result else None

    return oco_order_result, trade_result, novo_saldo_usdt, oco_timestamp

def log_and_notify_results(order_result, symbol, trade_result, total_difference, timestamp, vwap):
    """
    Registra e notifica os resultados das ordens, enviando detalhes relevantes via Telegram.
    Args:
        order_result (str): Resultado da ordem ('profit' ou 'stop loss').
        symbol (str): Símbolo negociado.
        trade_result (float): Resultado financeiro da transação.
        total_difference (float): Diferença total no saldo após a ordem.
        timestamp (str): Data e hora quando a ordem foi concluída.
        vwap (float): Valor do VWAP no momento da ordem.
    """
    if order_result == 'profit':
        print(f"✅️ Ordem OCO concluída com \033[1;32mlucro\033[0m, Moeda: \033[1;33m{symbol}\033[0m \033[1;36m({timestamp})\033[0m")
        message = f'✅️ Ordem OCO concluída com <b>lucro</b>, <b>Moeda: {symbol} ({timestamp})</b>'
    elif order_result == 'stop loss':
        print(f"⛔ Ordem OCO concluída em \033[1;31mstop loss\033[0m, Moeda: \033[1;33m{symbol}\033[0m \033[1;36m({timestamp})\033[0m")
        message = f'⛔ Ordem OCO concluída em <b>stop loss</b>, <b>Moeda: {symbol} ({timestamp})</b>'
    send_telegram_message(bot_token, chat_id, message)

    # Exibe e envia notificações sobre o resultado financeiro
    if trade_result >= 0:
        result_message = f'\nDiferença parcial no saldo: 🟢 \033[1;32m${trade_result:.2f}\033[0m'
        telegram_message1 = f'Diferença parcial no saldo: 🟢 <b>${trade_result:.2f}</b>'
        send_telegram_message(bot_token, chat_id, telegram_message1)
    else:
        result_message = f'\nDiferença parcial no saldo: 🔴 \033[1;31m${trade_result:.2f}\033[0m'
        telegram_message1 = f'Diferença parcial no saldo: 🔴 <b>${trade_result:.2f}</b>'
        send_telegram_message(bot_token, chat_id, telegram_message1)
    print(result_message)

    # Notifica sobre a diferença total no saldo
    if total_difference >= 0:
        total_balance_message = f'Diferença total no saldo: 🟢 \033[1;32m${total_difference:.2f}\033[0m\n'
        telegram_message2 = f'Diferença total no saldo: 🟢 <b>${total_difference:.2f}</b>'
        send_telegram_message(bot_token, chat_id, telegram_message2)
    else:
        total_balance_message = f'Diferença total no saldo: 🔴 \033[1;31m${total_difference:.2f}\033[0m\n'
        telegram_message2 = f'Diferença total no saldo: 🔴 <b>${total_difference:.2f}</b>'
        send_telegram_message(bot_token, chat_id, telegram_message2)
    print(total_balance_message)

    print(f'📊 VWAP: {vwap:.2f}') #Adicionado

def create_data_row(order_count, saldo_inicial_usdt, quantia_usdt_investimento_inicial, symbol, executed_qty, price_rounded, 
                    purchase_timestamp, lucro_alvo, stop_loss, stop_limit, order_result, oco_timestamp, 
                    trade_result, total_difference, saldo_atual_usdt, rsi_value, executed_condition, vwap):
    """
    Atualiza a linha de dados para incluir variáveis de configuração e salva no Excel.
    """
    from config import rsi_low_level_0, rsi_low_level_1, rsi_low_level_2, rsi_low_level_3, rsi_high_0
    from config import lucro_multiplier_1, lucro_multiplier_2, stop_loss_multiplier_1, stop_loss_multiplier_2
    from config import SELL_PRESSURE_THRESHOLD_1, interval, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg

    return {
        "Índice da Ordem": order_count,
        "Saldo Inicial em USDT": round(saldo_inicial_usdt, 2),
        "USDT Inicial Investido": round(quantia_usdt_investimento_inicial, 2),
        "Símbolo": symbol,
        "Quantidade de Moeda": executed_qty,
        "Preço de Compra": price_rounded,
        "Data/Hora da Compra": purchase_timestamp,
        "Meta de Lucro OCO": lucro_alvo,
        "Stop Loss OCO": stop_loss,
        "Limite de Stop OCO": stop_limit,
        "Resultado da Ordem OCO": order_result,
        "Data/Hora OCO": oco_timestamp,
        "Resultado da Transação": round(trade_result, 2),
        "Resultado Total": round(total_difference, 2),
        "Saldo Final em USDT": round(saldo_atual_usdt, 2),
        "RSI da operação": rsi_value,
	    "Condição Atendida": executed_condition,
        # Adicionando variáveis de configuração
        "RSI Baixo Nível 0": rsi_low_level_0,
        "RSI Baixo Nível 1": rsi_low_level_1,
        "RSI Baixo Nível 2": rsi_low_level_2,
        "RSI Baixo Nível 3": rsi_low_level_3,
        "RSI Alto Nível 0": rsi_high_0,
        "Multiplicador de Lucro (Preço < 1)": lucro_multiplier_1,
        "Multiplicador de Lucro (Preço >= 1)": lucro_multiplier_2,
        "Multiplicador de Stop Loss (Preço < 1)": stop_loss_multiplier_1,
        "Multiplicador de Stop Loss (Preço >= 1)": stop_loss_multiplier_2,
	    "Limiar de pressão de venda": SELL_PRESSURE_THRESHOLD_1,
	    "Intervalo de tempo (candles)": interval,
	    "Período de cálculo do RSI e médias móveis": period,
	    "Número desvios padrões Bollinger": num_std,
	    "Período curto cálculo média móvel <> tendência": short_period,
	    "Período longo cálculo média móvel <> tendência": long_period,
	    "Limite dados históricos para recuperar de uma vez": limit,
	    "Profundidade do livro de ofertas": depth,
	    "Tamanho máximo para deque": maxlen,
	    "Condicional volume": volume_avg,
        "VWAP": vwap, #Adicionado
    }
  
def save_to_excel(data_row):
    """
    Salva os resultados das transações em uma planilha Excel para futura referência.
    Args:
        data_row (dict): Dados da transação a serem salvos.
    """
    filename = "results.xlsx"
    filepath = Path(__file__).parent / filename  # Salva na mesma pasta do script

    # Cria um DataFrame a partir do dicionário data_row
    new_row_df = pd.DataFrame([data_row])

    if filepath.exists():
        # Carrega o DataFrame existente
        df = pd.read_excel(filepath, index_col=0)
        # Usa concat ao invés de append
        df = pd.concat([df, new_row_df], ignore_index=True)
    else:
        df = new_row_df

    df.to_excel(filepath)
