from typing import List

HIGH_ML_THRESHOLD = 0.8
HIGH_FLAGS_THRESHOLD = 2
MEDIUM_ML_THRESHOLD = 0.5
MEDIUM_FLAGS_THRESHOLD = 1

def compute_risk_score(rule_flags: List[str], ml_probability: float) -> str:
    """
    Computes overall risk level ("Low", "Medium", "High") based on ML probability and rule engine flags.
    High if ml_probability >= 0.8 or len(flags) >= 2.
    Medium if ml_probability >= 0.5 or len(flags) == 1.
    Else Low.
    """
    num_flags = len(rule_flags) if rule_flags is not None else 0
    ml_prob = float(ml_probability) if ml_probability is not None else 0.0

    if ml_prob >= HIGH_ML_THRESHOLD or num_flags >= HIGH_FLAGS_THRESHOLD:
        return "High"
    elif ml_prob >= MEDIUM_ML_THRESHOLD or num_flags == MEDIUM_FLAGS_THRESHOLD:
        return "Medium"
    else:
        return "Low"
