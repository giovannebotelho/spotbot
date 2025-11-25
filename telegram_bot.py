import aiohttp
import asyncio
import logging

class TelegramBot:
    def __init__(self, token, allowed_chat_id, command_handler):
        self.token = token
        self.allowed_chat_id = str(allowed_chat_id)
        self.command_handler = command_handler
        self.running = False
        self.offset = 0
        self.base_url = f"https://api.telegram.org/bot{token}"

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
        except Exception as e:
            # print(f"Erro de conexão Telegram: {e}")
            return []

    async def process_update(self, update, session):
        message = update.get('message')
        if not message: return
        
        chat_id = str(message['chat']['id'])
        text = message.get('text', '').strip()
        
        # Security check: only allow configured chat_id
        if chat_id != self.allowed_chat_id:
            print(f"⛔ Comando ignorado de chat_id desconhecido: {chat_id}")
            return
        
        if text.startswith('/'):
            print(f"📩 Comando recebido: {text}")
            response = await self.command_handler(text)
            if response:
                await self.send_message(session, chat_id, response)

    async def send_message(self, session, chat_id, text):
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
            await session.post(url, json=payload)
        except Exception as e:
            print(f"Erro ao enviar mensagem Telegram: {e}")
