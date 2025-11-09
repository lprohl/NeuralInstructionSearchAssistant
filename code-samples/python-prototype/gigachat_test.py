import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация - получаем ключи из переменных окружения
CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")
AUTHORIZATION_KEY = os.getenv("GIGACHAT_AUTHORIZATION_KEY")

# Базовые URL API GigaChat
AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Путь к сертификатам
CERTS_PATH = Path(__file__).parent / "certs"  # Папка certs должна находиться в корне проекта
CA_CERT_PATH = CERTS_PATH / "russian_trusted_root_ca.cer" #"ca-cert.pem"  # Путь к корневому сертификату
SUB_CA_CERT_PATH = CERTS_PATH / "russian_trusted_sub_ca.cer" #sub-ca-cert.pem"  # Путь к подчинённому сертификату


def get_access_token():
    """Получаем access_token для авторизации в API"""
    headers = {
        "Authorization": f"Bearer {AUTHORIZATION_KEY}",
        "RqUID": "6f0b1291-c7f3-43c6-bb2e-9f3efb2dc98e",  # Можно оставить постоянным
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "scope": "GIGACHAT_API_PERS"
    }

    auth = (CLIENT_ID, CLIENT_SECRET)

    # Используем verify с путём к сертификату
    response = requests.post(AUTH_URL, headers=headers, data=data, auth=auth, verify=str(CA_CERT_PATH))
    response.raise_for_status()
    return response.json()["access_token"]


def send_to_gigachat(prompt, text, access_token):
    """Отправляем запрос к GigaChat API"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "user",
            "content": f"{prompt}\n\n{text}"
        }
    ]

    payload = {
        "model": "GigaChat",
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.9,
        "n": 1,
        "max_tokens": 2000,
        "stream": False
    }

    # Используем verify с путём к сертификату
    response = requests.post(API_URL, headers=headers, json=payload, verify=str(CA_CERT_PATH))
    response.raise_for_status()
    return response.json()


def read_prompt(input_file_path):
    """Читаем промт из файла prompt.txt"""
    prompt_path = Path(input_file_path).parent / "prompt.txt"
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Ошибка: Файл с промтом не найден: {prompt_path}")
        exit(1)
    except Exception as e:
        print(f"Ошибка при чтении файла с промтом: {str(e)}")
        exit(1)


def process_file(input_file_path):
    """Основная функция обработки файла"""
    try:
        # Читаем исходный файл
        with open(input_file_path, 'r', encoding='utf-8') as file:
            text = file.read()

        # Читаем промт из файла
        prompt = read_prompt(input_file_path)
        print(f"Используется промт: {prompt[:100]}...")  # Показываем начало промта для проверки

        # Получаем токен доступа
        access_token = get_access_token()

        # Отправляем запрос к GigaChat
        response = send_to_gigachat(prompt, text, access_token)

        # Извлекаем ответ
        answer = response['choices'][0]['message']['content']

        # Выводим ответ на экран
        print("\nОтвет от GigaChat:")
        print(answer)

        # Сохраняем ответ в файл
        input_path = Path(input_file_path)
        output_file = input_path.parent / f"{input_path.stem}_response.txt"

        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(f"Prompt: {prompt}\n\n")
            file.write(f"Original file: {input_path.name}\n\n")
            file.write("GigaChat response:\n")
            file.write(answer)

        print(f"\nОтвет сохранён в файл: {output_file}")

    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")


if __name__ == "__main__":
    # Запрашиваем у пользователя путь к файлу
    input_file = input("Введите путь к файлу: ")

    # Проверяем, что файл существует
    if not os.path.isfile(input_file):
        print("Ошибка: Указанный файл не существует!")
        exit(1)

    # Проверяем, что все необходимые переменные окружения установлены
    print(f"GIGACHAT_CLIENT_ID: {CLIENT_ID}")
    print(f"CLIENT_SECRET: {CLIENT_SECRET}")
    print(f"AUTHORIZATION_KEY: {AUTHORIZATION_KEY}")
    required_env_vars = ["GIGACHAT_CLIENT_ID", "GIGACHAT_CLIENT_SECRET", "GIGACHAT_AUTHORIZATION_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Ошибка: Не заданы следующие переменные окружения: {', '.join(missing_vars)}")
        print("Пожалуйста, установите их перед запуском скрипта.")
        exit(1)

    # Проверяем наличие сертификатов
    if not CA_CERT_PATH.exists() or not SUB_CA_CERT_PATH.exists():
        print(f"Ошибка: Сертификаты не найдены в папке {CERTS_PATH}.")
        print("Пожалуйста, скачайте и добавьте сертификаты в указанную папку.")
        exit(1)

    # Запускаем обработку файла
    process_file(input_file)
