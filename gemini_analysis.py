import requests
import time

from dotenv import load_dotenv

load_dotenv()

def send_data_to_gemini(candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data,
                        api_key, model="gemini-2.5-flash-preview-04-17"):
    """Envia os dados das velas, padrões e indicadores para a API do Gemini."""

    headers = {
        "Content-Type": "application/json",
    }

    prompt = (
        "Você é um assistente especializado em negociação de criptomoedas, focado em análise técnica do Bitcoin (BTC/USDT) no gráfico de **1 hora (1h)** da Binance."
        "Analise os dados fornecidos, incluindo informações sobre o preço de fechamento das velas, indicadores técnicos, padrões de vela e dados históricos de trades, com um viés crítico."
        "Seu objetivo é identificar **oportunidades de compra com médio risco e alta probabilidade de sucesso** em um horizonte de **curto/médio prazo**.\n"

        "Preste atenção especial aos seguintes aspectos:\n"

        "1. **Dados das Velas:** Analise os preços de abertura, fechamento, máximo e mínimo de cada vela, bem como o volume. Identifique tendências, suportes e resistências.\n"

        "2. **Indicadores Técnicos:** Analise o RSI, MACD e as Bandas de Bollinger para identificar condições de sobrecompra/sobrevenda, divergências e possíveis reversões de tendência.\n"

        "3. **Dados Históricos de Trades:**"
        "*   A presente string de dados representa o histórico de operações realizadas até o momento, e tem como objetivo identificar a maior quantidade de padrões e regras que garantam a assertividade para as próximas operações."
        "*   Cada linha nesta string representa um trade, e os dados a seguir estão presentes:"
                "*   **Símbolo:** O símbolo do ativo negociado (por exemplo, BTCUSDT)."
                "*   **Preço de Compra:** O preço no qual a ordem de compra foi executada."
                "*   **VWAP:** Valor do VWAP no momento da compra."
                "*   **Data/Hora da Compra:** Data e hora em que a ordem de compra foi executada."
                "*   **Resultado da Ordem OCO:** Resultado da ordem OCO (profit ou stop loss)."
                "*   **Data/Hora OCO:** Data e hora em que a ordem OCO foi concluída."
                "*   **RSI da Operação:** O valor do RSI no momento da compra."
                "*   **Condição Atendida:** A condição específica que foi atendida para disparar a ordem (por exemplo, RSI_lvl1, MACD_crossover, etc.)."
                "*   **Intervalo de Tempo (Candles):** O intervalo de tempo usado para as velas (por exemplo, 15m, 1h)."
                "*   **Padrões de Candle:** Quaisquer padrões de candle identificados no momento da compra."
                "*   **Tendência de Alta:** Indica se a tendência era de alta no momento da compra (True ou False).\n"

        "4.  **Com base nos dados históricos, identifique:**"
            "*   Quais condições de compra levam aos resultados mais lucrativos?"
            "*   Quais níveis de RSI são mais propensos a gerar lucros?"
            "*   Quais padrões de candle são mais confiáveis?"
            "*   Em quais condições de mercado (tendência de alta, etc.) a estratégia tem melhor desempenho?\n"
        
        "5.  **Com base na análise histórica, formule um conjunto de regras específicas que devem ser seguidas para aumentar a probabilidade de sucesso de novas operações.**"
            "*Analise a consistência entre as EMAs, e cruze as informações de trades anteriores para definir qual o melhor ponto de entrada\n"
        
        "Com base na análise dos dados das velas, indicadores técnicos, dados históricos de trades e levando em conta o objetivo de **0.45%** de lucro e **0.8%** de stop loss, qual sua recomendação (sinal=compra, sinal=venda ou sinal=neutro)?\n"
        "Justifique sua resposta detalhadamente e inclua um resumo das principais regras que você formulou a partir dos dados históricos."
    )

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
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
                            f"Dados Históricos de Trades:\n{historical_trades_data}\n"
                            f"{prompt}"
                        )
                    }
                ]
            }
        ],
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    response = requests.post(
        url,
        headers=headers,
        json=data,
    )

    # Verifica se houve erro na resposta
    if response.status_code != 200:
        print(f"Erro na solicitação à API do Gemini: {response.status_code} - {response.text}")
        return None

    response.raise_for_status()

    # Mostra a URL da prompt
    #print(f"Prompt enviada para o Gemini.")
    print(f"\033[1;36mPrompt enviada para o Gemini:\033[0m {response.url}")

    return response.json()['candidates'][0]['content']['parts'][0]['text']

def interpret_gemini_response(response_text):
    """Interpreta a resposta do Gemini para extrair o sinal."""
    if response_text is None:
        return None

    if "sinal=compra" in response_text.lower():
        print("🟢 Sinal de \033[1;32mCOMPRA\033[0m recebido do Gemini.\n")
        time.sleep(1)
        return True
    elif "sinal=venda" in response_text.lower():
        print("🔴 Sinal de \033[1;31mVENDA\033[0m recebido do Gemini.\n")
        time.sleep(60)
        return False
    else:
        print("🟡 Sinal \033[1;33mNEUTRO\033[0m ou não interpretado do Gemini.\n")
        time.sleep(60)
        return None

def analyze_with_gemini(api_key, candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data):
    """Envia os dados das velas, padrões e indicadores para o Gemini e interpreta a resposta."""
    try:
        gemini_response = send_data_to_gemini(candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, historical_trades_data, 
                        api_key)

        # Verifica se a resposta do Gemini não é None antes de tentar acessá-la
        if gemini_response:
            #print(f"A resposta do Gemini foi gerada.") 
            print(f"\n\033[1;36mResposta do Gemini:\033[0m \033[1m{gemini_response}\033[0m")
            return gemini_response
        else:
            print("Resposta do Gemini é None.")
            time.sleep(60)
            return None

    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição HTTP: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
    time.sleep(60)
    return None
