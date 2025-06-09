import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

def load_firebase_config() -> dict:
    """Загрузка конфигурации Firebase из файла .venv"""
    env_path = r'C:\\Users\\alexm.ALEXHOST\\PycharmProjects\\MyDevices\\venv\\.venv'
    
    # Проверяем существование файла
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Файл с переменными окружения не найден: {env_path}")
    
    # Читаем файл напрямую
    with open(env_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
        
    # Пытаемся найти JSON-строку с учетными данными
    import re
    import json
    
    # Ищем JSON-объект в файле
    json_match = re.search(r'\{.*\}', file_content, re.DOTALL)
    if not json_match:
        raise ValueError("Не удалось найти JSON с учетными данными в файле .venv")
    
    try:
        # Парсим JSON
        service_account = json.loads(json_match.group(0))
        print("Успешно загружен JSON с учетными данными")
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка при разборе JSON: {e}")
    
    # Получаем URL базы данных из переменных окружения
    db_url = None
    env_vars = {}
    for line in file_content.split('\n'):
        line = line.strip()
        if line.startswith('FIREBASE_DATABASE_URL'):
            _, value = line.split('=', 1)
            db_url = value.strip('"\'').strip()
            break
    
    if not db_url:
        raise ValueError("Не удалось найти FIREBASE_DATABASE_URL в файле .venv")
    
    return {
        'service_account': service_account,
        'database_url': db_url
    }

def initialize_firebase():
    """Инициализация Firebase"""
    if not firebase_admin._apps:
        config = load_firebase_config()
        cred = credentials.Certificate(config['service_account'])
        firebase_admin.initialize_app(cred, {
            'databaseURL': config['database_url']
        })
    return firestore.client()

def upload_data(db, data: dict):
    """Загрузка данных в Firestore"""
    batch = db.batch()
    
    # Загрузка городов
    print("Загрузка городов...")
    for city in data['cities']:
        doc_ref = db.collection('cities').document(city['cityID'])
        batch.set(doc_ref, {'name': city['name']})
    
    # Собираем уникальные подразделения из данных сотрудников
    divisions = set()
    positions = set()
    
    # Сначала проходим по всем сотрудникам, чтобы собрать уникальные подразделения и должности
    for emp in data['employees']:
        divisions.add(emp['division'])
        positions.add(emp['position'])
    
    # Загрузка подразделений
    print("Загрузка подразделений...")
    for i, division in enumerate(divisions, 1):
        doc_ref = db.collection('divisions').document(f'div_{i:03d}')
        batch.set(doc_ref, {'name': division})
    
    # Загрузка должностей
    print("Загрузка должностей...")
    for i, position in enumerate(positions, 1):
        doc_ref = db.collection('positions').document(f'pos_{i:03d}')
        batch.set(doc_ref, {'name': position})
    
    # Создаем словари для быстрого поиска ID по имени
    division_name_to_id = {name: f'div_{i:03d}' for i, name in enumerate(divisions, 1)}
    position_name_to_id = {name: f'pos_{i:03d}' for i, name in enumerate(positions, 1)}
    
    # Загрузка сотрудников
    print("Загрузка сотрудников...")
    for emp in data['employees']:
        doc_ref = db.collection('employees').document(emp['empID'])
        batch.set(doc_ref, {
            'fio': emp['fio'],
            'tn': emp['tn'],
            'position': position_name_to_id[emp['position']],
            'division': division_name_to_id[emp['division']],
            'location': emp['location'],
            'is_manager': emp.get('is_manager', False)
        })
    
    # Загрузка устройств
    print("Загрузка устройств...")
    for dev in data['devices']:
        doc_ref = db.collection('devices').document(dev['deviceID'])
        device_data = {
            'empID': dev['empID'],
            'type': dev['nomenclature'],  # Используем nomenclature как type
            'model': dev['model'],
            'status': dev['status'],
            'dateReceipt': dev['dateReceipt'],
            'usefulLife': dev['usefulLife']
        }
        
        # Добавляем дополнительные поля, если они есть
        if 'serial' in dev:
            device_data['serial'] = dev['serial']
        if 'ctc' in dev:  # Добавляем техническое состояние
            device_data['ctc'] = dev['ctc']
            
        batch.set(doc_ref, device_data)
    
    # Выполняем пакетную запись
    print("Выполнение пакетной записи...")
    batch.commit()

def main():
    # Проверяем наличие файла с данными
    if not os.path.exists('generated_data.json'):
        print("Ошибка: Файл generated_data.json не найден. Сначала выполните data_generator.py")
        return
    
    # Загружаем данные
    with open('generated_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Инициализируем Firebase
    try:
        db = initialize_firebase()
        print("Firebase успешно инициализирован")
        
        # Загружаем данные
        upload_data(db, data)
        print("Данные успешно загружены в Firestore")
        
    except Exception as e:
        print(f"Ошибка при работе с Firebase: {e}")

if __name__ == "__main__":
    main()
