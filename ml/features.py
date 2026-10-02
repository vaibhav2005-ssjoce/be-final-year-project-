import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Union

CHANNEL_MAP = {"UPI": 0, "QR": 1, "CARD": 2, "NETBANKING": 3}
TYPE_MAP = {"transfer": 0, "payment": 1, "cash_out": 2, "debit": 3, "other": 4}

FEATURE_NAMES = [
    "amount",
    "type_encoded",
    "channel_encoded",
    "hour_of_day",
    "day_of_week",
    "is_new_payee",
    "recent_txn_count",
    "amount_vs_user_avg"
]

def _get_val(obj: Union[Dict[str, Any], Any], key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _normalize_dt(dt_val: Union[datetime.datetime, str, None]) -> datetime.datetime:
    if dt_val is None:
        return datetime.datetime.now(datetime.timezone.utc)
    if isinstance(dt_val, str):
        try:
            dt_val = datetime.datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
        except Exception:
            return datetime.datetime.now(datetime.timezone.utc)
    if dt_val.tzinfo is None:
        dt_val = dt_val.replace(tzinfo=datetime.timezone.utc)
    else:
        dt_val = dt_val.astimezone(datetime.timezone.utc)
    return dt_val

def build_features(transaction: Union[Dict[str, Any], Any], user_history: List[Union[Dict[str, Any], Any]]) -> pd.DataFrame:
    """
    Extracts numerical feature vector for live serving AND model training.
    Ensures ZERO train/serve skew by using exact same transformation logic.
    Returns a single-row pandas DataFrame with FEATURE_NAMES columns.
    """
    txn_id = _get_val(transaction, "id")
    amount = float(_get_val(transaction, "amount", 0.0))
    t_type = str(_get_val(transaction, "type", "transfer")).lower()
    channel = str(_get_val(transaction, "channel", "UPI")).upper()
    payee_id = str(_get_val(transaction, "payee_id", ""))
    dt = _normalize_dt(_get_val(transaction, "timestamp"))

    # Exclude current transaction from history if present
    prior_history = []
    for h in (user_history or []):
        h_id = _get_val(h, "id")
        if txn_id is not None and h_id is not None and h_id == txn_id:
            continue
        prior_history.append(h)

    # 1. amount
    # 2. type_encoded
    type_enc = TYPE_MAP.get(t_type, TYPE_MAP["other"])

    # 3. channel_encoded
    channel_enc = CHANNEL_MAP.get(channel, CHANNEL_MAP["UPI"])

    # 4. hour_of_day
    hour_of_day = dt.hour

    # 5. day_of_week
    day_of_week = dt.weekday()

    # 6. is_new_payee
    seen_payees = {str(_get_val(h, "payee_id")) for h in prior_history if _get_val(h, "payee_id") is not None}
    is_new_payee = 1.0 if payee_id not in seen_payees else 0.0

    # 7. recent_txn_count (txns in last 24h)
    window_24h = 86400.0
    recent_cnt = 0
    amounts = []
    for h in prior_history:
        h_dt = _normalize_dt(_get_val(h, "timestamp"))
        h_amt = float(_get_val(h, "amount", 0.0))
        amounts.append(h_amt)
        if abs((dt - h_dt).total_seconds()) <= window_24h:
            recent_cnt += 1

    # 8. amount_vs_user_avg
    user_avg = float(np.mean(amounts)) if len(amounts) > 0 else amount
    amount_vs_user_avg = amount / (user_avg + 1e-5)

    feat_dict = {
        "amount": [amount],
        "type_encoded": [float(type_enc)],
        "channel_encoded": [float(channel_enc)],
        "hour_of_day": [float(hour_of_day)],
        "day_of_week": [float(day_of_week)],
        "is_new_payee": [is_new_payee],
        "recent_txn_count": [float(recent_cnt)],
        "amount_vs_user_avg": [float(amount_vs_user_avg)]
    }

    return pd.DataFrame(feat_dict, columns=FEATURE_NAMES)
