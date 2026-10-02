import datetime
from typing import List, Dict, Any, Union

LARGE_AMOUNT_THRESHOLD = 50000.0
MICRO_TRANSACTION_THRESHOLD = 100.0
MICRO_TRANSACTION_COUNT_THRESHOLD = 3
MICRO_TRANSACTION_WINDOW_MINUTES = 5
ODD_HOUR_MAX_HOUR = 5
ODD_HOUR_MIN_AMOUNT = 10000.0
QR_HIGH_VALUE_THRESHOLD = 20000.0
DORMANCY_DAYS_THRESHOLD = 30
DORMANCY_MIN_AMOUNT = 50000.0

def _get_val(obj: Union[Dict[str, Any], Any], key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _normalize_dt(dt_val: Union[datetime.datetime, str, None]) -> datetime.datetime:
    if dt_val is None:
        return datetime.datetime.now(datetime.timezone.utc)
    if isinstance(dt_val, str):
        # Handle ISO strings
        try:
            dt_val = datetime.datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
        except Exception:
            return datetime.datetime.now(datetime.timezone.utc)
    if dt_val.tzinfo is None:
        dt_val = dt_val.replace(tzinfo=datetime.timezone.utc)
    else:
        dt_val = dt_val.astimezone(datetime.timezone.utc)
    return dt_val

def check(transaction: Union[Dict[str, Any], Any], user_history: List[Union[Dict[str, Any], Any]]) -> List[str]:
    """
    Evaluates 5 UPI fraud detection rules against a transaction and the user's prior history.
    Returns a list of triggered rule flag strings.
    """
    flags: List[str] = []

    txn_id = _get_val(transaction, "id")
    amount = float(_get_val(transaction, "amount", 0.0))
    channel = str(_get_val(transaction, "channel", ""))
    payee_id = str(_get_val(transaction, "payee_id", ""))
    txn_dt = _normalize_dt(_get_val(transaction, "timestamp"))

    # Clean prior history: exclude current transaction if present by id
    prior_history = []
    for h in user_history:
        h_id = _get_val(h, "id")
        if txn_id is not None and h_id is not None and h_id == txn_id:
            continue
        prior_history.append(h)

    # Historical payees set
    seen_payees = {str(_get_val(h, "payee_id")) for h in prior_history if _get_val(h, "payee_id") is not None}
    is_new_payee = payee_id not in seen_payees

    # Rule 1: large_amount_new_payee
    """
    Triggers if transaction amount > LARGE_AMOUNT_THRESHOLD (50000 INR) and payee has never been paid before.
    """
    if amount > LARGE_AMOUNT_THRESHOLD and is_new_payee:
        flags.append("large_amount_new_payee")

    # Rule 2: rapid_micro_transactions
    """
    Triggers if 3+ transactions <= 100 INR to the same payee occur within 5 minutes.
    """
    if amount <= MICRO_TRANSACTION_THRESHOLD:
        micro_count = 1  # Count current transaction
        window_seconds = MICRO_TRANSACTION_WINDOW_MINUTES * 60
        for h in prior_history:
            h_amount = float(_get_val(h, "amount", 0.0))
            h_payee = str(_get_val(h, "payee_id", ""))
            if h_payee == payee_id and h_amount <= MICRO_TRANSACTION_THRESHOLD:
                h_dt = _normalize_dt(_get_val(h, "timestamp"))
                diff_sec = abs((txn_dt - h_dt).total_seconds())
                if diff_sec <= window_seconds:
                    micro_count += 1
        if micro_count >= MICRO_TRANSACTION_COUNT_THRESHOLD:
            flags.append("rapid_micro_transactions")

    # Rule 3: odd_hour_transaction
    """
    Triggers if transaction occurs during odd hours (hour < 5 AM UTC/local) and amount > ODD_HOUR_MIN_AMOUNT (10000 INR).
    """
    if txn_dt.hour < ODD_HOUR_MAX_HOUR and amount > ODD_HOUR_MIN_AMOUNT:
        flags.append("odd_hour_transaction")

    # Rule 4: new_qr_merchant_high_value
    """
    Triggers if channel is QR, amount > 20000 INR, and payee has never been seen before.
    """
    if channel == "QR" and amount > QR_HIGH_VALUE_THRESHOLD and is_new_payee:
        flags.append("new_qr_merchant_high_value")

    # Rule 5: burst_after_dormancy
    """
    Triggers if amount > 50000 INR and gap since user's most recent prior transaction > 30 days ('digital arrest' pattern).
    """
    if amount > DORMANCY_MIN_AMOUNT and prior_history:
        prior_timestamps = [_normalize_dt(_get_val(h, "timestamp")) for h in prior_history]
        most_recent_dt = max(prior_timestamps)
        dormancy_days = (txn_dt - most_recent_dt).total_seconds() / 86400.0
        if dormancy_days > DORMANCY_DAYS_THRESHOLD:
            flags.append("burst_after_dormancy")

    return flags
