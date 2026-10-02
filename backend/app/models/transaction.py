import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    type = Column(String(50), default="transfer", nullable=False)
    channel = Column(String(50), nullable=False)  # "UPI" | "QR" | "CARD" | "NETBANKING"
    payee_id = Column(String(255), nullable=False)
    category = Column(String(50), default="other", nullable=False)  # food, travel, bills, shopping, transfer, other
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    risk_level = Column(String(20), default="Low", nullable=False)  # "Low" | "Medium" | "High"
    ml_probability = Column(Float, default=0.0, nullable=False)
    rule_flags = Column(JSON, default=list, nullable=False)  # list of strings
    status = Column(String(20), default="pending", nullable=False)  # "pending" | "approved" | "declined"
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="transactions")
    risk_score = relationship("RiskScore", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
    alert = relationship("Alert", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
