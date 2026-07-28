import json
import time
from datetime import datetime
from config.settings import API_KEYS
from utils.formatting import RESET, GREEN, RED, YELLOW, CYAN

_last_429_time = 0
COOLDOWN_429_SECONDS = 300  # 5 minutos de pausa no Gemini se der erro 429 de cota/crédito

def analyze_with_gemini(
    candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book,
    candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
    ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1,
    period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data,
    api_key=None, model_name="gemini-2.5-flash"
):
    global _last_429_time
    now = time.time()
    
    if now - _last_429_time < COOLDOWN_429_SECONDS:
        return None

    if not api_key:
        api_key = API_KEYS.get('gemini')
    if not api_key:
        print("⚠️ Chave API do Gemini não configurada no .env.")
        return None

    current_datetime_str = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-flash-latest"
    ]

    if model_name and model_name not in models_to_try:
        models_to_try.insert(0, model_name)

    prompt_system = (
        "Você é um engenheiro de trading quantitativo sênior focado em criptomoedas no gráfico da Binance.\n"
        "Seu objetivo é avaliar a qualidade técnica da oportunidade e atribuir uma NOTA DE CONFIANÇA QUANTITATIVA (0 a 100).\n\n"
        "REGRAS DE PONTUAÇÃO (confidence_score):\n"
        "- 80 a 100 (Oportunidade de Ouro): Reversão clara com volume forte, RSI muito baixo e suporte testado.\n"
        "- 50 a 79 (Oportunidade Padrão): Configuração técnica favorável de risco moderado.\n"
        "- 0 a 49 (Oportunidade Fraca): Mercado sem clareza, alta pressão vendedora ou consolidação estática.\n\n"
        "FORMATO DE RESPOSTA (JSON APENAS):\n"
        "{\n"
        '  "data_analise": "Data e Hora da Análise",\n'
        '  "sinal": "COMPRA", "VENDA" ou "NEUTRO",\n'
        '  "confidence_score": 85,\n'
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

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        for current_model in models_to_try:
            try:
                config = types.GenerateContentConfig(
                    system_instruction=prompt_system,
                    temperature=0.7,
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
                    print(f"{GREEN}✅ Sucesso! Resposta recebida da IA ({current_model}){RESET}")
                    return response.text
            except Exception as model_err:
                err_str = str(model_err)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    _last_429_time = time.time()
                    print(f"{YELLOW}⚠️ Cota da API Gemini excedida. O robô continuará operando normalmente com Filtros Técnicos.{RESET}")
                    return None
                elif "404" in err_str:
                    continue
                else:
                    print(f"❌ Erro ao consultar IA no modelo {current_model}: {model_err}")
                    continue

    except Exception as e:
        print(f"❌ Falha de integração com Gemini: {e}")

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
        
        # Fase 4: Extrai a pontuacao quantitativa de confianca (0 a 100)
        try:
            confidence_score = int(data.get("confidence_score", 70))
        except (ValueError, TypeError):
            confidence_score = 70

        print(f"\n{CYAN}Resposta do Gemini (JSON - Score: {confidence_score}/100):{RESET}")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        if sinal == "COMPRA":
            if confidence_score >= 80:
                print(f"🌟 {GREEN}Oportunidade de Ouro (Score {confidence_score}/100)! Dobrando a posição.{RESET}\n")
                return {'action': True, 'signal': 'COMPRA', 'justification': justificativa, 'score': confidence_score, 'position_multiplier': 2.0}
            elif confidence_score >= 50:
                print(f"🟢 Sinal de {GREEN}COMPRA (Score {confidence_score}/100){RESET} recebido do Gemini.\n")
                return {'action': True, 'signal': 'COMPRA', 'justification': justificativa, 'score': confidence_score, 'position_multiplier': 1.0}
            else:
                print(f"⚠️ {YELLOW}Sinal de COMPRA descartado por Score Baixo ({confidence_score}/100).{RESET}\n")
                return {'action': None, 'signal': 'NEUTRO', 'justification': 'Score de confiança insuficiente', 'score': confidence_score, 'position_multiplier': 1.0}
        elif sinal == "VENDA":
            print(f"🔴 Sinal de {RED}VENDA (Score {confidence_score}/100){RESET} recebido do Gemini.\n")
            return {'action': False, 'signal': 'VENDA', 'justification': justificativa, 'score': confidence_score, 'position_multiplier': 1.0}
        else:
            print(f"🟡 Sinal {YELLOW}NEUTRO (Score {confidence_score}/100){RESET} recebido do Gemini.\n")
            return {'action': None, 'signal': 'NEUTRO', 'justification': justificativa, 'score': confidence_score, 'position_multiplier': 1.0}

    except Exception as e:
        print(f"Erro ao interpretar resposta da IA: {e}")
        return None

def analyze_news_sentiment_with_gemini(headlines, api_key=None):
    """
    FASE 5 (v4.0): Classificador de Sentimento e Pânico Noticioso via IA Gemini.
    Avalia manchetes de notícias do mercado cripto e atribui uma nota de sentimento de 0 (Pânico) a 100 (Extase).
    Retorna: (sentiment_score: int, is_panic: bool, summary: str)
    """
    global _last_429_time
    if time.time() - _last_429_time < COOLDOWN_429_SECONDS:
        return 75, False, "Mercado estável (Gemini Cooldown)."

    if not api_key:
        api_key = API_KEYS.get('gemini')
    if not api_key:
        return 75, False, "Sem chave Gemini configurada."

    if not headlines:
        return 75, False, "Sem notícias relevantes."

    news_text = "\n".join([f"- {h}" for h in headlines[:5]])
    prompt = (
        "Você é um classificador quantitativo de sentimento de mercado cripto.\n"
        "Avalie as manchetes recentes abaixo e determine se há PÂNICO CATASTRÓFICO de mercado.\n\n"
        "Retorne APENAS um JSON com o formato:\n"
        '{"sentiment_score": 85, "is_panic": false, "summary": "Descrição concisa em português"}\n\n'
        "Regras:\n"
        "- sentiment_score de 0 a 29: Pânico Extremo (Processo regulatório grave, hack massivo, falência).\n"
        "- sentiment_score de 30 a 100: Sentimento Neutro ou Positivo.\n\n"
        f"MANCHETES:\n{news_text}"
    )

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        if response and response.text:
            text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(text)
            score = int(data.get('sentiment_score', 75))
            is_panic = bool(data.get('is_panic', False) or score < 30)
            summary = str(data.get('summary', 'Análise concluída.'))
            return score, is_panic, summary
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            _last_429_time = time.time()

    return 75, False, "Sentimento Neutro (Sem pânico detectado)."
