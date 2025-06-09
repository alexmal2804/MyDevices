@echo off
echo Установка окружения для генератора данных

:: Проверка наличия Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Ошибка: Python не установлен или не добавлен в PATH
    pause
    exit /b 1
)

:: Создание виртуального окружения
echo Создание виртуального окружения...
python -m venv venv
if %ERRORLEVEL% neq 0 (
    echo Ошибка при создании виртуального окружения
    pause
    exit /b 1
)

:: Активация виртуального окружения
call venv\Scripts\activate
if %ERRORLEVEL% neq 0 (
    echo Ошибка при активации виртуального окружения
    pause
    exit /b 1
)

:: Установка зависимостей
echo Установка зависимостей...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Ошибка при установке зависимостей
    pause
    exit /b 1
)

:: Создание файла .env, если его нет
if not exist .env (
    echo Создание файла .env...
    copy .env.sample .env
    echo Пожалуйста, откройте файл .env и настройте параметры
) else (
    echo Файл .env уже существует
)

:: Создание файла учетных данных Firebase, если его нет
if not exist firebase-credentials.json (
    if exist firebase-credentials.json.sample (
        echo Создание файла firebase-credentials.json...
        copy firebase-credentials.json.sample firebase-credentials.json
        echo Пожалуйста, настройте файл firebase-credentials.json с вашими учетными данными Firebase
    )
) else (
    echo Файл firebase-credentials.json уже существует
)

echo.
echo Установка завершена успешно!
echo 1. Настройте файлы .env и firebase-credentials.json
echo 2. Запустите генератор данных: python generator.py
pause
