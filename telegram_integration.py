import aiohttp
import asyncio

async def send_telegram_message(bot_token, chat_id, message):
    """
    Envia uma mensagem para um chat do Telegram usando a API do Telegram (Async).
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                return await response.json()
    except Exception as e:
        print(f"🚨 Erro ao enviar mensagem: {e}")
        return None

# https://api.telegram.org/bot{TOKEN}/getUpdates
