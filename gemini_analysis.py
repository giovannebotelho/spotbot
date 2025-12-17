import os
import time
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def send_data_to_gemini(candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data,
                        api_key, model_name="gemini-1.5-flash"):
    """Envia os dados das velas, padrões e indicadores para a API do Gemini usando o SDK."""
    
    from datetime import datetime
    current_datetime_str = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

    # Priority list of models to try
    models_to_try = [
        "gemini-2.5-flash", 
        "gemini-2.0-flash", 
        "gemini-2.0-flash-lite"
    ]
    
    # If the caller provided a specific model (that isn't the default old one), prioritize it
    if model_name != "gemini-1.5-flash" and model_name not in models_to_try:
        models_to_try.insert(0, model_name)

    genai.configure(api_key=api_key)

    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }

    # Prompt text definition (Keep existing prompt)
    prompt = (
    "Você é um assistente especializado em negociação de criptomoedas, focado em análise técnica do par BTC/USDT no gráfico de **1 hora (1h)** da Binance.\n"
    "Seu objetivo principal é identificar **oportunidades de COMPRA de médio risco com ALTA probabilidade de sucesso** para um horizonte de **curto/médio prazo**, visando um lucro de **0.5%** e um stop loss de **1%**.\n\n"

    "**ANÁLISE REQUERIDA:**\n"
    "1. **Cenário Atual:** Analise velas, volume, padrões, RSI, MACD, Bollinger, EMAs, VWAP e pressão de venda.\n"
    "2. **Histórico:** Use o histórico de trades fornecido para validar sua decisão.\n"
    "3. **Regras:** Formule regras para aumentar a assertividade.\n\n"

    "**FORMATO DE RESPOSTA (JSON):**\n"
    "Responda APENAS com um objeto JSON seguindo este esquema:\n"
    "{\n"
    "  \"data_analise\": \"Data e Hora da Análise\",\n"
    "  \"sinal\": \"COMPRA\", \"VENDA\" ou \"NEUTRO\",\n"
    "  \"confianca\": \"Alta\", \"Media\" ou \"Baixa\",\n"
    "  \"justificativa\": \"Explicação detalhada da decisão...\",\n"
    "  \"regras_chave\": [\"Regra 1\", \"Regra 2\"]\n"
    "}\n"
    )

    user_message = (
        f"**Data e Hora da Análise Solicitada: {current_datetime_str}**\n\n"
        f"Dados das velas (candlesticks):\n{candle_data}\n"
        f"Padrões de velas detectados: {candle_patterns}\n"
        f"RSI: {rsi}\n"
        f"MACD: {macd}\n"
        f"Bandas de Bollinger: {bollinger_bands}\n"
        f"Preço de Abertura (Candle): {candle_open}\n"
        f"Preço Máximo (Candle): {candle_high}\n"
        f"Preço Mínimo (Candle): {candle_low}\n"
        f"Preço de Fechamento (Candle): {candle_close}\n"
        f"Variação (Candle): {candle_variation}\n"
        f"Volume do último candle: {candle_volume}\n"
        f"Variação de preço em 24h: {variation_24h}%\n"
        f"VWAP: {vwap}\n"
        f"EMA 7 : {ema7}\n"
        f"EMA 15 : {ema15}\n"
        f"EMA 25 : {ema25}\n"
        f"EMA 50 : {ema50}\n"
        f"EMA 100: {ema100}\n"
        f"EMA 200: {ema200}\n"
        f"Tendência de alta: {trend_is_up}\n"
        f"Limiar de pressão de venda: {SELL_PRESSURE_THRESHOLD_1}\n"
        f"Período de cálculo do RSI e médias móveis: {period}\n"
        f"Número desvios padrões Bollinger: {num_std}\n"
        f"Período curto cálculo média móvel <> tendência: {short_period}\n"
        f"Período longo cálculo média móvel <> tendência: {long_period}\n"
        f"Limite dados históricos para recuperar de uma vez: {limit}\n"
        f"Profundidade do livro de ofertas: {depth}\n"
        f"Tamanho máximo para deque: {maxlen}\n"
        f"Condicional volume: {volume_avg}\n"
        f"Pressão de Venda: {sell_pressure}\n"
        f"Livro de Ofertas: {order_book}\n"
        f"Dados Históricos de Trades (Resumo):\n{historical_trades_data}\n"
    )

    # Loop through models with fallback
    for current_model in models_to_try:
        try:
            print(f"\n🔹 Tentando conectar com modelo: \033[1;33m{current_model}\033[0m...")
            
            model = genai.GenerativeModel(
                model_name=current_model,
                generation_config=generation_config,
            )

            chat_session = model.start_chat(
                history=[
                    {
                        "role": "user",
                        "parts": [prompt],
                    },
                    {
                        "role": "model",
                        "parts": ["Entendido. Aguardo os dados para análise."],
                    },
                ]
            )

            response = chat_session.send_message(user_message)
            
            print(f"\033[1;32m✅ Sucesso! Resposta recebida do modelo: {current_model}\033[0m")
            return response.text

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Falha com {current_model}: {error_msg}")
            
            if "429" in error_msg:
                print("⏳ Cota excedida (429). Aguardando 2 segundos antes de tentar próximo...")
                time.sleep(2)
            elif "404" in error_msg:
                print(f"⚠️ Modelo {current_model} não encontrado ou depreciado.")
            
            continue # Try next model
            
    print("❌ \033[1;31mFALHA CRÍTICA: Todos os modelos falharam.\033[0m")
    return None

def interpret_gemini_response(response_text):
    """Interpreta a resposta JSON do Gemini para extrair o sinal."""
    if response_text is None:
        return None

    try:
        data = json.loads(response_text)
        sinal = data.get("sinal", "").upper()
        justificativa = data.get("justificativa", "")
        
        print(f"\n\033[1;36mResposta do Gemini (JSON):\033[0m")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        if sinal == "COMPRA":
            print("🟢 Sinal de \033[1;32mCOMPRA\033[0m recebido do Gemini.\n")
            return {
                'action': True,
                'signal': 'COMPRA',
                'justification': justificativa
            }
        elif sinal == "VENDA":
            print("🔴 Sinal de \033[1;31mVENDA\033[0m recebido do Gemini.\n")
            return {
                'action': False,
                'signal': 'VENDA',
                'justification': justificativa
            }
        else:
            print("🟡 Sinal \033[1;33mNEUTRO\033[0m recebido do Gemini.\n")
            return {
                'action': None,
                'signal': 'NEUTRO', 
                'justification': justificativa
            }

    except json.JSONDecodeError:
        print(f"Erro ao decodificar JSON do Gemini: {response_text}")
        return None
    except Exception as e:
        print(f"Erro ao interpretar resposta do Gemini: {e}")
        return None

def analyze_with_gemini(api_key, candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data):
    """Envia os dados das velas, padrões e indicadores para o Gemini e interpreta a resposta."""
    
    gemini_response = send_data_to_gemini(candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                    ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data, 
                    api_key)

    return gemini_response
