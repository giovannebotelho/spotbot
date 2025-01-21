import requests
import time
import io
import base64
import os
from dotenv import load_dotenv
import pyautogui

load_dotenv()

def get_binance_screenshot(x, y, width, height):
    """
    Captura uma screenshot da área especificada na tela.
    Assume que a janela do Chrome com a Binance já está aberta e maximizada.
    """
    # Aguarda um pouco para garantir que a janela do Chrome esteja ativa
    time.sleep(2)

    # Traz a janela do Chrome para o primeiro plano (se necessário)
    try:
        chrome_window = pyautogui.getWindowsWithTitle("Bitcoin to USDT - Binance Spot")[0]
        if not chrome_window.isActive:
            chrome_window.activate()
        if chrome_window.isMinimized:
            chrome_window.restore()
        chrome_window.maximize()
    except IndexError:
        print("Janela da Binance não encontrada. Certifique-se de que ela está aberta, maximizada e com o título correto.")
        return None
    
    time.sleep(2)

    # Move o mouse para a posição desejada antes de tirar a screenshot
    pyautogui.moveTo(1420, 580)
    
    time.sleep(1)
    
    pyautogui.moveTo(1420, 590)
    
    time.sleep(2) # Espera para a estabilização

    # Captura a screenshot
    screenshot = pyautogui.screenshot(region=(x, y, width, height))

    # Salva a screenshot em um arquivo
    screenshot_folder = r"C:\Projetos\spotbot\prints"
    os.makedirs(screenshot_folder, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    screenshot_path = os.path.join(screenshot_folder, f"screenshot_{timestamp}.png")
    screenshot.save(screenshot_path)
    print(f"Screenshot salva em: {screenshot_path}")

    return screenshot

def get_tradingview_screenshot(x, y, width, height):
    """
    Captura uma screenshot da área especificada na tela da janela do TradingView.
    Assume que a janela do Chrome com o TradingView já está aberta e maximizada.
    """
    # Aguarda um pouco para garantir que a janela do Chrome esteja ativa
    time.sleep(2)

    # Traz a janela do Chrome para o primeiro plano (se necessário)
    try:
        chrome_window = pyautogui.getWindowsWithTitle("BTCUSD")[0]
        if not chrome_window.isActive:
            chrome_window.activate()
        if chrome_window.isMinimized:
            chrome_window.restore()
        chrome_window.maximize()
    except IndexError:
        print("Janela do TradingView não encontrada. Certifique-se de que ela está aberta, maximizada e com o título correto.")
        return None

    time.sleep(2)

    # Captura a screenshot
    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    
    time.sleep(2)
    
    pyautogui.keyDown('ctrl')
    time.sleep(0.5)  # Espera meio segundo
    pyautogui.press('tab')
    pyautogui.press('tab')
    pyautogui.keyUp('ctrl')

    # Salva a screenshot em um arquivo (opcional)
    screenshot_folder = r"C:\Projetos\spotbot\prints"  # Modifique para o caminho desejado
    os.makedirs(screenshot_folder, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    screenshot_path = os.path.join(screenshot_folder, f"screenshot_tradingview_{timestamp}.png")
    screenshot.save(screenshot_path)
    print(f"Screenshot do TradingView salva em: {screenshot_path}")

    return screenshot

def send_screenshots_to_gemini(binance_image, tradingview_image, api_key, model="gemini-2.0-flash-exp"):
    """
    Envia as screenshots da Binance e do TradingView para a API do Gemini para análise.
    """
    binance_buffered = io.BytesIO()
    binance_image.save(binance_buffered, format="PNG")
    binance_image_bytes = binance_buffered.getvalue()

    tradingview_buffered = io.BytesIO()
    tradingview_image.save(tradingview_buffered, format="PNG")
    tradingview_image_bytes = tradingview_buffered.getvalue()

    headers = {
        "Content-Type": "application/json",
    }

    prompt = (
        "Você é um assistente especializado em negociação de criptomoedas, focado em análise técnica do Bitcoin (BTC/USDT) no gráfico de 15 minutos da Binance e TradingView. "
        "Analise os gráficos fornecidos e todos os dados presentes na tela, com um viés conservador, priorizando a preservação do capital e buscando identificar oportunidades de compra com baixo risco e alta probabilidade de sucesso. "
        "Preste atenção especial aos seguintes indicadores e padrões, considerando o contexto do mercado e a volatilidade atual:\n\n"
        "1. **Contexto de Mercado:** Avalie o sentimento geral do mercado (otimista, neutro ou pessimista) e identifique se o Bitcoin está seguindo a tendência geral do mercado ou se há divergências. Considere notícias relevantes, eventos recentes e o desempenho de outras criptomoedas. \n"
        "2. **Volatilidade:** Analise a volatilidade do mercado. O preço está oscilando muito ou pouco? As bandas de Bollinger estão se expandindo ou contraindo? Identifique se o momento é propício para entradas rápidas ou se é melhor aguardar por maior estabilidade. \n"
        "3. **Tipos de Fundos:** Identifique a presença de fundos de alta ou de baixa no gráfico. Observe a formação de topos e fundos, a inclinação das médias móveis e o comportamento do volume para determinar a força dos compradores e vendedores. \n"
        "4. **Tendência Atual:** Qual é a tendência atual do mercado (alta, baixa ou lateral)? Considere a direção do preço, topos e fundos, e a inclinação das EMAs. \n"
        "5. **RSI (Índice de Força Relativa):** O RSI está acima de 70 (sobrecompra), abaixo de 30 (sobrevenda) ou em uma zona neutra? Qual a direção do RSI (crescente, decrescente, lateral)? Há divergências entre o RSI e o preço? \n"
        "6. **MACD (Convergência e Divergência de Médias Móveis):** A linha MACD está acima ou abaixo da linha de sinal? O histograma do MACD está crescendo ou diminuindo? Há sinais de cruzamento (crossover) ou divergência? \n"
        "7. **VWAP (Preço Médio Ponderado por Volume):** O preço atual está acima ou abaixo do VWAP? Qual a relação do preço com o VWAP (distante, próximo, cruzando)? \n"
        "8. **EMAs (Médias Móveis Exponenciais):** Considere as EMAs de 7, 15, 25, 50, 100 e 200 períodos. Qual a relação do preço com essas EMAs (acima, abaixo, cruzando)? Qual a disposição das EMAs entre si (ordenadas para cima/baixa, próximas, distantes)? \n"
        "9. **Bandas de Bollinger:** O preço atual está próximo da banda superior, inferior ou média? As bandas estão se contraindo (volatilidade diminuindo) ou se expandindo (volatilidade aumentando)? Houve algum toque ou rompimento das bandas? \n"
        "10. **Padrões de Candle:** Identifique e interprete quaisquer padrões de candle significativos (por exemplo, martelo, estrela cadente, engolfo, doji, etc.) além de suportes e resistências. \n"
        "11. **Livro de Ordens:** Analise a profundidade do livro de ordens. Há mais ordens de compra ou venda? Qual a diferença de volume entre as ordens de compra e venda nos níveis de preço próximos ao preço atual? Isso indica pressão de compra ou venda? \n\n"
        "Com base em sua análise detalhada de TODOS os indicadores e padrões acima, levando em consideração que estamos operando em período curto, com lucro projetado de 0.3 por cento, forneça uma recomendação clara e concisa: \n\n"
        "Responda com: \n"
        "*   '**sinal=compra**' se for um bom momento para **comprar**, com base em uma confluência de indicadores e padrões que indiquem alta probabilidade de sucesso. \n"
        "*   '**sinal=venda**' se for um bom momento para **vender**, com base em uma confluência de indicadores e padrões que indiquem alta probabilidade de queda. \n"
        "*   '**sinal=neutro**' se não houver um sinal claro, se houver sinais conflitantes, ou se o risco for considerado alto para a meta de lucro definida. \n"
        "(OBS: Manter formato de resposta 'sinal=x' e não 'sinal:x' ou algo diferente, por exemplo.)\n\n"
        "Justifique sua recomendação com base nos indicadores e padrões observados, no contexto de mercado e na volatilidade atual. Seja específico e detalhista na sua explicação. "
        "Explique como cada indicador e padrão contribui para a sua decisão, e se há algum indicador ou padrão que sugira cautela ou que invalide a sua recomendação."
    )

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64.b64encode(binance_image_bytes).decode("utf-8")
                        }
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64.b64encode(tradingview_image_bytes).decode("utf-8")
                        }
                    },
                    {
                        "text": prompt
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

    # URL da API corrigida e com a barra antes do v1beta
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
    print(f"Prompts enviadas para o Gemini") # OR print(f"Prompt enviada para o Gemini: {response.url}")

    return response.json()['candidates'][0]['content']['parts'][0]['text']

def interpret_gemini_response(response_text):
    """
    Interpreta a resposta do Gemini para extrair o sinal de compra ou venda.
    """
    if "sinal=compra" in response_text.lower():
        print("Sinal de \033[1;32mCOMPRA\033[0m recebido do Gemini.")
        time.sleep(1)
        return True
    elif "sinal=venda" in response_text.lower():
        print("Sinal de \033[1;31mVENDA\033[0m recebido do Gemini.\n")
        time.sleep(45)
        return False
    else:
        print("Sinal \033[1;33mNEUTRO\033[0m ou não interpretado do Gemini.\n")
        time.sleep(45)
        return None

def analyze_with_gemini(api_key, binance_x, binance_y, binance_width, binance_height, tradingview_x, tradingview_y, tradingview_width, tradingview_height):
    """
    Captura as screenshots da Binance e do TradingView, envia para o Gemini e retorna a resposta.

    Returns:
        str or None: A resposta do Gemini em formato de texto, ou None em caso de erro.
    """
    try:
        binance_screenshot = get_binance_screenshot(binance_x, binance_y, binance_width, binance_height)
        tradingview_screenshot = get_tradingview_screenshot(tradingview_x, tradingview_y, tradingview_width, tradingview_height)

        if binance_screenshot and tradingview_screenshot:
            gemini_response = send_screenshots_to_gemini(binance_screenshot, tradingview_screenshot, api_key)
            # Retorna a resposta do Gemini diretamente
            print(f"\nResposta do Gemini: \033[1m{gemini_response}\033[0m")
            return gemini_response
        else:
            print("Não foi possível capturar uma ou ambas as screenshots.")
            time.sleep(45)
            return None  # Retorna None se não conseguiu capturar as screenshots
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
        time.sleep(45)
        return None  # Retorna None em caso de erro