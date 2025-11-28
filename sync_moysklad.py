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

    acc = rows[0]
    token = acc.get("access_token")
    account_id = acc.get("account_id")

    print(f"🏦 ACCOUNT ID: {account_id}")
    print(f"🔑 ACCESS TOKEN: {token[:8]}... (скрыто)\n")

    if not token:
        print("❌ Нет токена доступа")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # ============================
    #      СПИСОК СКЛАДОВ
    # ============================
    print("🔎 Запрашиваю список складов...\n")

    url_stores = "https://api.moysklad.ru/api/remap/1.2/entity/store"
    r3 = requests.get(url_stores, headers=headers)
    print("HTTP статус (склады):", r3.status_code)

    stores = r3.json().get("rows", [])
    print(f"🏬 Складов найдено: {len(stores)}")
    print("-----------------------------------")

    for st in stores:
        print(f"🔹 {st.get('name')} — id: {st.get('id')} (archived: {st.get('archived')})")

    print("-----------------------------------\n")

    if not stores:
        print("❌ НЕТ СКЛАДОВ — невозможно получить остатки")
        return

    # Берём первый склад (или потом добавим все 3)
    store_id = stores[0].get("id")
    print(f"📦 Используем склад: {stores[0].get('name')} — {store_id}\n")

    # ============================
    #        ASSORTMENT (остатки)
    # ============================
    print("🔎 Запрашиваю остатки через /entity/assortment ...\n")

    url_assortment = (
        f"https://api.moysklad.ru/api/remap/1.2/entity/assortment"
        f"?limit=1000&stockstore={store_id}"
    )

    r = requests.get(url_assortment, headers=headers)
    print("HTTP статус (assortment):", r.status_code)

    if r.status_code != 200:
        print("❌ Ошибка получения assortment:")
        print(r.text)
        return

    items = r.json().get("rows", [])
    print(f"📊 ПОЗИЦИЙ ПОЛУЧЕНО: {len(items)}")
    print("-----------------------------------")

    print("🟦 ПЕРВЫЕ 20 ПОЗИЦИЙ:")
    for it in items[:20]:
        name = it.get("name")
        quantity = it.get("quantity", 0)
        sale_price = 0

        salePrices = it.get("salePrices", [])
        if salePrices:
            sale_price = salePrices[0].get("value", 0) / 100

        print(f"🔹 {name} — цена: {sale_price} ₽ — остаток: {quantity}")

    print("-----------------------------------\n")

    print("✅ Остатки через assortment получены УСПЕШНО!\n")


if __name__ == "__main__":
    main()
