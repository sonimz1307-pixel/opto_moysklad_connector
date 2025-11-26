from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import requests

app = FastAPI()

# ==============================
#   SUPABASE CONFIG
# ==============================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "moysklad_accounts")


# ==============================
#   MODELS (МойСклад формат)
# ==============================

class AccessItem(BaseModel):
    resource: str
    scope: list[str] | None = None
    access_token: str | None = None

class ActivationRequest(BaseModel):
    appUid: str
    accountName: str
    cause: str
    access: list[AccessItem] | None = None
    subscription: dict | None = None
    additional: dict | None = None


# ==============================
#   SAVE TO SUPABASE
# ==============================

def save_to_supabase(appId: str, accountId: str, body: ActivationRequest):
    """
    Сохраняет/обновляет запись МойСклад-аккаунта в Supabase.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("[ERROR] Supabase ENV variables missing")
        return

    access_token = None
    scope = None

    if body.access and len(body.access) > 0:
        access_token = body.access[0].access_token
        scope = body.access[0].scope

    payload = {
        "app_id": appId,
        "account_id": accountId,
        "app_uid": body.appUid,
        "account_name": body.accountName,
        "access_token": access_token,
        "scope": str(scope) if scope else None,
        "subscription_json": body.subscription,
    }

    print("[INFO] Saving to Supabase:", payload)

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    response = requests.post(url, json=[payload], headers=headers)

    print("[SUPABASE RESPONSE]:", response.status_code, response.text)



# ==============================
#   NEW ENDPOINT: LINK TELEGRAM
# ==============================
@app.post("/api/moysklad/vendor/link_telegram")
async def link_telegram(body: dict):
    """
    Бот вызывает этот endpoint, чтобы связать:
    account_id (UUID МойСклад) <-> telegram_user_id
    """
    print("\n=== LINK TELEGRAM ===")
    print("body:", body)

    telegram_user_id = body.get("telegram_user_id")
    account_id = body.get("account_id")

    if not telegram_user_id or not account_id:
        return {"error": "missing fields"}

    # обновляем запись в таблице moysklad_accounts
    url = f"{SUPABASE_URL}/rest/v1/moysklad_accounts?account_id=eq.{account_id}"

    payload = {
        "telegram_user_id": str(telegram_user_id)
    }

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    r = requests.patch(url, json=payload, headers=headers)

    print("[SUPABASE PATCH RESPONSE]:", r.status_code, r.text)

    return {"status": "linked"}



# ==============================
#   МойСклад: ACTIVATE
# ==============================
@app.put("/api/moysklad/vendor/1.0/apps/{appId}/{accountId}")
async def activate_solution(appId: str, accountId: str, body: ActivationRequest):

    print("\n=== ACTIVATE APP ===")
    print("appId:", appId)
    print("accountId:", accountId)
    print("body:", body.dict())

    save_to_supabase(appId, accountId, body)

    return {"status": "Activated"}



# ==============================
#   МойСклад: DEACTIVATE
# ==============================
@app.delete("/api/moysklad/vendor/1.0/apps/{appId}/{accountId}")
async def deactivate_solution(appId: str, accountId: str, request: Request):

    print("\n=== DEACTIVATE APP ===")
    body_raw = await request.body()
    print("body:", body_raw)

    return {"status": "Deactivated"}



# ==============================
#   ROOT
# ==============================
@app.get("/")
def root():
    return {"message": "OptoVizor x MoySklad backend is running"}
