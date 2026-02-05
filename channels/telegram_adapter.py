import os
import logging
from telethon import TelegramClient, events

logger = logging.getLogger(__name__)

class TelegramAdapter:
    """Адаптер для работы с Telegram"""
    
    def __init__(self):
        self.client = None
    
    async def connect(self, api_id: int, api_hash: str, phone: str) -> TelegramClient:
        """Подключается к Telegram"""
        self.client = TelegramClient(
            'universal_agent_session',
            api_id,
            api_hash
        )
        
        await self.client.start(phone=phone)
        logger.info("✅ Подключились к Telegram")
        
        return self.client