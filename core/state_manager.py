import json
from typing import Dict, Any, Optional

class StateManager:
    """Менеджер состояния диалога"""
    
    def __init__(self):
        self.user_states = {}
    
    def get_user_context(self, user_id: str) -> Dict:
        """Возвращает контекст пользователя"""
        return self.user_states.get(user_id, {})
    
    def set_user_context(self, user_id: str, context: Dict):
        """Устанавливает контекст пользователя"""
        self.user_states[user_id] = context
    
    def update_dialog_history(self, user_id: str, user_message: str, bot_response: str):
        """Обновляет историю диалога"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                'dialog_history': [],
                'context': {}
            }
        
        if 'dialog_history' not in self.user_states[user_id]:
            self.user_states[user_id]['dialog_history'] = []
        
        self.user_states[user_id]['dialog_history'].append({
            'user': user_message,
            'bot': bot_response
        })
        
        # Ограничиваем историю последними 10 сообщениями
        if len(self.user_states[user_id]['dialog_history']) > 10:
            self.user_states[user_id]['dialog_history'] = self.user_states[user_id]['dialog_history'][-10:]
    
    def clear_user_context(self, user_id: str):
        """Очищает контекст пользователя"""
        if user_id in self.user_states:
            del self.user_states[user_id]