import json
from typing import Dict, Any, List

class DialogManager:
    """Управляет диалоговым потоком на основе конфигурации"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.current_goal = None
        self.current_step = 0
        self.completed_steps = []
        
    def initialize_conversation(self, intent: str) -> str:
        """Инициализирует диалог на основе намерения"""
        # Сопоставляем намерение с целью
        intent_to_goal = {
            "express_interest": "collect_contact_info",
            "schedule_meeting": "schedule_demo",
            "ask_about_product": "qualify_lead"
        }
        
        self.current_goal = intent_to_goal.get(intent, "collect_contact_info")
        self.current_step = 0
        
        # Получаем первый шаг диалога
        return self.get_next_action()
    
    def get_next_action(self, entity_collected: str = None, value: Any = None) -> Dict:
        """Возвращает следующее действие в диалоге"""
        if not self.current_goal:
            return {"type": "error", "message": "No active goal"}
        
        flow = self.config['dialog_flows'].get(self.current_goal, [])
        
        if self.current_step >= len(flow):
            return {"type": "complete", "message": "Goal completed"}
        
        action = flow[self.current_step]
        
        # Если это сбор сущности и она уже собрана, переходим к следующему шагу
        if action.get('type') == 'collect_entity' and entity_collected == action.get('entity'):
            self.completed_steps.append({
                'entity': entity_collected,
                'value': value
            })
            self.current_step += 1
            
            if self.current_step < len(flow):
                return flow[self.current_step]
            else:
                return {"type": "complete", "message": "Goal completed"}
        
        return action
    
    def get_current_context(self) -> Dict:
        """Возвращает текущий контекст диалога"""
        return {
            "goal": self.current_goal,
            "step": self.current_step,
            "completed": self.completed_steps,
            "collected_entities": {
                step['entity']: step['value'] 
                for step in self.completed_steps 
                if 'entity' in step
            }
        }