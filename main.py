from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import os
import requests

app = FastAPI()

# ==============================
#   SUPABASE CONFIG
# ==============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

TABLE_MS = "moysklad_accounts"
TABLE_USERS = "suppliers"  # таблица, где хранятся токены пользователей (бот выдаёт токены)


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
#   SUPABASE HELPERS
# ==============================
def sb_upsert(table: str, payload: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = HEADERS.copy()
    headers["Prefer"] = "resolution=merge-duplicates"

    r = requests.post(url, json=[payload], headers=headers)
    print(f"[SUPABASE UPSERT {table}]:", r.status_code, r.text)
    return r


def sb_patch(table: str, match_field: str, match_value: str, update: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_field}=eq.{match_value}"
    headers = HEADERS.copy()
    headers["Prefer"] = "resolution=merge-duplicates"

    r = requests.patch(url, json=update, headers=headers)
    print(f"[SUPABASE PATCH {table}]:", r.status_code, r.text)
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

    sb_upsert(TABLE_MS, payload)
    return {"status": "Activated"}


# ==============================
#   DEACTIVATE (МойСклад)
# ==============================
@app.delete("/api/moysklad/vendor/1.0/apps/{appId}/{accountId}")
async def deactivate_solution(appId: str, accountId: str, request: Request):

    print("\n=== DEACTIVATE APP ===")
    body_raw = await request.body()
    print("body:", body_raw)

    # связь НЕ удаляем — пусть пользователь сам отвяжет в МойСклад
    return {"status": "Deactivated"}


# ==============================
#   API: ПОЛЬЗОВАТЕЛЬ ВВОДИТ ТОКЕН
# ==============================
@app.post("/api/moysklad/vendor/submit_token")
async def submit_token(data: dict):
    print("\n=== SUBMIT TOKEN ===")
    print("Incoming:", data)

    token = data.get("token")
    account_id = data.get("account_id")

    if not token or not account_id:
        return JSONResponse({"error": "missing_fields"}, status_code=400)

    # 1. Ищем пользователя по токену
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_USERS}?token=eq.{token}"
    r = requests.get(url, headers=HEADERS)
    users = r.json()

    if not users:
        return JSONResponse({"error": "token_not_found"}, status_code=404)

    user = users[0]
    telegram_user_id = user.get("telegram_user")

    if not telegram_user_id:
        return JSONResponse({"error": "invalid_user_data"}, status_code=400)

    # 2. Привязываем пользователя к MoySklad.accountId
    update = {
        "telegram_user_id": telegram_user_id,
        "token": token,
    }

    sb_patch(TABLE_MS, "account_id", account_id, update)

    return {"status": "linked", "telegram_user_id": telegram_user_id}


# ==============================
#   ROOT
# ==============================
@app.get("/")
def root():
    return {"message": "OptoVizor x MoySklad backend is running"}


# ==============================
#   SETTINGS PAGE (HTML + FORM TOKEN)
# ==============================

SETTINGS_PAGE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>OptoVizor — подключение к боту</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { margin: 0; background: #f5f7fb; font-family: Arial, sans-serif; color: #111; }
        .wrap { max-width: 760px; margin: 0 auto; padding: 26px; }
        .card { background: #fff; padding: 20px; border-radius: 12px;
                border: 1px solid #e5e7eb; margin-top: 26px; box-shadow: 0 8px 24px rgba(0,0,0,0.06); }
        h1 { font-size: 28px; margin-bottom: 12px; }
        input { width: 100%; padding: 12px; margin-top: 10px;
                border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; }
        button { width: 100%; padding: 12px; margin-top: 14px;
                 background: #2563eb; color: #fff; font-size: 16px; border: none;
                 border-radius: 8px; cursor: pointer; }
        button:active { opacity: 0.9; }
        .footer { text-align: center; margin-top: 30px; color: #6b7280; font-size: 13px; }
        #status { margin-top: 15px; font-size: 15px; }
    </style>
</head>
<body>
<div class="wrap">
    <h1>OptoVizor — привязка к Telegram</h1>

    <div class="card">
        <p>Введите токен, который вы получили в Telegram-боте OptoVizор.</p>

        <input id="token_input" placeholder="Например: OV-2KD9FQ">

        <button onclick="submitToken()">Привязать аккаунт</button>

        <div id="status"></div>
    </div>

    <div class="footer">OptoVizor · Поддержка: shader0630@gmail.com</div>
</div>

<script>
function submitToken() {
    const token = document.getElementById('token_input').value.trim();
    const params = new URLSearchParams(window.location.search);
    const accountId = params.get("accountId");

    if (!token) {
        document.getElementById("status").innerHTML = "<b style='color:red;'>Введите токен</b>";
        return;
    }

    if (!accountId) {
        document.getElementById("status").innerHTML = "<b style='color:red;'>Ошибка: accountId не передан МойСклад</b>";
        return;
    }

    fetch("/api/moysklad/vendor/submit_token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: token, account_id: accountId })
    })
    .then(r => r.json())
    .then(r => {
        if (r.error) {
            document.getElementById("status").innerHTML =
                "<b style='color:red;'>Ошибка: " + r.error + "</b>";
        } else {
            document.getElementById("status").innerHTML =
                "<b style='color:green;'>Аккаунт успешно привязан!</b>";
        }
    });
}
</script>

</body>
</html>
"""


@app.get("/moysklad/settings", response_class=HTMLResponse)
async def ms_settings():
    return SETTINGS_PAGE_HTML
