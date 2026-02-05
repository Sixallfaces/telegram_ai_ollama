import requests
import json
import re
from typing import Dict, Any, List

class NLUModule:
    """Улучшенный модуль понимания естественного языка"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "phi"):
        self.ollama_url = ollama_url
        self.model = model
        self.intent_keywords = {
            'express_interest': ['хочу', 'интерес', 'интересно', 'интересует', 'расскажи', 'покажи', 'подробнее'],
            'ask_about_product': ['работа', 'делаешь', 'умеешь', 'возможности', 'функции', 'что ты'],
            'request_price': ['цена', 'стоимость', 'сколько стоит', 'прайс', 'тариф'],
            'schedule_meeting': ['встреча', 'звонок', 'созвон', 'демо', 'демонстрация', 'запись', 'записаться'],
            'decline_offer': ['не интересно', 'не надо', 'отказ', 'нет спасибо', 'не хочу'],
            'request_info': ['информация', 'контакты', 'связаться', 'связь', 'поддержка']
        }
    
    def extract_intent_and_entities(self, text: str, context: Dict = None) -> Dict:
        """
        Определяет намерение и извлекает сущности
        Используем комбинацию правил и LLM
        """
        text_lower = text.lower().strip()
        
        # 1. Сначала проверяем по ключевым словам (быстро)
        detected_intent = self._rule_based_intent(text_lower)
        
        # 2. Если не нашли или уверенность низкая, используем LLM
        if detected_intent == 'unknown':
            detected_intent = self._llm_based_intent(text)
        
        # 3. Извлекаем сущности
        entities = self._extract_entities(text)
        
        return {
            "intent": detected_intent,
            "entities": entities,
            "confidence": 0.8 if detected_intent != 'unknown' else 0.3
        }
    
    def _rule_based_intent(self, text: str) -> str:
        """Определение намерения по правилам"""
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return intent
        
        # Специальные случаи
        if any(word in text for word in ['привет', 'здравствуй', 'добрый', 'hi', 'hello']):
            return 'greeting'
        elif any(word in text for word in ['спасибо', 'благодарю']):
            return 'thanks'
        elif any(word in text for word in ['пока', 'до свидания', 'выход']):
            return 'goodbye'
        
        return 'unknown'
    
    def _llm_based_intent(self, text: str) -> str:
        """Определение намерения через LLM"""
        try:
            prompt = f"""
            Пользователь написал: "{text}"
            
            Определи основное намерение из списка:
            - greeting (приветствие)
            - express_interest (проявил интерес)
            - ask_about_product (спросил о продукте/работе)
            - request_price (запросил цену)
            - schedule_meeting (хочет встретиться/записаться)
            - request_info (запросил информацию)
            - thanks (поблагодарил)
            - goodbye (попрощался)
            - unknown (не понятно)
            
            Ответь ТОЛЬКО одним словом из списка выше.
            """
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                intent = result.get('response', 'unknown').strip().lower()
                return intent if intent in ['greeting', 'express_interest', 'ask_about_product', 
                                          'request_price', 'schedule_meeting', 'request_info',
                                          'thanks', 'goodbye', 'unknown'] else 'unknown'
                
        except Exception as e:
            print(f"NLU LLM Error: {e}")
            
        return 'unknown'
    
    def _extract_entities(self, text: str) -> Dict:
        """Извлечение сущностей из текста"""
        entities = {}
        
        # Имя (слова с заглавной буквы, кроме начала предложения)
        name_pattern = r'(?:меня зовут|мое имя|зовут)\s+([А-Я][а-я]+)'
        name_match = re.search(name_pattern, text, re.IGNORECASE)
        if name_match:
            entities['name'] = name_match.group(1)
        
        # Email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, text)
        if email_match:
            entities['email'] = email_match.group()
        
        # Компания
        company_pattern = r'(?:компания|работаю в|из)\s+([«"]?[А-ЯA-Z][^,.!?]+[»"]?)'
        company_match = re.search(company_pattern, text, re.IGNORECASE)
        if company_match:
            entities['company'] = company_match.group(1)
        
        # Дата и время
        date_pattern = r'(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})|(завтра|послезавтра|понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)'
        date_match = re.search(date_pattern, text, re.IGNORECASE)
        if date_match:
            entities['date'] = date_match.group()
        
        # Время
        time_pattern = r'(\d{1,2}:\d{2})|(утром|днем|вечером|ночью|после обеда)'
        time_match = re.search(time_pattern, text, re.IGNORECASE)
        if time_match:
            entities['time'] = time_match.group()
        
        # Телефон
        phone_pattern = r'[\+]?[78][\s\(]?\d{3}[\)\s]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            entities['phone'] = phone_match.group()
        
        return entities