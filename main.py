from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel
import redis
import os
import json
import time
import hashlib

app = FastAPI(title="Idempotency Gateway")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
# Uncomment the following lines for local testing
# redis_host = os.getenv("REDIS_HOST", "redis")
# r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

TTL_SECONDS = 86400

metrics = {
    "processed": 0,
    "cache_hits": 0,
    "conflicts": 0
}


class PaymentRequest(BaseModel):
    amount: int
    currency: str


def request_hash(payload: dict):
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


@app.get("/")
def home():
    return {"message": "API Running"}


@app.get("/metrics")
def get_metrics():
    return metrics


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

        if data["hash"] != body_hash:
            metrics["conflicts"] += 1
            raise HTTPException(
                status_code=422,
                detail="Idempotency key already used for a different request body."
            )

        if data["status"] == "processing":
            while True:
                current = json.loads(r.get(key))
                if current["status"] == "completed":
                    metrics["cache_hits"] += 1
                    response.headers["X-Cache-Hit"] = "true"
                    return current["response"]
                time.sleep(0.1)

        metrics["cache_hits"] += 1
        response.headers["X-Cache-Hit"] = "true"
        return data["response"]

    created = r.setnx(
        key,
        json.dumps({
            "status": "processing",
            "hash": body_hash
        })
    )

    if not created:
        return process_payment(request, response, idempotency_key)

    r.expire(key, TTL_SECONDS)

    time.sleep(2)

    result = {
        "message": f"Charged {request.amount} {request.currency}"
    }

    final_data = {
        "status": "completed",
        "hash": body_hash,
        "response": result
    }

    r.set(key, json.dumps(final_data), ex=TTL_SECONDS)

    metrics["processed"] += 1

    response.status_code = 201
    return result