import aiohttp
import asyncio
from pathlib import Path

async def send_telegram_message(bot_token, chat_id, message, reply_markup=None):
    """Envia uma mensagem assíncrona para o Telegram com suporte a botões inline."""
    if not bot_token or not chat_id:
        return None

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                return await response.json()
    except Exception as e:
        print(f"🚨 Erro ao enviar mensagem no Telegram: {e}")
        return None

async def send_telegram_document(bot_token, chat_id, file_path, caption=""):
    """Envia um arquivo PDF ou documento assíncrono para o Telegram."""
    if not bot_token or not chat_id:
        return None

    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    try:
        data = aiohttp.FormData()
        data.add_field('chat_id', str(chat_id))
        if caption:
            data.add_field('caption', caption)
            data.add_field('parse_mode', 'HTML')
        
        with open(file_path, 'rb') as f:
            data.add_field('document', f, filename=Path(file_path).name, content_type='application/pdf')
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    return await response.json()
    except Exception as e:
        print(f"🚨 Erro ao enviar documento no Telegram: {e}")
        return None

class TelegramBot:
    def __init__(self, token, allowed_chat_id, command_handler):
        self.token = token
        self.allowed_chat_id = str(allowed_chat_id)
        self.command_handler = command_handler
        self.running = False
        self.offset = 0
        self.base_url = f"https://api.telegram.org/bot{token}"

    def get_menu_keyboard(self):
        """Retorna o teclado inline com botões de toque rápido."""
        return {
            "inline_keyboard": [
                [
                    {"text": "📊 Status", "callback_data": "/status"},
                    {"text": "💰 Lucro Hoje", "callback_data": "/lucro"},
                ],
                [
                    {"text": "⚡ Posições Ativas", "callback_data": "/posicoes"},
                    {"text": "📄 Relatório PDF", "callback_data": "/relatorio"},
                ]
            ]
        }

    async def start(self):
        self.running = True
        print("🤖 Telegram Bot ouvindo comandos...")
        async with aiohttp.ClientSession() as session:
            while self.running:
                try:
                    updates = await self.get_updates(session)
                    for update in updates:
                        await self.process_update(update, session)
                        self.offset = update['update_id'] + 1
                except Exception as e:
                    print(f"⚠️ Erro no loop do Telegram: {e}")
                    await asyncio.sleep(5)
                await asyncio.sleep(1)

    async def stop(self):
        self.running = False

    async def get_updates(self, session):
        try:
            url = f"{self.base_url}/getUpdates?offset={self.offset}&timeout=10"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result', [])
                return []
        except Exception:
            return []

    async def process_update(self, update, session):
        # Suporte a Clique em Botões Inline
        if 'callback_query' in update:
            cb = update['callback_query']
            chat_id = str(cb.get('message', {}).get('chat', {}).get('id', ''))
            cb_id = cb.get('id')
            cmd_data = cb.get('data', '')
            
            if chat_id == self.allowed_chat_id and cmd_data.startswith('/'):
                try:
                    await session.post(f"{self.base_url}/answerCallbackQuery", json={"callback_query_id": cb_id})
                except Exception:
                    pass
                    
                response_text = await self.command_handler(cmd_data)
                if response_text:
                    await send_telegram_message(self.token, chat_id, response_text, reply_markup=self.get_menu_keyboard())
            return

        message = update.get('message', {})
        chat_id = str(message.get('chat', {}).get('id', ''))
        text = message.get('text', '')

        if chat_id != self.allowed_chat_id:
            return

        if text.startswith('/'):
            response_text = await self.command_handler(text)
            if response_text:
                await send_telegram_message(self.token, chat_id, response_text, reply_markup=self.get_menu_keyboard())
