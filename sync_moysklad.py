import os
import requests
from supabase import create_client, Client
from collections import defaultdict

# === Загружаем переменные среды ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


def fetch_assortment(headers, store_id):
    """Возвращает rows для конкретного склада"""
    url = (
        "https://api.moysklad.ru/api/remap/1.2/entity/assortment"
        f"?limit=1000&stockstore={store_id}"
    )
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print("❌ Ошибка получения остатка:", r.status_code, r.text)
        return []
    return r.json().get("rows", [])


def merge_all_stores(headers, stores):
    """Суммирует остатки со всех складов"""
    merged = {}
    for s in stores:
        sid = s["id"]
        rows = fetch_assortment(headers, sid)

        for item in rows:
            uid = item.get("id")
            if not uid:
                continue

            name = item.get("name")
            quantity = item.get("quantity", 0)
            salePrices = item.get("salePrices", [])
            price = salePrices[0].get("value", 0) / 100 if salePrices else 0

            if uid not in merged:
                merged[uid] = {
                    "name": name,
                    "price": price,
                    "quantity": 0,
                }

            merged[uid]["quantity"] += quantity

    return list(merged.values())


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

    account = rows[0]

    token = account.get("access_token")
    default_store_id = account.get("default_store_id")

    print(f"🏦 ACCOUNT ID: {account.get('account_id')}")
    print(f"🔑 ACCESS TOKEN: {token[:8]}... (скрыто)")
    print(f"🏬 STORE SELECTED: {default_store_id}\n")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # ——— Получаем список складов ———
    print("🔎 Получаю список складов...\n")
    r_st = requests.get(
        "https://api.moysklad.ru/api/remap/1.2/entity/store", headers=headers
    )
    stores = r_st.json().get("rows", [])
    print("📦 Складов найдено:", len(stores))

    for s in stores:
        print(f"  • {s['name']} — {s['id']}")

    print("-----------------------------------\n")

    # ——— ALL STORES режим ———
    if default_store_id == "all":
        print("🔄 Режим: ВСЕ СКЛАДЫ\n")

        items = merge_all_stores(headers, stores)

        print("📊 Суммированные остатки:", len(items))
        print("-----------------------------------")
        print("🟦 Первые 20 позиций:")
        for it in items[:20]:
            print(
                f"🔹 {it['name']} — цена: {it['price']} ₽ — остаток: {it['quantity']}"
            )

        print("-----------------------------------")
        print("✅ Успешно (ALL STORES)")
        return

    # ——— SINGLE STORE режим ———
    print("🏬 Режим: одиночный склад:", default_store_id, "\n")

    rows = fetch_assortment(headers, default_store_id)

    print("📊 Получено товаров:", len(rows))
    print("-----------------------------------")
    print("🟦 Первые 20 позиций:")

    for it in rows[:20]:
        name = it.get("name")
        qty = it.get("quantity", 0)
        salePrices = it.get("salePrices", [])
        price = salePrices[0].get("value", 0) / 100 if salePrices else 0
        print(f"🔹 {name} — цена: {price} ₽ — остаток: {qty}")

    print("-----------------------------------")
    print("✅ Успешно (1 склад)")


if __name__ == "__main__":
    main()
