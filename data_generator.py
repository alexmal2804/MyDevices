import os
import re
import json
import asyncio
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI

# Глобальные настройки
NUM_EMPLOYEES = 1000
NUM_DEVICES = 7000

# Глобальные переменные
client: Optional[OpenAI] = None
cities: List[str] = []
divisions: List[Dict[str, str]] = []
positions: List[Dict[str, Any]] = []

# Конфигурация устройств
DEVICE_TYPES = {
    'monitor': {
        'count_per_employee': (1, 2),  # мин, макс на сотрудника
        'useful_life': 5,  # лет
        'models': [
            'Dell U2419H', 'LG 24MK400H-B', 'Samsung S24R350', 'Acer R240Y', 'HP 24mh'
        ]
    },
    'desktop': {
        'count_per_employee': (1, 1),
        'useful_life': 5,
        'models': [
            'Dell OptiPlex 3080', 'HP ProDesk 400 G7', 'Lenovo ThinkCentre M75q', 'Acer Veriton X2660G'
        ]
    },
    'laptop': {
        'count_per_employee': (0, 1),  # только для руководителей
        'useful_life': 3,
        'models': [
            'Dell Latitude 5420', 'HP EliteBook 840 G8', 'Lenovo ThinkPad T14', 'Apple MacBook Pro 16" M1'
        ]
    },
    'tablet': {
        'count_per_employee': (0, 1),  # только для руководителей
        'useful_life': 3,
        'models': [
            'Apple iPad Pro 12.9"', 'Samsung Galaxy Tab S7', 'Huawei MatePad Pro', 'Lenovo Tab P12 Pro'
        ]
    },
    'phone': {
        'count_per_employee': (1, 1),
        'useful_life': 3,
        'models': [
            'iPhone 13', 'Samsung Galaxy S21', 'Xiaomi Redmi Note 11', 'Huawei P50'
        ]
    },
    'keyboard': {
        'count_per_employee': (1, 1),
        'useful_life': 5,
        'models': [
            'Logitech K120', 'Dell KB216', 'HP K1500', 'A4Tech KR-85'
        ]
    },
    'mouse': {
        'count_per_employee': (1, 1),
        'useful_life': 5,
        'models': [
            'Logitech M90', 'Dell MS116', 'HP X500', 'A4Tech OP-620D'
        ]
    }
}

# Статусы устройств
DEVICE_STATUSES = [
    {'status': 'исправен', 'weight': 85},
    {'status': 'неисправен', 'weight': 10},
    {'status': 'поиск', 'weight': 3},
    {'status': 'утерян', 'weight': 2}
]

# Уровни подразделений
DIVISION_LEVELS = ['сектор', 'отдел', 'управление', 'центр']

# Генерация случайной даты
def random_date(start_date: str, end_date: str) -> str:
    """Генерирует случайную дату в заданном диапазоне."""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime('%Y-%m-%d')

# Выбор случайного элемента с учетом весов
def weighted_choice(choices: List[Tuple[str, int]]) -> str:
    """Выбирает случайный элемент с учетом весов.
    
    Args:
        choices: Список кортежей (значение, вес)
        
    Returns:
        Выбранное значение
    """
    total = sum(weight for _, weight in choices)
    r = random.uniform(0, total)
    upto = 0
    for value, weight in choices:
        if upto + weight >= r:
            return value
        upto += weight
    return choices[0][0]  # fallback

def get_env_value(key: str, env_content: str) -> Optional[str]:
    """Получение значения переменной из файла .venv"""
    try:
        # Ищем строку, начинающуюся с ключа
        pattern = fr'^{key}\s*=\s*([^\n#]+)'
        match = re.search(pattern, env_content, re.MULTILINE)
        if not match:
            return None
        
        value = match.group(1).strip()
        # Удаляем кавычки, если они есть
        value = value.strip('\'"')
        return value.strip()
    except Exception as e:
        print(f"Ошибка при получении значения {key}: {e}")
        return None

def init_openai_client() -> None:
    """Инициализация клиента OpenAI"""
    global client
    try:
        # Чтение файла .venv
        venv_path = os.path.join('venv', '.venv')
        with open(venv_path, 'r', encoding='utf-8') as f:
            venv_content = f.read()
        
        # Получаем AI_TUNNEL_KEY
        ai_tunnel_key = get_env_value('AI_TUNNEL_KEY', venv_content)
        if not ai_tunnel_key:
            raise ValueError("Не найден AI_TUNNEL_KEY в файле venv/.venv")
        
        # Инициализация клиента OpenAI
        client = OpenAI(
            api_key=ai_tunnel_key,
            base_url="https://api.aitunnel.ru/v1"
        )
        print("Клиент OpenAI успешно инициализирован")
        
    except Exception as e:
        print(f"Ошибка при инициализации клиента OpenAI: {e}")
        raise

async def generate_reference_data() -> Tuple[List[str], List[Dict], List[Dict]]:
    """Генерация справочных данных (города, подразделения, должности)"""
    prompt = """
    Сгенерируй справочные данные для банковской системы:
    
    1. Список из 15 крупных городов России (только названия, по одному на строку)
    
    2. Список из 15 подразделений банка в формате JSON-массива, где каждый элемент имеет поля:
       - name: полное название подразделения (с указанием уровня: сектор/отдел/управление/центр)
       - level: уровень иерархии (0-сектор, 1-отдел, 2-управление, 3-центр)
       - parent: индекс родительского подразделения (null для центров)
    
    3. Список из 15 должностей в банке в формате JSON-массива, где каждый элемент имеет поля:
       - name: название должности
       - is_manager: true/false (является ли руководящей)
    
    Пример структуры ответа:
    ```
    Города:
    Москва
    Санкт-Петербург
    ...
    
    Подразделения:
    [
        {"name": "Центр розничного бизнеса", "level": 3, "parent": null},
        {"name": "Управление кредитования", "level": 2, "parent": 0},
        ...
    ]
    
    Должности:
    [
        {"name": "Менеджер по продажам", "is_manager": false},
        {"name": "Начальник отдела", "is_manager": true},
        ...
    ]
    ```
    """
    
    try:
        # Пытаемся загрузить из кэша, чтобы не генерировать заново
        if os.path.exists('reference_cache.json'):
            with open('reference_cache.json', 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                return cached_data['cities'], cached_data['divisions'], cached_data['positions']
        
        # Если кэша нет, генерируем через API
        messages = [
            {"role": "system", "content": "Ты - генератор структурированных данных. Возвращай только запрошенные данные в указанном формате."},
            {"role": "user", "content": prompt}
        ]
        
        completion = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
            ),
            timeout=60.0
        )
        
        response = completion.choices[0].message.content.strip()
        
        # Парсим ответ
        cities_section = response.split('Города:')[1].split('\n\n')[0].strip()
        cities = [line.strip() for line in cities_section.split('\n') if line.strip()]
        
        divisions_section = response.split('Подразделения:')[1].split('\n\n')[0].strip()
        divisions = json.loads(divisions_section)
        
        positions_section = response.split('Должности:')[1].strip()
        positions = json.loads(positions_section)
        
        # Сохраняем в кэш
        with open('reference_cache.json', 'w', encoding='utf-8') as f:
            json.dump({
                'cities': cities,
                'divisions': divisions,
                'positions': positions
            }, f, ensure_ascii=False, indent=2)
        
        return cities, divisions, positions
        
    except Exception as e:
        print(f"Ошибка при генерации справочных данных: {e}")
        # Возвращаем тестовые данные в случае ошибки
        return (
            ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань"],
            [
                {"name": "Центр розничного бизнеса", "level": 3, "parent": None},
                {"name": "Управление кредитования", "level": 2, "parent": 0},
                {"name": "Отдел ипотечного кредитования", "level": 1, "parent": 1}
            ],
            [
                {"name": "Менеджер по продажам", "is_manager": False},
                {"name": "Начальник отдела", "is_manager": True}
            ]
        )

async def generate_employee(emp_id: int, cities: List[str], positions: List[Dict]) -> Dict[str, Any]:
    """Генерация данных сотрудника"""
    # Генерация ФИО
    last_names = ['Иванов', 'Петров', 'Сидоров', 'Смирнов', 'Кузнецов', 'Попов', 'Васильев', 'Павлов']
    first_names_male = ['Александр', 'Дмитрий', 'Михаил', 'Андрей', 'Сергей', 'Алексей', 'Артём', 'Иван']
    first_names_female = ['Елена', 'Мария', 'Анна', 'Ольга', 'Наталья', 'Ирина', 'Татьяна', 'Екатерина']
    
    # Определяем пол по случайному выбору
    gender = random.choice(['male', 'female'])
    
    if gender == 'male':
        first_name = random.choice(first_names_male)
        middle_name = random.choice(['Александрович', 'Дмитриевич', 'Сергеевич', 'Андреевич', 'Алексеевич'])
    else:
        first_name = random.choice(first_names_female)
        middle_name = random.choice(['Александровна', 'Дмитриевна', 'Сергеевна', 'Андреевна', 'Алексеевна'])
    
    last_name = random.choice(last_names) + ('а' if gender == 'female' else '')
    fio = f"{last_name} {first_name} {middle_name}"
    
    # Выбираем случайную должность
    position = random.choice(positions)
    is_manager = position.get('is_manager', False)
    
    # Выбираем город и генерируем полный адрес
    city = random.choice(cities)
    address = generate_address(city)
    
    return {
        'empID': f"emp_{emp_id:04d}",
        'fio': fio,
        'tn': f"{random.randint(10000000, 99999999)}",
        'position': position['name'],
        'division': 'Не распределено',  # Временное значение, будет перезаписано
        'location': address,  # Полный адрес
        'is_manager': is_manager
    }

def generate_device(device_id: int, emp_id: str, is_manager: bool) -> Dict[str, Any]:
    """Генерация данных устройства"""
    # Определяем типы устройств для сотрудника
    device_types = []
    for dev_type, config in DEVICE_TYPES.items():
        min_count, max_count = config['count_per_employee']
        if is_manager or dev_type not in ['laptop', 'tablet']:
            count = random.randint(min_count, max_count)
            device_types.extend([dev_type] * count)
    
    if not device_types:
        return None
    
    # Выбираем случайный тип устройства
    dev_type = random.choice(device_types)
    config = DEVICE_TYPES[dev_type]
    
    # Генерируем дату поступления (не ранее 2015, не позднее 2025-06-01)
    receipt_date = random_date('2015-01-01', '2025-06-01')
    
    # Вычисляем КТС (чем новее устройство, тем выше КТС в среднем)
    receipt_year = int(receipt_date[:4])
    years_passed = 2025 - receipt_year
    ctc_base = max(0, 100 - years_passed * 20)  # Базовый КТС уменьшается на 20% в год
    ctc = random.randint(max(0, ctc_base - 20), min(100, ctc_base + 20))  # Добавляем случайность ±20%
    
    # Генерируем статус устройства согласно заданным вероятностям
    status = random.choices(
        ["исправен", "неисправен", "поиск", "утерян"],
        weights=[85, 10, 3, 2],  # Проценты: 85%, 10%, 3%, 2%
        k=1
    )[0]
    
    return {
        'deviceID': f"dev_{device_id:06d}",
        'empID': emp_id,
        'nomenclature': dev_type,
        'model': random.choice(config['models']),
        'dateReceipt': receipt_date,
        'usefulLife': config['useful_life'],
        'status': status,  # Используем сгенерированный статус
        'ctc': ctc
    }

def assign_divisions_to_employees(employees: List[Dict], divisions: List[Dict]) -> None:
    """Распределение сотрудников по подразделениям"""
    # Собираем все доступные названия подразделений
    division_names = [d.get('name', 'Основное подразделение') for d in divisions]
    if not division_names:  # Если подразделений нет, используем заглушку
        division_names = ['Основное подразделение']
    
    # Сортируем подразделения по уровню (от высшего к низшему)
    sorted_divisions = sorted([d for d in divisions if d.get('parent') is not None], 
                             key=lambda x: x.get('level', 0), reverse=True)
    
    # Распределяем руководителей по подразделениям
    managers = [e for e in employees if e.get('is_manager', False)]
    non_managers = [e for e in employees if not e.get('is_manager', False)]
    
    # Распределяем руководителей по управлениям и отделам
    for i, manager in enumerate(managers):
        if i < len(sorted_divisions):
            manager['division'] = sorted_divisions[i].get('name', 'Основное подразделение')
        else:
            manager['division'] = random.choice(division_names)
    
    # Распределяем обычных сотрудников по подразделениям
    for emp in non_managers:
        emp['division'] = random.choice(division_names)
    
    # Дополнительная проверка на случай, если кто-то остался без подразделения
    for emp in employees:
        if not emp.get('division'):
            emp['division'] = random.choice(division_names)
    
    # Распределяем остальных сотрудников
    for emp in non_managers:
        # Выбираем случайное подразделение
        div = random.choice(divisions)
        emp['division'] = div.get('name', 'Основное подразделение')

def generate_divisions_hierarchy(divisions: List[Dict]) -> List[Dict]:
    """Генерация иерархии подразделений"""
    # Добавляем родительские подразделения в имена
    result = []
    for div in divisions:
        if div['parent'] is not None:
            parent = divisions[div['parent']]
            full_name = f"{div['name']} {parent['name']}"
        else:
            full_name = div['name']
        result.append({
            'divisionID': f"div_{len(result):03d}",
            'name': div['name'],
            'fullName': full_name,
            'level': div['level'],
            'parentID': f"div_{div['parent']:03d}" if div['parent'] is not None else None
        })
    return result

def save_to_json(data: Dict[str, Any], filename: str) -> None:
    """Сохранение данных в JSON файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"Данные сохранены в {filename}")

async def generate_data() -> Dict[str, Any]:
    """Основная функция генерации данных"""
    print("=== Начало генерации данных ===\n")
    
    try:
        # 1. Инициализация клиента OpenAI
        init_openai_client()
        
        # 2. Генерация справочных данных
        print("1. Генерация справочных данных...")
        cities, divisions_raw, positions = await generate_reference_data()
        
        # Преобразуем подразделения в иерархическую структуру
        divisions = generate_divisions_hierarchy(divisions_raw)
        
        print(f"   • Города: {len(cities)}")
        print(f"   • Подразделения: {len(divisions)}")
        print(f"   • Должности: {len(positions)}")
        
        # 3. Генерация сотрудников
        print("\n2. Генерация сотрудников...")
        employees = []
        for i in range(1, NUM_EMPLOYEES + 1):
            if i % 100 == 0 or i == 1 or i == NUM_EMPLOYEES:
                print(f"   • Сотрудник {i}/{NUM_EMPLOYEES}")
            employee = await generate_employee(i, cities, positions)
            employees.append(employee)
        
        # 4. Распределение по подразделениям
        print("\n3. Распределение по подразделениям...")
        assign_divisions_to_employees(employees, divisions_raw)
        
        # 5. Генерация устройств
        print("\n4. Генерация устройств...")
        devices = []
        device_id = 1
        
        for i, emp in enumerate(employees, 1):
            if i % 100 == 0 or i == 1 or i == len(employees):
                print(f"   • Обработка сотрудника {i}/{len(employees)}")
            
            # Генерируем устройства для сотрудника
            is_manager = emp.get('is_manager', False)
            dev_count = random.randint(3, 6) if is_manager else random.randint(2, 4)
            
            for _ in range(dev_count):
                if device_id > NUM_DEVICES:
                    break
                    
                device = generate_device(device_id, emp['empID'], is_manager)
                if device:
                    devices.append(device)
                    device_id += 1
        
        # 6. Формируем итоговые данные
        print("\n5. Формирование результата...")
        result = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'employees_count': len(employees),
                'devices_count': len(devices),
                'cities_count': len(cities),
                'divisions_count': len(divisions)
            },
            'cities': [{'cityID': f'city_{i:03d}', 'name': name} 
                      for i, name in enumerate(cities, 1)],
            'divisions': divisions,
            'employees': employees,
            'devices': devices
        }
        
        # 7. Сохраняем данные
        print("\n6. Сохранение данных...")
        save_to_json(result, 'generated_data.json')
        
        # 8. Выводим статистику
        print("\n=== Генерация данных завершена успешно ===")
        print(f"\nСтатистика:")
        print(f"- Сотрудники: {len(employees)}")
        print(f"- Устройства: {len(devices)}")
        print(f"- Города: {len(cities)}")
        print(f"- Подразделения: {len(divisions)}")
        
        return result
        
    except Exception as e:
        print(f"\n!!! Ошибка при генерации данных: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Основная функция для запуска генерации данных"""
    print("=== Генератор тестовых данных для банка ===")
    print(f"Будет сгенерировано:")
    print(f"- Сотрудники: {NUM_EMPLOYEES}")
    print(f"- Устройства: {NUM_DEVICES}")
    print("\nНачало генерации...")

    # Создаем директорию для выходных данных, если её нет
    os.makedirs('output', exist_ok=True)

    # Запускаем асинхронную генерацию данных
    try:
        return await generate_data()
    except Exception as e:
        print(f"\n!!! Произошла ошибка при генерации данных: {e}")
        import traceback
        traceback.print_exc()
        return False

# Веса для статусов устройств (чем больше вес, тем выше вероятность)
DEVICE_STATUSES = [
    ("исправен", 85),     # 85% вероятность
    ("неисправен", 10),   # 10% вероятность
    ("поиск", 3),         # 3% вероятность
    ("утерян", 2)         # 2% вероятность
]

# Списки для генерации адресов
STREET_TYPES = ['ул.', 'пр-т', 'шоссе', 'наб.', 'пер.', 'б-р']
STREET_NAMES = [
    'Ленина', 'Советская', 'Центральная', 'Молодежная', 'Школьная',
    'Садовая', 'Лесная', 'Набережная', 'Солнечная', 'Новая',
    'Гагарина', 'Мира', 'Кирова', 'Пушкина', 'Лермонтова'
]
CITY_ADDRESSES = {
    'Москва': {
        'streets': ['Тверская', 'Арбат', 'Новый Арбат', 'Кутузовский пр-т', 'Ленинский пр-т'],
        'districts': ['Центральный', 'Северный', 'Южный', 'Западный', 'Восточный']
    },
    'Санкт-Петербург': {
        'streets': ['Невский пр-т', 'Литейный пр-т', 'Московский пр-т', 'Каменноостровский пр-т'],
        'districts': ['Центральный', 'Петроградский', 'Василеостровский', 'Выборгский']
    },
    'Новосибирск': {
        'streets': ['Красный пр-т', 'Гоголя', 'Дуси Ковальчук', 'Кирова'],
        'districts': ['Центральный', 'Железнодорожный', 'Заельцовский']
    },
    'Екатеринбург': {
        'streets': ['Ленина', 'Малышева', 'Куйбышева', '8 Марта'],
        'districts': ['Верх-Исетский', 'Кировский', 'Октябрьский']
    },
    'Казань': {
        'streets': ['Кремлевская', 'Пушкина', 'Толстого', 'Московская'],
        'districts': ['Вахитовский', 'Советский', 'Приволжский']
    },
    'Нижний Новгород': {
        'streets': ['Большая Покровская', 'Рождественская', 'Максима Горького'],
        'districts': ['Нижегородский', 'Советский', 'Автозаводский']
    },
    'Челябинск': {
        'streets': ['Кирова', 'Цвиллинга', 'Молодогвардейцев'],
        'districts': ['Центральный', 'Советский', 'Ленинский']
    },
    'Омск': {
        'streets': ['Ленина', 'Маршала Жукова', 'Масленникова'],
        'districts': ['Центральный', 'Советский', 'Кировский']
    },
    'Самара': {
        'streets': ['Куйбышева', 'Ленинградская', 'Галактионовская'],
        'districts': ['Самарский', 'Ленинский', 'Октябрьский']
    },
    'Ростов-на-Дону': {
        'streets': ['Большая Садовая', 'Красноармейская', 'Пушкинская'],
        'districts': ['Ворошиловский', 'Советский', 'Кировский']
    }
}

def generate_address(city: str) -> str:
    """Генерирует случайный адрес в указанном городе"""
    if city not in CITY_ADDRESSES:
        # Если города нет в списке, используем общий формат
        street_type = random.choice(STREET_TYPES)
        street_name = random.choice(STREET_NAMES)
        house = random.randint(1, 200)
        building = random.choice(['', f', к{random.randint(1, 5)}', f', стр. {random.randint(1, 10)}'])
        return f"{city}, {street_type} {street_name}, д. {house}{building}"
    
    # Используем специфичные для города данные
    city_data = CITY_ADDRESSES[city]
    street = random.choice(city_data['streets'])
    district = random.choice(city_data['districts'])
    house = random.randint(1, 200)
    building = random.choice(['', f', к{random.randint(1, 5)}', f', стр. {random.randint(1, 10)}'])
    return f"{city}, {district} р-н, {street}, д. {house}{building}"

if __name__ == "__main__":
    import time
    start_time = time.time()
    
    try:
        print("=== Запуск генерации данных ===")
        success = asyncio.run(main())
        if not success:
            print("\n❌ Генерация данных завершилась с ошибками.")
            exit(1)
        print("\n✅ Генерация данных успешно завершена!")
    except KeyboardInterrupt:
        print("\n⚠️ Генерация данных прервана пользователем.")
        exit(1)
    except Exception as e:
        print(f"\n❌ Непредвиденная ошибка: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        elapsed_time = time.time() - start_time
        print(f"\n⏱ Общее время выполнения: {elapsed_time:.2f} секунд")
        
        # Сохраняем статистику в файл
        stats = {
            'generated_at': datetime.now().isoformat(),
            'execution_time_seconds': round(elapsed_time, 2),
            'status': 'completed' if success else 'failed',
            'output_file': 'generated_data.json'
        }
        
        with open('generation_stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
