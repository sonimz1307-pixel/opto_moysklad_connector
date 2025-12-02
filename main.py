from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import requests
import secrets
import string

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
#   TOKEN GENERATOR
# ==============================
def generate_token(account_id: str):
    alphabet = string.ascii_uppercase + string.digits
    rnd = ''.join(secrets.choice(alphabet) for _ in range(6))
    return f"MS-{account_id}-{rnd}"


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

    # 👉 Генерация токена для этого аккаунта
    token = generate_token(accountId)
    print("Generated token:", token)

    payload = {
        "app_id": appId,
        "account_id": accountId,
        "app_uid": body.appUid,
        "account_name": body.accountName,
        "access_token": access_token,
        "scope": str(scope) if scope else None,
        "subscription_json": body.subscription,
        "token": token,                 # ← токен сохраняется в Supabase
    }

    supabase_upsert(payload)
    return {"status": "Activated", "token": token}


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

    print("[SUPABASE PATCH]:", r.status_code, r.text)

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



# ==============================
#   SETTINGS PAGE
# ==============================
from fastapi.responses import HTMLResponse

SETTINGS_PAGE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>OptoVizor Connector — настройки</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            margin: 0;
            background: #f5f7fb;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #111827;
        }
        .wrap {
            max-width: 760px;
            margin: 0 auto;
            padding: 26px;
        }
        h1 {
            font-size: 26px;
            margin-bottom: 6px;
        }
        p {
            font-size: 15px;
            line-height: 1.6;
        }
        .card {
            background: #fff;
            padding: 20px;
            margin-top: 16px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        }
        a.btn {
            display: inline-block;
            margin-top: 16px;
            padding: 10px 18px;
            background: #2563eb;
            color: white;
            border-radius: 8px;
            text-decoration: none;
            font-size: 14px;
        }
        a.btn-secondary {
            background: #e5e7eb;
            color: #111827;
        }
        .footer {
            margin-top: 26px;
            font-size: 13px;
            color: #6b7280;
        }
    </style>
</head>
<body>
<div class="wrap">
    <h1>OptoVizor Connector</h1>
    <p><b>Интеграция OptoVizor</b> успешно установлена.  
       Приложение подключает ваш МойСклад к платформе OptoVizor и работает только в режиме чтения данных каталога товаров.</p>

    <div class="card">
        <h2>Что делать дальше?</h2>
        <p>1. Перейдите в раздел <b>«OptoVizor»</b> в боковом меню МойСклад.<br>
           2. Откройте каталог поставщиков и начните поиск товаров.<br>
           3. Используйте фильтры и интеллектуальный поиск для быстрого поиска нужных позиций.</p>

        <a class="btn" href="https://sonimz1307-pixel.github.io/optovizor-moysklad-instruction/company.html" target="_blank">📘 Инструкция</a>
        <a class="btn btn-secondary" href="mailto:shader0630@gmail.com">Написать разработчику</a>
    </div>

    <div class="footer">OptoVizor · Поддержка: shader0630@gmail.com</div>
</div>
</body>
</html>
"""

@app.get("/moysklad/settings", response_class=HTMLResponse)
async def ms_settings():
    return SETTINGS_PAGE_HTML
