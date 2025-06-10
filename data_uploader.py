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

def clear_collection(db, collection_name: str, batch_size: int = 100):
    """Очистка коллекции в Firestore"""
    print(f"Очистка коллекции {collection_name}...")
    try:
        # Получаем все документы партиями
        collection_ref = db.collection(collection_name)
        docs = collection_ref.limit(batch_size).stream()
        
        deleted = 0
        batch = db.batch()
        
        for doc in docs:
            batch.delete(doc.reference)
            deleted += 1
            
            if deleted % 400 == 0:  # Ограничение на размер батча
                batch.commit()
                batch = db.batch()
        
        if deleted % 400 != 0:
            batch.commit()
            
        print(f"Удалено {deleted} документов из коллекции {collection_name}")
        return deleted
    except Exception as e:
        print(f"Ошибка при очистке коллекции {collection_name}: {e}")
        return 0

def upload_data(db, data: dict):
    """Загрузка данных в Firestore"""
    # Очищаем существующие коллекции
    collections_to_clear = ['employees', 'devices']
    for collection in collections_to_clear:
        clear_collection(db, collection)
    
    # Собираем уникальные города, подразделения и должности из данных сотрудников
    cities = set()
    divisions = set()
    positions = set()
    
    for emp in data['employees']:
        cities.add(emp['location'])
        divisions.add(emp['division'])
        positions.add(emp['position'])
    
    # Создаем словари для хранения соответствий
    city_mapping = {city: f'city_{i+1:03d}' for i, city in enumerate(cities)}
    division_mapping = {div: f'div_{i+1:03d}' for i, div in enumerate(divisions)}
    position_mapping = {pos: f'pos_{i+1:03d}' for i, pos in enumerate(positions)}
    
    # Создаем коллекцию городов
    print("Загрузка городов...")
    city_batch = db.batch()
    for city, city_id in city_mapping.items():
        doc_ref = db.collection('cities').document(city_id)
        city_batch.set(doc_ref, {'name': city})
    city_batch.commit()
    
    # Создаем коллекцию подразделений
    print("Загрузка подразделений...")
    div_batch = db.batch()
    for div, div_id in division_mapping.items():
        doc_ref = db.collection('divisions').document(div_id)
        div_batch.set(doc_ref, {'name': div})
    div_batch.commit()
    
    # Создаем коллекцию должностей
    print("Загрузка должностей...")
    pos_batch = db.batch()
    for pos, pos_id in position_mapping.items():
        doc_ref = db.collection('positions').document(pos_id)
        pos_batch.set(doc_ref, {'name': pos})
    pos_batch.commit()
    
    # Загрузка сотрудников
    print(f"Загрузка {len(data['employees'])} сотрудников...")
    emp_batch = db.batch()
    for i, emp in enumerate(data['employees'], 1):
        doc_ref = db.collection('employees').document(emp['empID'])
        emp_batch.set(doc_ref, {
            'fio': emp['fio'],
            'tn': emp['tn'],
            'position': position_mapping[emp['position']],
            'division': division_mapping[emp['division']],
            'location': city_mapping[emp['location']],
            'is_manager': emp.get('is_manager', False)
        })
        
        if i % 400 == 0:  # Фиксируем каждые 400 записей
            emp_batch.commit()
            emp_batch = db.batch()
            print(f"Загружено {i} сотрудников...")
    
    if emp_batch._write_pbs:  # Если есть незафиксированные изменения
        emp_batch.commit()
    
    # Загрузка устройств
    print(f"Загрузка {len(data['devices'])} устройств...")
    dev_batch = db.batch()
    for i, dev in enumerate(data['devices'], 1):
        doc_ref = db.collection('devices').document(dev['ID'])
        device_data = {
            'empID': dev['empID'],
            'nomenclature': dev['nomenclature'],
            'model': dev['model'],
            'status': dev['status'],
            'dateReceipt': dev['dateReceipt'],
            'usefulLife': dev['usefulLife'],
            'ctc': dev.get('ctc', 1.0)  # Добавляем техническое состояние
        }
        
        if 'serial' in dev:
            device_data['serial'] = dev['serial']
            
        dev_batch.set(doc_ref, device_data)
        
        if i % 400 == 0:  # Фиксируем каждые 400 записей
            dev_batch.commit()
            dev_batch = db.batch()
            print(f"Загружено {i} устройств...")
    
    if dev_batch._write_pbs:  # Если есть незафиксированные изменения
        dev_batch.commit()
    
    print("Загрузка данных завершена")

def main():
    # Путь к файлу с данными
    data_file = os.path.join('data', 'generated_data.json')
    
    # Проверяем наличие файла с данными
    if not os.path.exists(data_file):
        print(f"Ошибка: Файл {data_file} не найден. Сначала выполните data_generator.py")
        return
    
    print(f"Загрузка данных из {data_file}...")
    # Загружаем данные
    with open(data_file, 'r', encoding='utf-8') as f:
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
