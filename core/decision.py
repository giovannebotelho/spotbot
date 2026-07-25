import asyncio
import math
import pandas as pd
from binance.exceptions import BinanceAPIException
from core.indicators import calculate_moving_average_sell_pressure, calculate_atr, calculate_adx, calculate_ema
from services.binance_client import get_order_book
from services.telegram_notifier import send_telegram_message
from config.settings import TRADING_CONFIG, RSI_CONFIG, OCO_CONFIG, TELEGRAM_CONFIG, ATR_CONFIG, API_KEYS
from services.gemini_ai import analyze_with_gemini, interpret_gemini_response
from services.database import DatabaseManager

pd.set_option('future.no_silent_downcasting', True)

def calculate_dynamic_position_slots(total_usdt, min_usdt_per_slot=10.0):
    """
    Calcula dinamicamente a quantidade de slots e o valor por ordem em USDT.
    Garante rigorosamente que NENHUMA ordem seja inferior a $10.00 USDT.
    Exemplo:
      - Saldo $10-$19: 1 slot de $10-$19.
      - Saldo $30: 3 slots de $10 (ou 2 slots de $15).
      - Saldo $100: 4 slots de $25.
    """
    if total_usdt < min_usdt_per_slot:
        return 0, 0.0
    
    if total_usdt < 20.0:
        return 1, round(total_usdt, 2)
    elif total_usdt < 40.0:
        slots = int(total_usdt // min_usdt_per_slot)
        return slots, round(total_usdt / slots, 2)
    else:
        slots = min(5, int(total_usdt // 20.0))
        if slots < 1: slots = 1
        val_per_slot = round(total_usdt / slots, 2)
        if val_per_slot < min_usdt_per_slot:
            val_per_slot = min_usdt_per_slot
            slots = int(total_usdt // min_usdt_per_slot)
        return slots, val_per_slot

def adjust_rsi_levels(result):
    if result == 'profit':
        for i in range(6):
            RSI_CONFIG['dynamic_low'][i] = RSI_CONFIG['levels'][i]
    elif result == 'stop loss':
        for i in range(6):
            RSI_CONFIG['dynamic_low'][i] = max(RSI_CONFIG['min'][i], RSI_CONFIG['dynamic_low'][i] - 1)

async def should_place_order(client, symbol, sell_pressure_threshold=None, interval=None, limit=None, status_callback=None, silent=False):
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

async def get_historical_trades_data():
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

        df = df.infer_objects(copy=False)
        if "Resultado da Ordem OCO" in df.columns:
            df["Resultado da Ordem OCO"] = df["Resultado da Ordem OCO"].replace({"profit": 1, "stop loss": 0})
        
        if "Padrões de Candle" in df.columns:
            df["Padrões de Candle"] = df["Padrões de Candle"].fillna("Nenhum")
        
        return df.to_string(index=False)
    except Exception as e:
        return f"Erro ao ler histórico do banco de dados: {e}"

async def get_gemini_analysis(candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                              ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data,
                              client, symbol):
    gemini_api_key = API_KEYS.get('gemini')
    if not gemini_api_key: return None

    try:
        return await asyncio.get_running_loop().run_in_executor(
            None,
            analyze_with_gemini,
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
            historical_trades_data,
            gemini_api_key
        )
    except Exception as e:
        print(f"Erro ao obter análise do Gemini: {e}")
        return None

async def should_buy(rsi, trend_is_up, macd_current, signal_line_current, last_close, lower_band, middle_band, upper_band, vwap, candle_patterns, candle_open, candle_high, candle_low, 
                     candle_close, candle_volume, variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, client, symbol, klines, silent=False, config_override=None, klines_4h=None):
    rsi_config = config_override.get('RSI_CONFIG', RSI_CONFIG) if config_override else RSI_CONFIG
    
    rsi_low_level0 = rsi <= rsi_config['dynamic_low'][0]
    rsi_low_level1 = rsi <= rsi_config['dynamic_low'][1]
    rsi_low_level2 = rsi <= rsi_config['dynamic_low'][2]
    rsi_low_level3 = rsi <= rsi_config['dynamic_low'][3]
    rsi_low_level4 = rsi <= rsi_config['dynamic_low'][4]
    rsi_low_level5 = rsi <= rsi_config['dynamic_low'][5]

    macd_bullish = macd_current > signal_line_current and last_close < lower_band
    vwap_tolerance = 0.07
    price_below_vwap = last_close < vwap * (1 + vwap_tolerance)

    use_ema_filter = TRADING_CONFIG.get('use_ema_filter', True)
    if config_override and 'TRADING_CONFIG' in config_override:
        use_ema_filter = config_override['TRADING_CONFIG'].get('use_ema_filter', use_ema_filter)

    trend_confirmed = True
    if use_ema_filter:
        if klines_4h and len(klines_4h) >= 200:
            closes_4h = [float(k[4]) for k in klines_4h]
            ema200_4h = calculate_ema(closes_4h, 200)
            trend_confirmed = last_close > ema200_4h
        elif ema200 > 0:
            trend_confirmed = last_close > ema200
        else:
            trend_confirmed = False

    if not trend_confirmed:
        return {"buy": False, "message": "Tendência Macro não confirmada (Preço < EMA200)", "candle_data": "", "gemini_response": None}

    # Validação de força de tendência via ADX
    adx_val = calculate_adx(klines, period=TRADING_CONFIG.get('adx_period', 14))
    min_adx = TRADING_CONFIG.get('min_adx', 15.0)
    if config_override and 'TRADING_CONFIG' in config_override:
        min_adx = config_override['TRADING_CONFIG'].get('min_adx', min_adx)

    if adx_val < min_adx:
        return {"buy": False, "message": f"Mercado lateralizado (ADX={adx_val:.1f} < {min_adx})", "candle_data": "", "gemini_response": None}

    if rsi > 55:
        return {"buy": False, "message": "RSI alto, compra descartada", "candle_data": "", "gemini_response": None}

    gemini_response = await get_gemini_analysis(
        f"Open: {candle_open}, High: {candle_high}, Low: {candle_low}, Close: {candle_close}, Volume: {candle_volume}",
        candle_patterns,
        rsi,
        f"MACD: {macd_current}, Signal: {signal_line_current}",
        f"Upper: {upper_band}, Middle: {middle_band}, Lower: {lower_band}",
        0,
        {},
        candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, 0.65, 20, 2, 12, 26, 300, 20, 20, 50,
        await get_historical_trades_data(),
        client,
        symbol
    )

    gemini_buy_signal = None
    gemini_analysis_dict = None
    if gemini_response:
        gemini_analysis_dict = interpret_gemini_response(gemini_response)
        if gemini_analysis_dict:
            gemini_buy_signal = gemini_analysis_dict.get('action')

    # Condição 0: Validação Direta da IA Gemini (Se IA aprovou com Confiança)
    if gemini_buy_signal is True and rsi <= 45:
        return {"buy": True, "message": "Aprovado pela IA Gemini", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict}

    # Condições Técnicas Tradicionais (Se IA for neutra ou indisponível)
    if rsi_low_level0 and trend_is_up and macd_bullish and price_below_vwap and ("Hammer" in candle_patterns or "Bullish Engulfing" in candle_patterns):
        return {"buy": True, "message": "RSI L0 + Tendência + MACD + VWAP + Padrão Reversão", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict}

    if rsi_low_level1 and trend_is_up and macd_bullish and price_below_vwap:
        return {"buy": True, "message": "RSI L1 + Tendência + MACD + VWAP", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict}

    if rsi_low_level2 and trend_is_up and price_below_vwap:
        return {"buy": True, "message": "RSI L2 + Tendência + VWAP", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict}

    if rsi_low_level3 and trend_is_up and macd_bullish:
        return {"buy": True, "message": "RSI L3 + Tendência + MACD", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict}

    if rsi_low_level4 and trend_is_up:
        return {"buy": True, "message": "RSI L4 + Tendência de Alta", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict}

    if rsi_low_level5:
        return {"buy": True, "message": "RSI L5 Sobre-vendido Extremo", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict}

    return {"buy": False, "message": "Nenhuma condição de compra atendida", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict}

async def should_sell(rsi, macd_current, signal_line_current, last_close, upper_band, vwap, candle_patterns):
    rsi_high = rsi >= RSI_CONFIG['high']
    macd_bearish = macd_current < signal_line_current and last_close > upper_band
    price_above_vwap = last_close > vwap * 1.05

    if rsi_high and macd_bearish and price_above_vwap:
        return True, "RSI Alto + MACD Baixista + Preço acima da VWAP"
    elif rsi_high:
        return True, "RSI Alto (Sobrecomprado)"
    elif macd_bearish:
        return True, "MACD Baixista + Preço acima da Banda Superior"
    elif "Shooting Star" in candle_patterns or "Bearish Engulfing" in candle_patterns:
        return True, "Padrão de Candlestick Baixista Detectado"

    return False, "Nenhuma condição de venda atendida"

def get_precision(tick_size):
    return int(round(-math.log10(tick_size)))

def adjust_price_to_tick_size(price, tick_size):
    precision = get_precision(tick_size)
    return round(math.floor(price / tick_size) * tick_size, precision)

def get_min_notional(symbol_info):
    for filter in symbol_info['filters']:
        if filter['filterType'] in ['NOTIONAL', 'MIN_NOTIONAL']:
            return float(filter.get('minNotional', filter.get('notional', 10.0)))
    return 10.0

async def calculate_oco_prices(symbol, price, tick_size, klines=None, atr_sl_multiplier=None, atr_tp_multiplier=None):
    if atr_sl_multiplier is None: atr_sl_multiplier = ATR_CONFIG['sl_multiplier']
    if atr_tp_multiplier is None: atr_tp_multiplier = ATR_CONFIG['tp_multiplier']

    use_atr_stop = ATR_CONFIG.get('use_atr_stop', True)

    if use_atr_stop and klines is not None and len(klines) >= ATR_CONFIG['period']:
        atr = calculate_atr(klines)
        stop_loss_distance = atr * atr_sl_multiplier
        target_profit_distance = atr * atr_tp_multiplier

        lucro_alvo = price + target_profit_distance
        stop_loss = price - stop_loss_distance
        stop_limit = stop_loss * (1 - OCO_CONFIG['stop_limit_buffer'])
    else:
        lucro_alvo = price * (1 + OCO_CONFIG['target_profit_percent'])
        stop_loss = price * (1 - OCO_CONFIG['stop_loss_percent'])
        stop_limit = stop_loss * (1 - OCO_CONFIG['stop_limit_buffer'])

    lucro_alvo = adjust_price_to_tick_size(lucro_alvo, tick_size)
    stop_loss = adjust_price_to_tick_size(stop_loss, tick_size)
    stop_limit = adjust_price_to_tick_size(stop_limit, tick_size)

    return lucro_alvo, stop_loss, stop_limit

async def adjust_and_place_oco_order(client, symbol, quantity, tick_size_price, tick_size_stop, klines=None):
    symbol_info = await client.get_symbol_info(symbol)
    step_size = float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'LOT_SIZE')['stepSize'])
    precision_qty = get_precision(step_size)

    adjusted_quantity = round(math.floor(quantity / step_size) * step_size, precision_qty)
    cur_ticker = await client.get_symbol_ticker(symbol=symbol)
    price = float(cur_ticker['price'])

    lucro_alvo, stop_loss, stop_limit = await calculate_oco_prices(symbol, price, tick_size_price, klines)

    precision_price = get_precision(tick_size_price)
    precision_stop = get_precision(tick_size_stop)

    oco_order = await client.create_oco_order(
        symbol=symbol,
        side='SELL',
        quantity=adjusted_quantity,
        price=f"{lucro_alvo:.{precision_price}f}",
        stopPrice=f"{stop_loss:.{precision_stop}f}",
        stopLimitPrice=f"{stop_limit:.{precision_stop}f}",
        stopLimitTimeInForce='GTC'
    )

    limit_order_id = oco_order['orders'][1]['orderId']
    stop_order_id = oco_order['orders'][0]['orderId']

    return oco_order, limit_order_id, stop_order_id, lucro_alvo, stop_loss, stop_limit
