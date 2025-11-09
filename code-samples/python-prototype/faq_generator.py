import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройки
CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")
AUTHORIZATION_KEY = os.getenv("GIGACHAT_AUTHORIZATION_KEY")

# Путь к сертификатам
CERTS_PATH = Path(__file__).parent / "certs"  # Папка certs должна находиться в корне проекта
CA_CERT_PATH = CERTS_PATH / "russian_trusted_root_ca.cer" #"ca-cert.pem"  # Путь к корневому сертификату
SUB_CA_CERT_PATH = CERTS_PATH / "russian_trusted_sub_ca.cer" #sub-ca-cert.pem"  # Путь к подчинённому сертификату

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL = "https://gigachat.devices.sberbank.ru/api/v1"
#API_URL = "https://api.gigachat.ai/api/v1"

FILES_FOLDER = "files"

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

    response = requests.post(AUTH_URL, headers=headers, data=data, auth=auth, verify=str(CA_CERT_PATH))
    response.raise_for_status()
    return response.json()["access_token"]


def upload_file(file_path, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    url = f"{API_URL}/files"

    # Определяем MIME-тип файла
    file_extension = os.path.splitext(file_path)[1].lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword'
    }
    mime_type = mime_types.get(file_extension, 'application/octet-stream')

    with open(file_path, "rb") as f:
        data = {
            "purpose": "general"
        }
        files = {
            "file": (os.path.basename(file_path), f, mime_type)
        }
        response = requests.post(url, headers=headers, data=data, files=files, verify=str(CA_CERT_PATH))

        print(f"Статус код: {response.status_code}")
        print(f"Ответ сервера: {response.text}")

        response.raise_for_status()
        file_info = response.json()
        return file_info["id"]


def generate_faq(file_ids, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"{API_URL}/chat/completions"

    system_prompt = ("Ты эксперт и должен создать FAQ по загруженным документам. "
                     "В каждом вопросе указывай номер страницы, где найдена информация."
                     "Ответ выведи в виде json файла с массивом структур с полями Вопрос, Ответ, НомерСтраницы" )

    # Формируем текст с упоминанием файлов
    files_mention = ", ".join([f"file_id:{fid}" for fid in file_ids])
    user_prompt = f"Проанализируй документы ({files_mention}) и создай подробный FAQ с указанием номеров страниц."

    payload = {
        "model": "GigaChat",
        "function_call": "auto",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt, "attachments": file_ids}
        ],
        "temperature": 0.7,
        "top_p": 0.9,
        #"max_tokens": 2048,
        "n": 1,
        "stream": False,
        "update_interval": 0
    }

    # Добавляем файлы на верхнем уровне payload, если API это поддерживает
    if file_ids:
        payload["files"] = [{"id": fid} for fid in file_ids]

    print(f"Отправка запроса с {len(file_ids)} файлами...")
    print(f"Payload: {payload}")

    response = requests.post(url, headers=headers, json=payload, verify=str(CA_CERT_PATH))

    print(f"Статус код: {response.status_code}")
    if response.status_code != 200:
        print(f"Ошибка: {response.text}")

    response.raise_for_status()
    return response.json()


def delete_file(file_id, access_token):
    """Удаление конкретного файла по ID"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    url = f"{API_URL}/files/{file_id}/delete"

    response = requests.post(url, headers=headers, verify=str(CA_CERT_PATH))

    if response.status_code == 200:
        print(f"✓ Файл {file_id} успешно удалён")
        return True
    else:
        print(f"✗ Ошибка при удалении файла {file_id}: {response.status_code} - {response.text}")
        return False


def get_file_info(file_id, access_token):
    """Получение информации о конкретном файле"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    url = f"{API_URL}/files/{file_id}"

    response = requests.get(url, headers=headers, verify=str(CA_CERT_PATH))

    print(f"Статус получения информации о файле: {response.status_code}")
    print(f"Ответ: {response.text}")

    if response.status_code == 200:
        return response.json()
    return None

def get_all_files(access_token):
    """Получение списка всех загруженных файлов"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    url = f"{API_URL}/files"

    response = requests.get(url, headers=headers, verify=str(CA_CERT_PATH))

    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print(f"Ошибка при получении списка файлов: {response.text}")
        return []


def delete_all_files(access_token):
    """Удаление всех загруженных файлов"""
    print("\nПолучение списка всех файлов...")
    files = get_all_files(access_token)

    if not files:
        print("Нет файлов для удаления")
        return

    print(f"Найдено файлов: {len(files)}")
    deleted_count = 0

    for file_info in files:
        file_id = file_info.get("id")
        filename = file_info.get("filename", "неизвестно")
        print(f"Удаление: {filename} (ID: {file_id})")

        if delete_file(file_id, access_token):
            deleted_count += 1

    print(f"\n✓ Удалено файлов: {deleted_count} из {len(files)}")


def main():
    access_token = get_access_token()

    # Опция 1: Удалить все файлы перед началом работы
    # Раскомментируйте, если хотите очищать все файлы при каждом запуске
    # delete_all_files(access_token)

    print("Загрузка файлов...")
    file_ids = []
    uploaded_files = []  # Сохраняем информацию о загруженных файлах

    for filename in os.listdir(FILES_FOLDER):
        if filename.lower().endswith((".docx", ".pdf")):
            file_path = os.path.join(FILES_FOLDER, filename)
            file_id = upload_file(file_path, access_token)
            print(f"Загружен {filename}, ID: {file_id}")
            file_ids.append(file_id)
            uploaded_files.append({"id": file_id, "filename": filename})

    if not file_ids:
        print("Нет файлов для обработки!")
        return

    print("\nГенерация FAQ по загруженным документам...")
    faq_response = generate_faq(file_ids, access_token)

    print("\nСгенерированный FAQ:")
    for choice in faq_response.get("choices", []):
        content = choice.get("message", {}).get("content", "")
        print(content)

        # Сохранение результата в файл
        with open("faq_output.txt", "w", encoding="utf-8") as f:
            f.write(content)
        print("\n✓ FAQ сохранён в файл faq_output.txt")

    # Опция 2: Удалить только загруженные в этой сессии файлы
    print("\nУдаление загруженных файлов...")
    for file_info in uploaded_files:
        delete_file(file_info["id"], access_token)

    # Опция 3: Удалить все файлы после завершения работы
    # Раскомментируйте, если нужно
    # delete_all_files(access_token)

# Дополнительная функция для ручной очистки (можно вызвать отдельно)
def cleanup_all_files():
    """Утилита для полной очистки всех файлов"""
    access_token = get_access_token()
    delete_all_files(access_token)


if __name__ == "__main__":
    #cleanup_all_files()
    main()
