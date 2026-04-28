from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import redis
import os

app = FastAPI(title="Idempotency Gateway")

redis_host = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)


class PaymentRequest(BaseModel):
    amount: int
    currency: str


@app.get("/")
def home():
    return {"message": "API Running"}


@app.post("/process-payment")
def process_payment(
    request: PaymentRequest,
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Missing Idempotency-Key header"
        )

    return {
        "message": f"Charged {request.amount} {request.currency}",
        "key": idempotency_key
    }