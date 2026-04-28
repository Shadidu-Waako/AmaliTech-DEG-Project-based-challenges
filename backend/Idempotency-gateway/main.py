from fastapi import FastAPI

app = FastAPI(title="Idempotency Gateway")


@app.get("/")
def home():
    return {"message": "API Running"}