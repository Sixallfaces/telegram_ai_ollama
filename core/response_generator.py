import json
from typing import Dict, Any

class ResponseGenerator:
    """Генератор ответов на основе конфигурации"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.templates = config.get('templates', {})
    
    def generate_from_template(self, template_name: str, context: Dict = None) -> str:
        """Генерирует ответ из шаблона"""
        template = self.templates.get(template_name)
        
        if not template:
            return self.templates.get('fallback', 'Извините, я не понял вопрос.')
        
        # Подстановка значений из контекста
        if context:
            for key, value in context.items():
                placeholder = '{' + key + '}'
                if placeholder in template:
                    template = template.replace(placeholder, str(value))
        
        return template
    
    def generate_entity_prompt(self, entity_name: str) -> str:
        """Генерирует запрос на ввод сущности"""
        prompts = {
            'user_name': 'Как вас зовут?',
            'user_email': 'На какой email вам отправить информацию?',
            'user_company': 'Из какой вы компании?',
            'preferred_date': 'Когда вам удобно?',
            'product_name': 'Какой продукт вас интересует?'
        }
        
        return prompts.get(entity_name, f'Пожалуйста, укажите {entity_name}')
    
    def generate_next_question(self, context: Dict) -> str:
        """Генерирует следующий вопрос"""
        return "Что еще вас интересует?"
    
    def generate_tool_response(self, tool_result: Dict) -> str:
        """Генерирует ответ на основе результата инструмента"""
        return tool_result.get('message', 'Готово!')