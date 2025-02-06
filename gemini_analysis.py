import requests
import time

from dotenv import load_dotenv

load_dotenv()

def send_data_to_gemini(candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, api_key, model="gemini-2.0-flash-exp"):
    """Envia os dados das velas, padrões e indicadores para a API do Gemini."""

    headers = {
        "Content-Type": "application/json",
    }

    prompt = (
        "Você é um assistente especializado em negociação de criptomoedas, focado em análise técnica do Bitcoin (BTC/USDT) no gráfico de **1 hora (1h)** da Binance. "
        "Analise os dados das velas, padrões de vela, indicadores técnicos e dados do livro de ofertas fornecidos, com um viés equilibrado, considerando tanto a preservação do capital quanto a busca por oportunidades de compra com **risco moderado e boa probabilidade de sucesso** em um horizonte de **curto a médio prazo**, alinhado com um **lucro alvo de 0.5%**.\n\n"
        "Preste atenção especial aos seguintes indicadores e padrões, considerando o contexto do mercado e a volatilidade atual:\n\n"
        "1. **Dados das Velas:** Analise os preços de abertura, fechamento, máximo e mínimo de cada vela, bem como o volume do último candle. Identifique tendências, suportes e resistências.\n"
        "2. **Padrões de Vela:** Identifique e interprete os padrões de vela fornecidos. Considere o contexto em que esses padrões aparecem (em suportes/resistências, após movimentos fortes, etc.).\n"
        "3. **Indicadores Técnicos:** Analise o RSI, MACD e as Bandas de Bollinger para identificar condições de sobrecompra/sobrevenda, divergências e possíveis reversões de tendência.\n"
        "4. **Volume do Último Candle:** Considere o volume do último candle. Um volume alto pode indicar um maior interesse no ativo e aumentar a probabilidade de movimentos significativos.\n"
        "5. **Volume de Negociação em 24h:** Avalie o volume total de negociação nas últimas 24 horas para identificar a liquidez do mercado e possíveis níveis de suporte e resistência.\n"
        "6. **Variação de Preço em 24h:** Analise a variação de preço nas últimas 24 horas para entender a tendência de curto prazo e identificar possíveis pontos de entrada ou saída.\n"
        "7. **VWAP:** Analise o VWAP e sua relação com o preço atual. \n"
        "8. **Tendência:** Analise a tendência. \n"
        "9. **Limiar de pressão de venda:** Analise o limiar de pressão de venda. \n"
        "10. **Período de cálculo do RSI e médias móveis:** Analise o período de cálculo do RSI e médias móveis. \n"
        "11. **Número desvios padrões Bollinger:** Analise o número de desvios padrões de bollinger. \n"
        "12. **Período curto cálculo média móvel <> tendência:** Analise o período curto cálculo média móvel. \n"
        "13. **Período longo cálculo média móvel <> tendência:** Analise o período longo cálculo média móvel. \n"
        "14. **Limite dados históricos para recuperar de uma vez:** Analise o limite de dados históricos para recuperar de uma vez. \n"
        "15. **Profundidade do livro de ofertas:** Analise a profundidade do livro de ofertas. \n"
        "16. **Tamanho máximo para deque:** Analise o tamanho máximo para deque. \n"
        "17. **Condicional volume:** Analise o condicional volume.\n"
        "18. **Pressão de Venda:** Avalie a pressão de venda média para determinar o sentimento do mercado e identificar possíveis oportunidades de compra em momentos de baixa.\n"
        "19. **Livro de Ofertas:** Analise a profundidade do livro de ofertas para identificar níveis de suporte e resistência, bem como a liquidez do mercado.\n"
        "Com base em sua análise detalhada dos dados das velas, padrões, indicadores e livro de ofertas, e considerando que estamos buscando operações de **curto prazo** com um **lucro alvo de 0.5%** e um **stop loss de 0.6%**, forneça uma recomendação clara e concisa:\n\n"
        "Responda com:\n"
        "*   '**sinal=compra**' se for um bom momento para **comprar**, com base em uma confluência de indicadores e padrões que indiquem alta probabilidade de sucesso, considerando o risco definido (stop loss de 0.5%).\n"
        "*   '**sinal=venda**' se for um bom momento para **vender**, com base em uma confluência de indicadores e padrões que indiquem alta probabilidade de queda.\n"
        "*   '**sinal=neutro**' se não houver um sinal claro, se houver sinais conflitantes, ou se o risco for considerado alto para a meta de lucro definida.\n\n"
        "**Importante:**\n"
        "*   Mantenha o formato de resposta exatamente como especificado acima ('sinal=compra', 'sinal=venda' ou 'sinal=neutro').\n"
        "*   Justifique sua recomendação com base nos dados fornecidos."
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
    print(f"Prompt enviada para o Gemini: {response.url}")

    return response.json()['candidates'][0]['content']['parts'][0]['text']

def interpret_gemini_response(response_text):
    """Interpreta a resposta do Gemini para extrair o sinal."""
    if response_text is None:
        return None

    if "sinal=compra" in response_text.lower():
        print("Sinal de COMPRA recebido do Gemini.")
        time.sleep(1)
        return True
    elif "sinal=venda" in response_text.lower():
        print("Sinal de VENDA recebido do Gemini.")
        time.sleep(60)
        return False
    else:
        print("Sinal NEUTRO ou não interpretado do Gemini.")
        time.sleep(60)
        return None

def analyze_with_gemini(api_key, candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg):
    """Envia os dados das velas, padrões e indicadores para o Gemini e interpreta a resposta."""
    try:
        gemini_response = send_data_to_gemini(candle_data, candle_patterns, rsi, macd, bollinger_bands, sell_pressure, order_book, candle_open, candle_high, candle_low, candle_close, candle_volume, variation_24h, candle_variation, 
                        ema7, ema15, ema25, ema50, ema100, ema200, vwap, trend_is_up, SELL_PRESSURE_THRESHOLD_1, period, num_std, short_period, long_period, limit, depth, maxlen, volume_avg, api_key)

        # Verifica se a resposta do Gemini não é None antes de tentar acessá-la
        if gemini_response:
            print(f"\nResposta do Gemini: \033[1m{gemini_response}\033[0m")
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
