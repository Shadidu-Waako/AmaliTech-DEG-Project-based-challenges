from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Idempotency Gateway")


class PaymentRequest(BaseModel):
    amount: int
    currency: str


@app.get("/")
def home():
    return {"message": "API Running"}


@app.post("/process-payment")
def process_payment(request: PaymentRequest):
    return {
        "message": f"Charged {request.amount} {request.currency}"
    }