from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel
import redis
import os
import json
import time
import hashlib

app = FastAPI(title="Idempotency Gateway")

redis_host = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)


class PaymentRequest(BaseModel):
    amount: int
    currency: str


def request_hash(payload: dict):
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


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

    payload = request.dict()
    body_hash = request_hash(payload)

    existing = r.get(key)

    if existing:
        data = json.loads(existing)

        # Check if same body
        if data["hash"] != body_hash:
            raise HTTPException(
                status_code=422,
                detail="Idempotency key already used for a different request body."
            )

        response.headers["X-Cache-Hit"] = "true"
        return data["response"]

    # Simulate processing
    time.sleep(2)

    result = {
        "message": f"Charged {request.amount} {request.currency}"
    }

    save_data = {
        "hash": body_hash,
        "response": result
    }

    r.setex(key, 86400, json.dumps(save_data))

    response.status_code = 201
    return result