import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('uploader.log')
    ]
)
logger = logging.getLogger(__name__)

# Константы
BATCH_SIZE = 400  # Максимальное количество операций в одной пакетной записи

class FirebaseUploader:
    def __init__(self):
        self.db = self.initialize_firebase()
        self.batch = self.db.batch()
        self.operation_count = 0
        self.total_operations = 0

    @staticmethod
    def initialize_firebase():
        """Инициализация Firebase Admin SDK из файла .venv"""
        try:
            if not firebase_admin._apps:
                # Путь к файлу с учетными данными
                venv_path = os.path.join('venv', '.venv')
                
                if not os.path.exists(venv_path):
                    raise FileNotFoundError(f"Файл с учетными данными не найден: {venv_path}")
                
                # Чтение содержимого файла
                with open(venv_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Извлечение JSON из содержимого файла
                import re
                import ast
                
                # Ищем словарь FIREBASE_SERVICE_ACCOUNT в файле
                match = re.search(r'FIREBASE_SERVICE_ACCOUNT\s*=\s*({.*?})\s*$', 
                                content, re.DOTALL | re.MULTILINE)
                
                if not match:
                    raise ValueError("Не удалось найти FIREBASE_SERVICE_ACCOUNT в файле .venv")
                
                # Преобразуем строку с JSON в словарь
                try:
                    # Используем ast.literal_eval для безопасного преобразования строки в словарь
                    cred_dict = ast.literal_eval(match.group(1).strip())
                except (ValueError, SyntaxError) as e:
                    raise ValueError(f"Ошибка при разборе FIREBASE_SERVICE_ACCOUNT: {e}")
                
                # Инициализация Firebase с учетными данными из словаря
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK успешно инициализирован")
            
            return firestore.client()
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации Firebase: {e}", exc_info=True)
            raise

    async def delete_collection(self, collection_name: str) -> int:
        """
        Удаление всех документов в коллекции
        
        Args:
            collection_name: Имя коллекции для удаления
            
        Returns:
            int: Количество удаленных документов
        """
        try:
            logger.info(f"Начало удаления коллекции: {collection_name}")
            collection_ref = self.db.collection(collection_name)
            
            # Получаем первую порцию документов
            docs = collection_ref.limit(BATCH_SIZE).stream()
            
            deleted = 0
            total_deleted = 0
            batch = self.db.batch()
            
            # Удаляем документы пакетами
            while True:
                doc_count = 0
                
                # Собираем пакет документов для удаления
                for doc in docs:
                    batch.delete(doc.reference)
                    deleted += 1
                    doc_count += 1
                    
                    # Если набрали пакет, фиксируем
                    if deleted % BATCH_SIZE == 0:
                        batch.commit()
                        logger.info(f"Удалено {deleted} документов из {collection_name}")
                        batch = self.db.batch()
                        break
                
                total_deleted += doc_count
                
                # Если документов больше нет, выходим
                if doc_count < BATCH_SIZE:
                    break
                    
                # Получаем следующую порцию документов
                last_doc = None
                for doc in collection_ref.limit(BATCH_SIZE).stream():
                    last_doc = doc
                    break
                    
                if last_doc is None:
                    break
                    
                docs = collection_ref.start_after(last_doc).limit(BATCH_SIZE).stream()
            
            # Фиксируем оставшиеся изменения
            if deleted % BATCH_SIZE != 0:
                batch.commit()
            
            logger.info(f"Успешно удалено {total_deleted} документов из {collection_name}")
            return total_deleted
            
        except Exception as e:
            logger.error(f"Критическая ошибка при удалении коллекции {collection_name}: {e}", exc_info=True)
            raise

    def add_to_batch(self, collection: str, doc_id: str, data: Dict[str, Any]) -> None:
        """Добавление операции в пакет"""
        doc_ref = self.db.collection(collection).document(doc_id)
        self.batch.set(doc_ref, data)
        self.operation_count += 1
        self.total_operations += 1
        
        # Если накопилось достаточно операций, выполняем пакет
        if self.operation_count >= BATCH_SIZE:
            self.commit_batch()

    def commit_batch(self) -> None:
        """Выполнение пакетной операции"""
        if self.operation_count > 0:
            try:
                self.batch.commit()
                logger.info(f"Выполнена пакетная запись {self.operation_count} операций")
                self.batch = self.db.batch()
                self.operation_count = 0
            except Exception as e:
                logger.error(f"Ошибка при выполнении пакетной записи: {e}", exc_info=True)
                raise

    async def upload_data(self, data: Dict[str, Any]) -> None:
        """Основная функция загрузки данных"""
        start_time = datetime.now()
        logger.info("Начало загрузки данных в Firestore")
        
        try:
            # Удаление существующих коллекций
            collections_to_delete = ['employees', 'devices', 'referenceData']
            logger.info(f"Начало удаления коллекций: {', '.join(collections_to_delete)}")
            
            for collection in collections_to_delete:
                try:
                    deleted_count = await self.delete_collection(collection)
                    logger.info(f"Удалено {deleted_count} документов из коллекции {collection}")
                except Exception as e:
                    logger.error(f"Не удалось удалить коллекцию {collection}: {e}")
                    raise
            
            # Загрузка эталонных данных
            if 'reference_data' in data:
                ref_data = data['reference_data']
                logger.info("Загрузка эталонных данных...")
                
                # Сохраняем города
                self.add_to_batch('referenceData', 'cities', {'cities': ref_data.get('cities', [])})
                
                # Сохраняем подразделения
                self.add_to_batch('referenceData', 'divisions', {'divisions': ref_data.get('divisions', [])})
                
                # Сохраняем должности
                self.add_to_batch('referenceData', 'positions', {'positions': ref_data.get('positions', [])})
                
                logger.info(f"Загружено {len(ref_data.get('cities', []))} городов, "
                          f"{len(ref_data.get('divisions', []))} подразделений, "
                          f"{len(ref_data.get('positions', []))} должностей")
            
            # Загрузка сотрудников
            if 'employees' in data and data['employees']:
                logger.info(f"Загрузка {len(data['employees'])} сотрудников...")
                for emp in data['employees']:
                    emp_id = str(emp.get('empID', ''))
                    if emp_id:
                        # Преобразуем все поля в строки, чтобы избежать проблем с типами
                        emp_data = {k: str(v) if not isinstance(v, (dict, list, bool)) else v 
                                  for k, v in emp.items()}
                        self.add_to_batch('employees', emp_id, emp_data)
                
                self.commit_batch()  # Финализируем последний пакет
                logger.info(f"Загружено {len(data['employees'])} сотрудников")
            
            # Загрузка устройств
            if 'devices' in data and data['devices']:
                logger.info(f"Загрузка {len(data['devices'])} устройств...")
                for device in data['devices']:
                    device_id = str(device.get('ID', ''))
                    if device_id:
                        device_data = {k: str(v) if not isinstance(v, (dict, list, bool)) else v 
                                     for k, v in device.items()}
                        self.add_to_batch('devices', device_id, device_data)
                
                self.commit_batch()  # Финализируем последний пакет
                logger.info(f"Загружено {len(data['devices'])} устройств")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Загрузка данных завершена за {duration:.2f} секунд")
            logger.info(f"Всего выполнено {self.total_operations} операций записи")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при загрузке данных: {e}", exc_info=True)
            raise

async def main():
    """Основная асинхронная функция"""
    try:
        # Загрузка данных из файла
        data_file = os.path.join('data', 'generated_data.json')
        if not os.path.exists(data_file):
            logger.error(f"Файл с данными не найден: {data_file}")
            return
        
        logger.info(f"Чтение данных из файла: {data_file}")
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Загрузка данных в Firebase
        uploader = FirebaseUploader()
        await uploader.upload_data(data)
        
        logger.info("Все операции успешно завершены")
        
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при разборе JSON: {e}")
    except Exception as e:
        logger.error(f"Ошибка в главной функции: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())