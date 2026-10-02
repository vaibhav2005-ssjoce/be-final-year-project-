from pydantic import BaseModel

class FraudRateOverTime(BaseModel):
    date: str
    fraud_rate: float
    total: int
    flagged: int

class RiskDistribution(BaseModel):
    level: str
    count: int
