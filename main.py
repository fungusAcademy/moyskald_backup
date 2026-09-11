import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("MOYSKLAD_TOKEN")
SAVE_DIR = r"C:\WORKSPACE\moyskald_backup\backup"
TEMPLATES_TO_EXPORT = ["check", "check NL", "upd"]

if not TOKEN:
    raise ValueError("❌ Токен не найден! Проверьте файл .env")

headers = {
    "Authorization": f"Bearer {TOKEN.strip()}",
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip"
}

def get_date_30_days_ago():
    """Возвращает дату и время ровно 30 дней назад от текущего момента"""
    date_30_days_ago = datetime.now() - timedelta(days=30)
    return date_30_days_ago.strftime("%Y-%m-%d %H:%M:%S")

def get_custom_templates_map(entity_type):
    url = f"https://api.moysklad.ru/api/remap/1.2/entity/{entity_type}/metadata/customtemplate"
    res = requests.get(url, headers=headers)
    templates_map = {}
    if res.status_code == 200:
        for t in res.json().get("rows", []):
            templates_map[t.get("name")] = t.get("meta")
    return templates_map

def download_printed_form(doc_id, doc_meta, template_meta, check_tables_dir, doc_name, t_name):
    clean_t_name = t_name.replace(" ", "_")
    
    # 1. Пакетный экспорт
    url_batch = "https://api.moysklad.ru/api/remap/1.2/entity/export/"
    payload_batch = {
        "templates": [{"template": {"meta": template_meta}, "count": 1}],
        "objects": [{"meta": doc_meta}]
    }
    
    res = requests.post(url_batch, headers=headers, json=payload_batch)
    if res.status_code == 200:
        content_disp = res.headers.get("Content-Disposition", "")
        ext = ".xlsx"
        if ".pdf" in content_disp:
            ext = ".pdf"
        elif ".xls" in content_disp:
            ext = ".xls"

        filename = f"Документ_{doc_name}_{clean_t_name}{ext}"
        with open(os.path.join(check_tables_dir, filename), "wb") as f:
            f.write(res.content)
        return True

    # 2. Одиночный экспорт с подбором расширений (xlsx -> xls -> pdf)
    url_single = f"https://api.moysklad.ru/api/remap/1.2/entity/demand/{doc_id}/export/"
    for ext in ["xlsx", "xls", "pdf"]:
        payload_single = {
            "template": {"meta": template_meta},
            "extension": ext
        }
        res_single = requests.post(url_single, headers=headers, json=payload_single)
        if res_single.status_code == 200:
            filename = f"Документ_{doc_name}_{clean_t_name}.{ext}"
            with open(os.path.join(check_tables_dir, filename), "wb") as f:
                f.write(res_single.content)
            return True

    print(f"❌ Ошибка экспорта '{t_name}' для {doc_name}: Код {res.status_code}")
    return False

def make_backup():
    today_folder = datetime.now().strftime("%Y-%m-%d")
    current_backup_dir = os.path.join(SAVE_DIR, today_folder)
    os.makedirs(current_backup_dir, exist_ok=True)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Начало выгрузки бэкапа...")

    # 1. Выгрузка Контрагентов
    try:
        url_cp = "https://api.moysklad.ru/api/remap/1.2/entity/counterparty"
        res_cp = requests.get(url_cp, headers=headers, params={"limit": 1000})
        
        if res_cp.status_code == 200:
            rows = res_cp.json().get("rows", [])
            cp_list = [{
                "Наименование": item.get("name", ""),
                "Телефон": item.get("phone", ""),
                "Email": item.get("email", ""),
                "ИНН": item.get("inn", ""),
                "КПП": item.get("kpp", ""),
                "Комментарий": item.get("description", ""),
                "Создан": item.get("created", "")
            } for item in rows]
            
            df_cp = pd.DataFrame(cp_list)
            df_cp.to_excel(os.path.join(current_backup_dir, "Контрагенты.xlsx"), index=False)
            print("✔ Контрагенты успешно сохранены.")
    except Exception as e:
        print(f"❌ Ошибка выгрузки контрагентов: {e}")

    # 2. Список отгрузок за последние 30 дней
    start_date = get_date_30_days_ago()
    print(f"⏳ Фильтр отгрузок с: {start_date}")
    
    url_demands = "https://api.moysklad.ru/api/remap/1.2/entity/demand"
    res_demands = requests.get(url_demands, headers=headers, params={"filter": f"moment>={start_date}", "limit": 100})
    
    if res_demands.status_code != 200:
        print(f"❌ Ошибка получения отгрузок: {res_demands.status_code}")
        return

    demands = res_demands.json().get("rows", [])
    print(f"✔ Найдено отгрузок за последние 30 дней: {len(demands)}")

    check_tables_dir = os.path.join(current_backup_dir, "Чеки_Таблицы")
    os.makedirs(check_tables_dir, exist_ok=True)

    templates_map = get_custom_templates_map("demand")

    # 3. Экспорт печатных форм
    success_count = 0
    for doc in demands:
        doc_id = doc.get("id")
        doc_name = doc.get("name", doc_id).replace("/", "_").replace("\\", "_")
        doc_meta = doc.get("meta")

        for t_name in TEMPLATES_TO_EXPORT:
            meta = templates_map.get(t_name)
            if not meta:
                continue

            if download_printed_form(doc_id, doc_meta, meta, check_tables_dir, doc_name, t_name):
                success_count += 1

    print(f"✔ Успешно сохранено файлов: {success_count}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Бэкап завершен!")

if __name__ == "__main__":
    make_backup()