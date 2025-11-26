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
SUPABASE_TABLE = "moysklad_accounts"

HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}

# ==============================
#   MODELS
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
#   HELPERS
# ==============================
def supabase_upsert(payload: dict):
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    headers = HEADERS.copy()
    headers["Prefer"] = "resolution=merge-duplicates"

    r = requests.post(url, json=[payload], headers=headers)
    print("[SUPABASE UPSERT]:", r.status_code, r.text)
    return r

def supabase_patch(account_id: str, update: dict):
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?account_id=eq.{account_id}"
    headers = HEADERS.copy()
    headers["Prefer"] = "resolution=merge-duplicates"

    r = requests.patch(url, json=update, headers=headers)
    print("[SUPABASE PATCH]:", r.status_code, r.text)
    return r

# ==============================
#   ACTIVATE APP (МойСклад)
# ==============================
@app.put("/api/moysklad/vendor/1.0/apps/{appId}/{accountId}")
async def activate_solution(appId: str, accountId: str, body: ActivationRequest):

    print("\n=== ACTIVATE APP ===")
    print("appId:", appId)
    print("accountId:", accountId)
    print("body:", body.dict())

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

    supabase_upsert(payload)
    return {"status": "Activated"}

# ==============================
#   LINK TELEGRAM (бот → backend)
# ==============================
@app.post("/api/moysklad/vendor/link_telegram")
async def link_telegram(body: dict):

    print("\n=== LINK TELEGRAM ===")
    print("body:", body)

    telegram_user_id = body.get("telegram_user_id")
    account_id = body.get("account_id")

    if not telegram_user_id or not account_id:
        return {"error": "missing fields"}

    update = {
        "telegram_user_id": str(telegram_user_id)
    }

    supabase_patch(account_id, update)

    return {"status": "linked"}

# ==============================
#   DEACTIVATE (МойСклад)
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
