from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel
import redis
import os
import json
import time

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
    response: Response,
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Missing Idempotency-Key header"
        )

    key = f"idem:{idempotency_key}"

    # Check if request already exists
    existing = r.get(key)

    if existing:
        response.headers["X-Cache-Hit"] = "true"
        return json.loads(existing)

    # Simulate payment processing
    time.sleep(2)

    result = {
        "message": f"Charged {request.amount} {request.currency}"
    }

    # Store result in Redis
    r.setex(key, 86400, json.dumps(result))

    response.status_code = 201
    return result