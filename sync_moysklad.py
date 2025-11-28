import os
import requests
from supabase import create_client, Client
from datetime import datetime

# === Supabase ENV ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# === MoySklad API base ===
MS_BASE = "https://api.moysklad.ru/api/remap/1.2"


def ms_get(url, token, params=None):
    """Обёртка для запросов в МойСклад"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    r = requests.get(url, headers=headers, params=params)
    return r


def main():
    print("\n==============================")
    print("🔗 Подключаюсь к Supabase...")
    print("==============================\n")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("📥 Читаю таблицу moysklad_accounts...\n")

    resp = supabase.table("moysklad_accounts").select("*").execute()
    rows = resp.data

    print("📄 Найдено аккаунтов МойСклад:", len(rows))
    print("-----------------------------------\n")

    if not rows:
        print("❌ Нет подключённых аккаунтов")
        return

    # === Каждый поставщик, подключивший МойСклад ===
    for acc in rows:
        token = acc.get("access_token")
        account_id = acc.get("account_id")
        supplier_telegram = acc.get("telegram_user_id")
        default_store_id = acc.get("default_store_id")

        if not token:
            print("❌ Нет токена доступа — пропуск")
            continue

        print(f"\n=================")
        print(f"🏪 Supplier Telegram: {supplier_telegram}")
        print(f"🏦 ACCOUNT ID: {account_id}")
        print(f"🟩 STORE SELECTED: {default_store_id}")
        print("=================\n")

        # ---- Находим supplier_id внутри нашей таблицы suppliers ----
        supplier_row = supabase.table("suppliers") \
            .select("id,name") \
            .eq("telegram_user", supplier_telegram) \
            .execute() \
            .data

        if not supplier_row:
            print("❌ supplier_id не найден — пропуск")
            continue

        supplier_id = supplier_row[0]["id"]
        supplier_name = supplier_row[0]["name"]

        print(f"🔗 supplier_id в products: {supplier_id}")

        # === 1. Удаляем ВСЕ старые товары этого поставщика ===
        print("🧹 Очищаю товары поставщика...")
        supabase.table("products").delete().eq("supplier_id", supplier_id).execute()
        print("✅ Удалено")

        # === 2. Получаем товары через assortment ===

        params = {
            "limit": 1000,
            "offset": 0,
            "expand": "salePrices, stock"
        }

        url_assortment = f"{MS_BASE}/entity/assortment"

        items = []
        print("📥 Загружаю товары из assortment...")

        while True:
            r = ms_get(url_assortment, token, params=params)
            if r.status_code != 200:
                print("❌ Ошибка запроса:", r.text)
                break

            data = r.json()
            rows = data.get("rows", [])
            items.extend(rows)

            if len(rows) < 1000:
                break

            params["offset"] += 1000

        print(f"📦 Получено позиций: {len(items)}\n")

        # === 3. Подготовка финального списка товаров ===
        final_goods = []

        for item in items:
            meta_type = item.get("meta", {}).get("type")
            if meta_type not in ["product", "variant"]:
                continue

            sale_price = None
            stock = None

            # --- Цена ---
            prices = item.get("salePrices", [])
            if prices:
                sale_price = prices[0].get("value", 0) / 100

            raw_stock = item.get("stock")

            # ====== ОПРЕДЕЛЕНИЕ ОСТАТКОВ ======
            if default_store_id == "all":
                stock = item.get("quantity")

            else:
                stock = None

                # Если stock — массив
                if isinstance(raw_stock, list):
                    for s in raw_stock:
                        store_meta = s.get("store", {}).get("meta", {}).get("href", "")
                        if store_meta.endswith(default_store_id):
                            stock = s.get("stock")
                            break

                # Если stock — число
                elif isinstance(raw_stock, (int, float)):
                    stock = raw_stock

            # Игнорируем товары без остатков
            if stock is None or stock <= 0:
                continue

            final_goods.append({
                "name": item.get("name"),
                "price": sale_price,
                "stock": stock
            })

        print(f"📦 Готово к вставке: {len(final_goods)} позиций")

        # === 4. Вставляем в products ===
        for g in final_goods:
            supabase.table("products").insert({
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "product_name": g["name"],
                "brand": None,
                "price_min": g["price"],
                "price_max": g["price"],
                "stock": g["stock"],
                "updated_at": datetime.utcnow().isoformat()
            }).execute()

        print("✅ Синхронизация завершена\n")


if __name__ == "__main__":
    main()
