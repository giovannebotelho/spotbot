import asyncio
import json
import re
from datetime import datetime
import pandas as pd

from config.settings import API_KEYS, TRADING_CONFIG, RSI_CONFIG
from services.binance_client import get_order_details, get_futures_analytics
from core.indicators import (
    detect_market_regime, detect_liquidity_sweep, calculate_ema, calculate_adx,
    analyze_futures_squeeze_potential
)
from services.gemini_ai import analyze_with_gemini
from services.database import DatabaseManager

db = DatabaseManager()

def adjust_price_to_tick_size(price, tick_size):
    precision = get_precision(tick_size)
    return round(price, precision)

def get_precision(tick_size):
    tick_str = f"{tick_size:.10f}".rstrip('0')
    if '.' in tick_str:
        return len(tick_str.split('.')[1])
    return 0

def get_min_notional(symbol_info):
    for f in symbol_info['filters']:
        if f['filterType'] in ['NOTIONAL', 'MIN_NOTIONAL']:
            return float(f.get('minNotional', f.get('notional', 10.0)))
    return 10.0

def calculate_dynamic_position_slots(usdt_balance, min_order_usdt=10.0):
    if usdt_balance < min_order_usdt:
        return 0, 0.0
    
    if usdt_balance < 30.0:
        return 1, round(usdt_balance, 2)
    elif usdt_balance < 60.0:
        return 2, round(usdt_balance / 2, 2)
    elif usdt_balance < 100.0:
        return 3, round(usdt_balance / 3, 2)
    else:
        num_slots = min(5, max(3, int(usdt_balance // 30)))
        slot_value = round(usdt_balance / num_slots, 2)
        return num_slots, slot_value

async def should_place_order(client, symbol, status_callback=None):
    try:
        orders = await client.get_open_orders(symbol=symbol)
        if len(orders) > 0:
            if status_callback: status_callback(f"⚠️ Já existem ordens abertas para {symbol}.")
            return False
        
        account = await client.get_account()
        balances = account.get('balances', [])
        asset_name = symbol.replace("USDT", "").replace("BUSD", "")
        
        asset_balance = next((float(b['free']) for b in balances if b['asset'] == asset_name), 0.0)
        ticker = await client.get_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])
        
        asset_usdt_value = asset_balance * current_price
        symbol_info = await client.get_symbol_info(symbol)
        min_notional = get_min_notional(symbol_info)
        
        if asset_usdt_value >= min_notional:
            if status_callback: status_callback(f"⚠️ Posição ativa em {symbol} (~${asset_usdt_value:.2f}).")
            return False
            
        return True
    except Exception as e:
        if status_callback: status_callback(f"Erro ao verificar ordens/saldo: {e}")
        return False

async def get_historical_trades_data():
    try:
        df = db.get_recent_trades(limit=10)
        if df.empty:
            return "Nenhum histórico recente de trades."
        
        selected_cols = ['Data/Hora da Compra', 'Símbolo', 'Resultado da Ordem OCO', 'Resultado Parcial da Transação Líquido', 'Padrões de Candle']
        available_cols = [col for col in selected_cols if col in df.columns]
        df = df[available_cols]
        
        if 'Padrões de Candle' in df.columns:
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

def interpret_gemini_response(response_text):
    if not response_text:
        return None

    try:
        cleaned_text = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        data = json.loads(cleaned_text)
        
        sinal = str(data.get('sinal', '')).upper()
        confidence_score = int(data.get('confidence_score', 0))
        justificativa = str(data.get('justificativa', 'Sem justificativa.'))
        
        should_buy_signal = (sinal == 'COMPRA') and (confidence_score >= 50)
        position_multiplier = 2.0 if confidence_score >= 80 else 1.0

        return {
            'action': should_buy_signal,
            'signal': sinal,
            'score': confidence_score,
            'justification': justificativa,
            'position_multiplier': position_multiplier,
            'raw_json': data
        }
    except Exception as e:
        print(f"Erro ao interpretar JSON do Gemini: {e}")
        return None

async def should_buy(rsi, trend_is_up, macd_current, signal_line_current, last_close, lower_band, middle_band, upper_band, vwap, candle_patterns, candle_open, candle_high, candle_low, 
                     candle_close, candle_volume, variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200, client, symbol, klines, silent=False, config_override=None, klines_4h=None):
    
    # 1. Validação de Regime de Mercado (Fase 1: Regime Switcher)
    regime, hurst_val = detect_market_regime(klines)
    if regime == "REGIME_CRASH_PANIC":
        return {"buy": False, "message": "Modo Defesa Ativado: Pânico de Queda no Mercado", "candle_data": "", "gemini_response": None, "regime": regime}

    # 2. Detecção de Varredura de Liquidez Institucional (Fase 2: SMC Sweeps) & Derivativos Futures (Fase A v3.0)
    is_sweep, sweep_msg = detect_liquidity_sweep(klines)
    futures_data = await get_futures_analytics(symbol)
    is_squeeze, squeeze_msg = analyze_futures_squeeze_potential(futures_data, smc_sweep_active=is_sweep)

    if is_sweep and rsi <= 55:
        mult = 2.0 if is_squeeze else 1.0
        prefix = "🔥 SHORT SQUEEZE EXPLOSIVO + " if is_squeeze else "🦈 "
        return {
            "buy": True,
            "message": f"{prefix}{sweep_msg} ({regime})",
            "candle_data": "",
            "gemini_response": None,
            "gemini_analysis": None,
            "regime": regime,
            "position_multiplier": mult,
            "futures_data": futures_data
        }

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
    if use_ema_filter and regime != "REGIME_RANGE_BOUND":
        if klines_4h and len(klines_4h) >= 200:
            closes_4h = [float(k[4]) for k in klines_4h]
            ema200_4h = calculate_ema(closes_4h, 200)
            trend_confirmed = last_close > ema200_4h
        elif ema200 > 0:
            trend_confirmed = last_close > ema200
        else:
            trend_confirmed = False

    if not trend_confirmed:
        return {"buy": False, "message": "Tendência Macro não confirmada (Preço < EMA200)", "candle_data": "", "gemini_response": None, "regime": regime}

    adx_val = calculate_adx(klines, period=TRADING_CONFIG.get('adx_period', 14))
    min_adx = TRADING_CONFIG.get('min_adx', 15.0)
    if config_override and 'TRADING_CONFIG' in config_override:
        min_adx = config_override['TRADING_CONFIG'].get('min_adx', min_adx)

    if adx_val < min_adx and regime != "REGIME_RANGE_BOUND":
        return {"buy": False, "message": f"Mercado lateralizado (ADX={adx_val:.1f} < {min_adx})", "candle_data": "", "gemini_response": None, "regime": regime}

    if rsi > 55:
        return {"buy": False, "message": "RSI alto, compra descartada", "candle_data": "", "gemini_response": None, "regime": regime}

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

    # Fase 4: Condição 0 (Validação Direta pela IA com Score Quantitativo 0-100)
    if gemini_buy_signal is True and rsi <= 45:
        mult = gemini_analysis_dict.get('position_multiplier', 1.0)
        score_v = gemini_analysis_dict.get('score', 70)
        
        # Se também houver indicativo de Short Squeeze nos Futuros, garante multiplicador 2.0x
        if is_squeeze:
            mult = 2.0
            score_v = max(score_v, 85)
            
        msg_title = f"🌟 Oportunidade de Ouro IA Gemini (Score {score_v}/100 - Dobrando Posição)" if mult >= 1.5 else f"Aprovado pela IA Gemini (Score {score_v}/100)"
        return {"buy": True, "message": f"{msg_title} ({regime})", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict, "regime": regime, "position_multiplier": mult, "futures_data": futures_data}

    # Condições Técnicas Tradicionais
    if rsi_low_level0 and trend_is_up and macd_bullish and price_below_vwap and ("Hammer" in candle_patterns or "Bullish Engulfing" in candle_patterns):
        return {"buy": True, "message": f"RSI L0 + MACD + VWAP + Reversão ({regime})", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data}

    if rsi_low_level1 and trend_is_up and macd_bullish and price_below_vwap:
        return {"buy": True, "message": f"RSI L1 + MACD + VWAP ({regime})", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data}

    if rsi_low_level2 and price_below_vwap:
        return {"buy": True, "message": f"RSI L2 + VWAP ({regime})", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data}

    if rsi_low_level3 and macd_bullish:
        return {"buy": True, "message": f"RSI L3 + MACD ({regime})", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data}

    if rsi_low_level4 and trend_is_up:
        return {"buy": True, "message": f"RSI L4 + Tendência ({regime})", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data}

    if rsi_low_level5:
        return {"buy": True, "message": f"RSI L5 Sobre-vendido Extremo ({regime})", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data}

    return {"buy": False, "message": f"Nenhuma condição atendida ({regime})", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data}

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
    return False, ""

async def adjust_and_place_oco_order(client, symbol, quantity, price_tick_size, qty_step_size, klines):
    symbol_info = await client.get_symbol_info(symbol)

    tick_size = float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'PRICE_FILTER')['tickSize'])
    step_size = float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'LOT_SIZE')['stepSize'])

    price_precision = get_precision(tick_size)
    quantity_precision = get_precision(step_size)

    quantity = round(math.floor(quantity / step_size) * step_size, quantity_precision)

    ticker = await client.get_symbol_ticker(symbol=symbol)
    current_price = float(ticker['price'])

    min_notional = get_min_notional(symbol_info)
    notional_value = quantity * current_price

    if notional_value < min_notional:
        print(f"⚠️ Valor nocional ({notional_value:.2f}) é menor que o mínimo exigido ({min_notional:.2f}). Ajustando...")
        quantity = round(math.ceil((min_notional / current_price) / step_size) * step_size, quantity_precision)

    stop_loss_pct = 0.02
    take_profit_pct = 0.04

    take_profit_price = current_price * (1 + take_profit_pct)
    stop_loss_price = current_price * (1 - stop_loss_pct)
    stop_limit_price = stop_loss_price * 0.999

    take_profit_price = adjust_price_to_tick_size(take_profit_price, tick_size)
    stop_loss_price = adjust_price_to_tick_size(stop_loss_price, tick_size)
    stop_limit_price = adjust_price_to_tick_size(stop_limit_price, tick_size)

    try:
        oco_order = await client.create_oco_order(
            symbol=symbol,
            side='SELL',
            quantity=f"{quantity:.{quantity_precision}f}",
            price=f"{take_profit_price:.{price_precision}f}",
            stopPrice=f"{stop_loss_price:.{price_precision}f}",
            stopLimitPrice=f"{stop_limit_price:.{price_precision}f}",
            stopLimitTimeInForce='GTC'
        )
        
        limit_order_id = oco_order['orders'][1]['orderId']
        stop_order_id = oco_order['orders'][0]['orderId']

        print(f"✅ Ordem OCO enviada com sucesso para {symbol}: TP=${take_profit_price:.4f}, SL=${stop_loss_price:.4f}")
        return oco_order, limit_order_id, stop_order_id, take_profit_price, stop_loss_price, stop_limit_price

    except Exception as e:
        print(f"❌ Erro ao enviar ordem OCO: {e}")
        return None, None, None, None, None, None
