#!/usr/bin/env python3
"""
Проверка настроек окружения
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("🔧 ПРОВЕРКА НАСТРОЕК ОКРУЖЕНИЯ")
print("="*50)

# Проверка обязательных полей
required = ['API_ID', 'API_HASH', 'PHONE_NUMBER']
all_ok = True

for key in required:
    value = os.getenv(key)
    if value:
        print(f"✅ {key}: {value[:10]}..." if len(str(value)) > 10 else f"✅ {key}: {value}")
    else:
        print(f"❌ {key}: НЕ НАЙДЕН")
        all_ok = False

print("\n📊 Дополнительные настройки:")
print(f"   OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL', 'phi')}")
print(f"   MAX_MESSAGES_PER_DAY: {os.getenv('MAX_MESSAGES_PER_DAY', '50')}")

if all_ok:
    print("\n✅ Все обязательные настройки найдены!")
    print("   Можете запускать бота командой: python main.py")
else:
    print("\n❌ Некоторые настройки отсутствуют")
    print("   Проверьте файл .env")

print("="*50)