import asyncio
import json
import logging
from typing import List, Dict
from telethon import TelegramClient
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)

class TelegramScraper:
    """Парсер Telegram групп/каналов"""
    
    def __init__(self, client: TelegramClient):
        self.client = client
    
    async def parse_group_members(self, group_identifier, limit: int = 20) -> List[Dict]:
        """
        Парсит участников группы
        group_identifier: @username, ссылка или ID группы
        """
        logger.info(f"🔍 Парсинг группы: {group_identifier}")
        
        try:
            # Получаем группу
            group = await self.client.get_entity(group_identifier)
            
            logger.info(f"✅ Найдена группа: {getattr(group, 'title', 'Без названия')}")
            
            members = []
            async for user in self.client.iter_participants(group, limit=limit):
                if user.bot or user.deleted or user.is_self:
                    continue
                
                user_info = {
                    'id': user.id,
                    'username': user.username or f"id{user.id}",
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'phone': user.phone or '',
                    'bio': getattr(user, 'about', '') or ''
                }
                
                members.append(user_info)
                
                # Пауза для избежания блокировки
                await asyncio.sleep(0.5)
            
            return members
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга: {e}")
            return []
    
    async def parse_group_messages(self, group_identifier, limit: int = 50) -> List[Dict]:
        """Парсит сообщения из группы"""
        try:
            group = await self.client.get_entity(group_identifier)
            
            messages = []
            async for message in self.client.iter_messages(group, limit=limit):
                if message.sender:
                    msg_info = {
                        'id': message.id,
                        'date': message.date.isoformat() if message.date else None,
                        'sender_id': message.sender_id,
                        'sender_name': self._get_sender_name(message.sender),
                        'text': message.text or '',
                        'has_media': bool(message.media)
                    }
                    messages.append(msg_info)
            
            return messages
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга сообщений: {e}")
            return []
    
    def _get_sender_name(self, sender):
        """Получает имя отправителя"""
        if not sender:
            return "Unknown"
        
        if hasattr(sender, 'first_name') and sender.first_name:
            return f"{sender.first_name} {sender.last_name or ''}".strip()
        elif hasattr(sender, 'title'):
            return sender.title
        elif hasattr(sender, 'username'):
            return f"@{sender.username}"
        
        return f"ID: {sender.id}"
    
    def save_to_json(self, data: List[Dict], filename: str = "parsed_data.json"):
        """Сохраняет данные в JSON файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Данные сохранены в {filename} ({len(data)} записей)")
        return filename