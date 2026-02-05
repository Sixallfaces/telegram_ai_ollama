import json
from typing import Dict, Any

class ConfigLoader:
    """Загрузчик конфигурационных файлов"""
    
    @staticmethod
    def load_config(file_path: str) -> Dict:
        """Загружает конфиг из JSON файла"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def validate_config(config: Dict) -> bool:
        """Валидирует конфигурацию"""
        required_sections = ['agent_config', 'goals', 'intents', 'templates']
        
        for section in required_sections:
            if section not in config:
                return False
        
        return True