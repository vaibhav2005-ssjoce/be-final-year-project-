import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.transaction import Transaction
from backend.app.models.risk_score import RiskScore
from backend.app.models.alert import Alert
from backend.app.schemas.transaction import TransactionCreate
from backend.app.services.rule_engine import check as check_rules
from backend.app.services.risk_scoring import compute_risk_score
from backend.app.services.ml_loader import model_manager
from backend.app.core.redis import publish_alert_sync

def process_transaction(txn_in: TransactionCreate, user_id: int, db: Session) -> Transaction:
    """
    Executes end-to-end fraud detection pipeline:
    1. Fetches prior transaction history for user.
    2. Runs rule engine (5 UPI fraud rules).
    3. Extracts features and computes ML fraud probability.
    4. Computes combined risk score ("Low", "Medium", "High").
    5. Saves Transaction and RiskScore records to database.
    6. If risk_level == "High", creates Alert record and publishes to Redis "alerts" pub/sub channel.
    7. Returns complete saved Transaction object.
    """
    # 1. Fetch user's prior history
    prior_txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
        .all()
    )

    txn_timestamp = txn_in.timestamp if txn_in.timestamp is not None else datetime.datetime.utcnow()

    # Transient transaction dict for feature building and rule check
    temp_txn = {
        "id": None,
        "amount": txn_in.amount,
        "type": txn_in.type,
        "channel": txn_in.channel,
        "payee_id": txn_in.payee_id,
        "category": txn_in.category or "other",
        "timestamp": txn_timestamp
    }

    # Convert prior ORM history to list of dicts for rules and ML features
    history_dicts = [
        {
            "id": t.id,
            "amount": t.amount,
            "type": t.type,
            "channel": t.channel,
            "payee_id": t.payee_id,
            "category": t.category,
            "timestamp": t.timestamp
        }
        for t in prior_txns
    ]

    # 2. Rule engine check
    rule_flags = check_rules(temp_txn, history_dicts)

    # 3. ML prediction
    try:
        ml_prob = model_manager.predict_probability(temp_txn, history_dicts)
    except Exception as e:
        print(f"Warning: ML inference failed ({e}), using default probability 0.1")
        ml_prob = 0.1

    # 4. Risk scoring
    risk_level = compute_risk_score(rule_flags, ml_prob)

    # 5. Persist Transaction
    db_txn = Transaction(
        user_id=user_id,
        amount=txn_in.amount,
        type=txn_in.type,
        channel=txn_in.channel,
        payee_id=txn_in.payee_id,
        category=txn_in.category or "other",
        timestamp=txn_timestamp,
        risk_level=risk_level,
        ml_probability=round(ml_prob, 4),
        rule_flags=rule_flags,
        status="pending"
    )
    db.add(db_txn)
    db.commit()
    db.refresh(db_txn)

    # 6. Persist RiskScore record
    db_risk_score = RiskScore(
        transaction_id=db_txn.id,
        rule_flags=rule_flags,
        ml_probability=round(ml_prob, 4),
        risk_level=risk_level,
        computed_at=datetime.datetime.utcnow()
    )
    db.add(db_risk_score)
    db.commit()

    # 7. If High risk, create Alert and publish to Redis
    if risk_level == "High":
        db_alert = Alert(
            transaction_id=db_txn.id,
            user_id=user_id,
            status="pending",
            created_at=datetime.datetime.utcnow()
        )
        db.add(db_alert)
        db.commit()

        # Publish WebSocket event
        alert_event = {
            "alert_id": db_alert.id,
            "transaction_id": db_txn.id,
            "user_id": user_id,
            "amount": db_txn.amount,
            "channel": db_txn.channel,
            "payee_id": db_txn.payee_id,
            "risk_level": db_txn.risk_level,
            "ml_probability": db_txn.ml_probability,
            "rule_flags": db_txn.rule_flags,
            "timestamp": db_txn.timestamp.isoformat(),
            "status": db_txn.status
        }
        publish_alert_sync(alert_event)

    return db_txn
