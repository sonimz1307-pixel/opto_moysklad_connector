from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import requests
import secrets
import string
from fastapi.responses import HTMLResponse

app = FastAPI()

# =====================================================
#   SUPABASE CONFIG
# =====================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_TABLE = "moysklad_accounts"

SB_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}


# =====================================================
#   MODELS
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
#   HELPERS
# =====================================================
def supabase_upsert(payload: dict):
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    headers = SB_HEADERS.copy()
    headers["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(url, json=[payload], headers=headers)
    print("[SUPABASE UPSERT]", r.status_code, r.text)
    return r


# =====================================================
#   TOKEN GENERATOR (user token)
# =====================================================
def generate_user_token(account_id: str):
    rnd = ''.join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    return f"MS-{account_id}-{rnd}"


# =====================================================
#   ACTIVATE (INSTALL)
# =====================================================
@app.put("/api/moysklad/vendor/1.0/apps/{appId}/{accountId}")
async def activate_solution(appId: str, accountId: str, body: ActivationRequest):
    print("\n=== ACTIVATE APP ===")
    print("accountId:", accountId)

    access_token = None
    if body.access and len(body.access) > 0:
        access_token = body.access[0].access_token

    user_token = generate_user_token(accountId)

    payload = {
        "app_id": appId,
        "account_id": accountId,
        "app_uid": body.appUid,
        "account_name": body.accountName,
        "access_token": access_token,
        "subscription_json": body.subscription,
        "token": user_token,
    }

    supabase_upsert(payload)
    return {"status": "Activated", "token": user_token}


# =====================================================
#   DEACTIVATE (UNINSTALL)
# =====================================================
@app.delete("/api/moysklad/vendor/1.0/apps/{appId}/{accountId}")
def deactivate_solution(appId: str, accountId: str):
    print("\n=== DEACTIVATE APP ===")
    print("appId:", appId, "accountId:", accountId)
    return {"status": "Deactivated"}


# =====================================================
#   RESOLVE ACCOUNT ID THROUGH CONTEXT (AppStore V2)
# =====================================================
def resolve_account_id(context_key: str, app_uid: str):
    print("\n=== RESOLVING CONTEXT ===")
    print("contextKey:", context_key, "appUid:", app_uid)

    # 1. Find proper access_token in Supabase by app_uid
    url = (
        f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
        f"?app_uid=eq.{app_uid}&select=access_token"
    )
    r = requests.get(url, headers=SB_HEADERS)
    rows = r.json()
    print("TOKEN LOOKUP RESULT:", rows)

    if not rows or "access_token" not in rows[0]:
        print("ERROR: access_token not found")
        return None

    access_token = rows[0]["access_token"]
    if not access_token:
        print("ERROR: empty access token")
        return None

    # 2. Query MySklad app context
    ctx_url = f"https://apps-api.moysklad.ru/api/appstore/apps/context/{context_key}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    resp = requests.get(ctx_url, headers=headers)
    print("CONTEXT RAW:", resp.text)

    if resp.status_code != 200:
        print("CONTEXT ERROR:", resp.text)
        return None

    j = resp.json()
    print("CONTEXT JSON:", j)
    return j.get("accountId")


# =====================================================
#   HTML TEMPLATE
# =====================================================
SETTINGS_PAGE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>OptoVizor — подключение</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { margin:0; background:#f5f7fb; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:#111827; }
        .wrap { max-width:760px; margin:0 auto; padding:26px; }
        h1 { font-size:28px; margin-bottom:12px; }
        .card { background:#fff; padding:22px; margin-top:18px; border-radius:12px; border:1px solid #e5e7eb; box-shadow:0 6px 18px rgba(0,0,0,0.06);}
        .token-display { background:#f1f5f9; padding:16px; border-radius:8px; font-size:26px; font-weight:700; text-align:center; letter-spacing:1px; margin-top:12px; }
        .copy-btn { width:100%; margin-top:12px; padding:12px; background:#2563eb; color:#fff; border-radius:8px; font-size:16px; border:none; cursor:pointer; }
        .footer { margin-top:30px; font-size:13px; color:#6b7280; text-align:center; }
    </style>
</head>
<body>
<div class="wrap">
    <h1>OptoVizor — подключение</h1>

    <!--TOKEN_BLOCK-->

    <div class="card">
        <h2>Инструкция</h2>
        <a class="copy-btn" href="https://sonimz1307-pixel.github.io/optovizor-moysklad-instruction/company.html" target="_blank">📘 Открыть инструкцию</a>
    </div>

    <div class="footer">OptoVizor · shader0630@gmail.com</div>
</div>

<script>
function copyToken() {
    const token = document.getElementById("token_value").innerText;
    navigator.clipboard.writeText(token).then(() => { alert("Токен скопирован!"); });
}
</script>

</body>
</html>
"""


# =====================================================
#   SETTINGS (Перейти в решение)
# =====================================================
@app.get("/moysklad/settings", response_class=HTMLResponse)
async def ms_settings(request: Request):

    print("\n=== OPEN SETTINGS ===")
    print("HEADERS:", dict(request.headers))
    print("QUERY:", dict(request.query_params))

    context_key = request.query_params.get("contextKey")
    app_uid = request.query_params.get("appUid")

    if not context_key or not app_uid:
        return HTMLResponse("Ошибка: МойСклад не передал contextKey/appUid", status_code=400)

    accountId = resolve_account_id(context_key, app_uid)
    print("RESOLVED ACCOUNT ID:", accountId)

    token = None
    if accountId:
        url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?account_id=eq.{accountId}&select=token"
        r = requests.get(url, headers=SB_HEADERS)
        js = r.json()
        print("TOKEN ROW:", js)

        if js and isinstance(js, list) and "token" in js[0]:
            token = js[0]["token"]

    token_html = f"""
    <div class="card">
        <h2>Ваш токен для привязки</h2>
        <div id="token_value" class="token-display">{token or "Токен не найден"}</div>
        <button class="copy-btn" onclick="copyToken()">📋 Скопировать токен</button>
        <p style="color:#6b7280; font-size:14px; margin-top:10px;">
            Введите этот токен в Telegram-бот OptoVizor.
        </p>
    </div>
    """

    html = SETTINGS_PAGE_HTML.replace("<!--TOKEN_BLOCK-->", token_html)
    return HTMLResponse(html)


# =====================================================
#   ROOT
# =====================================================
@app.get("/")
def root():
    return {"message": "OptoVizor MoySklad Connector running"}
