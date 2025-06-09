import os
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv
from faker import Faker
from faker.providers import person, job, address
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore
from dateutil.relativedelta import relativedelta

def find_config_file(filename: str) -> str:
    """Поиск файла конфигурации в venv/.venv"""
    for path in ['.venv', 'venv']:
        filepath = os.path.join(path, filename)
        if os.path.exists(filepath):
            return filepath
    raise FileNotFoundError(f"Файл {filename} не найден в venv/ или .venv/")

# Загрузка переменных окружения из venv/.venv
env_path = find_config_file('.env')
load_dotenv(env_path)

# Инициализация Faker с русской локалью
fake = Faker('ru_RU')
fake.add_provider(person)
fake.add_provider(job)
fake.add_provider(address)

# Настройка OpenAI
client = OpenAI(
    api_key=os.getenv('aiTonnelKey'),
    base_url="https://api.aitunnel.ru/v1"
)

# Инициализация Firebase
firebase_creds = find_config_file('firebase-credentials.json')
cred = credentials.Certificate(firebase_creds)
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
})

# Получаем экземпляр Firestore
db = firestore.client()

# Конфигурация данных
EMPLOYEES_COUNT = 1000
DEVICES_COUNT = 7000

# Списки для генерации данных
CITIES = [
    'Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань',
    'Нижний Новгород', 'Челябинск', 'Самара', 'Омск', 'Ростов-на-Дону'
]

DIVISIONS = [
    'Отдел разработки', 'Отдел тестирования', 'Отдел аналитики',
    'Отдел маркетинга', 'Отдел продаж', 'Отдел поддержки',
    'Бухгалтерия', 'Отдел кадров', 'Юридический отдел', 'Отдел ИТ'
]

POSITIONS = [
    'Разработчик', 'Тестировщик', 'Аналитик', 'Маркетолог',
    'Менеджер по продажам', 'Техподдержка', 'Бухгалтер', 'HR-менеджер',
    'Юрист', 'Системный администратор', 'Тимлид', 'Продукт-менеджер',
    'Дизайнер', 'DevOps-инженер', 'Технический писатель'
]

DEVICE_TYPES = [
    'Ноутбук', 'Монитор', 'Системный блок', 'Клавиатура', 'Мышь',
    'Телефон', 'Планшет', 'Принтер', 'Сканер', 'МФУ'
]

# Функции для генерации данных
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
    device_type = random.choice(DEVICE_TYPES)
    receipt_date = fake.date_between(start_date='-5y', end_date='today')
    
    return {
        'deviceID': device_id,
        'empID': emp_id,
        'nomenclature': device_type,
        'model': f"{device_type} {fake.bothify(text='??-####', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ')}",
        'dateReceipt': receipt_date.strftime('%Y-%m-%d'),
        'usefulLife': 3 if device_type in ['Ноутбук', 'Планшет', 'Телефон'] else 5,
        'status': random.choices(
            ['Исправен', 'Неисправен', 'В ремонте', 'Утерян'],
            weights=[0.85, 0.1, 0.03, 0.02],
            k=1
        )[0],
        'ctc': random.randint(30, 100)  # КТС от 30 до 100%
    }

def upload_to_firestore(collection: str, data: Dict[str, Any]):
    """Загрузка данных в Firestore"""
    doc_id = data.get('empID') or data.get('deviceID')
    if not doc_id:
        raise ValueError("Документ должен содержать empID или deviceID")
    
    doc_ref = db.collection(collection).document(doc_id)
    doc_ref.set(data)

# Основная функция
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
        
    'Нижний Новгород', 'Челябинск', 'Самара', 'Омск', 'Ростов-на-Дону',
    'Уфа', 'Красноярск', 'Воронеж', 'Пермь', 'Волгоград', 'Краснодар',
    'Саратов', 'Тюмень', 'Тольятти', 'Ижевск'
]

POSITIONS = [
    'Старший менеджер по работе с клиентами', 'Менеджер по продажам', 'Кредитный специалист',
    'Специалист по ипотечному кредитованию', 'Операционист', 'Кассир', 'Старший кассир',
    'Менеджер по развитию бизнеса', 'Руководитель отдела продаж', 'Начальник отдела кредитования',
    'Заместитель директора филиала', 'Директор филиала', 'Специалист по вкладам',
    'Менеджер по работе с премиальными клиентами', 'Консультант по инвестициям'
]

DIVISIONS = [
    'Центр развития розничного бизнеса', 'Департамент корпоративного бизнеса',
    'Управление по работе с частными клиентами', 'Отдел кредитных операций',
    'Департамент казначейства', 'Управление рисками', 'Отдел информационных технологий',
    'Департамент операционного управления', 'Отдел маркетинга и PR',
    'Департамент внутреннего контроля', 'Управление по работе с персоналом',
    'Отдел безопасности', 'Департамент расчетов и кассовых операций',
    'Управление по работе с проблемными активами', 'Отдел по работе с пластиковыми картами'
]

DEVICE_TYPES = [
    'Монитор', 'Системный блок', 'Ноутбук', 'Планшет', 'Смартфон',
    'Принтер', 'Сканер', 'МФУ', 'Телефонный аппарат', 'ИБП'
]

DEVICE_MODELS = {
    'Монитор': ['Dell U2720Q', 'LG 27UL850-W', 'Samsung U32J590UQI', 'AOC 24G2U', 'ASUS ProArt PA278QV'],
    'Системный блок': ['HP EliteDesk 800 G5', 'Lenovo ThinkCentre M720q', 'Dell OptiPlex 7080', 'Acer Veriton X2660G', 'ASUS ExpertCenter D5'],
    'Ноутбук': ['Lenovo ThinkPad X1 Carbon', 'Dell XPS 13', 'HP EliteBook 840 G7', 'ASUS ZenBook 14', 'Acer Swift 5'],
    'Планшет': ['Apple iPad Pro 12.9', 'Samsung Galaxy Tab S7+', 'Huawei MatePad Pro', 'Lenovo Tab P11 Pro', 'Xiaomi Mi Pad 5'],
    'Смартфон': ['iPhone 13 Pro', 'Samsung Galaxy S21', 'Xiaomi 12 Pro', 'Huawei P50 Pro', 'Realme GT 2 Pro'],
    'Принтер': ['HP LaserJet Pro M404n', 'Canon i-SENSYS LBP6030', 'Brother HL-1212WR', 'Xerox Phaser 3020', 'Epson L13210'],
    'Сканер': ['Epson Perfection V39', 'Canon CanoScan LiDE 300', 'HP ScanJet Pro 2500 f1', 'Brother DS-640', 'Plustek ePhoto Z300'],
    'МФУ': ['HP LaserJet Pro MFP M227sdn', 'Canon i-SENSYS MF3010', 'Brother DCP-L2500DR', 'Xerox B205', 'Epson L3150'],
    'Телефонный аппарат': ['Panasonic KX-TS2350', 'Gigaset A540', 'Philips E255', 'ATCOM ATH-200', 'Yealink T21'],
    'ИБП': ['APC Back-UPS 700VA', 'IPPON Back Power Pro 800', 'Powercom Raptor RPT-1000A', 'Eltena Green Line 1000', 'CyberPower UT650EG']
}

STATUSES = ['исправен', 'неисправен', 'поиск', 'утерян']
STATUS_WEIGHTS = [0.85, 0.10, 0.03, 0.02]

def generate_employees() -> List[Dict[str, Any]]:
    """Генерация списка сотрудников"""
    employees = []
    used_tns = set()
    
    # Разделяем города между сотрудниками
    city_assignments = {}
    cities_per_employee = len(CITIES) / EMPLOYEES_COUNT
    
    for i, city in enumerate(CITIES):
        start_idx = int(i * cities_per_employee)
        end_idx = int((i + 1) * cities_per_employee)
        city_assignments[city] = list(range(start_idx, min(end_idx, EMPLOYEES_COUNT)))
    
    for i in range(EMPLOYEES_COUNT):
        # Генерация уникального табельного номера
        while True:
            tn = f"{random.randint(10000000, 99999999)}"
            if tn not in used_tns:
                used_tns.add(tn)
                break
        
        # Выбор города для сотрудника
        city = next((c for c, emps in city_assignments.items() if i in emps), random.choice(CITIES))
        
        employee = {
            'empID': str(uuid.uuid4()),
            'fio': fake.name(),
            'tn': tn,
            'position': random.choice(POSITIONS),
            'division': random.choice(DIVISIONS),
            'location': city
        }
        employees.append(employee)
    
    return employees

def generate_devices(employees: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Генерация списка устройств"""
    devices = []
    employee_devices = {emp['empID']: [] for emp in employees}
    
    # Сначала добавляем обязательные устройства для каждого сотрудника
    for emp in employees:
        emp_id = emp['empID']
        is_manager = any(role in emp['position'].lower() for role in ['руководитель', 'директор', 'начальник'])
        
        # Добавляем системный блок
        devices.append(create_device(emp_id, 'Системный блок'))
        employee_devices[emp_id].append('Системный блок')
        
        # Добавляем монитор (1-2 штуки)
        num_monitors = random.choices([1, 2], weights=[0.7, 0.3])[0]
        for _ in range(num_monitors):
            devices.append(create_device(emp_id, 'Монитор'))
            employee_devices[emp_id].append('Монитор')
        
        # Добавляем клавиатуру и мышь
        devices.append(create_device(emp_id, 'Клавиатура'))
        devices.append(create_device(emp_id, 'Мышь'))
        employee_devices[emp_id].extend(['Клавиатура', 'Мышь'])
        
        # Для руководителей добавляем дополнительные устройства
        if is_manager:
            devices.append(create_device(emp_id, 'Ноутбук'))
            devices.append(create_device(emp_id, 'Смартфон'))
            if random.random() < 0.5:  # 50% вероятность планшета
                devices.append(create_device(emp_id, 'Планшет'))
            employee_devices[emp_id].extend(['Ноутбук', 'Смартфон', 'Планшет'])
    
    # Добавляем оставшиеся устройства до нужного количества
    while len(devices) < DEVICES_COUNT:
        emp = random.choice(employees)
        device_type = random.choice(DEVICE_TYPES)
        
        # Пропускаем, если у сотрудника уже есть 2 монитора
        if device_type == 'Монитор' and employee_devices[emp['empID']].count('Монитор') >= 2:
            continue
            
        devices.append(create_device(emp['empID'], device_type))
        employee_devices[emp['empID']].append(device_type)
    
    return devices[:DEVICES_COUNT]  # На всякий случай обрезаем до нужного количества

def create_device(emp_id: str, device_type: str) -> Dict[str, Any]:
    """Создание устройства заданного типа"""
    # Генерация даты поступления (2015-01-01 по 2025-06-01)
    start_date = datetime(2015, 1, 1)
    end_date = datetime(2025, 6, 1)
    random_days = random.randint(0, (end_date - start_date).days)
    date_receipt = start_date + timedelta(days=random_days)
    
    # Определение срока полезного использования
    useful_life = 3 if device_type in ['Ноутбук', 'Планшет', 'Смартфон'] else 5
    
    # Расчет КТС (зависит от срока службы)
    years_in_use = (datetime.now() - date_receipt).days / 365
    ctc = max(0, 100 - (years_in_use / useful_life) * 100 + random.uniform(-10, 10))
    ctc = min(100, max(0, ctc))  # Ограничиваем от 0 до 100
    
    # Выбор статуса с учетом весов
    status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
    
    return {
        'deviceID': str(uuid.uuid4()),
        'empID': emp_id,
        'nomenclature': device_type,
        'model': random.choice(DEVICE_MODELS.get(device_type, ['Неизвестная модель'])),
        'dateReceipt': date_receipt.strftime('%Y-%m-%d'),
        'usefulLife': useful_life,
        'status': status,
        'ctc': round(ctc, 2)
    }

async def generate_with_ai():
    """Генерация структуры базы данных с помощью AI"""
    system_prompt = """
    Ты - помощник, который создает структуру базы данных для приложения на Firebase.
    Структура базы данных должна быть максимально оптимальной для приложения.
    
    Верни ответ в формате JSON с двумя массивами: employees и devices.
    """
    
    try:
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Сгенерируй структуру базы данных"}
            ],
            temperature=0.5
        )
        
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Ошибка при генерации данных с помощью AI: {e}")
        return None

def upload_to_firebase(employees: List[Dict[str, Any]], devices: List[Dict[str, Any]]):
    """Загрузка данных в Firebase"""
    batch = db.batch()
    employees_ref = db.collection('employees')
    devices_ref = db.collection('devices')
    
    # Загружаем сотрудников
    for emp in employees:
        emp_doc = employees_ref.document(emp['empID'])
        batch.set(emp_doc, {
            'fio': emp['fio'],
            'tn': emp['tn'],
            'position': emp['position'],
            'division': emp['division'],
            'location': emp['location']
        })
    
    # Загружаем устройства
    for dev in devices:
        dev_doc = devices_ref.document(dev['deviceID'])
        batch.set(dev_doc, {
            'empID': dev['empID'],
            'nomenclature': dev['nomenclature'],
            'model': dev['model'],
            'dateReceipt': dev['dateReceipt'],
            'usefulLife': dev['usefulLife'],
            'status': dev['status'],
            'ctc': dev['ctc']
        })
    
    # Применяем пакетную запись
    batch.commit()
    print(f"Загружено {len(employees)} сотрудников и {len(devices)} устройств в Firebase")

def main():
    print("Начало генерации данных...")
    
    # Генерация сотрудников
    print("Генерация сотрудников...")
    employees = generate_employees()
    
    # Генерация устройств
    print("Генерация устройств...")
    devices = generate_devices(employees)
    
    # Загрузка в Firebase
    print("Загрузка данных в Firebase...")
    upload_to_firebase(employees, devices)
    
    print("Генерация данных завершена успешно!")

if __name__ == "__main__":
    main()
