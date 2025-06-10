import os
import json
import random
import re
import asyncio
import uuid
import string
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from openai import OpenAI
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Кэш для хранения серийных номеров по моделям
model_serial_cache = {}

def generate_serial_number(length: int) -> str:
    """Генерация случайного серийного номера заданной длины"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

def get_env_value(key: str, env_content: str) -> Optional[str]:
    """Получение значения переменной из файла .env"""
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
        venv_path = Path('venv/.venv')
        if not venv_path.exists():
            raise FileNotFoundError(f"Файл {venv_path} не найден")
            
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

# Глобальные настройки
NUM_EMPLOYEES = 1000
NUM_DEVICES = 7000

# Глобальные переменные
client: Optional[OpenAI] = None

# Статусы устройств
class DeviceStatus(Enum):
    WORKING = "исправен"
    BROKEN = "неисправен"
    SEARCH = "поиск"
    LOST = "утерян"

# Типы устройств
class DeviceType(Enum):
    DESKTOP = "Настольный ПК"
    LAPTOP = "Ноутбук"
    MONITOR = "Монитор"
    KEYBOARD = "Клавиатура"
    MOUSE = "Мышь"
    PHONE = "Телефон"
    TABLET = "Планшет"

# Справочные данные
CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
    "Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону",
    "Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград"
]

# Глобальные переменные
cities: List[str] = []
divisions: List[Dict[str, Any]] = []
positions: List[Dict[str, Any]] = []
used_tns: Set[str] = set()  # Для хранения использованных табельных номеров
city_assignments: Dict[str, int] = defaultdict(int)  # Счетчик назначений по городам
assigned_employees: Set[str] = set()  # Для отслеживания назначенных сотрудников

# Модели устройств
DEVICE_MODELS = {
    DeviceType.DESKTOP: [
        "Dell OptiPlex 3080", "HP ProDesk 400 G7", "Lenovo ThinkCentre M75q", 
        "Acer Veriton X2660G", "HP EliteDesk 800 G6"
    ],
    DeviceType.LAPTOP: [
        "Dell Latitude 5420", "HP EliteBook 840 G8", "Lenovo ThinkPad T14", 
        "Apple MacBook Pro 16"
    ],
    DeviceType.MONITOR: [
        "Dell U2419H", "LG 24MK400H-B", "Samsung S24R350", 
        "Acer R240Y", "HP 24mh"
    ],
    DeviceType.KEYBOARD: [
        "Logitech K120", "Dell KB216", "HP K1500", "A4Tech KR-85"
    ],
    DeviceType.MOUSE: [
        "Logitech M90", "Dell MS116", "HP X500", "A4Tech OP-620D"
    ],
    DeviceType.PHONE: [
        "Cisco 8845", "Yealink T54W", "Grandstream GXP2170", "Panasonic KX-UT113"
    ],
    DeviceType.TABLET: [
        "Apple iPad Pro 12.9", "Samsung Galaxy Tab S7", "Huawei MatePad Pro"
    ]
}

# Настройки по умолчанию для типов устройств
DEVICE_DEFAULTS = {
    DeviceType.DESKTOP: {
        'min': 1,  # Минимальное количество на сотрудника
        'max': 1,  # Максимальное количество на сотрудника
        'useful_life': 5,  # Срок полезного использования в годах
        'manager_only': False
    },
    DeviceType.LAPTOP: {
        'min': 0,
        'max': 1,
        'useful_life': 4,
        'manager_only': True
    },
    DeviceType.MONITOR: {
        'min': 1,
        'max': 2,
        'useful_life': 7,
        'manager_only': False
    },
    DeviceType.KEYBOARD: {
        'min': 1,
        'max': 1,
        'useful_life': 4,
        'manager_only': False
    },
    DeviceType.MOUSE: {
        'min': 1,
        'max': 1,
        'useful_life': 3,
        'manager_only': False
    },
    DeviceType.PHONE: {
        'min': 1,
        'max': 1,
        'useful_life': 4,
        'manager_only': False
    },
    DeviceType.TABLET: {
        'min': 0,
        'max': 1,
        'useful_life': 3,
        'manager_only': True
    }
}

# Статусы устройств с весами
DEVICE_STATUS_WEIGHTS = [
    (DeviceStatus.WORKING.value, 85),
    (DeviceStatus.BROKEN.value, 10),
    (DeviceStatus.SEARCH.value, 3),
    (DeviceStatus.LOST.value, 2)
]

@dataclass
class Employee:
    empID: str
    fio: str
    tn: str
    position: str
    division: str
    location: str
    is_manager: bool = False

@dataclass
class Device:
    device_id: str
    emp_id: str
    nomenclature: str
    model: str
    date_receipt: str
    useful_life: int
    status: str
    ctc: int
    serial_number: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ID': self.device_id,
            'empID': self.emp_id,
            'nomenclature': self.nomenclature.split(' ')[0],  # Берем только тип устройства (первое слово)
            'model': self.model,
            'dateReceipt': self.date_receipt,
            'usefulLife': self.useful_life,
            'status': self.status,
            'ctc': self.ctc,
            'serialNumber': self.serial_number,
            'fullNomenclature': self.nomenclature  # Сохраняем полное название для отладки
        }

async def generate_divisions() -> List[Dict]:
    """Генерация иерархии подразделений"""
    levels = ["Центр", "Управление", "Отдел", "Сектор"]
    divisions = []
    
    # Генерация центров (уровень 0)
    centers = [
        "Розничного бизнеса",
        "Корпоративного бизнеса",
        "Инвестиционного бизнеса",
        "Казначейских операций"
    ]
    
    for i, center in enumerate(centers):
        divisions.append({
            "id": len(divisions) + 1,
            "name": f"Центр {center}",
            "level": 0,
            "parent_id": None
        })
    
    # Генерация управлений (уровень 1)
    for center_id in range(1, len(centers) + 1):
        for j in range(1, 4):  # 3 управления на центр
            divisions.append({
                "id": len(divisions) + 1,
                "name": f"Управление {j} при центре {center_id}",
                "level": 1,
                "parent_id": center_id
            })
    
    # Генерация отделов (уровень 2)
    for i in range(len(centers) * 3):
        management_id = len(centers) + i + 1
        for j in range(1, 4):  # 3 отдела на управление
            divisions.append({
                "id": len(divisions) + 1,
                "name": f"Отдел {j} управления {management_id}",
                "level": 2,
                "parent_id": management_id
            })
    
    # Генерация секторов (уровень 3)
    for i in range(len(centers) * 3 * 3):
        department_id = len(centers) * 4 + i + 1
        for j in range(1, 4):  # 3 сектора на отдел
            divisions.append({
                "id": len(divisions) + 1,
                "name": f"Сектор {j} отдела {department_id}",
                "level": 3,
                "parent_id": department_id
            })
    
    return divisions

async def generate_positions() -> List[Dict]:
    """Генерация списка должностей"""
    positions = [
        {"name": "Директор департамента", "is_manager": True},
        {"name": "Заместитель директора департамента", "is_manager": True},
        {"name": "Начальник управления", "is_manager": True},
        {"name": "Заместитель начальника управления", "is_manager": True},
        {"name": "Начальник отдела", "is_manager": True},
        {"name": "Заместитель начальника отдела", "is_manager": True},
        {"name": "Руководитель группы", "is_manager": True},
        {"name": "Главный специалист", "is_manager": False},
        {"name": "Ведущий специалист", "is_manager": False},
        {"name": "Старший специалист", "is_manager": False},
        {"name": "Специалист", "is_manager": False},
        {"name": "Младший специалист", "is_manager": False},
        {"name": "Аналитик", "is_manager": False},
        {"name": "Экономист", "is_manager": False},
        {"name": "Бухгалтер", "is_manager": False}
    ]
    return positions

class DataGenerator:
    def __init__(self):
        self.employees: List[Employee] = []
        self.devices: List[Device] = []
        self.used_tns: Set[str] = set()
        self.city_assignments: Dict[str, int] = defaultdict(int)
        self.assigned_employees: Set[str] = set()
        self._model_serial_cache = {}  # Кэш для хранения использованных серийных номеров по моделям
    
    async def generate_employee(self, emp_id: int) -> Employee:
        """Генерация данных сотрудника"""
        try:
            # Генерация ФИО
            fio = self._generate_fio()
            
            # Генерация уникального табельного номера
            while True:
                tn = f"{random.randint(1, 99999999):08d}"
                if tn not in self.used_tns:
                    self.used_tns.add(tn)
                    break
            
            # Выбор города с учетом ограничений
            if emp_id > 0 and emp_id % 100 == 0:
                print(f"Сгенерировано {emp_id} сотрудников...")
            
            city = self._select_city()
            
            # Выбор должности
            position = random.choice(positions)
            is_manager = position.get('is_manager', False)
            
            # Создание сотрудника
            employee = Employee(
                empID=str(emp_id),
                fio=fio,
                tn=tn,
                position=position['name'],
                division="",  # Будет заполнено позже
                location=city,
                is_manager=is_manager
            )
            
            self.employees.append(employee)
            return employee
        
        except Exception as e:
            print(f"Ошибка при генерации сотрудника {emp_id}: {e}")
            # Возвращаем сотрудника с минимальными данными
            return Employee(
                empID=str(emp_id),
                fio=f"Сотрудник {emp_id}",
                tn="",
                position=random.choice(positions)['name'],
                division="",
                location="",
                is_manager=False
            )
    
    async def generate_device(self, device_id: int, emp_id: str, is_manager: bool, device_type: DeviceType = None, model: str = None) -> Optional[Device]:
        """
        Генерация устройства
        
        Args:
            device_id: ID устройства
            emp_id: ID сотрудника, которому принадлежит устройство
            is_manager: Является ли сотрудник руководителем
            device_type: Опционально, тип устройства (если None, выбирается случайно)
            model: Опционально, модель устройства (если None, выбирается случайно)
            
        Returns:
            Device или None в случае ошибки
        """
        try:
            if device_id > 0 and device_id % 100 == 0:
                print(f"Сгенерировано {device_id} устройств...")
            
            # Если тип устройства не указан, выбираем случайный
            if device_type is None:
                available_types = []
                for dev_type, settings in DEVICE_DEFAULTS.items():
                    # Пропускаем устройства только для руководителей, если сотрудник не руководитель
                    if settings.get('manager_only', False) and not is_manager:
                        continue
                    # Проверяем минимальное и максимальное количество устройств этого типа
                    if settings['min'] > 0 or random.random() < 0.5:  # 50% шанс добавить опциональное устройство
                        available_types.append(dev_type)
                
                if not available_types:
                    available_types = [DeviceType.PHONE]  # Хотя бы телефон у всех
                
                device_type = random.choice(available_types)
            
            # Если модель не указана, выбираем случайную из доступных для данного типа
            if model is None:
                model = random.choice(DEVICE_MODELS[device_type])
            
            # Генерация даты поступления (последние 10 лет)
            date_receipt = (datetime.now() - timedelta(days=random.randint(1, 3650))).strftime('%Y-%m-%d')
            
            # Получаем настройки для типа устройства
            settings = DEVICE_DEFAULTS[device_type]
            
            # Генерация статуса с учетом весов
            status = random.choices(
                [s for s, _ in DEVICE_STATUS_WEIGHTS],
                weights=[w for _, w in DEVICE_STATUS_WEIGHTS]
            )[0]
            
            # Генерация серийного номера
            serial_number = self._generate_serial_number(model)
            
            # Расчет КТС с учетом возраста устройства
            ctc = self._calculate_ctc(date_receipt)
            
            # Определяем производителя для номенклатуры
            manufacturer_map = {
                'Dell': 'Dell',
                'HP': 'HP',
                'Lenovo': 'Lenovo',
                'Acer': 'Acer',
                'LG': 'LG',
                'Samsung': 'Samsung',
                'Apple': 'Apple',
                'Logitech': 'Logitech',
                'Huawei': 'Huawei',
                'Xiaomi': 'Xiaomi',
                'A4Tech': 'A4Tech'
            }
            
            manufacturer = 'Неизвестный производитель'
            for name, mf in manufacturer_map.items():
                if name.lower() in model.lower():
                    manufacturer = mf
                    break
            
            # Формируем номенклатуру: [Тип] [Производитель] [Модель] [Серийный номер]
            nomenclature = f"{device_type.value} {manufacturer} {model} (SN: {serial_number})"
            
            # Создаем и возвращаем устройство
            device = Device(
                device_id=str(device_id),
                emp_id=emp_id,
                nomenclature=nomenclature,
                model=model,
                date_receipt=date_receipt,
                useful_life=settings['useful_life'],
                status=status,
                ctc=ctc,
                serial_number=serial_number
            )
            
            self.devices.append(device)
            return device
            
        except Exception as e:
            print(f"Ошибка при генерации устройства {device_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_fio(self) -> str:
        """
        Генерация ФИО
        
        Returns:
            Строка с ФИО в формате 'Фамилия Имя Отчество'
        """
        first_names = ["Александр", "Дмитрий", "Максим", "Сергей", "Андрей", 
                      "Алексей", "Артём", "Илья", "Кирилл", "Михаил",
                      "Анна", "Мария", "Елена", "Дарья", "Анастасия",
                      "Виктория", "Полина", "Екатерина", "София", "Алиса"]
        
        last_names = ["Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов",
                     "Попов", "Васильев", "Павлов", "Семёнов", "Голубев",
                     "Виноградова", "Ковалёва", "Новикова", "Морозова", "Волкова"]
        
        middle_names = ["Александрович", "Дмитриевич", "Сергеевич", "Андреевич", 
                        "Алексеевич", "Максимович", "Ильич", "Кириллович",
                        "Александровна", "Дмитриевна", "Сергеевна", "Андреевна",
                        "Алексеевна", "Максимовна", "Ильинична", "Кирилловна"]
        
        return f"{random.choice(last_names)} {random.choice(first_names)} {random.choice(middle_names)}"
    
    def _generate_fallback_fio(self) -> str:
        """Запасной генератор ФИО (теперь не используется, оставлен для совместимости)"""
        return self._generate_fio()
    
    def _generate_serial_number(self, model: str) -> str:
        """
        Генерация уникального серийного номера для модели.
        Формат: [Префикс производителя][Год][Месяц][Последовательный номер][Контрольная сумма]
        Длина фиксирована для каждой модели.
        """
        if model not in self._model_serial_cache:
            # Определяем префикс по производителю
            prefix_map = {
                'Dell': 'DL',
                'HP': 'HP',
                'Lenovo': 'LN',
                'Acer': 'AC',
                'LG': 'LG',
                'Samsung': 'SM',
                'Apple': 'AP',
                'Logitech': 'LG',
                'Huawei': 'HW',
                'Xiaomi': 'XM',
                'A4Tech': 'AT'
            }
            
            # Находим префикс по названию модели
            prefix = 'SN'
            for name, code in prefix_map.items():
                if name.lower() in model.lower():
                    prefix = code
                    break
            
            # Инициализируем кэш для модели
            self._model_serial_cache[model] = {
                'prefix': prefix,
                'counter': 0,
                'used': set()
            }
        
        # Получаем данные модели
        cache = self._model_serial_cache[model]
        
        # Генерируем уникальный серийный номер
        while True:
            # Текущая дата
            now = datetime.now()
            year = str(now.year)[-2:]  # Последние 2 цифры года
            month = f"{now.month:02d}"  # Месяц с ведущим нулём
            
            # Увеличиваем счётчик и форматируем с ведущими нулями
            cache['counter'] += 1
            counter_str = f"{cache['counter']:06d}"  # 6 цифр с ведущими нулями
            
            # Собираем базовый номер
            base = f"{cache['prefix']}{year}{month}{counter_str}"
            
            # Добавляем контрольную сумму (сумма кодов символов по модулю 10)
            checksum = str(sum(ord(c) for c in base) % 10)
            serial = f"{base}{checksum}"
            
            # Проверяем уникальность
            if serial not in cache['used']:
                cache['used'].add(serial)
                return serial
    
    def _calculate_ctc(self, date_receipt: str) -> int:
        """
        Расчет Коэффициента Технического Состояния (КТС) с учетом даты поступления.
        
        Args:
            date_receipt: Дата поступления устройства в формате 'YYYY-MM-DD'
            
        Returns:
            int: Значение КТС от 1 до 100
        """
        try:
            receipt_date = datetime.strptime(date_receipt, '%Y-%m-%d')
            age_days = (datetime.now() - receipt_date).days
            
            # Чем новее устройство, тем выше начальный КТС
            if age_days < 180:  # Меньше 6 месяцев
                base_ctc = random.randint(80, 100)
            elif age_days < 365:  # От 6 месяцев до года
                base_ctc = random.randint(70, 95)
            elif age_days < 730:  # 1-2 года
                base_ctc = random.randint(60, 85)
            elif age_days < 1460:  # 2-4 года
                base_ctc = random.randint(40, 70)
            else:  # Более 4 лет
                base_ctc = random.randint(20, 50)
            
            # Добавляем случайное отклонение +/- 5%
            ctc = base_ctc + random.randint(-5, 5)
            
            # Ограничиваем значения от 1 до 100
            return max(1, min(100, ctc))
            
        except Exception as e:
            print(f"Ошибка при расчете КТС: {e}")
            # Возвращаем среднее значение в случае ошибки
            return random.randint(40, 80)
            
    def _select_city(self) -> str:
        """Выбор города с учетом распределения по городам"""
        # Выбираем город с учетом весов (чем больше город, тем больше вероятность выбора)
        city_weights = [
            (city, 100 - i)  # Уменьшаем вес для каждого следующего города
            for i, city in enumerate(CITIES)
        ]
        
        # Нормализуем веса
        total_weight = sum(weight for city, weight in city_weights)
        normalized_weights = [weight / total_weight for city, weight in city_weights]
        
        # Выбираем город с учетом весов
        selected_city = random.choices(
            [city for city, weight in city_weights],
            weights=normalized_weights,
            k=1
        )[0]
        
        return selected_city
    
    async def _generate_fios_batch(self, count: int) -> None:
        """Генерация пакета ФИО с использованием OpenAI API"""
        try:
            prompt = f"""Сгенерируй {count} случайных русских ФИО в формате 'Фамилия Имя Отчество'.
Каждое ФИО с новой строки. Только список, без номеров и дополнительного текста.

Примеры правильного формата:
Иванов Иван Иванович
Петрова Мария Сергеевна
Сидоров Алексей Петрович"""
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Ты помощник, который генерирует списки русских ФИО. Важно: только ФИО, по одному на строку."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.8,
                timeout=30
            )
            
            # Обработка ответа
            content = response.choices[0].message.content.strip()
            fios = [line.strip() for line in content.split('\n') if line.strip()]
            
            # Инициализируем кэш, если его еще нет
            if not hasattr(self, '_fio_cache'):
                self._fio_cache = []
                
            self._fio_cache.extend(fios)
            print(f"Сгенерировано {len(fios)} ФИО через API")
            
        except Exception as e:
            print(f"Ошибка при генерации ФИО через API: {e}")
            if not hasattr(self, '_fio_cache') or not self._fio_cache:
                # Если не удалось сгенерировать через API и кэш пуст, заполняем запасными значениями
                self._fio_cache = [self._generate_fallback_fio() for _ in range(count)]
    
    def _generate_date_receipt(self) -> str:
        """Генерация даты поступления"""
        start_date = datetime(2015, 1, 1)
        end_date = datetime(2025, 6, 1)
        delta = end_date - start_date
        random_days = random.randint(0, delta.days)
        return (start_date + timedelta(days=random_days)).strftime('%Y-%m-%d')
    
    def _generate_status(self) -> str:
        """Генерация статуса с учетом весов"""
        total = sum(weight for status, weight in DEVICE_STATUS_WEIGHTS)
        r = random.uniform(0, total)
        upto = 0
        for status, weight in DEVICE_STATUS_WEIGHTS:
            if upto + weight >= r:
                return status
            upto += weight
        return DEVICE_STATUS_WEIGHTS[0][0]
    
    def _generate_ctc(self, date_receipt: str) -> int:
        """Генерация КТС с учетом даты поступления"""
        receipt_date = datetime.strptime(date_receipt, '%Y-%m-%d')
        now = datetime.now()
        months_since_receipt = (now.year - receipt_date.year) * 12 + (now.month - receipt_date.month)
        
        # Чем новее устройство, тем выше КТС
        if months_since_receipt <= 12:  # Менее года
            return random.randint(80, 100)
        elif months_since_receipt <= 36:  # 1-3 года
            return random.randint(50, 90)
        else:  # Более 3 лет
            return random.randint(10, 60)
    
    async def assign_divisions(self, divisions: List[Dict]) -> None:
        """Назначение сотрудников по подразделениям"""
        # Группируем подразделения по уровням
        level_groups = {}
        for div in divisions:
            level = div['level']
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(div)
        
        # Распределяем сотрудников по подразделениям
        for emp in self.employees:
            # Выбираем случайный уровень (0-3)
            level = random.choices(
                [0, 1, 2, 3],
                weights=[0.02, 0.08, 0.3, 0.6]  # Больше всего сотрудников в секторах
            )[0]
            
            # Выбираем случайное подразделение нужного уровня
            division = random.choice(level_groups[level])
            emp.division = division['name']
    
    async def generate_all_data(self) -> Dict[str, List[Dict]]:
        """Генерация всех данных"""
        print("Начало генерации данных...")
        
        # 1. Генерация справочных данных
        print("Генерация подразделений...")
        divisions = await generate_divisions()
        print(f"Сгенерировано {len(divisions)} подразделений")
        
        print("Генерация должностей...")
        global positions
        positions = await generate_positions()
        print(f"Сгенерировано {len(positions)} должностей")
        
        # 2. Генерация сотрудников
        print(f"Генерация {NUM_EMPLOYEES} сотрудников...")
        for i in range(1, NUM_EMPLOYEES + 1):
            if i % 100 == 0:
                print(f"Сгенерировано {i} сотрудников...")
            await self.generate_employee(i)
        
        # 3. Распределение по подразделениям
        print("Распределение сотрудников по подразделениям...")
        await self.assign_divisions(divisions)
        
        # 4. Генерация устройств
        print(f"Генерация {NUM_DEVICES} устройств...")
        device_count = 0
        
        # Сначала генерируем обязательные устройства для всех сотрудников
        for emp in self.employees:
            # Обязательные устройства для всех
            mandatory_devices = [
                (DeviceType.DESKTOP, 1, 1),
                (DeviceType.KEYBOARD, 1, 1),
                (DeviceType.MOUSE, 1, 1),
                (DeviceType.PHONE, 1, 1),
                (DeviceType.MONITOR, 1, 2)  # 1-2 монитора
            ]
            
            # Генерация обязательных устройств
            for device_type, min_count, max_count in mandatory_devices:
                if device_count >= NUM_DEVICES:
                    break
                    
                # Выбираем модель для данного типа устройства
                model = random.choice(DEVICE_MODELS[device_type])
                
                # Генерируем указанное количество устройств
                count = random.randint(min_count, max_count)
                for _ in range(count):
                    if device_count >= NUM_DEVICES:
                        break
                        
                    # Создаем устройство с указанным типом и моделью
                    await self.generate_device(
                        device_id=device_count + 1,
                        emp_id=emp.empID,
                        is_manager=emp.is_manager,
                        device_type=device_type,
                        model=model
                    )
                    device_count += 1
        
        # Затем генерируем дополнительные устройства для руководителей
        manager_employees = [emp for emp in self.employees if emp.is_manager]
        if manager_employees and device_count < NUM_DEVICES:
            # Дополнительные устройства для руководителей
            extra_devices = [
                (DeviceType.LAPTOP, 0.7),  # 70% шанс на ноутбук
                (DeviceType.TABLET, 0.4),   # 40% шанс на планшет
                (DeviceType.MONITOR, 0.3)   # 30% шанс на дополнительный монитор
            ]
            
            for emp in manager_employees:
                if device_count >= NUM_DEVICES:
                    break
                    
                for device_type, probability in extra_devices:
                    if random.random() < probability:
                        # Выбираем модель для данного типа устройства
                        model = random.choice(DEVICE_MODELS[device_type])
                        
                        # Создаем устройство с указанным типом и моделью
                        await self.generate_device(
                            device_id=device_count + 1,
                            emp_id=emp.empID,
                            is_manager=True,
                            device_type=device_type,
                            model=model
                        )
                        device_count += 1
                        
                        if device_count >= NUM_DEVICES:
                            break
        
        # Если остались доступные устройства, распределяем их случайным образом
        remaining_devices = NUM_DEVICES - device_count
        if remaining_devices > 0:
            print(f"Распределение оставшихся {remaining_devices} устройств...")
            
            # Создаем список всех возможных типов устройств с их весами
            device_weights = [
                (DeviceType.DESKTOP, 20),
                (DeviceType.LAPTOP, 15),
                (DeviceType.MONITOR, 25),
                (DeviceType.PHONE, 15),
                (DeviceType.TABLET, 10),
                (DeviceType.KEYBOARD, 10),
                (DeviceType.MOUSE, 5)
            ]
            
            for _ in range(remaining_devices):
                if device_count >= NUM_DEVICES:
                    break
                    
                # Выбираем случайный тип устройства с учетом весов
                total_weight = sum(weight for _, weight in device_weights)
                r = random.uniform(0, total_weight)
                upto = 0
                for device_type, weight in device_weights:
                    if upto + weight >= r:
                        break
                    upto += weight
                
                # Выбираем случайного сотрудника
                emp = random.choice(self.employees)
                
                # Выбираем модель для данного типа устройства
                model = random.choice(DEVICE_MODELS[device_type])
                
                # Создаем устройство
                await self.generate_device(
                    device_id=device_count + 1,
                    emp_id=emp.empID,
                    is_manager=emp.is_manager,
                    device_type=device_type,
                    model=model
                )
                device_count += 1
        
        print(f"Всего сгенерировано {len(self.employees)} сотрудников и {len(self.devices)} устройств")
        
        # Конвертация в словари для сериализации
        employees_data = [{
            'empID': emp.empID,
            'fio': emp.fio,
            'tn': emp.tn,
            'position': emp.position,
            'division': emp.division,
            'location': emp.location
        } for emp in self.employees]
        
        devices_data = [{
            'ID': dev.device_id,
            'empID': dev.emp_id,
            'nomenclature': dev.nomenclature,
            'model': dev.model,
            'dateReceipt': dev.date_receipt,
            'usefulLife': dev.useful_life,
            'status': dev.status,
            'ctc': dev.ctc,
            'serialNumber': dev.serial_number
        } for dev in self.devices]
        
        return {
            'employees': employees_data,
            'devices': devices_data
        }

async def save_to_json(data: Dict, filename: str) -> None:
    """Сохранение данных в JSON файл"""
    filepath = Path('data') / filename
    filepath.parent.mkdir(exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Данные сохранены в {filepath}")

async def main():
    """Основная функция"""
    try:
        # Инициализация клиента OpenAI
        init_openai_client()
        
        # Создание генератора данных
        generator = DataGenerator()
        
        # Генерация всех данных
        data = await generator.generate_all_data()
        
        # Сохранение данных
        await save_to_json(data, 'generated_data.json')
        
        print("Генерация данных успешно завершена!")
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

# Конфигурация моделей устройств
DEVICE_MODELS = {
    DeviceType.MONITOR: [
        'Dell U2419H', 'LG 24MK400H-B', 'Samsung S24R350', 'Acer R240Y', 'HP 24mh'
    ],
    DeviceType.DESKTOP: [
        'Dell OptiPlex 3080', 'HP ProDesk 400 G7', 'Lenovo ThinkCentre M75q', 'Acer Veriton X2660G'
    ],
    DeviceType.LAPTOP: [
        'Dell Latitude 5420', 'HP EliteBook 840 G8', 'Lenovo ThinkPad T14', 'Apple MacBook Pro 16" M1'
    ],
    DeviceType.TABLET: [
        'Apple iPad Pro 12.9"', 'Samsung Galaxy Tab S7', 'Huawei MatePad Pro', 'Lenovo Tab P12 Pro'
    ],
    DeviceType.PHONE: [
        'iPhone 13', 'Samsung Galaxy S21', 'Xiaomi Redmi Note 11', 'Huawei P50'
    ],
    DeviceType.KEYBOARD: [
        'Logitech K120', 'Dell KB216', 'HP K1500', 'A4Tech KR-85'
    ],
    DeviceType.MOUSE: [
        'Logitech M90', 'Dell MS116', 'HP X500', 'A4Tech OP-620D'
    ]
}

# Настройки по умолчанию для типов устройств
DEVICE_DEFAULTS = {
    DeviceType.MONITOR: {'min': 1, 'max': 2, 'useful_life': 5},
    DeviceType.DESKTOP: {'min': 1, 'max': 1, 'useful_life': 5},
    DeviceType.LAPTOP: {'min': 0, 'max': 1, 'useful_life': 3, 'manager_only': True},
    DeviceType.TABLET: {'min': 0, 'max': 1, 'useful_life': 3, 'manager_only': True},
    DeviceType.PHONE: {'min': 1, 'max': 1, 'useful_life': 3},
    DeviceType.KEYBOARD: {'min': 1, 'max': 1, 'useful_life': 5},
    DeviceType.MOUSE: {'min': 1, 'max': 1, 'useful_life': 5}
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

async def generate_reference_data() -> Dict[str, Any]:
    """Генерация справочных данных (города, подразделения, должности)"""
    try:
        # Пытаемся загрузить из кэша, чтобы не генерировать заново
        if os.path.exists('reference_cache.json'):
            with open('reference_cache.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Если кэша нет, используем встроенные тестовые данные
        data = {
            'cities': [
                "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
                "Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону",
                "Уфа", "Красноярск", "Пермь", "Воронеж", "Волгоград"
            ],
            'divisions': [
                {"name": "Центр розничного бизнеса", "level": 3, "parent": None},
                {"name": "Управление кредитования", "level": 2, "parent": 0},
                {"name": "Отдел ипотечного кредитования", "level": 1, "parent": 1},
                {"name": "Сектор андеррайтинга", "level": 0, "parent": 2},
                {"name": "Центр корпоративного бизнеса", "level": 3, "parent": None},
                {"name": "Управление расчетно-кассового обслуживания", "level": 2, "parent": 4},
                {"name": "Отдел валютного контроля", "level": 1, "parent": 5}
            ],
            'positions': [
                {"name": "Менеджер по продажам", "is_manager": False},
                {"name": "Старший менеджер", "is_manager": False},
                {"name": "Ведущий специалист", "is_manager": False},
                {"name": "Начальник отдела", "is_manager": True},
                {"name": "Заместитель начальника отдела", "is_manager": True},
                {"name": "Директор департамента", "is_manager": True},
                {"name": "Руководитель направления", "is_manager": True},
                {"name": "Специалист", "is_manager": False}
            ]
        }
        
        # Сохраняем в кэш
        with open('reference_cache.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return data
        
    except Exception as e:
        print(f"Ошибка при генерации справочных данных: {e}")
        # Возвращаем минимальный набор данных в случае ошибки
        return {
            'cities': ["Москва", "Санкт-Петербург", "Новосибирск"],
            'divisions': [{"name": "Головной офис", "level": 3, "parent": None}],
            'positions': [
                {"name": "Специалист", "is_manager": False},
                {"name": "Руководитель", "is_manager": True}
            ]
        }

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

async def generate_data():
    """Основная функция генерации данных"""
    print("=== Генератор тестовых данных для банка ===")
    print(f"Будет сгенерировано:")
    print(f"- Сотрудники: {NUM_EMPLOYEES}")
    print(f"- Устройства: {NUM_DEVICES}")
    print("\nНачало генерации...")
    
    start_time = time.time()
    
    try:
        # 1. Генерация справочных данных
        print("\n1. Генерация справочных данных...")
        try:
            ref_data = await generate_reference_data()
            print(f"   • Города: {len(ref_data['cities'])}")
            print(f"   • Подразделения: {len(ref_data['divisions'])}")
            print(f"   • Должности: {len(ref_data['positions'])}")
        except Exception as e:
            print(f"Ошибка при генерации справочных данных: {str(e)}")
            ref_data = {
                'cities': CITIES,
                'divisions': [{"name": "Головной офис", "level": 3, "parent": None}],
                'positions': [
                    {"name": "Специалист", "is_manager": False},
                    {"name": "Руководитель", "is_manager": True}
                ]
            }
            print(f"   • Используются стандартные значения")
            print(f"   • Города: {len(ref_data['cities'])}")
            print(f"   • Подразделения: {len(ref_data['divisions'])}")
            print(f"   • Должности: {len(ref_data['positions'])}")
        
        # 2. Генерация сотрудников
        print("\n2. Генерация сотрудников...")
        employees = []
        for i in range(1, NUM_EMPLOYEES + 1):
            if i % 100 == 0 or i == 1 or i == NUM_EMPLOYEES:
                print(f"   • Сотрудник {i}/{NUM_EMPLOYEES}")
            
            emp = await generate_employee(i, ref_data['cities'], ref_data['positions'])
            if emp:
                employees.append(emp)
        
        # 3. Распределение по подразделениям
        print("\n3. Распределение по подразделениям...")
        if ref_data['divisions']:
            assign_divisions_to_employees(employees, ref_data['divisions'])
        else:
            print("   • Нет данных о подразделениях, пропускаем распределение")
        
        # 4. Генерация устройств
        print("\n4. Генерация устройств...")
        devices = []
        data_gen = DataGenerator()
        
        # Сначала генерируем обязательные устройства для всех сотрудников
        for emp in employees:
            is_manager = emp.get('is_manager', False)
            
            # Обязательные устройства для всех
            for dev_type, settings in DEVICE_DEFAULTS.items():
                if settings.get('manager_only', False) and not is_manager:
                    continue
                    
                min_count = settings['min']
                max_count = settings['max']
                
                # Генерируем указанное количество устройств
                count = random.randint(min_count, max_count)
                for _ in range(count):
                    if len(devices) >= NUM_DEVICES:
                        break
                        
                    # Выбираем модель для данного типа устройства
                    model = random.choice(DEVICE_MODELS[dev_type])
                    
                    # Создаем устройство с указанным типом и моделью
                    device = await data_gen.generate_device(
                        device_id=len(devices) + 1,
                        emp_id=emp['empID'],
                        is_manager=is_manager,
                        device_type=dev_type,
                        model=model
                    )
                    
                    if device:
                        devices.append(device.to_dict() if hasattr(device, 'to_dict') else device)
        
        # Затем генерируем дополнительные устройства для руководителей
        manager_employees = [emp for emp in employees if emp.get('is_manager', False)]
        if manager_employees and len(devices) < NUM_DEVICES:
            # Дополнительные устройства для руководителей
            extra_devices = [
                (DeviceType.LAPTOP, 0.7),  # 70% шанс на ноутбук
                (DeviceType.TABLET, 0.4),   # 40% шанс на планшет
                (DeviceType.MONITOR, 0.3)   # 30% шанс на дополнительный монитор
            ]
            
            for emp in manager_employees:
                if len(devices) >= NUM_DEVICES:
                    break
                    
                for device_type, probability in extra_devices:
                    if random.random() < probability:
                        # Выбираем модель для данного типа устройства
                        model = random.choice(DEVICE_MODELS[device_type])
                        
                        # Создаем устройство с указанным типом и моделью
                        device = await data_gen.generate_device(
                            device_id=len(devices) + 1,
                            emp_id=emp['empID'],
                            is_manager=True,
                            device_type=device_type,
                            model=model
                        )
                        
                        if device:
                            devices.append(device.to_dict() if hasattr(device, 'to_dict') else device)
                            
                        if len(devices) >= NUM_DEVICES:
                            break
        
        # Если остались доступные устройства, распределяем их случайным образом
        remaining_devices = NUM_DEVICES - len(devices)
        if remaining_devices > 0:
            print(f"   • Распределение оставшихся {remaining_devices} устройств...")
            
            # Создаем список всех возможных типов устройств с их весами
            device_weights = [
                (DeviceType.DESKTOP, 20),
                (DeviceType.LAPTOP, 15),
                (DeviceType.MONITOR, 25),
                (DeviceType.PHONE, 15),
                (DeviceType.TABLET, 10),
                (DeviceType.KEYBOARD, 10),
                (DeviceType.MOUSE, 5)
            ]
            
            for _ in range(remaining_devices):
                if len(devices) >= NUM_DEVICES:
                    break
                    
                # Выбираем случайный тип устройства с учетом весов
                total_weight = sum(weight for _, weight in device_weights)
                r = random.uniform(0, total_weight)
                upto = 0
                for device_type, weight in device_weights:
                    if upto + weight >= r:
                        break
                    upto += weight
                
                # Выбираем случайного сотрудника
                emp = random.choice(employees)
                
                # Выбираем модель для данного типа устройства
                model = random.choice(DEVICE_MODELS[device_type])
                
                # Создаем устройство
                device = await data_gen.generate_device(
                    device_id=len(devices) + 1,
                    emp_id=emp['empID'],
                    is_manager=emp.get('is_manager', False),
                    device_type=device_type,
                    model=model
                )
                
                if device:
                    devices.append(device.to_dict() if hasattr(device, 'to_dict') else device)
        
        print(f"   • Всего сгенерировано {len(devices)} устройств")
        
        # 5. Формируем итоговые данные
        print("\n5. Формирование результата...")
        result = {
            'employees': employees,
            'devices': devices,
            'reference_data': ref_data
        }
        
        # 6. Сохранение в JSON
        print("\n6. Сохранение данных...")
        os.makedirs('data', exist_ok=True)
        output_file = os.path.join('data', 'generated_data.json')
        
        # Удаляем старый файл, если он существует
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"Удален старый файл: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
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

# Удаляем дублирующееся определение DEVICE_STATUSES

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

async def shutdown(signal, loop):
    """Аккуратная обработка завершения работы"""
    print(f"Получен сигнал {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

if __name__ == "__main__":
    import asyncio
    import signal
    import time
    from datetime import datetime
    
    # Создаем и настраиваем цикл событий
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    start_time = time.time()
    
    async def main():
        try:
            print("=== Запуск генерации данных ===")
            result = await generate_data()
            
            if result:
                print("\n=== Генерация данных завершена успешно ===")
                print(f"\nСтатистика:")
                print(f"- Сотрудники: {len(result['employees'])}")
                print(f"- Устройства: {len(result['devices'])}")
                print(f"- Города: {len(result['reference_data']['cities'])}")
                print(f"- Подразделения: {len(result['reference_data']['divisions'])}")
                
                # Сохраняем статистику
                elapsed_time = time.time() - start_time
                stats = {
                    'generated_at': datetime.now().isoformat(),
                    'execution_time_seconds': round(elapsed_time, 2),
                    'status': 'completed',
                    'output_file': 'data/generated_data.json',
                    'employees_count': len(result['employees']),
                    'devices_count': len(result['devices'])
                }
                
                os.makedirs('data', exist_ok=True)
                with open('data/generation_stats.json', 'w', encoding='utf-8') as f:
                    json.dump(stats, f, ensure_ascii=False, indent=2)
                
                return True
            else:
                print("\n!!! Генерация данных завершилась с ошибкой")
                return False
                
        except Exception as e:
            print(f"\n!!! Критическая ошибка: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Останавливаем цикл событий после завершения
            loop.stop()
    
    # Настраиваем обработчики сигналов для корректного завершения
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(sig, loop)))
        except (NotImplementedError, RuntimeError):
            # Игнорируем ошибки на платформах, где не поддерживается
            pass
    
    # Удаляем старые файлы данных, если они существуют
    for filename in ['data/generated_data.json', 'data/employees.json', 'data/devices.json']:
        try:
            os.makedirs('data', exist_ok=True)
            os.remove(filename)
            print(f"Удален старый файл: {filename}")
        except FileNotFoundError:
            pass
    
    # Запускаем генерацию данных
    success = False
    try:
        loop.run_until_complete(main())
        success = True
    except KeyboardInterrupt:
        print("\nГенерация данных прервана пользователем.")
    except Exception as e:
        print(f"\nПроизошла ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        elapsed_time = time.time() - start_time
        print(f"\nОбщее время выполнения: {elapsed_time:.2f} секунд")
        
        # Закрываем цикл событий
        loop.close()
        exit(0 if success else 1)
