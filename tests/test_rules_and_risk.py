import pytest
import datetime
from backend.app.services.rule_engine import check
from backend.app.services.risk_scoring import compute_risk_score

def test_large_amount_new_payee_positive():
    txn = {"id": 1, "amount": 60000, "channel": "UPI", "payee_id": "payee_new", "timestamp": "2026-10-01T12:00:00Z"}
    history = [{"id": 2, "amount": 1000, "channel": "UPI", "payee_id": "payee_old", "timestamp": "2026-09-30T12:00:00Z"}]
    flags = check(txn, history)
    assert "large_amount_new_payee" in flags

def test_large_amount_new_payee_negative_seen_payee():
    txn = {"id": 1, "amount": 60000, "channel": "UPI", "payee_id": "payee_old", "timestamp": "2026-10-01T12:00:00Z"}
    history = [{"id": 2, "amount": 1000, "channel": "UPI", "payee_id": "payee_old", "timestamp": "2026-09-30T12:00:00Z"}]
    flags = check(txn, history)
    assert "large_amount_new_payee" not in flags

def test_rapid_micro_transactions_positive():
    now = datetime.datetime.now(datetime.timezone.utc)
    txn = {"id": 1, "amount": 50, "channel": "UPI", "payee_id": "merchant_1", "timestamp": now}
    history = [
        {"id": 2, "amount": 20, "channel": "UPI", "payee_id": "merchant_1", "timestamp": now - datetime.timedelta(minutes=1)},
        {"id": 3, "amount": 30, "channel": "UPI", "payee_id": "merchant_1", "timestamp": now - datetime.timedelta(minutes=3)},
    ]
    flags = check(txn, history)
    assert "rapid_micro_transactions" in flags

def test_rapid_micro_transactions_negative_outside_window():
    now = datetime.datetime.now(datetime.timezone.utc)
    txn = {"id": 1, "amount": 50, "channel": "UPI", "payee_id": "merchant_1", "timestamp": now}
    history = [
        {"id": 2, "amount": 20, "channel": "UPI", "payee_id": "merchant_1", "timestamp": now - datetime.timedelta(minutes=10)},
        {"id": 3, "amount": 30, "channel": "UPI", "payee_id": "merchant_1", "timestamp": now - datetime.timedelta(minutes=12)},
    ]
    flags = check(txn, history)
    assert "rapid_micro_transactions" not in flags

def test_odd_hour_transaction_positive():
    odd_dt = datetime.datetime(2026, 10, 1, 3, 30, 0, tzinfo=datetime.timezone.utc)
    txn = {"id": 1, "amount": 15000, "channel": "UPI", "payee_id": "payee_1", "timestamp": odd_dt}
    flags = check(txn, [])
    assert "odd_hour_transaction" in flags

def test_odd_hour_transaction_negative_low_amount():
    odd_dt = datetime.datetime(2026, 10, 1, 3, 30, 0, tzinfo=datetime.timezone.utc)
    txn = {"id": 1, "amount": 5000, "channel": "UPI", "payee_id": "payee_1", "timestamp": odd_dt}
    flags = check(txn, [])
    assert "odd_hour_transaction" not in flags

def test_new_qr_merchant_high_value_positive():
    txn = {"id": 1, "amount": 25000, "channel": "QR", "payee_id": "qr_new", "timestamp": "2026-10-01T12:00:00Z"}
    flags = check(txn, [])
    assert "new_qr_merchant_high_value" in flags

def test_new_qr_merchant_high_value_negative_not_qr():
    txn = {"id": 1, "amount": 25000, "channel": "CARD", "payee_id": "qr_new", "timestamp": "2026-10-01T12:00:00Z"}
    flags = check(txn, [])
    assert "new_qr_merchant_high_value" not in flags

def test_burst_after_dormancy_positive_unsorted_history():
    now = datetime.datetime.now(datetime.timezone.utc)
    txn = {"id": 1, "amount": 60000, "channel": "UPI", "payee_id": "payee_old", "timestamp": now}
    # Unsorted history with most recent prior transaction 40 days ago
    history = [
        {"id": 2, "amount": 1000, "channel": "UPI", "payee_id": "payee_old", "timestamp": now - datetime.timedelta(days=100)},
        {"id": 3, "amount": 500, "channel": "UPI", "payee_id": "payee_old", "timestamp": now - datetime.timedelta(days=40)},
        {"id": 4, "amount": 200, "channel": "UPI", "payee_id": "payee_old", "timestamp": now - datetime.timedelta(days=150)},
    ]
    flags = check(txn, history)
    assert "burst_after_dormancy" in flags

def test_burst_after_dormancy_negative_recent_history():
    now = datetime.datetime.now(datetime.timezone.utc)
    txn = {"id": 1, "amount": 60000, "channel": "UPI", "payee_id": "payee_old", "timestamp": now}
    history = [
        {"id": 2, "amount": 1000, "channel": "UPI", "payee_id": "payee_old", "timestamp": now - datetime.timedelta(days=5)},
    ]
    flags = check(txn, history)
    assert "burst_after_dormancy" not in flags

def test_edge_case_empty_history():
    txn = {"id": 1, "amount": 100, "channel": "UPI", "payee_id": "payee_1", "timestamp": "2026-10-01T10:00:00Z"}
    flags = check(txn, [])
    assert isinstance(flags, list)

def test_edge_case_timezone_mix():
    naive_dt = datetime.datetime(2026, 10, 1, 10, 0, 0)
    aware_dt = datetime.datetime(2026, 8, 25, 10, 0, 0, tzinfo=datetime.timezone.utc)
    txn = {"id": 1, "amount": 60000, "channel": "UPI", "payee_id": "payee_old", "timestamp": naive_dt}
    history = [{"id": 2, "amount": 500, "channel": "UPI", "payee_id": "payee_old", "timestamp": aware_dt}]
    flags = check(txn, history)
    assert "burst_after_dormancy" in flags

def test_edge_case_self_exclusion_of_current_txn():
    now = datetime.datetime.now(datetime.timezone.utc)
    txn = {"id": 1, "amount": 60000, "channel": "UPI", "payee_id": "payee_new", "timestamp": now}
    # History contains current txn id=1
    history = [{"id": 1, "amount": 60000, "channel": "UPI", "payee_id": "payee_new", "timestamp": now}]
    flags = check(txn, history)
    # Since id=1 is excluded, payee_new is correctly identified as new payee!
    assert "large_amount_new_payee" in flags

def test_risk_scoring_boundaries():
    # Low risk
    assert compute_risk_score([], 0.1) == "Low"
    assert compute_risk_score([], 0.49) == "Low"
    
    # Medium risk
    assert compute_risk_score([], 0.5) == "Medium"
    assert compute_risk_score([], 0.79) == "Medium"
    assert compute_risk_score(["flag1"], 0.2) == "Medium"
    
    # High risk
    assert compute_risk_score([], 0.8) == "High"
    assert compute_risk_score([], 0.95) == "High"
    assert compute_risk_score(["flag1", "flag2"], 0.1) == "High"
    assert compute_risk_score(["flag1", "flag2", "flag3"], 0.85) == "High"
