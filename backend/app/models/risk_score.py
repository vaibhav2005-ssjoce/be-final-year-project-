import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    rule_flags = Column(JSON, default=list, nullable=False)
    ml_probability = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)  # "Low" | "Medium" | "High"
    computed_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    transaction = relationship("Transaction", back_populates="risk_score")
