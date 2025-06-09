import os
import sys
import json
from dotenv import load_dotenv

def find_file(filename, search_paths=None):
    """Поиск файла в указанных директориях"""
    if search_paths is None:
        search_paths = ['', 'venv', '.venv']
    
    for path in search_paths:
        filepath = os.path.join(path, filename)
        if os.path.exists(filepath):
            return filepath
    return None

def check_env_file():
    """Проверка наличия и заполненности файла .env"""
    env_path = find_file('.env')
    if not env_path:
        print("❌ Файл .env не найден. Создайте его на основе .env.sample")
        return False
    
    print(f"✅ Найден файл .env по пути: {env_path}")
    
    load_dotenv(env_path)
    ai_key = os.getenv('aiTonnelKey')
    firebase_url = os.getenv('FIREBASE_DATABASE_URL')
    
    if not ai_key or ai_key == 'your_aitunnel_key_here':
        print("❌ Не настроен aiTonnelKey в файле .env")
        return False
    
    if not firebase_url or firebase_url == 'your_firebase_database_url_here':
        print("❌ Не настроен FIREBASE_DATABASE_URL в файле .env")
        return False
    
    print("✅ Файл .env настроен корректно")
    return True

def check_firebase_creds():
    """Проверка наличия и валидности файла учетных данных Firebase"""
    creds_path = find_file('firebase-credentials.json')
    if not creds_path:
        print("❌ Файл firebase-credentials.json не найден в корне проекта, venv/ или .venv/")
        return False
    
    print(f"✅ Найден файл firebase-credentials.json по пути: {creds_path}")
    
    try:
        with open(creds_path, 'r') as f:
            creds = json.load(f)
            
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        for field in required_fields:
            if field not in creds or not creds[field]:
                print(f"❌ В файле firebase-credentials.json отсутствует или пустое поле: {field}")
                return False
            
        print("✅ Файл firebase-credentials.json настроен корректно")
        return True
        
    except json.JSONDecodeError:
        print("❌ Ошибка при чтении файла firebase-credentials.json: неверный формат JSON")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке файла firebase-credentials.json: {str(e)}")
        return False

def check_requirements():
    """Проверка установленных зависимостей"""
    try:
        import firebase_admin
        import faker
        import openai
        import python_dotenv
        print("✅ Все необходимые зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствуют необходимые зависимости: {str(e)}")
        print("   Установите их с помощью команды: pip install -r requirements.txt")
        return False

def main():
    print("🔍 Проверка настроек...\n")
    
    env_ok = check_env_file()
    firebase_ok = check_firebase_creds()
    deps_ok = check_requirements()
    
    print("\n" + "="*50)
    
    if env_ok and firebase_ok and deps_ok:
        print("\n✅ Всё настроено правильно! Вы можете запустить генератор данных командой:")
        print("   python generator.py")
    else:
        print("\n❌ Обнаружены проблемы с настройкой. Пожалуйста, исправьте отмеченные выше ошибки.")
    
    return 0 if (env_ok and firebase_ok and deps_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
