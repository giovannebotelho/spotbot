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
    
    time.sleep(2)
    
    pyautogui.hotkey('alt', 'tab')

    # Salva a screenshot em um arquivo
    # screenshot_folder = r"C:\Projetos\spotbot\prints"
    # os.makedirs(screenshot_folder, exist_ok=True)
    # timestamp = time.strftime("%Y%m%d-%H%M%S")
    # screenshot_path = os.path.join(screenshot_folder, f"screenshot_{timestamp}.png")
    # screenshot.save(screenshot_path)
    # print(f"Screenshot salva em: {screenshot_path}")

    return screenshot

def send_screenshot_to_gemini(image, api_key, model="gemini-2.0-flash-exp"):
    """
    Envia a screenshot para a API do Gemini para análise.
    """
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    image_bytes = buffered.getvalue()

    headers = {
        "Content-Type": "application/json",
    }

    prompt = (
        "Você é um assistente especializado em negociação de criptomoedas, focado em análise técnica do Bitcoin (BTC/USDT) no gráfico de 15 minutos da Binance."
        "Analise o gráfico fornecido e todos os dados presentes na tela, prestando atenção especial aos seguintes indicadores e padrões:\n\n"
        "1. **Tendência Atual:** Qual é a tendência atual do mercado (alta, baixa ou lateral)? Considere a direção do preço, topos e fundos, e a inclinação das EMAs.\n"
        "2. **RSI (Índice de Força Relativa):** O RSI está acima de 70 (sobrecompra), abaixo de 30 (sobrevenda) ou em uma zona neutra? Qual a direção do RSI (crescente, decrescente, lateral)?\n"
        "3. **MACD (Convergência e Divergência de Médias Móveis):** A linha MACD está acima ou abaixo da linha de sinal? O histograma do MACD está crescendo ou diminuindo? Há sinais de cruzamento (crossover) ou divergência?\n"
        "4. **VWAP (Preço Médio Ponderado por Volume):** O preço atual está acima ou abaixo do VWAP? Qual a relação do preço com o VWAP (distante, próximo, cruzando)?\n"
        "5. **EMAs (Médias Móveis Exponenciais):** Considere as EMAs de 7, 15, 25, 50, 100 e 200 períodos. Qual a relação do preço com essas EMAs (acima, abaixo, cruzando)? Qual a disposição das EMAs entre si (ordenadas para cima/baixa, próximas, distantes)? \n"
        "6. **Bandas de Bollinger:** O preço atual está próximo da banda superior, inferior ou média? As bandas estão se contraindo (volatilidade diminuindo) ou se expandindo (volatilidade aumentando)? Houve algum toque ou rompimento das bandas?\n"
        "7. **Padrões de Candle:** Identifique e interprete quaisquer padrões de candle significativos (por exemplo, martelo, estrela cadente, engolfo, doji, etc.) além de suportes e resistências.\n"
        "8. **Livro de Ordens:** Analise a profundidade do livro de ordens. Há mais ordens de compra ou venda? Qual a diferença de volume entre as ordens de compra e venda nos níveis de preço próximos ao preço atual? Isso indica pressão de compra ou venda?\n\n"
        "**Com base em sua análise detalhada de TODOS os indicadores e padrões acima, levando em consideração que estamos operando em período curto, com lucro projetado de 0.3 por cento, forneça uma recomendação clara e concisa:**\n\n"
        "Responda com:\n"
        "*   '**sinal=compra**' se for um bom momento para **comprar**.\n"
        "*   '**sinal=venda**' se for um bom momento para **vender**.\n"
        "*   '**sinal=neutro**' se não houver um sinal claro ou se for melhor aguardar.\n"
        "(OBS: Manter formato de resposta 'sinal=x' e não 'sinal:x' ou algo diferente, por exemplo.)\n\n"
        "**Justifique sua recomendação com base nos indicadores e padrões observados.** Seja específico e detalhista na sua explicação."
    )

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64.b64encode(image_bytes).decode("utf-8")
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
    print(f"Prompt enviada para o Gemini") # or print(f"Prompt enviada para o Gemini: {response.url}")

    return response.json()['candidates'][0]['content']['parts'][0]['text']

def interpret_gemini_response(response_text):
    """
    Interpreta a resposta do Gemini para extrair o sinal de compra ou venda.
    """
    if "sinal=compra" in response_text.lower():
        return True
    elif "sinal=venda" in response_text.lower():
        return False
    else:
        return None

def analyze_with_gemini(api_key, x, y, width, height):
    """
    Captura a screenshot da Binance, envia para o Gemini e interpreta a resposta.

    Returns:
        bool: True para compra, False para venda ou erro.
    """
    try:
        screenshot = get_binance_screenshot(x, y, width, height)
        if screenshot:
            gemini_response = send_screenshot_to_gemini(screenshot, api_key)
            signal = interpret_gemini_response(gemini_response)
            # print(f"\nResposta do Gemini: \033[1m{gemini_response}\033[0m")

            if signal is True:
                print("Sinal de \033[1;32mCOMPRA\033[0m recebido do Gemini.")
                time.sleep(1)
                return True
            elif signal is False:
                print("Sinal de \033[1;31mVENDA\033[0m recebido do Gemini.\n")
                time.sleep(53)
                return False
            else:
                print("Sinal \033[1;33mNEUTRO\033[0m ou não interpretado do Gemini.\n")
                time.sleep(53)
                return False  # Retorna False em caso de sinal neutro
        else:
            print("Não foi possível capturar a screenshot.")
            time.sleep(53)
            return False  # Retorna False se não conseguiu capturar a screenshot
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
        time.sleep(53)
        return False  # Retorna False em caso de erro

if __name__ == "__main__":
    GEMINI_API_KEY = os.getenv("gemini_api")
    SCREENSHOT_X = 5
    SCREENSHOT_Y = 90
    SCREENSHOT_WIDTH = 1920 # Foi pra 1920 para capturar toda a largura da tela
    SCREENSHOT_HEIGHT = 950 # Foi pra 950 para capturar quase toda a altura

    result = analyze_with_gemini(GEMINI_API_KEY, SCREENSHOT_X, SCREENSHOT_Y, SCREENSHOT_WIDTH, SCREENSHOT_HEIGHT)
    if result is not None:
        print(f"Sinal recebido: {'Compra' if result else 'Venda'}")
    else:
        print("Não foi possível obter um sinal claro do Gemini.")
