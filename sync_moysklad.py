import os
import requests
from supabase import create_client, Client

# === Загружаем переменные среды ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


def main():
    print("\n==============================")
    print("🔗 Подключаюсь к Supabase...")
    print("==============================\n")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("📥 Читаю таблицу moysklad_accounts...\n")

    response = supabase.table("moysklad_accounts").select("*").execute()
    rows = response.data

    print("📄 Найдено аккаунтов МойСклад:", len(rows))
    print("-----------------------------------\n")

    if not rows:
        print("❌ Нет записей в moysklad_accounts")
        return

    # Берём первый аккаунт (для теста)
    acc = rows[0]

    token = acc.get("access_token")
    account_id = acc.get("account_id")

    print(f"🏦 ACCOUNT ID: {account_id}")
    print(f"🔑 ACCESS TOKEN: {token[:8]}... (скрыто)\n")

    if not token:
        print("❌ Нет токена доступа, нельзя запросить МойСклад API")
        return

    # ============================
    #   ЗАПРОС ТОВАРОВ
    # ============================
    print("🔎 Запрашиваю товары из МойСклад...\n")

    url_products = "https://api.moysklad.ru/api/remap/1.2/entity/product"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    r = requests.get(url_products, headers=headers)
    print("HTTP статус (товары):", r.status_code)

    if r.status_code != 200:
        print("❌ Ошибка получения товаров:")
        print(r.text)
        return

    products = r.json().get("rows", [])
    print(f"📦 ТОВАРОВ ПОЛУЧЕНО: {len(products)}\n")
    print("-----------------------------------")

    # Покажем первые 5 товаров
    print("🟦 ПЕРВЫЕ 5 ТОВАРОВ:")
    for p in products[:5]:
        name = p.get("name")
        prices = p.get("salePrices", [])
        price = 0

        if prices:
            price = prices[0].get("value", 0) / 100

        print(f"🔹 {name} — {price} ₽")

    print("-----------------------------------\n")

    # ============================
    #   ЗАПРОС ОСТАТКОВ
    # ============================
    print("🔎 Запрашиваю остатки товаров...\n")

    url_stock = "https://api.moysklad.ru/api/remap/1.2/report/stock/bystore"

    r2 = requests.get(url_stock, headers=headers)
    print("HTTP статус (остатки):", r2.status_code)

    if r2.status_code != 200:
        print("❌ Ошибка получения остатков:")
        print(r2.text)
        return

    stocks = r2.json().get("rows", [])
    print(f"📊 ОСТАТКОВ ПОЛУЧЕНО: {len(stocks)}\n")
    print("-----------------------------------")

    # Покажем первые 5 остатков
    print("🟦 ПЕРВЫЕ 5 ОСТАТКОВ:")
    for s in stocks[:5]:
        print(f"🔹 {s.get('name')} — остаток: {s.get('stock')}")

    print("-----------------------------------\n")
    print("✅ Тест запроса МойСклад завершён успешно!\n")


if __name__ == "__main__":
    main()
