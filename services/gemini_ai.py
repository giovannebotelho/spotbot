import json
import time
from datetime import datetime
from config.settings import API_KEYS, TRADING_CONFIG
from utils.formatting import BOLD, RESET, GREEN, RED, YELLOW, CYAN

def analyze_with_gemini(
    candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book,
    candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
    ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1,
    period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data,
    api_key=None, model_name="gemini-1.5-flash"
):
    if not api_key:
        api_key = API_KEYS.get('gemini')
    if not api_key:
        print("⚠️ Chave API do Gemini não configurada.")
        return None

    current_datetime_str = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

    # Lista prioritária de modelos para tentar com fallback completo (incluindo 1.5-flash e 1.5-pro da cota gratuita)
    models_to_try = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash", 
        "gemini-2.5-flash"
    ]

    if model_name and model_name not in models_to_try:
        models_to_try.insert(0, model_name)

    prompt_system = (
        "Você é um assistente especializado em negociação de criptomoedas, focado em análise técnica no gráfico da Binance.\n"
        "Seu objetivo principal é identificar oportunidades de COMPRA de médio risco com ALTA probabilidade de sucesso para curto/médio prazo.\n\n"
        "FORMATO DE RESPOSTA (JSON APENAS):\n"
        "{\n"
        '  "data_analise": "Data e Hora da Análise",\n'
        '  "sinal": "COMPRA", "VENDA" ou "NEUTRO",\n'
        '  "confianca": "Alta", "Media" ou "Baixa",\n'
        '  "justificativa": "Explicação detalhada da decisão...",\n'
        '  "regras_chave": ["Regra 1", "Regra 2"]\n'
        "}\n\n"
        "IMPORTANTE: Retorne APENAS o JSON puro sem formatação markdown ```json."
    )

    user_message = (
        f"**Data e Hora da Análise Solicitada: {current_datetime_str}**\n\n"
        f"Dados das velas (candlesticks):\n{candle_data}\n"
        f"Padrões de velas detectados: {candle_patterns}\n"
        f"RSI: {rsi}\n"
        f"MACD: {macd}\n"
        f"Bandas de Bollinger: {bollinger_bands}\n"
        f"Preço de Abertura: {candle_open}\n"
        f"Preço Máximo: {candle_high}\n"
        f"Preço Mínimo: {candle_low}\n"
        f"Preço de Fechamento: {candle_close}\n"
        f"Variação (Candle): {candle_variation}\n"
        f"Volume do último candle: {candle_volume}\n"
        f"Variação de preço em 24h: {variation_24h}%\n"
        f"VWAP: {vwap}\n"
        f"EMA 7: {ema7} | EMA 15: {ema15} | EMA 25: {ema25}\n"
        f"EMA 50: {ema50} | EMA 100: {ema100} | EMA 200: {ema200}\n"
        f"Tendência de alta: {trend_is_up}\n"
        f"Limiar de pressão de venda: {SELL_PRESSURE_THRESHOLD_1}\n"
        f"Período RSI/MA: {period} | Desvio Bollinger: {num_std}\n"
        f"Pressão de Venda Atual: {sell_pressure}\n"
        f"Livro de Ofertas: {order_book}\n"
        f"Histórico de Trades Recentes:\n{historical_trades_data}\n"
    )

    # Tentativa via nova SDK `google.genai`
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        for current_model in models_to_try:
            try:
                print(f"\n🔹 Conectando ao Gemini usando google-genai SDK ({current_model})...")
                
                config = types.GenerateContentConfig(
                    system_instruction=prompt_system,
                    temperature=1.0,
                    top_p=0.95,
                    top_k=64,
                    max_output_tokens=8192,
                    response_mime_type="application/json"
                )

                response = client.models.generate_content(
                    model=current_model,
                    contents=user_message,
                    config=config
                )

                if response and response.text:
                    print(f"{GREEN}✅ Sucesso! Resposta recebida do modelo: {current_model}{RESET}")
                    return response.text
            except Exception as model_err:
                print(f"❌ Erro ao tentar modelo {current_model} via google.genai: {model_err}")
                time.sleep(1)
                continue

    except ImportError:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            for current_model in models_to_try:
                try:
                    print(f"\n🔹 Conectando ao Gemini via SDK legado ({current_model})...")
                    model = genai.GenerativeModel(model_name=current_model)
                    response = model.generate_content(f"{prompt_system}\n\n{user_message}")
                    if response and response.text:
                        print(f"{GREEN}✅ Sucesso! Resposta recebida do modelo: {current_model}{RESET}")
                        return response.text
                except Exception as model_err:
                    print(f"❌ Erro ao tentar modelo {current_model} via SDK legado: {model_err}")
                    time.sleep(1)
                    continue
        except Exception as legacy_err:
            print(f"❌ Falha crítica de conexão com Gemini: {legacy_err}")

    print("❌ FALHA CRÍTICA: Nenhum modelo da IA Gemini respondeu.")
    return None

def interpret_gemini_response(response_text):
    if not response_text:
        return None

    try:
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]

        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        clean_text = clean_text.strip()
        data = json.loads(clean_text)

        sinal = data.get("sinal", "").upper()
        justificativa = data.get("justificativa", "")

        print(f"\n{CYAN}Resposta do Gemini (JSON):{RESET}")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        if sinal == "COMPRA":
            print(f"🟢 Sinal de {GREEN}COMPRA{RESET} recebido do Gemini.\n")
            return {'action': True, 'signal': 'COMPRA', 'justification': justificativa}
        elif sinal == "VENDA":
            print(f"🔴 Sinal de {RED}VENDA{RESET} recebido do Gemini.\n")
            return {'action': False, 'signal': 'VENDA', 'justification': justificativa}
        else:
            print(f"🟡 Sinal {YELLOW}NEUTRO{RESET} recebido do Gemini.\n")
            return {'action': None, 'signal': 'NEUTRO', 'justification': justificativa}

    except json.JSONDecodeError:
        print(f"Erro ao decodificar JSON do Gemini: {response_text}")
        return None
    except Exception as e:
        print(f"Erro ao interpretar resposta do Gemini: {e}")
        return None
