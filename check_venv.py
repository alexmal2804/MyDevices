import os

# Путь к файлу с учетными данными
venv_path = os.path.join('venv', '.venv')

# Проверяем существование файла
if not os.path.exists(venv_path):
    print(f"Файл {venv_path} не найден")
else:
    print(f"Содержимое файла {venv_path}:")
    print("-" * 50)
    with open(venv_path, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
    print("-" * 50)
    print(f"Тип содержимого: {type(content)}")
    print(f"Длина содержимого: {len(content)} символов")
    
    # Пытаемся найти JSON в содержимом
    import re
    import json
    
    # Ищем JSON-объект в файле
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        print("\nНайден JSON в файле:")
        try:
            json_data = json.loads(json_match.group(0))
            print("JSON успешно распарсен!")
            print("Ключи в JSON:", list(json_data.keys()))
        except json.JSONDecodeError as e:
            print(f"Ошибка при парсинге JSON: {e}")
    else:
        print("\nНе удалось найти JSON в файле")
