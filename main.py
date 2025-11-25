from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# ----- Модели, которые МойСклад присылает -----

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


# ----- Endpoints, которые требует МойСклад -----


@app.put("/api/moysklad/vendor/1.0/apps/{appId}/{accountId}")
async def activate_solution(appId: str, accountId: str, body: ActivationRequest):

    print("\n=== ACTIVATE APP ===")
    print("appId:", appId)
    print("accountId:", accountId)
    print("body:", body.dict())

    # тут позже будем сохранять токен в Supabase
    # access_token = body.access[0].access_token if body.access else None

    return {"status": "Activated"}


@app.delete("/api/moysklad/vendor/1.0/apps/{appId}/{accountId}")
async def deactivate_solution(appId: str, accountId: str, request: Request):

    print("\n=== DEACTIVATE APP ===")
    body = await request.body()
    print("body:", body)

    return {"status": "Deactivated"}


# Проверка
@app.get("/")
def root():
    return {"message": "OptoVizor x MoySklad server is running"}
