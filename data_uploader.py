import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

def load_firebase_config() -> dict:
    """Загрузка конфигурации Firebase из переменных окружения"""
    load_dotenv(os.path.join('venv', '.venv'))
    
    # Получаем данные сервисного аккаунта из переменных окружения
    service_account = {
        'type': 'service_account',
        'project_id': os.getenv('FIREBASE_PROJECT_ID'),
        'private_key_id': os.getenv('FIREBASE_PRIVATE_KEY_ID'),
        'private_key': os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
        'client_email': os.getenv('FIREBASE_CLIENT_EMAIL'),
        'client_id': os.getenv('FIREBASE_CLIENT_ID'),
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
        'client_x509_cert_url': os.getenv('FIREBASE_CLIENT_CERT_URL'),
        'universe_domain': 'googleapis.com'
    }
    
    return {
        'service_account': service_account,
        'database_url': os.getenv('FIREBASE_DATABASE_URL')
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
    
    # Загрузка справочников
    print("Загрузка справочников...")
    for city in data['cities']:
        doc_ref = db.collection('cities').document()
        batch.set(doc_ref, {'name': city})
    
    for division in data['divisions']:
        doc_ref = db.collection('divisions').document()
        batch.set(doc_ref, {'name': division})
    
    for position in data['positions']:
        doc_ref = db.collection('positions').document()
        batch.set(doc_ref, {'name': position})
    
    # Загрузка сотрудников
    print("Загрузка сотрудников...")
    for emp in data['employees']:
        doc_ref = db.collection('employees').document(emp['empID'])
        batch.set(doc_ref, {
            'fio': emp['fio'],
            'tn': emp['tn'],
            'position': emp['position'],
            'division': emp['division'],
            'location': emp['location']
        })
    
    # Загрузка устройств
    print("Загрузка устройств...")
    for dev in data['devices']:
        doc_ref = db.collection('devices').document(dev['deviceID'])
        batch.set(doc_ref, {
            'empID': dev['empID'],
            'type': dev['type'],
            'model': dev['model'],
            'serial': dev['serial'],
            'purchase_date': dev['purchase_date'],
            'status': dev['status'],
            'last_maintenance': dev['last_maintenance'],
            'warranty_until': dev['warranty_until']
        })
    
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
