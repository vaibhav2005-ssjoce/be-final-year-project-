import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.app.core.config import settings
from backend.app.core.database import get_db, engine, Base
from backend.app.auth.router import router as auth_router
from backend.app.schemas.transaction import TransactionCreate, TransactionResponse
from backend.app.services.fraud_pipeline import process_transaction
from backend.app.models.transaction import Transaction
from backend.app.models.alert import Alert

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Real-Time Fraud & Scams Operations API",
    version="1.0.0"
)

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Authentication Router
app.include_router(auth_router)

# Endpoint: Health Check
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}

# Endpoint: Screen a Transaction
@app.post("/api/transactions/screen", response_model=TransactionResponse)
def screen_transaction(txn_in: TransactionCreate, user_id: int = 1, db: Session = Depends(get_db)):
    """
    Screens an incoming payment through the complete 5-rule deterministic check
    and ML model probability score pipeline.
    """
    db_txn = process_transaction(txn_in, user_id=user_id, db=db)
    return db_txn

# Endpoint: Fetch Recent Transactions / Cases
@app.get("/api/transactions", response_model=List[TransactionResponse])
def get_transactions(limit: int = 50, db: Session = Depends(get_db)):
    txns = db.query(Transaction).order_by(Transaction.timestamp.desc()).limit(limit).all()
    return txns

# Endpoint: Analyze Message for Scam/Phishing (Scam Desk)
@app.post("/api/scam-desk/analyze")
def analyze_scam_message(payload: Dict[str, str]):
    message = payload.get("message", "").lower().strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message text is required")
    
    keywords = ["otp", "pin", "cvv", "digital arrest", "cbi", "police", "urgent", "immediately", "blocked", "kyc", "click", "collect request", "transfer", "lottery"]
    matched = [k for k in keywords if k in message]
    
    if len(matched) >= 3:
        risk = "High"
        title = "Likely Phishing / Scam"
        explanation = f"High-risk parameters detected ({', '.join(matched)}). Pressures customer for urgent action or sensitive credentials."
    elif len(matched) >= 1:
        risk = "Medium"
        title = "Suspicious - Caution Advised"
        explanation = f"Suspicious patterns found ({', '.join(matched)}). Customer should verify strictly inside official app."
    else:
        risk = "Low"
        title = "Likely Safe"
        explanation = "No common phishing or fraudulent pressure keywords identified."
        
    return {
        "risk_level": risk,
        "title": title,
        "explanation": explanation,
        "matched_keywords": matched
    }

# Serve Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "FraudShield AI API is operational. HTML web frontend file index.html is ready in backend/app/static."}

@app.get("/{filename}")
def read_static_file(filename: str):
    file_path = os.path.join(static_dir, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

