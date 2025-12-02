from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import requests
from fastapi.responses import HTMLResponse

app = FastAPI()

# =====================================================
#   SUPABASE CONFIG
# =====================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_TABLE = "moysklad_accounts"

HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}


# =====================================================
#   MODELS (твои)
# =====================================================
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


# =====================================================
#   ACTIVATE (INSTALL)
# =====================================================
@app.put("/api/moysklad/vendor/1.0/apps/{appId}/{accountId}")
async def activate_solution(appId: str, accountId: str, body: ActivationRequest):

    print("\n=== ACTIVATE APP ===")
    print("accountId:", accountId)
    print("body:", body.dict())

    access_token = None

    if body.access and len(body.access) > 0:
        access_token = body.access[0].access_token

    payload = {
        "app_id": appId,
        "account_id": accountId,
        "app_uid": body.appUid,
        "account_name": body.accountName,
        "access_token": access_token,
        "subscription_json": body.subscription,
    }

    supabase_upsert(payload)
    return {"status": "Activated"}


# =====================================================
#   SUPABASE UPSERT (твоя функция)
# =====================================================
def supabase_upsert(payload: dict):
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    headers = HEADERS.copy()
    headers["Prefer"] = "resolution=merge-duplicates"

    r = requests.post(url, json=[payload], headers=headers)
    print("[SUPABASE UPSERT]:", r.status_code, r.text)
    return r


# =====================================================
#   DEACTIVATE (UNINSTALL) — ДОБАВЛЕНО
# =====================================================
@app.delete("/api/moysklad/vendor/1.0/apps/{appId}/{accountId}")
def deactivate_solution(appId: str, accountId: str):
    print("\n=== DEACTIVATE APP ===")
    print("appId:", appId, "accountId:", accountId)
    return {"status": "Deactivated"}


# =====================================================
#   RESOLVE ACCOUNT THROUGH contextKey — ДОБАВЛЕНО
#   (полностью безопасно и не мешает твоей логике)
# =====================================================
def resolve_account_id(context_key: str, app_uid: str):

    print("\n=== RESOLVING CONTEXT ===")
    print("contextKey:", context_key, "| appUid:", app_uid)

    # 1. Находим правильный access_token (по appUid)
    url = (
        f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
        f"?app_uid=eq.{app_uid}&select=access_token"
    )

    r = requests.get(url, headers=HEADERS)
    rows = r.json()

    print("TOKEN LOOKUP RESULT:", rows)

    if not rows or not rows[0].get("access_token"):
        print("ERROR: no access_token for appUid")
        return None

    access_token = rows[0]["access_token"]

    # 2. Получаем контекст у МойСклад
    ctx_url = f"https://apps-api.moysklad.ru/api/appstore/apps/context/{context_key}"

    resp = requests.get(ctx_url, headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    })

    print("CONTEXT RAW:", resp.text)

    if resp.status_code != 200:
        print("CONTEXT ERROR:", resp.text)
        return None

    return resp.json().get("accountId")


# =====================================================
#   SETTINGS PAGE HTML (твоя страница — НЕ менял)
# =====================================================
SETTINGS_PAGE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>OptoVizor — Настройки</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
</head>
<body>
  <h1>OptoVizor — подключение</h1>
  <p>Здесь будет токен подключения.</p>
</body>
</html>
"""


# =====================================================
#   SETTINGS ENDPOINT (обновлено БЕЗ опасных изменений)
# =====================================================
@app.get("/moysklad/settings", response_class=HTMLResponse)
async def ms_settings(request: Request):

    print("\n=== OPEN SETTINGS ===")
    print("QUERY:", dict(request.query_params))

    context_key = request.query_params.get("contextKey")
    app_uid = request.query_params.get("appUid")

    accountId = None

    if context_key and app_uid:
        accountId = resolve_account_id(context_key, app_uid)

    print("RESOLVED ACCOUNT:", accountId)

    # Пока ничего не меняем в выводе HTML
    # → просто возвращаем твою страницу
    return HTMLResponse(SETTINGS_PAGE_HTML)


# =====================================================
#   ROOT
# =====================================================
@app.get("/")
def root():
    return {"message": "OptoVizor MoySklad Connector running"}
