from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "OptoVizor x MoySklad server is running"}
