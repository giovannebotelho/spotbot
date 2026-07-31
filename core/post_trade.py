from datetime import datetime
from core.indicators import calculate_trade_result, calculate_fee
from services.telegram_notifier import send_telegram_message
from config.settings import TELEGRAM_CONFIG, RSI_CONFIG, OCO_CONFIG, TRADING_CONFIG
from core.decision import adjust_rsi_levels
from services.database import DatabaseManager

async def process_order_details(symbol, client, limit_order_details, stop_order_details, price, executed_qty, quantia_usdt_investimento_inicial):
    if limit_order_details['status'] == 'FILLED':
        oco_order_result = 'profit'
        price_sold = float(limit_order_details['price'])
        adjust_rsi_levels('profit')
    elif stop_order_details['status'] == 'FILLED':
        oco_order_result = 'stop loss'
        price_sold = float(stop_order_details['price'])
        adjust_rsi_levels('stop loss')
    else:
        oco_order_result = None
        price_sold = 0

    if oco_order_result is not None:
        trade_result = calculate_trade_result(price, executed_qty, price_sold)
        fee = await calculate_fee(client, symbol, executed_qty, price_sold)
        trade_result_liquid = trade_result - fee
        novo_saldo_usdt = quantia_usdt_investimento_inicial + trade_result
    else:
        trade_result = 0
        novo_saldo_usdt = quantia_usdt_investimento_inicial
        fee = 0
        trade_result_liquid = 0

    oco_timestamp = datetime.now().strftime("%d/%m/%Y at %H:%M:%S") if oco_order_result else None
    return symbol, oco_order_result, trade_result, novo_saldo_usdt, oco_timestamp, fee, trade_result_liquid

async def log_and_notify_results(order_result, symbol, trade_result, total_difference, timestamp, vwap, fee, trade_result_liquid, total_difference_liquid, bnb_balance_usdt, log=print):
    if order_result == 'profit':
        log(f"🎉 Ordem OCO concluída com \033[1;32mlucro (PROFIT)\033[0m em \033[1;33m{symbol}\033[0m ({timestamp})")
        message = f'🎉 <b>Ordem OCO concluída com PROFIT!</b>\n\n🪙 Par: <b>{symbol}</b>\n⏱️ Horário: <i>{timestamp}</i>'
    elif order_result == 'stop loss':
        log(f"⛔ Ordem OCO concluída em \033[1;31mSTOP LOSS\033[0m em \033[1;33m{symbol}\033[0m ({timestamp})")
        message = f'⛔ <b>Ordem OCO concluída em STOP LOSS!</b>\n\n🪙 Par: <b>{symbol}</b>\n⏱️ Horário: <i>{timestamp}</i>'
    
    if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
        await send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], message)

    if trade_result >= 0:
        result_message = f"Lucro Parcial Bruto: 🟢 ${trade_result:.2f} | Taxa: 🔴 ${fee:.2f} | Lucro Líquido: 🟢 ${trade_result_liquid:.2f}"
        telegram_message1 = f"💰 Lucro Parcial Bruto: 🟢 <b>${trade_result:.2f}</b>\n🔴 Taxa: <b>${fee:.2f}</b>\n💵 Lucro Líquido: 🟢 <b>${trade_result_liquid:.2f} USDT</b>"
    else:
        result_message = f"Prejuízo Parcial Bruto: 🔴 ${trade_result:.2f} | Taxa: 🔴 ${fee:.2f} | Prejuízo Líquido: 🔴 ${trade_result_liquid:.2f}"
        telegram_message1 = f"🔻 Prejuízo Parcial Bruto: 🔴 <b>${trade_result:.2f}</b>\n🔴 Taxa: <b>${fee:.2f}</b>\n💵 Prejuízo Líquido: 🔴 <b>${trade_result_liquid:.2f} USDT</b>"
    
    log(result_message)
    if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
        await send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], telegram_message1)

    if total_difference_liquid >= 0:
        total_balance_liquid_message = f"📈 PnL Acumulado Líquido no Saldo: 🟢 ${total_difference_liquid:.2f} USDT"
        telegram_message3 = f"📈 <b>PnL Acumulado Líquido no Saldo</b>: 🟢 <b>${total_difference_liquid:.2f} USDT</b>"
    else:
        total_balance_liquid_message = f"📉 PnL Acumulado Líquido no Saldo: 🔴 ${total_difference_liquid:.2f} USDT"
        telegram_message3 = f"📉 <b>PnL Acumulado Líquido no Saldo</b>: 🔴 <b>${total_difference_liquid:.2f} USDT</b>"
    
    log(total_balance_liquid_message)
    if TELEGRAM_CONFIG.get('bot_token') and TELEGRAM_CONFIG.get('chat_id'):
        await send_telegram_message(TELEGRAM_CONFIG['bot_token'], TELEGRAM_CONFIG['chat_id'], telegram_message3)
    
    log(f"🪙 Saldo BNB na carteira: ${bnb_balance_usdt:.2f} USDT")

def create_data_row(order_count, saldo_inicial_usdt, quantia_usdt_investimento_inicial, symbol,
                    executed_qty, price_rounded, purchase_timestamp, lucro_alvo, stop_loss, stop_limit,
                    order_result, oco_timestamp, trade_result, total_difference, saldo_atual_usdt,
                    rsi, executed_condition, vwap, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation,
                    ema7, ema15, ema25, ema50, ema100, ema200, candle_patterns, volume_avg, amplitude, macd_current, signal_line_current, 
                    lower_band, middle_band, upper_band, trend_is_up, fee, trade_result_liquid, total_difference_liquid, gemini_response, bnb_balance_usdt,
                    confluence_score=0.0, slippage=0.0, initial_stop_loss=0.0, dca_levels=0, bot_version="v6.0"):
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
        "Taxa": fee,
        "Resultado Parcial da Transação Líquido": round(trade_result_liquid, 2),
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
        "Amplitude (Candle)": amplitude,
        "Variação (24h)": variation_24h,
        "Volume (Candle)": candle_volume,
        "Padrões de Candle": candle_patterns,
        "MACD": macd_current,
        "Linha de Sinal": signal_line_current,
        "Banda Inferior BB": lower_band,
        "Banda Média BB": middle_band,
        "Banda Superior BB": upper_band,
        "Tendência de Alta": trend_is_up,
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
        "Resposta do Gemini": gemini_response if gemini_response is not None else "N/A",
        "confluence_score": confluence_score,
        "slippage": slippage,
        "initial_stop_loss": initial_stop_loss,
        "dca_levels": dca_levels,
        "bot_version": bot_version,
    }

def save_to_csv(data_row):
    try:
        db = DatabaseManager()
        db.add_trade(data_row)
        print("✅ Dados salvos no banco de dados com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao salvar no banco de dados: {e}")
