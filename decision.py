import asyncio
import math
import time
import os
from dotenv import load_dotenv
load_dotenv()  # Carregue as variáveis de ambiente do arquivo .env, incluindo GEMINI_API_KEY
from binance.exceptions import BinanceAPIException
from trading_functions import calculate_moving_average_sell_pressure
from binance_api import get_order_book
from telegram_integration import send_telegram_message
from config import bot_token, chat_id
from config import lucro_multiplier_1, stop_loss_multiplier_1, lucro_multiplier_2, stop_loss_multiplier_2
from config import SELL_PRESSURE_THRESHOLD_1
from config import interval, limit #importar interval e limit
from config import (
    dynamic_rsi_low_0, dynamic_rsi_low_1, dynamic_rsi_low_2, dynamic_rsi_low_3, dynamic_rsi_low_4, dynamic_rsi_low_5,
    rsi_low_level_0, rsi_low_level_1, rsi_low_level_2, rsi_low_level_3, rsi_low_level_4, rsi_low_level_5, rsi_high_0,
    rsi_min_level_0, rsi_min_level_1, rsi_min_level_2, rsi_min_level_3, rsi_min_level_4, rsi_min_level_5
)
from gemini_analysis import analyze_with_gemini, interpret_gemini_response  # Importe a função analyze_with_gemin

async def should_place_order(client, symbol, SELL_PRESSURE_THRESHOLD = SELL_PRESSURE_THRESHOLD_1, interval=interval, limit=limit):
    """
    Determina se uma ordem deve ser colocada com base na pressão de venda média.
    Args:
        client (BinanceAsyncClient): O cliente conectado à API da Binance.
        symbol (str): O símbolo de trading (ex.: 'BTCUSDT').
        SELL_PRESSURE_THRESHOLD (float): Limite de pressão de venda para disparar uma ordem.
    Returns:
        bool: True se a pressão de venda estiver abaixo do limiar, False caso contrário.
    """
    avg_sell_pressure = await calculate_moving_average_sell_pressure(client, symbol, interval, limit)
    avg_sell_pressure_percent = avg_sell_pressure * 100
    
    msg = f"⛔ Alta pressão de venda média detectada: \033[1;31m{avg_sell_pressure_percent:.1f}%\033[0m, Aguardando..."
    
    if avg_sell_pressure < SELL_PRESSURE_THRESHOLD:
        print("\033[2K\r", end='')
        return True
    else:
        # Imprime a nova mensagem
        print(f"\r{msg}", end='', flush=True)
        # Espera um breve momento antes de limpar a linha novamente
        await asyncio.sleep(0.6)
        # Limpa a linha anterior
        print("\033[2K\r", end='')
        await asyncio.sleep(0.15)
    return False

async def should_buy(rsi, trend_is_up, macd_current, signal_line_current, last_close, lower_band, vwap, candle_patterns):
    """
    Avalia se as condições são adequadas para comprar baseando-se em RSI, tendência, decisão de vela e MACD.
    Args:
        rsi (float): Valor atual do RSI.
        trend_is_up (bool): Indica se a tendência está subindo.
        candle_decision (str): Decisão tomada com base no padrão de vela.
        macd_current (float): Valor atual do MACD.
        signal_line_current (float): Valor atual da linha de sinal do MACD.
        last_close (float): Último preço de fechamento.
        lower_band (float): Banda inferior de Bollinger.
        vwap (float): Valor atual do VWAP.
        candle_patterns (list): Lista de padrões de candle detectados.
    Returns:
        dict: Um dicionário com True ou False (compra), uma mensagem (qual condição de compra) e dados da candle atual.
    """
    rsi_low_level0 = rsi <= rsi_low_level_0
    rsi_low_level1 = rsi <= rsi_low_level_1
    rsi_low_level2 = rsi <= rsi_low_level_2
    rsi_low_level3 = rsi <= rsi_low_level_3
    rsi_low_level4 = rsi <= rsi_low_level_4
    rsi_low_level5 = rsi <= rsi_low_level_5
    
    # Corrigido: Adicionado 'and' para verificar se o MACD está realmente acima da linha de sinal
    macd_bullish = macd_current > signal_line_current and last_close < lower_band  
    vwap_tolerance = 0.07  # 7% de tolerância
    price_below_vwap = last_close < vwap * (1 + vwap_tolerance)
    
    # Adicionado: Verifica se há algum padrão de candle na lista
    has_candle_patterns = candle_patterns is not None and len(candle_patterns) > 0
    
    # Condição 5: Análise do Gemini
    # Obter o loop de eventos atual
    loop = asyncio.get_running_loop()

    # Executar a função assíncrona dentro do loop de eventos atual
    gemini_response = await loop.run_in_executor(
        None,  # Usa o executor padrão (pool de threads)
        analyze_with_gemini,  # A função a ser executada
        os.getenv("gemini_api"),  # Argumentos para a função
        5,    # binance_x
        90,   # binance_y
        1920, # binance_width
        950,  # binance_height
        5,    # tradingview_x
        90,   # tradingview_y
        1920, # tradingview_width
        950   # tradingview_height
    )
    
    # Extrai o sinal da resposta do Gemini
    if gemini_response:
        gemini_buy_signal = interpret_gemini_response(gemini_response)
    else:
        gemini_buy_signal = None  # Ou False, dependendo de como você quer tratar a ausência de resposta do Gemini

    if rsi_low_level0:
        print("\nEntrando na condição 0 de compra do RSI considerado muito baixo")
        message = "Entrando na <b>condição 0</b> de compra do <b>RSI considerado muito baixo</b>"
        send_telegram_message(bot_token, chat_id, message)
        return {"buy": True, "message": "RSI_lvl0", "candle_data": "", "gemini_response": None}

    elif rsi_low_level1 and price_below_vwap:
        print("\nEntrando na condição 1 de compra do RSI considerado baixo e considerando o indicador VWAP")
        message = "Entrando na <b>condição 1</b> de compra do <b>RSI considerado baixo e considerando o indicador VWAP</b>"
        send_telegram_message(bot_token, chat_id, message)
        return {"buy": True, "message": "RSI_lvl1 e VWAP", "candle_data": "", "gemini_response": None}
    
    elif rsi_low_level2 and has_candle_patterns:  
        print("\nEntrando na condição 2 de compra do RSI considerado médio e considerando padrões de Candle")
        message = "Entrando na <b>condição 2</b> de compra do <b>RSI considerado médio e considerando padrões de Candle</b>"
        send_telegram_message(bot_token, chat_id, message)
        return {"buy": True, "message": "RSI_lvl2 e candles", "candle_data": "", "gemini_response": None}
    
    elif rsi_low_level3 and trend_is_up and price_below_vwap:  
        print("\nEntrando na condição 3 de compra do RSI considerado médio-alto considerando tendências de alta e o indicador VWAP")
        message = "Entrando na <b>condição 3</b> de compra do <b>RSI considerado médio-alto considerando tendências de alta e o indicador VWAP</b>"
        send_telegram_message(bot_token, chat_id, message)
        return {"buy": True, "message": "RSI_lvl3, tendência e VWAP", "candle_data": "", "gemini_response": None}

    elif rsi_low_level4 and trend_is_up and price_below_vwap and macd_bullish:
        print("\nEntrando na condição 4 de compra do RSI considerado alto considerando tendências de alta, indicador VWAP e MACD")
        message = "Entrando na <b>condição 4</b> de compra do <b>RSI considerado alto considerando tendências de alta, indicador VWAP e MACD</b>"
        send_telegram_message(bot_token, chat_id, message)
        return {"buy": True, "message": "RSI_lvl4, tendência, VWAP e MACD", "candle_data": "", "gemini_response": None}
    
    elif gemini_buy_signal and rsi_low_level5:
        print("\nEntrando na condição 5 de compra: Sinal de COMPRA do Gemini e RSI")
        message = "Entrando na <b>condição 5</b> de compra: <b>Sinal de COMPRA do Gemini e RSI</b>"
        send_telegram_message(bot_token, chat_id, message)
        return {"buy": True, "message": "Gemini Buy Signal e RSI", "candle_data": "", "gemini_response": gemini_response}
    
    elif gemini_buy_signal in (False, None):
        # print("Sinal \033[1;33mNEUTRO\033[0m ou \033[1;31mVENDA\033[0m recebido do Gemini.\n")
        pass
    
    return {"buy": False, "message": None, "candle_data": "", "gemini_response": gemini_response}

def should_sell(rsi, trend_is_up, macd_current, signal_line_current, last_close, lower_band, vwap):
    """
    Avalia se as condições são adequadas para vender baseando-se em RSI, tendência, decisão de vela e MACD.
    Args:
        rsi (float): Valor atual do RSI.
        trend_is_up (bool): Indica se a tendência está subindo.
        candle_decision (str): Decisão tomada com base no padrão de vela.
        macd_current (float): Valor atual do MACD.
        signal_line_current (float): Valor atual da linha de sinal do MACD.
        last_close (float): Último preço de fechamento.
        lower_band (float): Banda inferior de Bollinger.
        vwap (float): Valor atual do VWAP.
    Returns:
        bool: True se as condições forem favoráveis para venda, False caso contrário.
    """
    rsi_high = rsi >= rsi_high_0
    macd_bearish = macd_current < signal_line_current and last_close > lower_band
    
    price_above_vwap = last_close > vwap

    return (rsi_high and not trend_is_up) or macd_bearish or price_above_vwap

def adjust_price_to_tick_size(price, tick_size):
    """Ajusta o preço para o tamanho do tick mais próximo permitido pelo mercado."""
    return math.floor(price / tick_size) * tick_size

def adjust_quantity_to_lot_size(quantity, symbol_info):
    """Ajusta a quantidade para cumprir com o requisito de tamanho do lote do símbolo."""
    lot_size_filter = next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'LOT_SIZE')
    step_size = float(lot_size_filter['stepSize'])
    quantity = math.floor(quantity / step_size) * step_size
    return max(quantity, float(lot_size_filter['minQty']))

def calculate_adjustment(current_price, current_quantity, required_notional, current_notional):
    """Calcula o ajuste necessário para atender ao notional mínimo."""
    if current_notional < required_notional:
        adjustment_factor = required_notional / current_notional
        new_price = current_price * adjustment_factor
        new_quantity = current_quantity * (1 / adjustment_factor)
        return new_price, new_quantity
    return current_price, current_quantity

def get_min_notional(symbol_info):
    """Retorna o valor notional mínimo para um símbolo."""
    return float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'MIN_NOTIONAL')['minNotional'])

async def adjust_and_place_oco_order(client, symbol, quantity, tick_size, min_price_move):
    """Ajusta os preços para as condições de mercado e coloca uma ordem OCO."""
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            order_book = await get_order_book(client, symbol)
            current_price = float(order_book['asks'][0][0])

            lucro_multiplier = lucro_multiplier_1 if current_price < 1 else lucro_multiplier_2
            stop_loss_multiplier = stop_loss_multiplier_1 if current_price < 1 else stop_loss_multiplier_2

            lucro_alvo = adjust_price_to_tick_size(current_price * lucro_multiplier, tick_size)
            stop_loss = adjust_price_to_tick_size(current_price * stop_loss_multiplier, tick_size)
            stop_limit = adjust_price_to_tick_size(stop_loss - (20 * min_price_move), tick_size)

            # Parâmetros para a ordem OCO
            params = {
                'symbol': symbol,
                'side': 'SELL',
                'quantity': f"{quantity:.6f}",
                'aboveType': 'LIMIT_MAKER',
                'belowType': 'STOP_LOSS_LIMIT',
                'abovePrice': f"{lucro_alvo:.2f}",  # Preço para a ordem LIMIT_MAKER (lucro)
                'belowStopPrice': f"{stop_loss:.2f}",  # Preço de ativação para a ordem STOP_LOSS_LIMIT
                'belowPrice': f"{stop_limit:.2f}", # Preço limite para a ordem STOP_LOSS_LIMIT
                'belowTimeInForce': 'GTC',  # Time in force para a ordem STOP_LOSS_LIMIT
                'timestamp': int(time.time() * 1000)
            }

            oco_order = await client.create_oco_order(**params)

            order_list_id = oco_order.get('orderListId', 'N/A')
            limit_order_id = oco_order['orders'][1]['orderId']
            stop_order_id = oco_order['orders'][0]['orderId']
            
            if symbol == "DOGEUSDT" or symbol == "ADAUSDT":
                print(f"✅️ Ordem OCO colocada. Moeda: \033[1;33m{symbol}\033[0m. ID: \033[1;34m{order_list_id}\033[0m. Lucro: \033[1;32m${lucro_alvo:.4f}\033[0m, Preço de Parada: \033[1;31m${stop_loss:.4f}\033[0m, Limite de Parada: \033[1;31m${stop_limit:.4f}\033[0m")
                message = f"✅️ Ordem OCO colocada. Moeda: <b>{symbol}</b>. ID: <b>{order_list_id}</b>. Lucro: <b>${lucro_alvo:.4f}</b>, Preço de Parada: <b>${stop_loss:.4f}</b>, Limite de Parada: <b>${stop_limit:.4f}</b>"
                send_telegram_message(bot_token, chat_id, message)
            else:
                print(f"✅️ Ordem OCO colocada. Moeda: \033[1;33m{symbol}\033[0m. ID: \033[1;34m{order_list_id}\033[0m. Lucro: \033[1;32m${lucro_alvo:.2f}\033[0m, Preço de Parada: \033[1;31m${stop_loss:.2f}\033[0m, Limite de Parada: \033[1;31m${stop_limit:.2f}\033[0m")
                message = f"✅️ Ordem OCO colocada. Moeda: <b>{symbol}</b>. ID: <b>{order_list_id}</b>. Lucro: <b>${lucro_alvo:.2f}</b>, Preço de Parada: <b>${stop_loss:.2f}</b>, Limite de Parada: <b>${stop_limit:.2f}</b>"
                send_telegram_message(bot_token, chat_id, message)
            return oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit
        
        except BinanceAPIException as e:
            print(f"Erro na tentativa {attempt + 1}: {e}")
            if "MIN_NOTIONAL" in str(e):
                required_notional = get_min_notional(await client.get_symbol_info(symbol))
                current_notional = current_price * quantity
                new_price, new_quantity = calculate_adjustment(current_price, quantity, required_notional, current_notional)
                current_price = new_price
                quantity = new_quantity
            await asyncio.sleep(0.6)  # Pequena pausa antes de tentar novamente

    print(f"\n🚨 \033[1;31mFalha\033[0m ao colocar a ordem OCO após {max_attempts} tentativas.")
    message = f'<b>🚨 Falha ao colocar a ordem OCO após {max_attempts} tentativas</b>, Moeda: <b>{symbol}</b>'
    send_telegram_message(bot_token, chat_id, message)
    raise Exception("Falha ao colocar ordem OCO")  # Lança uma exceção

def adjust_rsi_levels(result):
    """
    Ajusta os níveis de RSI dinâmicos com base no resultado do trade.
    Args:
        result (str): Resultado da última ordem ('profit' ou 'stop loss').
    """
    global dynamic_rsi_low_0, dynamic_rsi_low_1, dynamic_rsi_low_2, dynamic_rsi_low_3, dynamic_rsi_low_4, dynamic_rsi_low_5

    if result == 'stop loss':
        # Reduz níveis de RSI
        dynamic_rsi_low_0 = max(dynamic_rsi_low_0 - 2, rsi_min_level_0)
        dynamic_rsi_low_1 = max(dynamic_rsi_low_1 - 2, rsi_min_level_1)
        dynamic_rsi_low_2 = max(dynamic_rsi_low_2 - 2, rsi_min_level_2)
        dynamic_rsi_low_3 = max(dynamic_rsi_low_3 - 2, rsi_min_level_3)
        dynamic_rsi_low_4 = max(dynamic_rsi_low_4 - 2, rsi_min_level_4)
        dynamic_rsi_low_5 = max(dynamic_rsi_low_5 - 2, rsi_min_level_5)
    elif result == 'profit':
        # Aumenta níveis de RSI, mas não excede os valores iniciais
        dynamic_rsi_low_0 = min(dynamic_rsi_low_0 + 2, rsi_low_level_0)
        dynamic_rsi_low_1 = min(dynamic_rsi_low_1 + 2, rsi_low_level_1)
        dynamic_rsi_low_2 = min(dynamic_rsi_low_2 + 2, rsi_low_level_2)
        dynamic_rsi_low_3 = min(dynamic_rsi_low_3 + 2, rsi_low_level_3)
        dynamic_rsi_low_4 = min(dynamic_rsi_low_4 + 2, rsi_low_level_4)
        dynamic_rsi_low_5 = min(dynamic_rsi_low_5 + 2, rsi_low_level_5)

    print(f"\033[1mRSI ajustados:\033[0m {dynamic_rsi_low_0}, {dynamic_rsi_low_1}, {dynamic_rsi_low_2}, {dynamic_rsi_low_3}, {dynamic_rsi_low_4}, {dynamic_rsi_low_5}")
    message = f'<b>RSI ajustados:</b> {dynamic_rsi_low_0}, {dynamic_rsi_low_1}, {dynamic_rsi_low_2}, {dynamic_rsi_low_3}, {dynamic_rsi_low_4}, {dynamic_rsi_low_5}'
    send_telegram_message(bot_token, chat_id, message)
