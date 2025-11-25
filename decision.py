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
from config import TRADING_CONFIG, RSI_CONFIG, OCO_CONFIG, TELEGRAM_CONFIG, ATR_CONFIG, API_KEYS
from gemini_analysis import analyze_with_gemini, interpret_gemini_response

pd.set_option('future.no_silent_downcasting', True)

async def should_place_order(client, symbol, sell_pressure_threshold=None, interval=None, limit=None, status_callback=None, silent=False):
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
        return True
    else:
        if not silent:
            if status_callback:
                status_callback(msg)
            else:
                print(f"\r{msg}", end='', flush=True)
        await asyncio.sleep(0.6)
        await asyncio.sleep(0.15)
    return False

async def should_buy(rsi, trend_is_up, macd_current, signal_line_current, last_close, lower_band, middle_band, upper_band, vwap, candle_patterns, candle_open, candle_high, candle_low, 
                     candle_close, candle_volume, variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, client, symbol, klines, silent=False, config_override=None):
    """
    Avalia se as condições são adequadas para comprar.
    """
    # Use config override if provided
    rsi_config = config_override.get('RSI_CONFIG', RSI_CONFIG) if config_override else RSI_CONFIG
    
    # Use dynamic RSI levels
    rsi_low_level0 = rsi <= rsi_config['dynamic_low'][0]
    rsi_low_level1 = rsi <= rsi_config['dynamic_low'][1]
    rsi_low_level2 = rsi <= rsi_config['dynamic_low'][2]
    rsi_low_level3 = rsi <= rsi_config['dynamic_low'][3]
    rsi_low_level4 = rsi <= rsi_config['dynamic_low'][4]
    rsi_low_level5 = rsi <= rsi_config['dynamic_low'][5]

    macd_bullish = macd_current > signal_line_current and last_close < lower_band
    vwap_tolerance = 0.07
    price_below_vwap = last_close < vwap * (1 + vwap_tolerance)

    # Prepare data for Gemini
    gemini_response = await get_gemini_analysis(
        f"Open: {candle_open}, High: {candle_high}, Low: {candle_low}, Close: {candle_close}, Volume: {candle_volume}",
        candle_patterns,
        rsi,
        f"MACD: {macd_current}, Signal: {signal_line_current}",
        f"Upper: {upper_band}, Middle: {middle_band}, Lower: {lower_band}",
        0,
        {},
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
        await get_historical_trades_data(),
        client,
        symbol
    )

    if gemini_response:
        gemini_buy_signal = interpret_gemini_response(gemini_response)
    else:
        gemini_buy_signal = None

    if rsi_low_level0:
        if not silent:
            print("\nEntrando na condição 0 de compra do RSI considerado muito baixo")
            message = "Entrando na <b>condição 0</b> de compra do <b>RSI considerado muito baixo</b>"
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        return {"buy": True, "message": "RSI_lvl0", "candle_data": "", "gemini_response": None}

    elif rsi_low_level1 and price_below_vwap:
        if not silent:
            print("\nEntrando na condição 1 de compra do RSI considerado baixo e considerando o indicador VWAP")
            message = "Entrando na <b>condição 1</b> de compra do <b>RSI considerado baixo e considerando o indicador VWAP</b>"
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        return {"buy": True, "message": "RSI_lvl1 e VWAP", "candle_data": "", "gemini_response": None}

    elif rsi_low_level2 and candle_patterns:
        if not silent:
            print("\nEntrando na condição 2 de compra do RSI considerado médio e considerando padrões de Candle")
            message = "Entrando na <b>condição 2</b> de compra do <b>RSI considerado médio e considerando padrões de Candle</b>"
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        return {"buy": True, "message": "RSI_lvl2 e candles", "candle_data": "", "gemini_response": None}

    elif rsi_low_level3 and price_below_vwap:
        if not silent:
            print("\nEntrando na condição 3 de compra do RSI considerado médio-alto considerando tendências de alta e o indicador VWAP")
            message = "Entrando na <b>condição 3</b> de compra do <b>RSI considerado médio-alto considerando tendências de alta e o indicador VWAP</b>"
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        return {"buy": True, "message": "RSI_lvl3, tendência e VWAP", "candle_data": "", "gemini_response": None}

    elif rsi_low_level4 and price_below_vwap and macd_bullish:
        if not silent:
            print("\nEntrando na condição 4 de compra do RSI considerado alto considerando tendências de alta, indicador VWAP e MACD")
            message = "Entrando na <b>condição 4</b> de compra do <b>RSI considerado alto considerando tendências de alta, indicador VWAP e MACD</b>"
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        return {"buy": True, "message": "RSI_lvl4, tendência, VWAP e MACD", "candle_data": "", "gemini_response": None}

    elif gemini_buy_signal and rsi_low_level5:
        if not silent:
            print("\nEntrando na condição 5 de compra: Sinal de COMPRA do Gemini e RSI")
            message = "Entrando na <b>condição 5</b> de compra: <b>Sinal de COMPRA do Gemini e RSI</b>"
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
        return {"buy": True, "message": "Gemini Buy Signal e RSI", "candle_data": "", "gemini_response": gemini_response}

    return {"buy": False, "message": None, "candle_data": "", "gemini_response": gemini_response}

async def get_gemini_analysis(candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                              ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data,
                              client, symbol):
    """Função auxiliar para obter a análise do Gemini."""
    gemini_api_key = API_KEYS['gemini']
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

async def adjust_and_place_oco_order(client, symbol, quantity, tick_size, min_price_move, klines, silent=False, config_override=None):
    """
    Calcula preços e coloca ordem OCO.
    """
    # Use config override if provided
    atr_config = config_override.get('ATR_CONFIG', ATR_CONFIG) if config_override else ATR_CONFIG
    oco_config = config_override.get('OCO_CONFIG', OCO_CONFIG) if config_override else OCO_CONFIG

    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            # Validate balance
            symbol_info = await client.get_symbol_info(symbol)
            base_asset = symbol_info['baseAsset']
            balance_info = await client.get_asset_balance(asset=base_asset)
            free_balance = float(balance_info['free'])

            if quantity > free_balance:
                if not silent: print(f"⚠️ Quantidade ajustada ao saldo real: {quantity} -> {free_balance}")
                quantity = free_balance

            quantity = adjust_quantity_to_lot_size(quantity, symbol_info)

            order_book = await get_order_book(client, symbol)
            current_price = float(order_book['asks'][0][0])

            # Calculate ATR
            atr = calculate_atr(klines, atr_config['period'])
            
            use_atr = atr_config.get('use_atr_stop', False)
            
            if use_atr and atr > 0:
                lucro_alvo = current_price + (atr * atr_config['tp_multiplier'])
                stop_loss = current_price - (atr * atr_config['sl_multiplier'])
                
                if not silent: print(f"🔹 Usando ATR para SL/TP. ATR: {atr:.4f}, TP: {lucro_alvo:.4f}, SL: {stop_loss:.4f}")
                
            else:
                # Fixed Percentage Logic (Fallback)
                if use_atr and not silent:
                    print("🔸 ATR inválido ou insuficiente. Usando multiplicadores fixos.")
                
                if current_price < 1:
                    lucro_multiplier = oco_config['price_under_1']['profit_multiplier']
                    stop_loss_multiplier = oco_config['price_under_1']['stop_loss_multiplier']
                else:
                    lucro_multiplier = oco_config['price_over_1']['profit_multiplier']
                    stop_loss_multiplier = oco_config['price_over_1']['stop_loss_multiplier']

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
            
            # If silent (backtest), we don't actually place the order on Binance
            if silent:
                return {
                    'orderListId': 'SIMULATED',
                    'orders': [{'orderId': 'SIM_STOP'}, {'orderId': 'SIM_LIMIT'}]
                }, 'SIM_LIMIT', 'SIM_STOP', lucro_alvo, stop_loss, stop_limit

            oco_order = await client.create_oco_order(
                symbol=symbol,
                side='SELL',
                quantity=quantity,
                price=f"{lucro_alvo:.{get_precision(tick_size)}f}",
                stopPrice=f"{stop_loss:.{get_precision(tick_size)}f}",
                stopLimitPrice=f"{stop_limit:.{get_precision(tick_size)}f}",
                stopLimitTimeInForce='GTC'
            )

            order_list_id = oco_order.get('orderListId', 'N/A')
            limit_order_id = oco_order['orders'][1]['orderId']
            stop_order_id = oco_order['orders'][0]['orderId']
            
            message = f"✅️ Ordem OCO colocada. Moeda: <b>{symbol}</b>. ID: <b>{order_list_id}</b>. Lucro: <b>${lucro_alvo:.4f}</b>, Preço de Parada: <b>${stop_loss:.4f}</b>"
            print(f"✅️ Ordem OCO colocada: {symbol}")
            asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
            
            return oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit
        
        except BinanceAPIException as e:
            if not silent: print(f"Erro na tentativa {attempt + 1}: {e}")
            if "MIN_NOTIONAL" in str(e):
                required_notional = get_min_notional(await client.get_symbol_info(symbol))
                current_notional = current_price * quantity
                new_price, new_quantity = calculate_adjustment(current_price, quantity, required_notional, current_notional)
                current_price = new_price
                quantity = new_quantity
            await asyncio.sleep(0.6)

    if not silent:
        print(f"\n🚨 Falha ao colocar a ordem OCO após {max_attempts} tentativas.")
        message = f'<b>🚨 Falha ao colocar a ordem OCO após {max_attempts} tentativas</b>, Moeda: <b>{symbol}</b>'
        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))
    raise Exception("Falha ao colocar ordem OCO")

def adjust_rsi_levels(result, silent=False):
    """
    Ajusta os níveis de RSI dinâmicos.
    """
    if result == 'stop loss':
        for i in range(6):
            RSI_CONFIG['dynamic_low'][i] = max(RSI_CONFIG['dynamic_low'][i] - 2, RSI_CONFIG['min'][i])
    elif result == 'profit':
        for i in range(6):
            RSI_CONFIG['dynamic_low'][i] = min(RSI_CONFIG['dynamic_low'][i] + 2, RSI_CONFIG['levels'][i])

    if not silent:
        print(f"\033[1mRSI ajustados:\033[0m {list(RSI_CONFIG['dynamic_low'].values())}")
        message = f"<b>RSI ajustados:</b> {list(RSI_CONFIG['dynamic_low'].values())}"
        asyncio.create_task(send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message))

from database import DatabaseManager

async def get_historical_trades_data():
    """
    Lê os dados do banco de dados SQLite.
    """
    try:
        db = DatabaseManager()
        df = db.get_recent_trades(limit=20)
        
        if df.empty:
            return "Nenhum dado histórico disponível."

        cols_to_keep = ["Símbolo", "Preço de Compra", "VWAP", "Data/Hora da Compra", "Resultado da Ordem OCO", "Data/Hora OCO",
                 "RSI da operação", "Condição Atendida", "Intervalo de tempo (Candles)", "Padrões de Candle", 
                 "Tendência de Alta"]
        
        existing_cols = [col for col in cols_to_keep if col in df.columns]
        df = df[existing_cols]

        # No need to tail(20) as get_recent_trades already limits

        df = df.infer_objects(copy=False)
        if "Resultado da Ordem OCO" in df.columns:
            df["Resultado da Ordem OCO"] = df["Resultado da Ordem OCO"].replace({"profit": 1, "stop loss": 0})
        
        if "Padrões de Candle" in df.columns:
            df["Padrões de Candle"] = df["Padrões de Candle"].fillna("Nenhum")
        
        return df.to_string(index=False)

    except Exception as e:
        return f"Erro ao ler histórico do banco de dados: {e}"

def get_precision(tick_size):
    return int(-math.log10(tick_size))
