import os
from supabase import create_client, Client

# === Загружаем переменные среды ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def main():
    print("🔗 Подключаюсь к Supabase...")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("📥 Читаю таблицу moysklad_accounts...")

    response = supabase.table("moysklad_accounts").select("*").execute()

    rows = response.data

    print("📄 Получено строк:", len(rows))
    print("-----------------------------------")

    for row in rows:
        print(row)
        print("-----------------------------------")

if __name__ == "__main__":
    main()
