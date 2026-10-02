from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any
from datetime import datetime

class TransactionCreate(BaseModel):
    amount: float
    type: str = "transfer"
    channel: Literal["UPI", "QR", "CARD", "NETBANKING"]
    payee_id: str
    category: str = "other"  # food, travel, bills, shopping, transfer, other
    timestamp: Optional[datetime] = None

class TransactionResponse(BaseModel):
    id: int
    amount: float
    type: str
    channel: str
    payee_id: str
    category: str
    timestamp: datetime
    risk_level: Literal["Low", "Medium", "High"]
    ml_probability: float
    rule_flags: List[str]
    status: Literal["pending", "approved", "declined"]

    class Config:
        from_attributes = True

class SHAPFeatureContribution(BaseModel):
    feature: str
    value: Any
    contribution: float
