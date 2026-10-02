from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
from backend.app.schemas.transaction import TransactionResponse

class AlertVerify(BaseModel):
    decision: Literal["approve", "decline"]

class AlertResponse(BaseModel):
    id: int
    transaction_id: int
    user_id: int
    status: Literal["pending", "approved", "declined"]
    created_at: datetime
    transaction: Optional[TransactionResponse] = None

    class Config:
        from_attributes = True
