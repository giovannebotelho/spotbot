import asyncio
import json
import re
import math
from decimal import Decimal, ROUND_DOWN
from datetime import datetime
import pandas as pd

from config.settings import API_KEYS, TRADING_CONFIG, RSI_CONFIG
from services.binance_client import get_order_details, get_futures_analytics, get_order_book, get_multi_timeframe_klines, get_lead_lag_btc_klines, get_recent_trades_cvd, get_klines
from core.indicators import (
    detect_market_regime, detect_liquidity_sweep, calculate_ema, calculate_adx,
    analyze_futures_squeeze_potential, calculate_orderbook_imbalance, calculate_multi_timeframe_confluence,
    detect_orderbook_whale_walls, calculate_atr, calculate_lead_lag_alpha, calculate_cvd_trend,
    calculate_pair_cointegration_zscore
)
from services.gemini_ai import analyze_with_gemini, analyze_news_sentiment_with_gemini
from services.news_scanner import fetch_crypto_news
from services.database import DatabaseManager

db = DatabaseManager()

def adjust_rsi_levels(trade_result):
    if trade_result == 'profit':
        for i in range(len(RSI_CONFIG['dynamic_low'])):
            RSI_CONFIG['dynamic_low'][i] = min(RSI_CONFIG['levels'][i] + 5, 55)
    elif trade_result == 'stop loss':
        for i in range(len(RSI_CONFIG['dynamic_low'])):
            RSI_CONFIG['dynamic_low'][i] = max(RSI_CONFIG['levels'][i] - 5, 20)

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

def calculate_dynamic_position_slots(usdt_balance, min_order_usdt=10.0, accumulated_net_profit=0.0, max_concurrent_positions=3, reserve_fraction_for_dca=0.25):
    usable_usdt = math.floor(usdt_balance * 0.99 * 100) / 100.0
    
    if usable_usdt < min_order_usdt:
        return 0, 0.0

    # Preserva 25% do saldo em reserva liquida para o Smart Recovery DCA (Suportes Fibonacci 61.8%)
    allocatable_usdt = usable_usdt * (1.0 - reserve_fraction_for_dca)
    if allocatable_usdt < min_order_usdt:
        allocatable_usdt = usable_usdt

    if allocatable_usdt < 20.0:
        num_slots = 1
    elif allocatable_usdt < 35.0:
        num_slots = 2
    else:
        num_slots = min(max_concurrent_positions, 3)

    slot_value = max(min_order_usdt, round(allocatable_usdt / num_slots, 2))
    slot_value = min(usable_usdt, slot_value)
    
    return num_slots, slot_value

async def place_safe_oco_sell_order(client, symbol, quantity, price, stop_price, stop_limit_price, precision_price, precision_qty):
    q_str = f"{quantity:.{precision_qty}f}"
    p_str = f"{price:.{precision_price}f}"
    sp_str = f"{stop_price:.{precision_price}f}"
    slp_str = f"{stop_limit_price:.{precision_price}f}"
    
    try:
        return await client._post(
            "order/oco",
            signed=True,
            data={
                'symbol': symbol,
                'side': 'SELL',
                'quantity': q_str,
                'price': p_str,
                'stopPrice': sp_str,
                'stopLimitPrice': slp_str,
                'stopLimitTimeInForce': 'GTC'
            }
        )
    except Exception as e1:
        return await client.create_oco_order(
            symbol=symbol,
            side='SELL',
            quantity=q_str,
            price=p_str,
            stopPrice=sp_str,
            stopLimitPrice=slp_str,
            stopLimitTimeInForce='GTC',
            aboveType='LIMIT_MAKER',
            belowType='STOP_LOSS_LIMIT'
        )

async def should_place_order(client, symbol, status_callback=None):
    try:
        open_ocos = await client.get_open_oco_orders()
        for oco in open_ocos:
            if oco.get('symbol') == symbol or oco.get('listClientOrderId', '').startswith(symbol):
                if status_callback: status_callback(f"⚠️ OCO ativa já existente para {symbol}. Posição ignorada.")
                return False

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
    
    # (Movido para o final da função para economia de tokens)

    # 0. Breakout Confirmation (Filtro Anti-Whipsaw)
    if TRADING_CONFIG.get('use_candle_close_confirmation', False) and len(klines) >= 1:
        current_candle_open = float(klines[-1][1])
        current_candle_close = float(klines[-1][4])
        # Se o candle atual (fechado ou rodando) estiver vermelho (fechamento < abertura), recusa a entrada para evitar "falling knives" e violinadas.
        if current_candle_close <= current_candle_open:
            return {"buy": False, "message": "Aguardando confirmação de reversão (Vela atual ainda está vermelha).", "candle_data": "", "gemini_response": None, "regime": "N/A"}

    # 1. Validação de Regime de Mercado (Fase 1: Regime Switcher)
    regime, hurst_val = detect_market_regime(klines)
    if regime == "REGIME_CRASH_PANIC":
        return {"buy": False, "message": "Modo Defesa Ativado: Pânico de Queda no Mercado", "candle_data": "", "gemini_response": None, "regime": regime}

    # 2. Detecção de Varredura de Liquidez Institucional (Fase 2: SMC Sweeps) & Derivativos Futures (Fase A v3.0)
    is_sweep, sweep_msg = detect_liquidity_sweep(klines)
    futures_data = await get_futures_analytics(symbol)
    is_squeeze, squeeze_msg = analyze_futures_squeeze_potential(futures_data, smc_sweep_active=is_sweep)

    # 3. Análise de Profundidade do Livro de Ofertas (Fase B v3.0: Orderbook Imbalance Scanner)
    try:
        ob = await get_order_book(client, symbol, depth=20)
        ob_ratio, bids_v, asks_v, has_buy_wall, ob_msg = calculate_orderbook_imbalance(ob)
    except Exception:
        ob_ratio, has_buy_wall, ob_msg = 1.0, False, "Sem dados do livro de ofertas."

    if ob_ratio < 0.2:
        return {"buy": False, "message": f"Muro de Venda Massivo no Livro (Bids/Asks={ob_ratio:.2f}x)", "candle_data": "", "gemini_response": None, "regime": regime}

    # 3.1. FASE 2 (v4.0): Matriz de Confluência Multi-Timeframe (4H + 1H + 15M)
    try:
        mtf_data = await get_multi_timeframe_klines(client, symbol)
        score_mtf, is_confluent, details_mtf = calculate_multi_timeframe_confluence(
            mtf_data.get('4h', []),
            mtf_data.get('1h', []),
            mtf_data.get('15m', klines)
        )
    except Exception:
        score_mtf, is_confluent, details_mtf = 75, True, {'reasons': []}

    if not is_confluent:
        return {
            "buy": False,
            "message": f"Confluência Multi-Timeframe Insuficiente (Score {score_mtf}% < 70%)",
            "candle_data": "",
            "gemini_response": None,
            "regime": regime,
            "mtf_score": score_mtf
        }

    # 3.2. FASE 2 (v5.0): Correlation Lead-Lag Alpha Engine (Antecipação BTC)
    try:
        btc_1m = await get_lead_lag_btc_klines(client)
        is_lead_alpha, btc_imp_pct, alpha_msg = calculate_lead_lag_alpha(btc_1m, klines)
        if is_lead_alpha and rsi <= 55:
            return {
                "buy": True,
                "message": f"{alpha_msg} ({regime})",
                "candle_data": "",
                "gemini_response": None,
                "gemini_analysis": None,
                "regime": regime,
                "position_multiplier": 1.5,
                "futures_data": futures_data,
                "orderbook_imbalance": ob_ratio
            }
    except Exception:
        pass

    # 3.3. FASE 3 (v5.0): Order Flow Cumulative Volume Delta (CVD Tape Reading)
    try:
        recent_trades = await get_recent_trades_cvd(client, symbol, limit=500)
        cvd_val_usdt, buy_ratio_pct, is_bullish_cvd = calculate_cvd_trend(recent_trades)
        if is_bullish_cvd and rsi <= 55:
            mult = 2.0 if cvd_val_usdt >= 50000 else 1.0
            return {
                "buy": True,
                "message": f"📊 TAPE READING CVD: AGRESSÃO COMPRADORA ({buy_ratio_pct:.1f}% Buys | +${cvd_val_usdt:,.0f} USDT) ({regime})",
                "candle_data": "",
                "gemini_response": None,
                "gemini_analysis": None,
                "regime": regime,
                "position_multiplier": mult,
                "futures_data": futures_data,
                "orderbook_imbalance": ob_ratio
            }
    except Exception:
        pass

    # 3.4. FASE 4 (v5.0): Cointegration Pair Trading & Statistical Arbitrage
    try:
        ref_symbol = "BTCUSDT" if symbol != "BTCUSDT" else "ETHUSDT"
        ref_klines = await get_klines(client, ref_symbol, TRADING_CONFIG['interval'], 50)
        z_score, is_stat_arb_buy, r_mean, r_std = calculate_pair_cointegration_zscore(klines, ref_klines)
        if is_stat_arb_buy and rsi <= 55:
            return {
                "buy": True,
                "message": f"⚖️ STATISTICAL ARBITRAGE: REVERSÃO À MÉDIA (Z-Score: {z_score:.2f}σ vs {ref_symbol}) ({regime})",
                "candle_data": "",
                "gemini_response": None,
                "gemini_analysis": None,
                "regime": regime,
                "position_multiplier": 1.5,
                "futures_data": futures_data,
                "orderbook_imbalance": ob_ratio
            }
    except Exception:
        pass

    if is_sweep and rsi <= 55:
        mult = 2.0 if (is_squeeze or has_buy_wall) else 1.0
        prefix = "🔥 SHORT SQUEEZE EXPLOSIVO + " if is_squeeze else ("🛡️ MURO DE COMPRA BALEIA + " if has_buy_wall else "🦈 ")
        return {
            "buy": True,
            "message": f"{prefix}{sweep_msg} ({regime})",
            "candle_data": "",
            "gemini_response": None,
            "gemini_analysis": None,
            "regime": regime,
            "position_multiplier": mult,
            "futures_data": futures_data,
            "orderbook_imbalance": ob_ratio
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

    # Otimização: A análise profunda do Gemini só é feita se alguma técnica padrão estiver perto de aprovar, ou se quisermos validar diretamente
    # No caso original, havia um "if gemini_buy_signal is True", mas para economizar vamos só rodar o Gemini SE os filtros técnicos passarem!
    
    proposed_result = None

    # Condições Técnicas Tradicionais
    if rsi_low_level0 and trend_is_up and macd_bullish and price_below_vwap and ("Hammer" in candle_patterns or "Bullish Engulfing" in candle_patterns):
        proposed_result = {"buy": True, "message": f"RSI L0 + MACD + VWAP + Reversão ({regime})", "candle_data": "", "gemini_response": None, "gemini_analysis": None, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data, "orderbook_imbalance": ob_ratio}
    elif rsi_low_level1 and trend_is_up and macd_bullish and price_below_vwap:
        proposed_result = {"buy": True, "message": f"RSI L1 + MACD + VWAP ({regime})", "candle_data": "", "gemini_response": None, "gemini_analysis": None, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data, "orderbook_imbalance": ob_ratio}
    elif rsi_low_level2 and price_below_vwap:
        proposed_result = {"buy": True, "message": f"RSI L2 + VWAP ({regime})", "candle_data": "", "gemini_response": None, "gemini_analysis": None, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data, "orderbook_imbalance": ob_ratio}
    elif rsi_low_level3 and macd_bullish:
        proposed_result = {"buy": True, "message": f"RSI L3 + MACD ({regime})", "candle_data": "", "gemini_response": None, "gemini_analysis": None, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data, "orderbook_imbalance": ob_ratio}
    elif rsi_low_level4 and trend_is_up:
        proposed_result = {"buy": True, "message": f"RSI L4 + Tendência ({regime})", "candle_data": "", "gemini_response": None, "gemini_analysis": None, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data, "orderbook_imbalance": ob_ratio}
    elif rsi_low_level5:
        proposed_result = {"buy": True, "message": f"RSI L5 Sobre-vendido Extremo ({regime})", "candle_data": "", "gemini_response": None, "gemini_analysis": None, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data, "orderbook_imbalance": ob_ratio}

    if not proposed_result:
        return {"buy": False, "message": f"Nenhuma condição atendida ({regime})", "candle_data": "", "gemini_response": None, "gemini_analysis": None, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data, "orderbook_imbalance": ob_ratio}

    # Se chegou aqui, alguma técnica aprovou! AGORA chamamos a IA Gemini para evitar Pânico Noticioso (Fase 5) e obter o Score!
    try:
        headlines = await fetch_crypto_news(symbol)
        news_score, is_panic_news, panic_summary = analyze_news_sentiment_with_gemini(headlines)
        if is_panic_news or news_score < 30:
            return {
                "buy": False,
                "message": f"Modo Defesa Ativado: Pânico Noticioso IA (Score {news_score}/100 - {panic_summary})",
                "candle_data": "",
                "gemini_response": None,
                "regime": "REGIME_CRASH_PANIC"
            }
    except Exception:
        pass

    # Agora sim pega o Score Quantitativo
    gemini_response = await get_gemini_analysis(
        f"Open: {candle_open}, High: {candle_high}, Low: {candle_low}, Close: {candle_close}, Volume: {candle_volume}",
        candle_patterns, rsi, f"MACD: {macd_current}, Signal: {signal_line_current}", f"Upper: {upper_band}, Middle: {middle_band}, Lower: {lower_band}", 0, {},
        candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, 0.65, 20, 2, 12, 26, 300, 20, 20, 50,
        await get_historical_trades_data(), client, symbol
    )

    if gemini_response:
        gemini_analysis_dict = interpret_gemini_response(gemini_response)
        if gemini_analysis_dict:
            score_v = gemini_analysis_dict.get('score', 70)
            proposed_result['gemini_response'] = gemini_response
            proposed_result['gemini_analysis'] = gemini_analysis_dict
            if score_v >= 80:
                proposed_result['position_multiplier'] = 2.0
                proposed_result['message'] = f"🌟 Oportunidade de Ouro IA Gemini (Score {score_v}/100 - Dobrando Posição) | " + proposed_result['message']
            else:
                proposed_result['message'] = f"Aprovado IA (Score {score_v}/100) | " + proposed_result['message']
            
            if gemini_analysis_dict.get('action') is False:
                # O Gemini pode vetar a entrada se achar muito ruim
                if score_v < 40:
                    return {"buy": False, "message": f"Veto IA Gemini (Score {score_v}/100)", "candle_data": "", "gemini_response": gemini_response, "gemini_analysis": gemini_analysis_dict, "regime": regime, "position_multiplier": 1.0, "futures_data": futures_data, "orderbook_imbalance": ob_ratio}

    return proposed_result



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

def frontrun_round_numbers(price, log=print):
    """
    Anticipates psychological resistance levels (round numbers).
    If the target price is slightly above a major round number, 
    pulls it just below the round number to ensure execution before the 'wall'.
    """
    if price >= 1000:
        magnitude = 100
        tolerance = 0.02
        frontrun_pct = 0.002 
    elif price >= 100:
        magnitude = 10
        tolerance = 0.02
        frontrun_pct = 0.002
    elif price >= 10:
        magnitude = 1
        tolerance = 0.02
        frontrun_pct = 0.003
    elif price >= 1:
        magnitude = 0.1
        tolerance = 0.02
        frontrun_pct = 0.005
    elif price >= 0.1:
        magnitude = 0.01
        tolerance = 0.02
        frontrun_pct = 0.005
    else:
        return price
        
    nearest_round_down = math.floor(price / magnitude) * magnitude
    if nearest_round_down > 0 and (price - nearest_round_down) / nearest_round_down <= tolerance:
        adj_price = nearest_round_down * (1 - frontrun_pct)
        log(f"🧠 \033[1;36mPsychological Resistance\033[0m: TP ajustado de ${price:.4f} para \033[1;33m${adj_price:.4f}\033[0m (Front-running ${nearest_round_down:.0f})")
        return adj_price
        
    return price

async def adjust_and_place_oco_order(client, symbol, quantity, price_tick_size, qty_step_size, klines, log=print):
    symbol_info = await client.get_symbol_info(symbol)

    tick_size = float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'PRICE_FILTER')['tickSize'])
    step_size = float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'LOT_SIZE')['stepSize'])

    price_precision = get_precision(tick_size)
    quantity_precision = get_precision(step_size)

    # Use Decimal for strict LOT_SIZE compliance to avoid floating point issues
    qty_dec = Decimal(str(quantity))
    step_dec = Decimal(str(step_size))
    # Round down to the nearest multiple of step_size
    quantized_qty = (qty_dec / step_dec).quantize(Decimal('1'), rounding=ROUND_DOWN) * step_dec
    quantity = float(quantized_qty)

    ticker = await client.get_symbol_ticker(symbol=symbol)

    current_price = float(ticker['price'])

    min_notional = get_min_notional(symbol_info)
    notional_value = quantity * current_price

    if notional_value < min_notional:
        log(f"⚠️ Valor nocional ({notional_value:.2f}) é menor que o mínimo exigido ({min_notional:.2f}). Ajustando...")
        required_qty = Decimal(str(min_notional / current_price))
        quantized_adj = (required_qty / step_dec).quantize(Decimal('1'), rounding=ROUND_DOWN)
        # If rounding down makes it smaller than required, add one step
        if quantized_adj * step_dec < required_qty:
            quantized_adj += Decimal('1')
        quantity = float(quantized_adj * step_dec)

    # FASE 4 (v4.0): Dynamic ATR Volatility Protection anti-Stop Hunt
    try:
        atr_val, atr_pct = calculate_atr(klines, period=14)
        stop_loss_pct = max(0.015, min(0.020, atr_pct * 1.5))
        take_profit_pct = max(0.020, min(0.030, stop_loss_pct * 1.5))
        log(f"⚡ \033[1;36mVolatility Adaptive Protection\033[0m: ATR(14)={atr_pct*100:.2f}%. Stop Loss ajustado para \033[1;31m-{stop_loss_pct*100:.2f}%\033[0m | Take Profit: \033[1;32m+{take_profit_pct*100:.2f}%\033[0m")
    except Exception:
        stop_loss_pct = 0.018
        take_profit_pct = 0.025

    raw_tp = current_price * (1 + take_profit_pct)
    raw_sl = current_price * (1 - stop_loss_pct)

    # FASE 3 (v4.0): Proteção de Muro de Baleias no Orderbook (Depth 50)
    try:
        ob_50 = await get_order_book(client, symbol, depth=50)
        adj_tp, adj_sl, wall_detected, wall_info = detect_orderbook_whale_walls(
            ob_50, current_price, raw_tp, raw_sl, tick_size
        )
        if wall_detected and wall_info:
            w_p = wall_info['wall_price']
            w_usdt = wall_info['wall_usdt']
            log(f"🛡️ \033[1;36mWhale Wall Protection\033[0m: Muro de Venda detectado em \033[1;33m${w_p:.4f}\033[0m (~${w_usdt:,.0f} USDT)!")
            log(f"🎯 Take Profit antecipado de ${raw_tp:.4f} para \033[1;32m${adj_tp:.4f}\033[0m (0.15% antes do muro da baleia).")
            take_profit_price = adj_tp
        else:
            take_profit_price = raw_tp
    except Exception:
        take_profit_price = raw_tp

    take_profit_price = frontrun_round_numbers(take_profit_price, log=log)

    stop_loss_price = raw_sl
    stop_limit_price = stop_loss_price * 0.999

    take_profit_price = adjust_price_to_tick_size(take_profit_price, tick_size)
    stop_loss_price = adjust_price_to_tick_size(stop_loss_price, tick_size)
    stop_limit_price = adjust_price_to_tick_size(stop_limit_price, tick_size)

    try:
        oco_order = await place_safe_oco_sell_order(
            client, symbol, quantity, take_profit_price, stop_loss_price, stop_limit_price, price_precision, quantity_precision
        )
        
        limit_order_id = oco_order['orders'][1]['orderId']
        stop_order_id = oco_order['orders'][0]['orderId']

        log(f"🎯 Ordem OCO Posicionada ({symbol}): TP=${take_profit_price:.4f} (+4.0%) | SL=${stop_loss_price:.4f} (-2.0%)")
        return oco_order, limit_order_id, stop_order_id, take_profit_price, stop_loss_price, stop_limit_price

    except Exception as e:
        log(f"❌ Erro ao enviar ordem OCO: {e}")
        return None, None, None, None, None, None

def calculate_kelly_position_size(db, usdt_balance, default_slot_value=20.0):
    """
    FASE 5 (v5.0): Kelly Criterion Position Sizing Engine.
    Calcula o tamanho matematicamente ótimo da posição em USDT com base na Taxa de Vitória (Win Rate)
    e no Payoff Ratio das últimas operações do banco de dados SQLite.
    Aplica o "Half-Kelly" (50% de f*) para conter volatilidade e evitar risco de ruína.
    Retorna: (slot_val_usdt: float, kelly_pct: float, is_kelly_active: bool)
    """
    try:
        stats = db.get_stats()
        total_trades = stats.get('total_trades', 0)
        win_rate_pct = stats.get('win_rate', 60.0)

        if total_trades < 5:
            return default_slot_value, 0.20, False

        p = win_rate_pct / 100.0
        q = 1.0 - p
        b = 2.0

        f_kelly = (p * b - q) / b
        half_kelly = max(0.10, min(0.40, f_kelly * 0.5))

        slot_val_usdt = round(math.floor((usdt_balance * half_kelly) * 100) / 100.0, 2)
        safe_min_notional = 6.0
        slot_val_usdt = max(safe_min_notional, min(usdt_balance * 0.98, slot_val_usdt))

        return slot_val_usdt, half_kelly, True
    except Exception:
        return default_slot_value, 0.20, False
