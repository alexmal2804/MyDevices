import os
import random
import uuid
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from faker import Faker
from faker.providers import person, job, address
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore

# Инициализация Faker с русской локалью
fake = Faker('ru_RU')
fake.add_provider(person)
fake.add_provider(job)
fake.add_provider(address)

def find_config_file(filename: str) -> str:
    """Поиск файла конфигурации в venv/.venv"""
    for path in ['.venv', 'venv']:
        filepath = os.path.join(path, filename)
        if os.path.exists(filepath):
            return filepath
    raise FileNotFoundError(f"Файл {filename} не найден в venv/ или .venv/")

try:
    # Загрузка переменных окружения
    env_path = find_config_file('.env')
    load_dotenv(env_path)
    
    # Инициализация Firebase
    firebase_creds = find_config_file('firebase-credentials.json')
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
    })
    
    # Получаем экземпляр Firestore
    db = firestore.client()
    
    # Инициализация OpenAI
    client = OpenAI(
        api_key=os.getenv('aiTonnelKey'),
        base_url="https://api.aitunnel.ru/v1"
    )
    
except Exception as e:
    print(f"Ошибка инициализации: {e}")
    raise

# Конфигурация данных
EMPLOYEES_COUNT = 1000
DEVICES_COUNT = 7000

# Списки для генерации данных
CITIES = [
    'Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань',
    'Нижний Новгород', 'Челябинск', 'Самара', 'Омск', 'Ростов-на-Дону'
]

DIVISIONS = [
    'Центр развития розничного бизнеса', 'Департамент корпоративного бизнеса',
    'Управление по работе с частными клиентами', 'Отдел кредитных операций',
    'Департамент казначейства', 'Управление рисками', 'Отдел информационных технологий'
]

POSITIONS = [
    'Старший менеджер по работе с клиентами', 'Менеджер по продажам', 'Кредитный специалист',
    'Специалист по ипотечному кредитованию', 'Операционист', 'Кассир', 'Старший кассир'
]

def generate_employee(emp_id: str) -> Dict[str, Any]:
    """Генерация данных сотрудника"""
    return {
        'empID': emp_id,
        'fio': fake.name(),
        'tn': str(random.randint(10000000, 99999999)),
        'position': random.choice(POSITIONS),
        'division': random.choice(DIVISIONS),
        'location': random.choice(CITIES)
    }

def generate_device(device_id: str, emp_id: str) -> Dict[str, Any]:
    """Генерация данных устройства"""
    device_types = ['Ноутбук', 'Монитор', 'Системный блок', 'Телефон', 'Принтер']
    device_type = random.choice(device_types)
    
    receipt_date = fake.date_between(start_date='-5y', end_date='today')
    useful_life = 3 if device_type in ['Ноутбук', 'Телефон'] else 5
    
    # Расчет КТС (коэффициент технического состояния)
    days_since_receipt = (datetime.now().date() - receipt_date).days
    age_factor = max(0, 1 - (days_since_receipt / (useful_life * 365)))
    ctc = int(30 + (70 * age_factor * random.uniform(0.9, 1.1)))
    
    return {
        'deviceID': device_id,
        'empID': emp_id,
        'nomenclature': device_type,
        'model': f"{device_type} {fake.bothify(text='??-####')}",
        'dateReceipt': receipt_date.strftime('%Y-%m-%d'),
        'usefulLife': useful_life,
        'status': random.choices(
            ['Исправен', 'Неисправен', 'В ремонте', 'Утерян'],
            weights=[0.85, 0.1, 0.03, 0.02],
            k=1
        )[0],
        'ctc': min(100, max(0, ctc))  # Ограничиваем от 0 до 100
    }

def upload_to_firestore(collection: str, data: Dict[str, Any]) -> None:
    """Загрузка данных в Firestore"""
    try:
        doc_id = data.get('empID') or data.get('deviceID')
        if not doc_id:
            raise ValueError("Документ должен содержать empID или deviceID")
        
        doc_ref = db.collection(collection).document(doc_id)
        doc_ref.set(data)
    except Exception as e:
        print(f"Ошибка при загрузке документа: {e}")

def main():
    print("Начало генерации данных...")
    
    # Генерация сотрудников
    print(f"Генерация {EMPLOYEES_COUNT} сотрудников...")
    employees = []
    for i in range(EMPLOYEES_COUNT):
        emp_id = f"emp_{i:04d}"
        employee = generate_employee(emp_id)
        employees.append(employee)
        upload_to_firestore('employees', employee)
        
        if (i + 1) % 100 == 0:
            print(f"Обработано {i + 1} сотрудников")
    
    # Генерация устройств
    print(f"\nГенерация {DEVICES_COUNT} устройств...")
    for i in range(DEVICES_COUNT):
        emp = random.choice(employees)
        device_id = f"dev_{i:06d}"
        device = generate_device(device_id, emp['empID'])
        upload_to_firestore('devices', device)
        
        if (i + 1) % 500 == 0:
            print(f"Обработано {i + 1} устройств")
    
    print("\nГенерация данных завершена!")

if __name__ == "__main__":
    main()
