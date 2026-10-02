import os
import json
import joblib
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

def train_xgboost(prep_data: dict, reports_dir: str = "ml/reports", models_dir: str = "ml/models") -> dict:
    """
    Trains XGBoost baseline model on SMOTE-resampled train set.
    Evaluates on untouched test set and saves baseline_metrics.json & xgboost.joblib.
    """
    X_train = prep_data["X_train_res"]
    y_train = prep_data["y_train_res"]
    X_test = prep_data["X_test_scaled"]
    y_test = prep_data["y_test"]

    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss"
    )

    model.fit(X_train, y_train)

    y_pred_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_prob >= 0.5).astype(int)

    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_pred_prob))
    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "model": "XGBoost Baseline",
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
        "confusion_matrix": cm
    }

    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)

    metrics_path = os.path.join(reports_dir, "baseline_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    model_path = os.path.join(models_dir, "xgboost.joblib")
    joblib.dump(model, model_path)

    print(f"XGBoost trained successfully! Precision: {precision:.4f}, Recall: {recall:.4f}, ROC-AUC: {roc_auc:.4f}")
    print(f"Saved metrics to {metrics_path} and model to {model_path}")

    return {"model": model, "metrics": metrics, "y_pred_prob": y_pred_prob}
