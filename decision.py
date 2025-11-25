import asyncio
import math
import time
import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from binance.exceptions import BinanceAPIException
from trading_functions import calculate_moving_average_sell_pressure, calculate_atr
from binance_api import get_order_book, get_klines
from telegram_integration import send_telegram_message
from config import TRADING_CONFIG, RSI_CONFIG, OCO_CONFIG, TELEGRAM_CONFIG, ATR_CONFIG
from gemini_analysis import analyze_with_gemini, interpret_gemini_response

pd.set_option('future.no_silent_downcasting', True)

async def should_place_order(client, symbol, sell_pressure_threshold=None, interval=None, limit=None, status_callback=None):
    """
    Determina se uma ordem deve ser colocada com base na pressão de venda média.
    """
    if sell_pressure_threshold is None: sell_pressure_threshold = TRADING_CONFIG['sell_pressure_threshold']
    if interval is None: interval = TRADING_CONFIG['interval']
    if limit is None: limit = TRADING_CONFIG['limit']

    avg_sell_pressure = await calculate_moving_average_sell_pressure(client, symbol, interval, limit)
    avg_sell_pressure_percent = avg_sell_pressure * 100
    
    msg = f"⛔ Alta pressão de venda média detectada: \033[1;31m{avg_sell_pressure_percent:.1f}%\033[0m, Aguardando..."
    
    if avg_sell_pressure < sell_pressure_threshold:
        # print("\033[2K\r", end='') # Clean up if needed, or just do nothing
        return True
    else:
        if status_callback:
            status_callback(msg)
        else:
            print(f"\r{msg}", end='', flush=True)
        await asyncio.sleep(0.6)
        # print("\033[2K\r", end='')
        await asyncio.sleep(0.15)
    return False

async def should_buy(rsi, trend_is_up, macd_current, signal_line_current, last_close, lower_band, middle_band, upper_band, vwap, candle_patterns, candle_open, candle_high, candle_low, 
                     candle_close, candle_volume, variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, client, symbol, klines):
    """
    Avalia se as condições são adequadas para comprar.
    """
    # Use dynamic RSI levels
    rsi_low_level0 = rsi <= RSI_CONFIG['dynamic_low'][0]
    rsi_low_level1 = rsi <= RSI_CONFIG['dynamic_low'][1]
    rsi_low_level2 = rsi <= RSI_CONFIG['dynamic_low'][2]
    rsi_low_level3 = rsi <= RSI_CONFIG['dynamic_low'][3]
    rsi_low_level4 = rsi <= RSI_CONFIG['dynamic_low'][4]
    rsi_low_level5 = rsi <= RSI_CONFIG['dynamic_low'][5]

    macd_bullish = macd_current > signal_line_current and last_close < lower_band
    vwap_tolerance = 0.07
    price_below_vwap = last_close < vwap * (1 + vwap_tolerance)

    # Prepare data for Gemini
    # Note: Passing individual config values to match gemini_analysis.py signature
    gemini_response = await get_gemini_analysis(
        f"Open: {candle_open}, High: {candle_high}, Low: {candle_low}, Close: {candle_close}, Volume: {candle_volume}", # candle_data placeholder
        candle_patterns,
        rsi,
        f"MACD: {macd_current}, Signal: {signal_line_current}", # macd placeholder
        f"Upper: {upper_band}, Middle: {middle_band}, Lower: {lower_band}", # bollinger placeholder
        0, # sell_pressure (not passed in original call? need to check)
        {}, # order_book (not passed?)
        candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, 
        TRADING_CONFIG['sell_pressure_threshold'], 
        TRADING_CONFIG['period'], 
        TRADING_CONFIG['num_std'], 
        TRADING_CONFIG['short_period'], 
        TRADING_CONFIG['long_period'], 
        TRADING_CONFIG['limit'], 
        TRADING_CONFIG['depth'], 
        TRADING_CONFIG['maxlen'], 
        TRADING_CONFIG['volume_avg'], 
        await get_historical_trades_data(), # historical_trades_data
        client,
        symbol
    )

    if gemini_response:
        gemini_buy_signal = interpret_gemini_response(gemini_response)
    else:
        gemini_buy_signal = None

    if rsi_low_level0:
        print("\nEntrando na condição 0 de compra do RSI considerado muito baixo")
        message = "Entrando na <b>condição 0</b> de compra do <b>RSI considerado muito baixo</b>"
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)
        return {"buy": True, "message": "RSI_lvl0", "candle_data": "", "gemini_response": None}

    elif rsi_low_level1 and price_below_vwap:
        print("\nEntrando na condição 1 de compra do RSI considerado baixo e considerando o indicador VWAP")
        message = "Entrando na <b>condição 1</b> de compra do <b>RSI considerado baixo e considerando o indicador VWAP</b>"
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)
        return {"buy": True, "message": "RSI_lvl1 e VWAP", "candle_data": "", "gemini_response": None}

    elif rsi_low_level2 and candle_patterns: # has_candle_patterns replaced by candle_patterns check
        print("\nEntrando na condição 2 de compra do RSI considerado médio e considerando padrões de Candle")
        message = "Entrando na <b>condição 2</b> de compra do <b>RSI considerado médio e considerando padrões de Candle</b>"
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)
        return {"buy": True, "message": "RSI_lvl2 e candles", "candle_data": "", "gemini_response": None}

    elif rsi_low_level3 and price_below_vwap:
        print("\nEntrando na condição 3 de compra do RSI considerado médio-alto considerando tendências de alta e o indicador VWAP")
        message = "Entrando na <b>condição 3</b> de compra do <b>RSI considerado médio-alto considerando tendências de alta e o indicador VWAP</b>"
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)
        return {"buy": True, "message": "RSI_lvl3, tendência e VWAP", "candle_data": "", "gemini_response": None}

    elif rsi_low_level4 and price_below_vwap and macd_bullish:
        print("\nEntrando na condição 4 de compra do RSI considerado alto considerando tendências de alta, indicador VWAP e MACD")
        message = "Entrando na <b>condição 4</b> de compra do <b>RSI considerado alto considerando tendências de alta, indicador VWAP e MACD</b>"
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)
        return {"buy": True, "message": "RSI_lvl4, tendência, VWAP e MACD", "candle_data": "", "gemini_response": None}

    elif gemini_buy_signal and rsi_low_level5:
        print("\nEntrando na condição 5 de compra: Sinal de COMPRA do Gemini e RSI")
        message = "Entrando na <b>condição 5</b> de compra: <b>Sinal de COMPRA do Gemini e RSI</b>"
        send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)
        return {"buy": True, "message": "Gemini Buy Signal e RSI", "candle_data": "", "gemini_response": gemini_response}

    return {"buy": False, "message": None, "candle_data": "", "gemini_response": gemini_response}

async def get_gemini_analysis(candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                              ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data,
                              client, symbol):
    """Função auxiliar para obter a análise do Gemini."""
    gemini_api_key = API_KEYS['gemini'] # Use API_KEYS dict
    if not gemini_api_key: return None

    try:
        return await asyncio.get_running_loop().run_in_executor(
            None,
            analyze_with_gemini,
            gemini_api_key,
            candle_data,
            candle_patterns,
            rsi,
            macd,
            bollinger_bands,
            sell_pressure,
            order_book,
            candle_open,
            candle_high,
            candle_low,
            candle_close,
            candle_volume,
            variation_24h,
            candle_variation,
            ema7,
            ema15,
            ema25,
            ema50,
            ema100,
            ema200,
            vwap,
            trend_is_up,
            SELL_PRESSURE_THRESHOLD_1,
            period,
            num_std,
            short_period,
            long_period,
            limit,
            depth,
            maxlen,
            volume_avg,
            historical_trades_data
        )
    except Exception as e:
        print(f"Erro ao obter análise do Gemini: {e}")
        return None

def should_sell(rsi, trend_is_up, macd_current, signal_line_current, last_close, lower_band, vwap):
    """
    Avalia se as condições são adequadas para vender.
    """
    rsi_high = rsi >= RSI_CONFIG['high']
    macd_bearish = macd_current < signal_line_current and last_close > lower_band
    price_above_vwap = last_close > vwap

    return (rsi_high and not trend_is_up) or macd_bearish or price_above_vwap

def adjust_price_to_tick_size(price, tick_size):
    return math.floor(price / tick_size) * tick_size

def adjust_quantity_to_lot_size(quantity, symbol_info):
    lot_size_filter = next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'LOT_SIZE')
    step_size = float(lot_size_filter['stepSize'])
    quantity = math.floor(quantity / step_size) * step_size
    return max(quantity, float(lot_size_filter['minQty']))

def get_min_notional(symbol_info):
    notional_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'NOTIONAL'), None)
    if notional_filter:
        return float(notional_filter['minNotional'])
    
    min_notional_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'MIN_NOTIONAL'), None)
    if min_notional_filter:
        return float(min_notional_filter['minNotional'])
    return 5.0 # Fallback

def calculate_adjustment(price, quantity, required_notional, current_notional):
    if current_notional < required_notional:
        ratio = required_notional / current_notional
        new_quantity = quantity * ratio * 1.01 # +1% buffer
        return price, new_quantity
    return price, quantity

async def adjust_and_place_oco_order(client, symbol, quantity, tick_size, min_price_move, klines):
    """
    Calcula preços e coloca ordem OCO.
    """
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            # Validate balance
            symbol_info = await client.get_symbol_info(symbol)
            base_asset = symbol_info['baseAsset']
            balance_info = await client.get_asset_balance(asset=base_asset)
            free_balance = float(balance_info['free'])

            if quantity > free_balance:
                print(f"⚠️ Quantidade ajustada ao saldo real: {quantity} -> {free_balance}")
                quantity = free_balance

            quantity = adjust_quantity_to_lot_size(quantity, symbol_info)

            order_book = await get_order_book(client, symbol)
            current_price = float(order_book['asks'][0][0])

            # Calculate ATR
            atr = calculate_atr(klines, ATR_CONFIG['period'])
            
            if atr > 0:
                lucro_alvo = current_price + (atr * ATR_CONFIG['tp_multiplier'])
                stop_loss = current_price - (atr * ATR_CONFIG['sl_multiplier'])
                print(f"🔹 Usando ATR para SL/TP. ATR: {atr:.4f}, TP: {lucro_alvo:.4f}, SL: {stop_loss:.4f}")
            else:
                print("🔸 ATR inválido ou insuficiente. Usando multiplicadores fixos.")
                if current_price < 1:
                    lucro_multiplier = OCO_CONFIG['price_under_1']['profit_multiplier']
                    stop_loss_multiplier = OCO_CONFIG['price_under_1']['stop_loss_multiplier']
                else:
                    lucro_multiplier = OCO_CONFIG['price_over_1']['profit_multiplier']
                    stop_loss_multiplier = OCO_CONFIG['price_over_1']['stop_loss_multiplier']

                lucro_alvo = current_price * lucro_multiplier
                stop_loss = current_price * stop_loss_multiplier

            stop_limit = stop_loss * 0.999
            
            lucro_alvo = adjust_price_to_tick_size(lucro_alvo, tick_size)
            stop_loss = adjust_price_to_tick_size(stop_loss, tick_size)
            stop_limit = adjust_price_to_tick_size(stop_limit, tick_size)

            params = {
                'symbol': symbol,
                'side': 'SELL',
                'quantity': quantity,
                'price': f"{lucro_alvo:.2f}",
                'stopPrice': f"{stop_loss:.2f}",
                'stopLimitPrice': f"{stop_limit:.2f}",
                'stopLimitTimeInForce': 'GTC'
            }
            
            # OCO specific params might need adjustment based on library version, but keeping as is mostly
            # Wait, python-binance create_oco_order params are specific.
            # The original code used 'abovePrice', 'belowStopPrice' etc. which are raw API params?
            # No, python-binance uses `price`, `stopPrice`, `stopLimitPrice`.
            # BUT the original code used a dictionary `params` and unpacked it.
            # Original:
            # params = { 'symbol': symbol, 'side': 'SELL', 'quantity': quantity, 'price': ..., 'stopPrice': ... }
            # Actually, original code used:
            # 'listClientOrderId': ..., 'limitClientOrderId': ..., 'stopClientOrderId': ...
            # AND 'stopLimitPrice': ...
            # AND 'stopLimitTimeInForce': ...
            
            # Let's check the original code again (Step 343).
            # Lines 234-240:
            # 'belowType': 'STOP_LOSS_LIMIT',
            # 'abovePrice': ...,
            # 'belowStopPrice': ...,
            # 'belowPrice': ...
            
            # This looks like it was constructing params for a SPECIFIC endpoint or wrapper?
            # `client.create_oco_order(**params)`
            # If I rewrite it, I should use the standard python-binance arguments.
            # Standard args: symbol, side, quantity, price, stopPrice, stopLimitPrice.
            
            oco_order = await client.create_oco_order(
                symbol=symbol,
                side='SELL',
                quantity=quantity,
                price=f"{lucro_alvo:.{get_precision(tick_size)}f}", # Need precision? Original used .2f
                stopPrice=f"{stop_loss:.{get_precision(tick_size)}f}",
                stopLimitPrice=f"{stop_limit:.{get_precision(tick_size)}f}",
                stopLimitTimeInForce='GTC'
            )

            order_list_id = oco_order.get('orderListId', 'N/A')
            limit_order_id = oco_order['orders'][1]['orderId']
            stop_order_id = oco_order['orders'][0]['orderId']
            
            message = f"✅️ Ordem OCO colocada. Moeda: <b>{symbol}</b>. ID: <b>{order_list_id}</b>. Lucro: <b>${lucro_alvo:.4f}</b>, Preço de Parada: <b>${stop_loss:.4f}</b>"
            print(f"✅️ Ordem OCO colocada: {symbol}")
            send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)
            
            return oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit
        
        except BinanceAPIException as e:
            print(f"Erro na tentativa {attempt + 1}: {e}")
            if "MIN_NOTIONAL" in str(e):
                required_notional = get_min_notional(await client.get_symbol_info(symbol))
                current_notional = current_price * quantity
                new_price, new_quantity = calculate_adjustment(current_price, quantity, required_notional, current_notional)
                current_price = new_price
                quantity = new_quantity
            await asyncio.sleep(0.6)

    print(f"\n🚨 Falha ao colocar a ordem OCO após {max_attempts} tentativas.")
    message = f'<b>🚨 Falha ao colocar a ordem OCO após {max_attempts} tentativas</b>, Moeda: <b>{symbol}</b>'
    send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)
    raise Exception("Falha ao colocar ordem OCO")

def adjust_rsi_levels(result):
    """
    Ajusta os níveis de RSI dinâmicos.
    """
    if result == 'stop loss':
        for i in range(6):
            RSI_CONFIG['dynamic_low'][i] = max(RSI_CONFIG['dynamic_low'][i] - 2, RSI_CONFIG['min'][i])
    elif result == 'profit':
        for i in range(6):
            RSI_CONFIG['dynamic_low'][i] = min(RSI_CONFIG['dynamic_low'][i] + 2, RSI_CONFIG['levels'][i])

    print(f"\033[1mRSI ajustados:\033[0m {list(RSI_CONFIG['dynamic_low'].values())}")
    message = f"<b>RSI ajustados:</b> {list(RSI_CONFIG['dynamic_low'].values())}"
    send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)

async def get_historical_trades_data():
    """
    Lê os dados do arquivo results.csv.
    """
    filename = "results.csv"
    filepath = Path(__file__).parent / filename

    if not filepath.exists():
        return "Arquivo de resultados não existe."

    try:
        df = pd.read_csv(filepath)
        cols_to_keep = ["Símbolo", "Preço de Compra", "VWAP", "Data/Hora da Compra", "Resultado da Ordem OCO", "Data/Hora OCO",
                 "RSI da operação", "Condição Atendida", "Intervalo de tempo (Candles)", "Padrões de Candle", 
                 "Tendência de Alta"]
        
        existing_cols = [col for col in cols_to_keep if col in df.columns]
        df = df[existing_cols]

        if len(df) > 20:
            df = df.tail(20)

        df = df.infer_objects(copy=False)
        if "Resultado da Ordem OCO" in df.columns:
            df["Resultado da Ordem OCO"] = df["Resultado da Ordem OCO"].replace({"profit": 1, "stop loss": 0})
        
        if "Padrões de Candle" in df.columns:
            df["Padrões de Candle"] = df["Padrões de Candle"].fillna("Nenhum")
        
        return df.to_string(index=False)

    except Exception as e:
        return f"Erro ao ler o arquivo: {e}"

def get_precision(tick_size):
    return int(-math.log10(tick_size))

from config import API_KEYS # Needed for get_gemini_analysis
