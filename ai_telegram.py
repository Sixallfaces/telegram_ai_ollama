# ai_telegram.py - ИСПРАВЛЕННАЯ ВЕРСИЯ ДЛЯ ТВОЕЙ ГРУППЫ
import asyncio
import random
import logging
import time
import json
import requests
from telethon import TelegramClient
from telethon.errors import FloodWaitError
import os
from dotenv import load_dotenv

# Загружаем настройки
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OllamaAISender:
    """Telegram отправитель с локальной Ollama ИИ"""
    
    def __init__(self):
        # Telegram API
        self.api_id = int(os.getenv('API_ID', 0))
        self.api_hash = os.getenv('API_HASH', '')
        self.phone = os.getenv('PHONE_NUMBER', '')
        self.client = None
        
        # Ollama настройки
        self.ollama_url = "http://localhost:11434"
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'phi')
        
        # Настройки безопасности
        self.max_per_day = int(os.getenv('MAX_MESSAGES_PER_DAY', 5))
        self.min_delay = int(os.getenv('MIN_DELAY_SECONDS', 120))
        self.max_delay = int(os.getenv('MAX_DELAY_SECONDS', 300))
        
        # Статистика
        self.sent_today = 0
        self.ai_requests = 0
        
        # Запасные шаблоны
        self.fallback_templates = [
            "Привет! Как дела?",
            "Здравствуйте! Нашел ваш профиль.",
            "Приветствую! Рад познакомиться.",
            "Добрый день! Заметил вашу активность.",
            "Привет! Интересный профиль.",
        ]
    
    async def connect(self):
        """Подключение к Telegram"""
        try:
            logger.info("🔗 Подключаемся к Telegram...")
            self.client = TelegramClient(
                'ollama_sender_session',
                self.api_id,
                self.api_hash,
                device_model="MacBook Pro 2018",
                system_version="macOS",
                app_version="1.0"
            )
            
            await self.client.start(phone=self.phone)
            
            me = await self.client.get_me()
            logger.info(f"✅ Успешный вход! Привет, {me.first_name}!")
            
            if self.check_ollama():
                logger.info(f"🤖 Ollama готова, модель: {self.ollama_model}")
            else:
                logger.warning("⚠️  Ollama не отвечает, будем использовать шаблоны")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            return False
    
    def check_ollama(self):
        """Проверка доступности Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate_with_ollama(self, username, first_name="", bio=""):
        """Генерация сообщения через Ollama"""
        self.ai_requests += 1
        
        if not self.check_ollama() or self.ai_requests > 20:
            return self.generate_fallback(first_name)
        
        try:
            prompt = f"""Напиши короткое приветственное сообщение (1-2 предложения) для {first_name or 'пользователя'}.
            
            Сообщение должно быть:
            - Дружелюбным, но не навязчивым
            - Без спама и рекламы
            - Естественным, как будто пишешь знакомому
            - На русском языке
            
            Не используй эмодзи в начале сообщения."""
            
            if bio:
                prompt += f"\n\nПользователь интересуется: {bio[:100]}"
            
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result.get("response", "").strip()
                message = self.clean_ai_response(message)
                logger.info(f"🤖 ИИ сгенерировал сообщение для @{username}")
                return message
            else:
                logger.warning(f"⚠️  Ollama ошибка: {response.status_code}")
                return self.generate_fallback(first_name)
                
        except Exception as e:
            logger.warning(f"⚠️  Ошибка ИИ: {e}, используем шаблон")
            return self.generate_fallback(first_name)
    
    def clean_ai_response(self, text):
        """Очистка ответа от ИИ"""
        text = text.strip('"').strip("'")
        tags_to_remove = ['Assistant:', 'AI:', 'Bot:', 'Ассистент:', 'Бот:']
        for tag in tags_to_remove:
            if text.startswith(tag):
                text = text[len(tag):].strip()
        text = ' '.join(text.split())
        if len(text) > 200:
            text = text[:200] + "..."
        return text
    
    def generate_fallback(self, first_name=""):
        """Запасной вариант - шаблонные сообщения"""
        template = random.choice(self.fallback_templates)
        if first_name:
            return f"{template}, {first_name}!"
        return template
    
    def generate_message(self, username, first_name="", bio=""):
        """Главная функция генерации сообщения"""
        if self.ai_requests < 10 and self.ai_requests % 3 == 0:
            return self.generate_with_ollama(username, first_name, bio)
        else:
            return self.generate_fallback(first_name)
    
    async def send_to_user(self, username):
        """Отправка сообщения пользователю"""
        try:
            if self.sent_today >= self.max_per_day:
                logger.warning(f"⚠️  Достигнут лимит: {self.sent_today}/{self.max_per_day}")
                return False
            
            user = await self.client.get_entity(username)
            first_name = user.first_name or ""
            bio = ""
            if hasattr(user, 'about') and user.about:
                bio = user.about
            
            message = self.generate_message(username, first_name, bio)
            await self.client.send_message(user, message)
            
            self.sent_today += 1
            logger.info(f"📨 Отправлено @{username}: {message[:50]}...")
            logger.info(f"   📊 Сегодня: {self.sent_today}/{self.max_per_day}")
            
            return True
            
        except FloodWaitError as e:
            logger.warning(f"⏳ Ожидание {e.seconds} секунд")
            await asyncio.sleep(e.seconds)
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки @{username}: {e}")
            return False
    
    async def parse_group(self, group_identifier, limit=5):
        """Парсинг пользователей из группы"""
        logger.info(f"🔍 Собираем пользователей из {group_identifier}")
        
        try:
            # Пробуем получить группу
            group = await self.client.get_entity(group_identifier)
            
            logger.info(f"✅ Нашли группу: {getattr(group, 'title', 'Без названия')}")
            
            members = []
            count = 0
            
            # Собираем участников
            async for user in self.client.iter_participants(group, limit=limit):
                if user.bot or user.deleted:
                    continue
                
                if user.username:
                    members.append({
                        'username': user.username,
                        'first_name': user.first_name or '',
                        'last_name': user.last_name or '',
                        'id': user.id
                    })
                    count += 1
                    if count >= limit:
                        break
                
                # Маленькая пауза
                await asyncio.sleep(0.1)
            
            # Сохраняем в JSON
            with open('parsed_users.json', 'w', encoding='utf-8') as f:
                json.dump(members, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Сохранено {len(members)} пользователей в parsed_users.json")
            return members
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга: {e}")
            print(f"\n🔧 Подробности ошибки: {e}")
            return []
    
    async def run_safe_campaign(self, usernames):
        """Безопасная рассылка"""
        logger.info(f"🚀 Начинаем рассылку на {len(usernames)} пользователей")
        
        success = 0
        
        for i, username in enumerate(usernames, 1):
            logger.info(f"📊 Прогресс: {i}/{len(usernames)}")
            
            if await self.send_to_user(username):
                success += 1
            
            delay = random.randint(self.min_delay, self.max_delay)
            logger.info(f"⏸️  Пауза {delay//60} мин {delay%60} сек...")
            await asyncio.sleep(delay)
            
            if i % 2 == 0:
                big_pause = random.randint(300, 600)
                logger.info(f"☕ Большая пауза {big_pause//60} минут...")
                await asyncio.sleep(big_pause)
            
            if self.sent_today >= self.max_per_day:
                logger.warning("🎯 Достигнут дневной лимит!")
                break
        
        logger.info(f"✅ Рассылка завершена! Успешно: {success}/{len(usernames)}")
    
    async def interactive_mode(self):
        """Интерактивный режим"""
        print("\n" + "="*50)
        print("🤖 TELEGRAM AI SENDER с Ollama")
        print("="*50)
        print(f"Модель ИИ: {self.ollama_model}")
        print(f"Лимит в день: {self.max_per_day} сообщений")
        print("="*50)
        print("1. Тест ИИ (без отправки)")
        print("2. Парсинг группы (используй ID: -4965837410)")
        print("3. Рассылка из файла")
        print("4. Ручная отправка")
        print("5. Статистика")
        print("6. Тест Ollama")
        print("0. Выход")
        print("="*50)
        
        while True:
            choice = input("\nВыберите действие (0-6): ").strip()
            
            if choice == "1":
                await self.test_ai_generation()
            elif choice == "2":
                await self.parse_group_menu()
            elif choice == "3":
                await self.send_from_file_menu()
            elif choice == "4":
                await self.manual_send_menu()
            elif choice == "5":
                self.show_stats()
            elif choice == "6":
                self.test_ollama()
            elif choice == "0":
                print("👋 Выход...")
                break
            else:
                print("❌ Неверный выбор")
    
    async def parse_group_menu(self):
        """Меню парсинга группы - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        print("\n📥 ПАРСИНГ ГРУППЫ")
        print("="*30)
        print("Введи ID группы (например: -1001234567890 или -4965837410)")
        print("Или @username (например: @groupname)")
        print("="*30)
        
        group_input = input("Введите ID или @username: ").strip()
        
        # Определяем тип идентификатора
        if group_input.startswith('-100'):
            # Это супергруппа/канал
            group_identifier = int(group_input)
            print(f"🔍 Супергруппа: {group_identifier}")
        elif group_input.startswith('-') and group_input[1:].isdigit():
            # Это обычная группа (отрицательный ID) - НЕ ПРЕОБРАЗОВЫВАЕМ!
            group_identifier = int(group_input)
            print(f"🔍 Обычная группа: {group_identifier}")
        elif group_input.isdigit():
            # Это числовой ID (положительный) - возможно это ID пользователя
            print(f"⚠️  {group_input} - это положительный ID. Группы имеют отрицательный ID!")
            return
        elif group_input.startswith('@'):
            # Это username
            group_identifier = group_input
            print(f"🔍 Username: {group_identifier}")
        else:
            # Пробуем как username без @
            group_identifier = f"@{group_input}"
            print(f"🔍 Username: {group_identifier}")
        
        limit = input("Сколько пользователей собрать? (1-10): ").strip()
        
        try:
            limit = int(limit)
            if limit > 10:
                print("⚠️  Для безопасности максимум 10")
                limit = 10
        except:
            limit = 5
        
        print(f"\n🔍 Парсим {group_identifier}, собираем {limit} пользователей...")
        members = await self.parse_group(group_identifier, limit)
        
        if members:
            print(f"\n✅ Собрано {len(members)} пользователей:")
            for i, member in enumerate(members[:5], 1):
                print(f"  {i}. 👤 @{member['username']} - {member['first_name']}")
            if len(members) > 5:
                print(f"  ... и еще {len(members)-5} пользователей")
        else:
            print("❌ Не удалось собрать пользователей")
    
    async def test_ai_generation(self):
        """Тест генерации сообщений ИИ"""
        print("\n🧪 ТЕСТ ГЕНЕРАЦИИ СООБЩЕНИЙ")
        print("-"*30)
        
        test_cases = [
            {"name": "Иван", "bio": "программист, Python, стартапы"},
            {"name": "Анна", "bio": "дизайнер, UI/UX, рисование"},
            {"name": "Алексей", "bio": "бизнес, маркетинг, путешествия"},
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\nТест {i}: {case['name']} - {case['bio']}")
            message = self.generate_with_ollama(
                username=f"test_user_{i}",
                first_name=case['name'],
                bio=case['bio']
            )
            print(f"🤖 Сообщение: {message}")
            if i < len(test_cases):
                time.sleep(2)
    
    async def send_from_file_menu(self):
        """Рассылка из файла"""
        if not os.path.exists('parsed_users.json'):
            print("❌ Файл parsed_users.json не найден")
            print("   Сначала спарси группу (пункт 2)")
            return
        
        with open('parsed_users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        if not users:
            print("❌ В файле нет пользователей")
            return
        
        usernames = [user['username'] for user in users if user.get('username')]
        
        print(f"\n📋 Найдено {len(usernames)} пользователей")
        print(f"📊 Можно отправить: {self.max_per_day - self.sent_today}")
        
        if self.sent_today >= self.max_per_day:
            print("❌ Достигнут дневной лимит!")
            return
        
        # Ограничиваем количество для теста
        test_users = usernames[:min(3, len(usernames))]
        
        print(f"\n📋 Будет отправлено {len(test_users)} пользователям:")
        for i, username in enumerate(test_users, 1):
            print(f"  {i}. @{username}")
        
        confirm = input(f"\nНачать рассылку? (y/n): ").lower()
        
        if confirm == 'y':
            print("🚀 Начинаем рассылку...")
            await self.run_safe_campaign(test_users)
        else:
            print("❌ Отменено")
    
    async def manual_send_menu(self):
        """Ручная отправка"""
        username = input("Введите @username: ").replace('@', '').strip()
        
        if not username:
            print("❌ Пустой username")
            return
        
        print(f"\nОтправляем сообщение @{username}...")
        success = await self.send_to_user(username)
        
        if success:
            print("✅ Сообщение отправлено!")
        else:
            print("❌ Не удалось отправить")
    
    def show_stats(self):
        """Показать статистику"""
        print(f"\n📊 СТАТИСТИКА:")
        print(f"   🤖 Модель ИИ: {self.ollama_model}")
        print(f"   📨 Отправлено сегодня: {self.sent_today}/{self.max_per_day}")
        print(f"   🧠 Запросов к ИИ: {self.ai_requests}")
        print(f"   🔄 Осталось на сегодня: {self.max_per_day - self.sent_today}")
        
        if self.check_ollama():
            print("   ✅ Ollama работает")
        else:
            print("   ⚠️  Ollama не отвечает")
    
    def test_ollama(self):
        """Тест подключения к Ollama"""
        print("\n🧪 ТЕСТ OLLAMA")
        
        if self.check_ollama():
            print("✅ Ollama сервер работает")
            
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": "Напиши 'Привет, мир!'",
                        "stream": False
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Модель отвечает: {result.get('response', '')[:50]}...")
                else:
                    print(f"⚠️  Модель не отвечает: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Ошибка: {e}")
        else:
            print("❌ Ollama сервер не запущен")
            print("\n🔧 Запусти Ollama:")
            print("   brew services start ollama")
    
    async def disconnect(self):
        """Отключение от Telegram"""
        if self.client:
            await self.client.disconnect()
            logger.info("👋 Отключились от Telegram")

async def main():
    """Основная функция"""
    print("🤖 Запуск Telegram AI Sender с Ollama...")
    
    bot = OllamaAISender()
    
    if not await bot.connect():
        print("\n❌ Не удалось подключиться")
        return
    
    try:
        await bot.interactive_mode()
    except KeyboardInterrupt:
        print("\n\n⚠️  Программа прервана")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.disconnect()
        print("\n✅ Работа завершена!")

if __name__ == "__main__":
    asyncio.run(main())