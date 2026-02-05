#!/usr/bin/env python3
"""
УНИВЕРСАЛЬНЫЙ ТЕЛЕГРАМ АГЕНТ С ПАРСИНГОМ И ДИАЛОГОМ
"""
import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List  # ДОБАВЛЕНО List
from dotenv import load_dotenv
from telethon import TelegramClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.nlu import NLUModule
    from core.dialog_manager import DialogManager
    from core.response_generator import ResponseGenerator
    from core.state_manager import StateManager
    from core.scraper import TelegramScraper
    from core.tools import ToolExecutor
except ImportError as e:
    logger.error(f"❌ Ошибка импорта: {e}")
    logger.info("Создайте недостающие файлы модулей")
    sys.exit(1)

class UniversalTelegramAgent:
    """Главный класс универсального агента"""
    
    def __init__(self, config_path: str = "config/leads.json"):
        # Загрузка конфигурации
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Инициализация модулей
        self.nlu = NLUModule(
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "phi")
        )
        
        self.dialog_manager = DialogManager(self.config)
        self.response_gen = ResponseGenerator(self.config)
        self.state_manager = StateManager()
        self.tool_executor = ToolExecutor(self.config.get('tools', []))
        
        # Telegram клиент
        self.client = None
        self.scraper = None
        
        logger.info(f"🤖 Агент инициализирован: {self.config['agent_config']['name']}")
        logger.info(f"🎯 Цели: {self.config['goals']}")
        logger.info(f"📊 Намерения: {', '.join(self.config['intents'])}")
    
    async def connect_telegram(self):
        """Подключение к Telegram"""
        try:
            api_id = int(os.getenv("API_ID"))
            api_hash = os.getenv("API_HASH")
            phone = os.getenv("PHONE_NUMBER")
            
            self.client = TelegramClient(
                'universal_agent_session',
                api_id,
                api_hash
            )
            
            await self.client.start(phone=phone)
            
            # Создаем скрапер
            self.scraper = TelegramScraper(self.client)
            
            me = await self.client.get_me()
            logger.info(f"✅ Подключились как: {me.first_name} (@{me.username})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Telegram: {e}")
            return False
    
    async def process_incoming_message(self, event):
        """Обработка входящего сообщения в Telegram"""
        user_id = str(event.sender_id)
        message_text = event.text
        
        if not message_text:
            return
        
        # Обрабатываем сообщение
        response = await self._process_message_logic(user_id, message_text)
        
        # Отправляем ответ
        await event.reply(response)
    
    async def _process_message_logic(self, user_id: str, message: str) -> str:
        """Логика обработки сообщения"""
        logger.info(f"📥 Сообщение от {user_id}: {message[:100]}")
        
        # 1. Получаем контекст
        context = self.state_manager.get_user_context(user_id)
        
        # 2. Анализируем намерение
        nlu_result = self.nlu.extract_intent_and_entities(message, context)
        intent = nlu_result['intent']
        entities = nlu_result['entities']
        
        logger.info(f"🧠 Намерение: {intent} (уверенность: {nlu_result['confidence']:.2f})")
        if entities:
            logger.info(f"📝 Сущности: {entities}")
        
        # 3. Обработка специальных намерений
        if intent == 'greeting':
            self.state_manager.clear_user_context(user_id)
            return self.response_gen.generate_from_template('welcome_message')
        
        elif intent == 'goodbye':
            self.state_manager.clear_user_context(user_id)
            return "До свидания! Буду рад помочь снова."
        
        elif intent == 'thanks':
            return "Всегда рад помочь! 😊"
        
        # 4. Если нет активного диалога, начинаем новый
        if not context.get('active_goal'):
            # Определяем цель по намерению
            goal_map = {
                'express_interest': 'collect_contact_info',
                'ask_about_product': 'qualify_lead',
                'request_price': 'collect_contact_info',
                'schedule_meeting': 'schedule_demo',
                'request_info': 'collect_contact_info'
            }
            
            goal = goal_map.get(intent, 'collect_contact_info')
            
            # Инициализируем диалог
            self.dialog_manager.initialize_conversation(goal)
            self.state_manager.set_user_context(user_id, {
                'active_goal': goal,
                'current_step': 0,
                'collected_data': {},
                'last_intent': intent
            })
            
            # Если есть сущности, сразу сохраняем
            if entities:
                self.state_manager.update_user_data(user_id, entities)
            
            # Возвращаем первый вопрос
            return self._get_next_question(user_id)
        
        # 5. Если диалог активен, продолжаем
        else:
            # Обновляем собранные данные
            if entities:
                self.state_manager.update_user_data(user_id, entities)
            
            # Переходим к следующему шагу
            return self._get_next_question(user_id)
    
    def _get_next_question(self, user_id: str) -> str:
        """Получает следующий вопрос для пользователя"""
        context = self.state_manager.get_user_context(user_id)
        goal = context.get('active_goal')
        step = context.get('current_step', 0)
        
        if not goal:
            return self.response_gen.generate_from_template('welcome_message')
        
        # Получаем следующий шаг из конфигурации
        flows = self.config.get('dialog_flows', {}).get(goal, [])
        
        if step >= len(flows):
            # Диалог завершен
            collected_data = context.get('collected_data', {})
            
            # Проверяем, есть ли достаточные данные
            if self._has_enough_data(collected_data):
                # Вызываем инструмент для сохранения лида
                self._save_lead_data(user_id, collected_data)
                
                # Очищаем контекст
                self.state_manager.clear_user_context(user_id)
                
                return self.response_gen.generate_from_template('success_message', collected_data)
            else:
                # Запрашиваем недостающие данные
                return self._ask_for_missing_data(collected_data)
        
        # Получаем текущий шаг
        current_step = flows[step]
        
        # Обновляем шаг
        self.state_manager.update_user_context(user_id, {'current_step': step + 1})
        
        # Генерируем ответ
        if current_step.get('type') == 'generate_response':
            template = current_step.get('template', 'welcome_message')
            return self.response_gen.generate_from_template(template, context.get('collected_data', {}))
        
        elif current_step.get('type') == 'collect_entity':
            entity = current_step.get('entity')
            template = current_step.get('question_template', f'ask_{entity}')
            
            # Проверяем, может быть уже собрали эту сущность
            if entity in context.get('collected_data', {}):
                return self._get_next_question(user_id)
            
            return self.response_gen.generate_from_template(template, {})
        
        return "Как я могу вам помочь?"
    
    def _has_enough_data(self, data: Dict) -> bool:
        """Проверяет, достаточно ли данных для сохранения лида"""
        required = ['name', 'email']
        return all(key in data and data[key] for key in required)
    
    def _ask_for_missing_data(self, data: Dict) -> str:
        """Запрашивает недостающие данные"""
        if 'name' not in data or not data['name']:
            return self.response_gen.generate_entity_prompt('user_name')
        elif 'email' not in data or not data['email']:
            return self.response_gen.generate_entity_prompt('user_email')
        
        return "Что еще вас интересует?"
    
    def _save_lead_data(self, user_id: str, data: Dict):
        """Сохраняет данные лида (заглушка)"""
        logger.info(f"💾 Сохранение лида от {user_id}: {data}")
        # Здесь будет вызов API CRM
    
    async def parse_group_command(self, group_identifier: str):
        """Команда парсинга группы"""
        if not self.scraper:
            return "❌ Не подключено к Telegram"
        
        logger.info(f"🔍 Начинаем парсинг группы: {group_identifier}")
        
        # Парсим участников
        members = await self.scraper.parse_group_members(group_identifier, limit=10)
        
        if members:
            # Сохраняем в файл
            filename = self.scraper.save_to_json(members, "parsed_members.json")
            
            # Анализируем аудиторию
            analysis = self._analyze_audience(members)
            
            return (f"✅ Спаршено {len(members)} участников\n"
                   f"💾 Сохранено в: {filename}\n"
                   f"📊 Анализ: {analysis}")
        else:
            return "❌ Не удалось спарсить группу"
    
    def _analyze_audience(self, members: List[Dict]) -> str:
        """Анализирует спаршенную аудиторию"""
        total = len(members)
        with_names = sum(1 for m in members if m.get('first_name'))
        with_usernames = sum(1 for m in members if m.get('username') and m['username'].startswith('@'))
        
        return f"{total} чел., {with_names} с именами, {with_usernames} с @username"
    
    async def start_conversation_with_user(self, username: str):
        """Начинает диалог с пользователем"""
        try:
            user = await self.client.get_entity(username)
            
            # Начинаем диалог
            welcome_msg = self.response_gen.generate_from_template('welcome_message')
            await self.client.send_message(user, welcome_msg)
            
            logger.info(f"💬 Начат диалог с @{username}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка начала диалога: {e}")
            return False
    
    async def interactive_mode(self):
        """Интерактивный режим управления"""
        print("\n" + "="*60)
        print("🤖 УНИВЕРСАЛЬНЫЙ ТЕЛЕГРАМ АГЕНТ")
        print("="*60)
        print("1. Тест диалога")
        print("2. Парсинг группы")
        print("3. Рассылка по спаршеным пользователям")
        print("4. Статистика")
        print("5. Запуск автоответчика")
        print("0. Выход")
        print("="*60)
        
        while True:
            choice = input("\nВыберите действие (0-5): ").strip()
            
            if choice == "1":
                await self.test_dialog()
            elif choice == "2":
                await self.parse_group_ui()
            elif choice == "3":
                await self.mass_messaging_ui()
            elif choice == "4":
                self.show_stats()
            elif choice == "5":
                await self.start_auto_responder()
            elif choice == "0":
                print("👋 Выход...")
                break
            else:
                print("❌ Неверный выбор")
    
    async def test_dialog(self):
        """Тестовый диалог"""
        print("\n🧪 ТЕСТ ДИАЛОГА")
        print("-"*30)
        
        test_user = "test_user_001"
        self.state_manager.clear_user_context(test_user)
        
        while True:
            user_input = input("\nВы: ").strip()
            
            if user_input.lower() in ['выход', 'exit']:
                break
            
            response = await self._process_message_logic(test_user, user_input)
            print(f"🤖: {response}")
    
    async def parse_group_ui(self):
        """UI для парсинга группы"""
        print("\n📥 ПАРСИНГ ГРУППЫ")
        print("-"*30)
        
        group_input = input("Введите ID группы (@username или числовой ID): ").strip()
        
        if not group_input:
            print("❌ Пустой ввод")
            return
        
        result = await self.parse_group_command(group_input)
        print(f"\n{result}")
    
    async def mass_messaging_ui(self):
        """Рассылка сообщений"""
        print("\n📨 РАССЫЛКА СООБЩЕНИЙ")
        print("-"*30)
        
        if not os.path.exists("parsed_members.json"):
            print("❌ Файл parsed_members.json не найден")
            print("   Сначала спарсите группу (пункт 2)")
            return
        
        with open("parsed_members.json", 'r', encoding='utf-8') as f:
            members = json.load(f)
        
        print(f"📋 Найдено {len(members)} пользователей")
        print("Примеры первых 5:")
        for i, member in enumerate(members[:5], 1):
            print(f"  {i}. @{member.get('username', 'N/A')} - {member.get('first_name', '')}")
        
        confirm = input("\nНачать рассылку? (y/n): ").lower()
        
        if confirm == 'y':
            print("🚀 Начинаем рассылку...")
            success_count = 0
            
            for member in members[:5]:  # Первые 5 для теста
                username = member.get('username')
                if username and not username.startswith('id'):
                    print(f"Отправляю @{username}...")
                    if await self.start_conversation_with_user(username):
                        success_count += 1
                        await asyncio.sleep(5)  # Пауза между отправками
            
            print(f"✅ Рассылка завершена. Успешно: {success_count}/{len(members[:5])}")
    
    def show_stats(self):
        """Показывает статистику"""
        print("\n📊 СТАТИСТИКА")
        print("-"*30)
        print(f"🤖 Агент: {self.config['agent_config']['name']}")
        print(f"🎯 Цели: {', '.join(self.config['goals'])}")
        print(f"🧠 Модель NLU: {self.nlu.model}")
        print(f"💾 Состояний в памяти: {len(self.state_manager.user_states)}")
    
    async def start_auto_responder(self):
        """Запускает автоответчика"""
        print("\n🤖 ЗАПУСК АВТООТВЕТЧИКА")
        print("-"*30)
        print("Бот будет отвечать на все входящие сообщения")
        print("Нажмите Ctrl+C для остановки")
        
        @self.client.on_message()
        async def handler(event):
            await self.process_incoming_message(event)
        
        try:
            await self.client.run_until_disconnected()
        except KeyboardInterrupt:
            print("\n⏹️  Автоответчик остановлен")

async def main():
    """Главная функция"""
    load_dotenv()
    
    print("\n🚀 Запуск Универсального Telegram Агента...")
    
    # Проверяем настройки
    required = ['API_ID', 'API_HASH', 'PHONE_NUMBER']
    missing = [key for key in required if not os.getenv(key)]
    
    if missing:
        print(f"❌ Отсутствуют настройки: {', '.join(missing)}")
        print("   Проверьте файл .env")
        return
    
    # Создаем агента
    agent = UniversalTelegramAgent("config/leads.json")
    
    # Подключаемся к Telegram
    if not await agent.connect_telegram():
        print("❌ Не удалось подключиться к Telegram")
        return
    
    # Запускаем интерактивный режим
    await agent.interactive_mode()
    
    # Отключаемся
    if agent.client:
        await agent.client.disconnect()
        print("✅ Отключились от Telegram")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Программа прервана")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()