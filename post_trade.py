from datetime import datetime
from pathlib import Path
import pandas as pd

from trading_functions import calculate_trade_result, calculate_fee
from telegram_integration import send_telegram_message
from config import TELEGRAM_CONFIG

from decision import adjust_rsi_levels

async def process_order_details(symbol, client, limit_order_details, stop_order_details, price, executed_qty, quantia_usdt_investimento_inicial):
    """
    Analisa os resultados das ordens OCO e atualiza o saldo baseado nos resultados das ordens de lucro ou stop loss.
    Também ajusta dinamicamente os níveis de RSI com base nos resultados das ordens.
    Args:
        client: Cliente da API da Binance.
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
        
        # Calcula a taxa e o resultado líquido
        fee = await calculate_fee(client, symbol, executed_qty, price_sold) # Enviando symbol como parametro
        trade_result_liquid = trade_result - fee  # Resultado final menos a taxa
        
        # Mantenha o cálculo do novo_saldo_usdt usando o trade_result BRUTO, para os juros compostos
        novo_saldo_usdt = quantia_usdt_investimento_inicial + trade_result
    else:
        trade_result = 0
        novo_saldo_usdt = quantia_usdt_investimento_inicial  # Mantém o saldo atual se não houve ordem preenchida
        fee = 0
        trade_result_liquid = 0

    oco_timestamp = datetime.now().strftime("%d/%m/%Y at %H:%M:%S") if oco_order_result else None

    return symbol, oco_order_result, trade_result, novo_saldo_usdt, oco_timestamp, fee, trade_result_liquid

def log_and_notify_results(order_result, symbol, trade_result, total_difference, timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_usdt):
    """
    Registra e notifica os resultados das ordens, enviando detalhes relevantes via Telegram.
    Args:
        order_result (str): Resultado da ordem ('profit' ou 'stop loss').
        symbol (str): Símbolo negociado.
        trade_result (float): Resultado financeiro da transação.
        total_difference (float): Diferença total no saldo após a ordem.
        timestamp (str): Data e hora quando a ordem foi concluída.
        vwap (float): Valor do VWAP no momento da ordem.
        fee (float): Valor da taxa
        trade_result_liquid (float): Valor do resultado descontado a taxa
    """
    if order_result == 'profit':
        print(f"✅️ Ordem OCO concluída com \033[1;32mlucro\033[0m, Moeda: \033[1;33m{symbol}\033[0m \033[1;36m({timestamp})\033[0m")
        message = f'✅️ Ordem OCO concluída com <b>lucro</b>, <b>Moeda: {symbol} ({timestamp})</b>'
    elif order_result == 'stop loss':
        print(f"⛔ Ordem OCO concluída em \033[1;31mstop loss\033[0m, Moeda: \033[1;33m{symbol}\033[0m \033[1;36m({timestamp})\033[0m")
        message = f'⛔ Ordem OCO concluída em <b>stop loss</b>, <b>Moeda: {symbol} ({timestamp})</b>'
    send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)

    # Exibe e envia notificações sobre o resultado financeiro
    if trade_result >= 0:
        result_message = f'\nLucro Parcial Bruto: 🟢 \033[1;32m${trade_result:.2f}\033[0m\nTaxa: 🔴 \033[1;31m${fee:.2f}\033[0m\nLucro Parcial Líquido: 🟢 \033[1;32m${trade_result_liquid:.2f}\033[0m\n'
        telegram_message1 = f'Lucro Parcial Bruto: 🟢 <b>${trade_result:.2f}</b>\nTaxa: 🔴 <b>${fee:.2f}</b>\nLucro Parcial Líquido: 🟢 <b>${trade_result_liquid:.2f}</b>'
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], telegram_message1)
    else:
        result_message = f'\nPrejuízo Parcial Bruto: 🔴 \033[1;31m${trade_result:.2f}\033[0m\nTaxa: 🔴 \033[1;31m${fee:.2f}\033[0m\nPrejuízo Parcial Líquido: 🔴 \033[1;31m${trade_result_liquid:.2f}\033[0m\n'
        telegram_message1 = f'Prejuízo Parcial Bruto: 🔴 <b>${trade_result:.2f}</b>\nTaxa: 🔴 <b>${fee:.2f}</b>\nPrejuízo Parcial Líquido: 🔴 <b>${trade_result_liquid:.2f}</b>'
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], telegram_message1)
    print(result_message)

    # Notifica sobre a diferença total no saldo
    if total_difference >= 0:
        total_balance_message = f'Diferença total bruta no saldo: 🟢 \033[1;32m${total_difference:.2f}\033[0m'
        telegram_message2 = f'Diferença total bruta no saldo: 🟢 <b>${total_difference:.2f}</b>'
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], telegram_message2)
    else:
        total_balance_message = f'Diferença total bruta no saldo: 🔴 \033[1;31m${total_difference:.2f}\033[0m'
        telegram_message2 = f'Diferença total bruta no saldo: 🔴 <b>${total_difference:.2f}</b>'
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], telegram_message2)
    print(total_balance_message)
    
    # Adiciona a notificação sobre a diferença total líquida
    if total_difference_liquid >= 0:
        total_balance_liquid_message = f'Diferença total líquida no saldo: 🟢 \033[1;32m${total_difference_liquid:.2f}\033[0m\n'
        telegram_message3 = f'Diferença total líquida no saldo: 🟢 <b>${total_difference_liquid:.2f}</b>'
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], telegram_message3)
    else:
        total_balance_liquid_message = f'Diferença total líquida no saldo: 🔴 \033[1;31m${total_difference_liquid:.2f}\033[0m\n'
        telegram_message3 = f'Diferença total líquida no saldo: 🔴 <b>${total_difference_liquid:.2f}</b>'
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], telegram_message3)
    print(total_balance_liquid_message)
    
    # Exibe o saldo de BNB em USDT
    print(f"💰 Saldo BNB em USDT na carteira: \033[1;34m${bnb_balance_usdt:.2f}\033[0m")
    message = f"💰 Saldo BNB em USDT na carteira: <b>${bnb_balance_usdt:.2f}</b>"
    send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)

    # print(f'📊 VWAP: {vwap:.2f}') #Adicionado

def create_data_row(order_count, saldo_inicial_usdt, quantia_usdt_investimento_inicial, symbol,
                    executed_qty, price_rounded, purchase_timestamp, lucro_alvo, stop_loss, stop_limit,
                    order_result, oco_timestamp, trade_result, total_difference, saldo_atual_usdt,
                    rsi, executed_condition, vwap, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation,
                    ema7, ema15, ema25, ema50, ema100, ema200, candle_patterns, volume_avg, amplitude, macd_current, signal_line_current, 
                    lower_band, middle_band, upper_band, trend_is_up, fee, trade_result_liquid, total_difference_liquid, gemini_response, bnb_balance_usdt):
    """
    Atualiza a linha de dados para incluir variáveis de configuração e salva no Excel.
    """
    from config import RSI_CONFIG, OCO_CONFIG, TRADING_CONFIG

    return {
        "Índice da Ordem": order_count,
        "Saldo Inicial em USDT": round(saldo_inicial_usdt, 2),
        "USDT Inicial Investido": round(quantia_usdt_investimento_inicial, 2),
        "Símbolo": symbol,
        "Quantidade de Moeda": executed_qty,
        "Preço de Compra": price_rounded,
        "VWAP": vwap,
        "EMA 7" : ema7,
        "EMA 15" : ema15,
        "EMA 25" : ema25,
        "EMA 50" : ema50,
        "EMA 100": ema100,
        "EMA 200": ema200,
        "Data/Hora da Compra": purchase_timestamp,
        "Meta de Lucro OCO": lucro_alvo,
        "Stop Loss OCO": stop_loss,
        "Limite de Stop OCO": stop_limit,
        "Resultado da Ordem OCO": order_result,
        "Data/Hora OCO": oco_timestamp,
        "Resultado Parcial da Transação": round(trade_result, 2),
        "Taxa": fee, # Nova coluna
        "Resultado Parcial da Transação Líquido": round(trade_result_liquid, 2), # Nova coluna
        "Resultado Total Bruto": round(total_difference, 2),
        "Resultado Total Liquido": round(total_difference_liquid, 2),
        "Saldo Final em USDT": round(saldo_atual_usdt, 2),
        "Saldo BNB em USDT": bnb_balance_usdt,
        "RSI da operação": rsi,
        "Condição Atendida": executed_condition,
        "Intervalo de tempo (Candles)": TRADING_CONFIG['interval'],
        "Preço de Abertura (Candle)": candle_open,
        "Preço Máximo (Candle)": candle_high,
        "Preço Mínimo (Candle)": candle_low,
        "Preço de Fechamento (Candle)": candle_close,
        "Variação (Candle)": candle_variation,
        "Amplitude (Candle)": amplitude, # Adicionado
        "Variação (24h)": variation_24h,
        "Volume (Candle)": candle_volume,
        "Padrões de Candle": candle_patterns,
        "MACD": macd_current,
        "Linha de Sinal": signal_line_current,
        "Banda Inferior BB": lower_band,
        "Banda Média BB": middle_band,
        "Banda Superior BB": upper_band,
        "Tendência de Alta": trend_is_up,
        # Adicionando variáveis de configuração
        "RSI Nível 0": RSI_CONFIG['levels'][0],
        "RSI Nível 1": RSI_CONFIG['levels'][1],
        "RSI Nível 2": RSI_CONFIG['levels'][2],
        "RSI Nível 3": RSI_CONFIG['levels'][3],
        "RSI Nível 4": RSI_CONFIG['levels'][4],
        "RSI Nível 5": RSI_CONFIG['levels'][5],
        "RSI Alto Nível 0": RSI_CONFIG['high'],
        "Multiplicador de Lucro (Preço < 1)": OCO_CONFIG['price_under_1']['profit_multiplier'],
        "Multiplicador de Stop Loss (Preço < 1)": OCO_CONFIG['price_under_1']['stop_loss_multiplier'],
        "Multiplicador de Lucro (Preço >= 1)": OCO_CONFIG['price_over_1']['profit_multiplier'],
        "Multiplicador de Stop Loss (Preço >= 1)": OCO_CONFIG['price_over_1']['stop_loss_multiplier'],
        "Limiar de pressão de venda": TRADING_CONFIG['sell_pressure_threshold'],
        "Período de cálculo do RSI e médias móveis": TRADING_CONFIG['period'],
        "Número desvios padrões Bollinger": TRADING_CONFIG['num_std'],
        "Período curto cálculo média móvel <> tendência": TRADING_CONFIG['short_period'],
        "Período longo cálculo média móvel <> tendência": TRADING_CONFIG['long_period'],
        "Limite dados históricos para recuperar de uma vez": TRADING_CONFIG['limit'],
        "Profundidade do livro de ofertas": TRADING_CONFIG['depth'],
        "Tamanho máximo para deque": TRADING_CONFIG['maxlen'],
        "Condicional volume": TRADING_CONFIG['volume_avg'],
        "Resposta do Gemini": gemini_response if gemini_response is not None else "N/A", # Adiciona a resposta do Gemini à linha de dados
    }

from database import DatabaseManager

def save_to_csv(data_row):
    """
    Salva os resultados das transações no banco de dados SQLite.
    Mantém o nome da função para compatibilidade, mas agora usa o DB.
    """
    try:
        db = DatabaseManager()
        db.add_trade(data_row)
        print("✅ Dados salvos no banco de dados SQLite.")
    except Exception as e:
        print(f"❌ Erro ao salvar no banco de dados: {e}")
        # Fallback to CSV if DB fails? No, let's trust the DB or log the error.
        # We could implement a fallback here if critical.
