#!/bin/bash
echo "Установка окружения для генератора данных"

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "Ошибка: Python 3 не установлен"
    exit 1
fi

# Создание виртуального окружения
echo "Создание виртуального окружения..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Ошибка при создании виртуального окружения"
    exit 1
fi

# Активация виртуального окружения
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Ошибка при активации виртуального окружения"
    exit 1
fi

# Установка зависимостей
echo "Установка зависимостей..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Ошибка при установке зависимостей"
    exit 1
fi

# Создание файла .env, если его нет
if [ ! -f .env ]; then
    echo "Создание файла .env..."
    cp .env.sample .env
    echo "Пожалуйста, откройте файл .env и настройте параметры"
else
    echo "Файл .env уже существует"
fi

# Создание файла учетных данных Firebase, если его нет
if [ ! -f firebase-credentials.json ]; then
    if [ -f firebase-credentials.json.sample ]; then
        echo "Создание файла firebase-credentials.json..."
        cp firebase-credentials.json.sample firebase-credentials.json
        echo "Пожалуйста, настройте файл firebase-credentials.json с вашими учетными данными Firebase"
    fi
else
    echo "Файл firebase-credentials.json уже существует"
fi

echo ""
echo "Установка завершена успешно!"
echo "1. Настройте файлы .env и firebase-credentials.json"
echo "2. Запустите генератор данных: python generator.py"
