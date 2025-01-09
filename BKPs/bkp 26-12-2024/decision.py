import asyncio
import math
from binance.exceptions import BinanceAPIException

from trading_functions import calculate_moving_average_sell_pressure
from binance_api import get_order_book
from telegram_integration import send_telegram_message
from config import bot_token, chat_id
from config import lucro_multiplier_1, stop_loss_multiplier_1, lucro_multiplier_2, stop_loss_multiplier_2
from config import rsi_low_level_0, rsi_low_level_1, rsi_low_level_2, rsi_low_level_3, rsi_high_0
from config import SELL_PRESSURE_THRESHOLD_1
from config import interval, limit #importar interval e limit
from config import (
    dynamic_rsi_low_0, dynamic_rsi_low_1, dynamic_rsi_low_2, dynamic_rsi_low_3,
    rsi_low_level_0, rsi_low_level_1, rsi_low_level_2, rsi_low_level_3
)

async def should_place_order(client, symbol, SELL_PRESSURE_THRESHOLD = SELL_PRESSURE_THRESHOLD_1, interval=interval, limit=limit): # 🟣🟣
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
        await asyncio.sleep(1)
        # Limpa a linha anterior
        print("\033[2K\r", end='')
        await asyncio.sleep(0.2)
    return False

def should_buy(rsi, trend_is_up, candle_decision, macd_current, signal_line_current, last_close, lower_band, vwap):
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
    Returns:
        bool: True se as condições forem favoráveis para compra, False caso contrário.
    """
    rsi_low_level0 = rsi <= rsi_low_level_0
    rsi_low_level1 = rsi <= rsi_low_level_1
    rsi_low_level2 = rsi <= rsi_low_level_2
    rsi_low_level3 = rsi <= rsi_low_level_3
    macd_bullish = macd_current > signal_line_current and last_close < lower_band
    price_below_vwap = last_close < vwap
    
    if (rsi < rsi_low_level_0 - 2):
        print("\nEntrando na condição 1 de compra do RSI_lvl0")
        message = "Entrando na <b>condição 1</b> de compra do <b>RSI_lvl0</b>"
        send_telegram_message(bot_token, chat_id, message)
        return "RSI_lvl0 - 2"

    elif rsi_low_level1 and trend_is_up and price_below_vwap:
        print("\nEntrando na condição 2 de compra do RSI_lvl1, tendência e VWAP")
        message = "Entrando na <b>condição 2</b> de compra do <b>RSI_lvl1, tendência e VWAP</b>"
        send_telegram_message(bot_token, chat_id, message)
        return "RSI_lvl1, tendência e VWAP"
    
    elif rsi_low_level2 and candle_decision == 'buy' and price_below_vwap:
        print("\nEntrando na condição 3 de compra do RSI_lvl2, candles e VWAP")
        message = "Entrando na <b>condição 3</b> de compra do <b>RSI_lvl2, candles e VWAP</b>"
        send_telegram_message(bot_token, chat_id, message)
        return "RSI_lvl2, candles e VWAP"

    elif rsi_low_level3 and trend_is_up and candle_decision == 'buy' and price_below_vwap:
        print("\nEntrando na condição 4 de compra do RSI_lvl3, tendência, candles e VWAP")
        message = "Entrando na <b>condição 4</b> de compra do <b>RSI_lvl3, tendência, candles e VWAP</b>"
        send_telegram_message(bot_token, chat_id, message)
        return "RSI_lvl3, tendência, candles e VWAP"

    elif macd_bullish and price_below_vwap:
        print("\nEntrando na condição 5 de compra com macd e VWAP")
        message = "Entrando na <b>condição 5</b> de compra com <b>macd e VWAP</b>"
        send_telegram_message(bot_token, chat_id, message)
        return "MACD e VWAP"
    
    elif rsi_low_level0 and price_below_vwap :
        print("\nEntrando na condição 6 de compra do RSI_lvl0 sem tendencia e com VWAP")
        message = "Entrando na <b>condição 6</b> de compra do <b>RSI_lvl0 sem tendencia e com VWAP</b>"
        send_telegram_message(bot_token, chat_id, message)
        return "RSI_lvl0 e VWAP"
      
    elif rsi_low_level1 and price_below_vwap:
        print("\nEntrando na condição 7 de compra do RSI_lvl1 sem tendencia e com VWAP")
        message = "Entrando na <b>condição 7</b> de compra do <b>RSI_lvl1 sem tendencia e com VWAP</b>"
        send_telegram_message(bot_token, chat_id, message)
        return "RSI_lvl1 e VWAP"

    elif rsi_low_level2 and price_below_vwap:
        print("\nEntrando na condição 8 de compra do RSI_lvl2, sem candle e VWAP")
        message = "Entrando na <b>condição 8</b> de compra do <b>RSI_lvl2, sem candle e VWAP</b>"
        send_telegram_message(bot_token, chat_id, message)
        return "RSI_lvl2 e VWAP"

    elif macd_bullish:
        print("\nEntrando na condição 9 de compra com macd (sem vwap)")
        message = "Entrando na <b>condição 9</b> de compra com <b>macd</b>"
        send_telegram_message(bot_token, chat_id, message)
        return "MACD"

    return False

def should_sell(rsi, trend_is_up, candle_decision, macd_current, signal_line_current, last_close, lower_band, vwap):
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
    rsi_high = rsi >= rsi_high_0  # 🟣🟣
    macd_bearish = macd_current < signal_line_current and last_close > lower_band
    
    price_above_vwap = last_close > vwap

    return (rsi_high and not trend_is_up) or (rsi_high and candle_decision == 'sell') or macd_bearish or price_above_vwap

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
            adjusted_quantity = adjust_quantity_to_lot_size(quantity, await client.get_symbol_info(symbol))

            lucro_multiplier = lucro_multiplier_1 if current_price < 1 else lucro_multiplier_2  # Ajuste conforme necessário
            stop_loss_multiplier = stop_loss_multiplier_1 if current_price < 1 else stop_loss_multiplier_2  # Ajuste conforme necessário

            lucro_alvo = adjust_price_to_tick_size(current_price * lucro_multiplier, tick_size)
            stop_loss = adjust_price_to_tick_size(current_price * stop_loss_multiplier, tick_size)
            stop_limit = adjust_price_to_tick_size(stop_loss - (20 * min_price_move), tick_size)  # Garante que stop_limit também esteja no tick size correto

            oco_order = await client.create_oco_order(
                symbol=symbol,
                side="SELL",
                quantity=f"{adjusted_quantity:.6f}",
                price=f"{lucro_alvo:.2f}",
                stopPrice=f"{stop_loss:.2f}",
                stopLimitPrice=f"{stop_limit:.2f}",
                stopLimitTimeInForce='GTC'
            )
            
            order_list_id = oco_order.get('orderListId', 'N/A')  # Acessa o ID da ordem OCO, se disponível

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
    return None

def adjust_rsi_levels(result):
    """
    Ajusta os níveis de RSI dinâmicos com base no resultado do trade.
    Args:
        result (str): Resultado da última ordem ('profit' ou 'stop loss').
    """
    global dynamic_rsi_low_0, dynamic_rsi_low_1, dynamic_rsi_low_2, dynamic_rsi_low_3

    if result == 'stop loss':
        # Reduz níveis de RSI
        dynamic_rsi_low_0 = max(dynamic_rsi_low_0 - 1, 10)
        dynamic_rsi_low_1 = max(dynamic_rsi_low_1 - 1, 15)
        dynamic_rsi_low_2 = max(dynamic_rsi_low_2 - 1, 20)
        dynamic_rsi_low_3 = max(dynamic_rsi_low_3 - 1, 25)
    elif result == 'profit':
        # Aumenta níveis de RSI, mas não excede os valores iniciais
        dynamic_rsi_low_0 = min(dynamic_rsi_low_0 + 2, rsi_low_level_0)
        dynamic_rsi_low_1 = min(dynamic_rsi_low_1 + 2, rsi_low_level_1)
        dynamic_rsi_low_2 = min(dynamic_rsi_low_2 + 2, rsi_low_level_2)
        dynamic_rsi_low_3 = min(dynamic_rsi_low_3 + 2, rsi_low_level_3)

    print(f"\033[1mRSI ajustados:\033[0m {dynamic_rsi_low_0}, {dynamic_rsi_low_1}, {dynamic_rsi_low_2}, {dynamic_rsi_low_3}")
    message = f'<b>RSI ajustados:</b> {dynamic_rsi_low_0}, {dynamic_rsi_low_1}, {dynamic_rsi_low_2}, {dynamic_rsi_low_3}'
    send_telegram_message(bot_token, chat_id, message)
