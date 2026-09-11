import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("MOYSKLAD_TOKEN")
SAVE_DIR = r"C:\WORKSPACE\moyskald_backup\backup"

if not TOKEN:
    raise ValueError("❌ Токен не найден! Проверьте файл .env")

headers = {
    "Authorization": f"Bearer {TOKEN.strip()}",
    "Content-Type": "application/json"
}

ENTITIES = [
    "demand",          # Отгрузки
    "customerorder",    # Заказы покупателей
    "retaildemand",     # Розничные продажи (чеки ККМ)
    "salesreturn",      # Возвраты
    "facturein",        # Полученные счета-фактуры
    "factureout",       # Выданные счета-фактуры
    "invoiceout"        # Счета покупателям
]

TEMPLATE_TYPES = ["embeddedtemplate", "customtemplate"]

def fetch_all_templates():
    os.makedirs(SAVE_DIR, exist_ok=True)
    output_file = os.path.join(SAVE_DIR, "all_templates.txt")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Скачиваем список шаблонов...")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=== СПИСОК ВСЕХ ШАБЛОНОВ ИЗ МОЙСКЛАД ===\n\n")

        for entity in ENTITIES:
            f.write(f"----------------------------------------\n")
            f.write(f"СУЩНОСТЬ: {entity.upper()}\n")
            f.write(f"----------------------------------------\n")

            found_any = False
            for t_type in TEMPLATE_TYPES:
                url = f"https://api.moysklad.ru/api/remap/1.2/entity/{entity}/metadata/{t_type}"
                res = requests.get(url, headers=headers)
                
                if res.status_code == 200:
                    rows = res.json().get("rows", [])
                    for t in rows:
                        found_any = True
                        name = t.get("name")
                        meta_type = t.get("meta", {}).get("type")
                        href = t.get("meta", {}).get("href")
                        
                        info = f"Имя: '{name}' | Категория: {t_type} | Тип: '{meta_type}'\nHref: {href}\n\n"
                        f.write(info)
                        print(f"[{entity.upper()}] Найдено ({t_type}): '{name}'")
                else:
                    f.write(f"[{t_type}] Ошибка (код {res.status_code})\n")

            if not found_any:
                f.write("Шаблоны не найдены.\n")
            f.write("\n")

    print(f"\n✔ Готово! Полный список сохранен в файл:\n{output_file}")

if __name__ == "__main__":
    fetch_all_templates()