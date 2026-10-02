import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from ml.features import build_features, FEATURE_NAMES

def generate_synthetic_dataset(n_samples: int = 3000, random_state: int = 42) -> pd.DataFrame:
    """
    Generates a realistic synthetic UPI transaction dataset modeled after PaySim / IEEE-CIS fraud patterns.
    Uses exact build_features logic to ensure zero train/serve skew.
    """
    np.random.seed(random_state)
    records = []
    labels = []

    channels = ["UPI", "QR", "CARD", "NETBANKING"]
    types = ["transfer", "payment", "cash_out", "debit"]
    payees = [f"merchant_{i}" for i in range(1, 50)]

    user_histories = {u: [] for u in range(1, 101)}

    base_time = pd.Timestamp("2026-09-01 00:00:00")

    for i in range(n_samples):
        user_id = np.random.randint(1, 101)
        history = user_histories[user_id]

        # 5% target fraud rate
        is_fraud = 1 if np.random.rand() < 0.05 else 0

        if is_fraud:
            # Fraudulent transaction characteristics
            amount = float(np.random.choice([
                np.random.uniform(50000, 200000),  # large amount
                np.random.uniform(10, 80),          # micro burst
                np.random.uniform(25000, 80000)    # odd hour / QR scam
            ]))
            channel = np.random.choice(["UPI", "QR"])
            t_type = "transfer"
            payee_id = f"suspicious_payee_{np.random.randint(100, 999)}"
            # Fraud often at odd hours (1 AM to 4 AM)
            hour = np.random.choice([1, 2, 3, 4, 23])
            day_offset = np.random.randint(0, 30)
            txn_dt = base_time + pd.Timedelta(days=day_offset, hours=int(hour), minutes=np.random.randint(0, 60))
        else:
            # Normal transaction characteristics
            amount = float(np.random.exponential(scale=1500) + 20)
            channel = np.random.choice(channels, p=[0.7, 0.15, 0.1, 0.05])
            t_type = np.random.choice(types, p=[0.5, 0.3, 0.1, 0.1])
            payee_id = np.random.choice(payees)
            hour = np.random.randint(6, 22)
            day_offset = np.random.randint(0, 30)
            txn_dt = base_time + pd.Timedelta(days=day_offset, hours=int(hour), minutes=np.random.randint(0, 60))

        txn = {
            "id": i + 1,
            "user_id": user_id,
            "amount": amount,
            "type": t_type,
            "channel": channel,
            "payee_id": payee_id,
            "timestamp": txn_dt.isoformat()
        }

        # Build feature vector using single build_features function
        feat_df = build_features(txn, history)
        records.append(feat_df.iloc[0].to_dict())
        labels.append(is_fraud)

        # Update history
        history.append(txn)

    df = pd.DataFrame(records)
    df["is_fraud"] = labels
    return df

def run_preprocessing(models_dir: str = "ml/models") -> dict:
    """
    Full preprocessing pipeline:
    1. Loads / generates dataset
    2. Prints EDA summary (class imbalance, missing values)
    3. Stratified Train/Test split (80/20)
    4. StandardScaler fit on train set ONLY
    5. SMOTE applied on train set ONLY
    6. Saves preprocessor.joblib
    """
    print("--- ML Preprocessing & EDA Summary ---")
    df = generate_synthetic_dataset()

    total_samples = len(df)
    fraud_samples = df["is_fraud"].sum()
    print(f"Total samples: {total_samples}")
    print(f"Class imbalance: Fraud={fraud_samples} ({fraud_samples/total_samples*100:.2f}%), Non-Fraud={total_samples-fraud_samples}")
    print(f"Missing values per column:\n{df.isnull().sum()}")

    X = df[FEATURE_NAMES]
    y = df["is_fraud"]

    # Stratified Train/Test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # Fit StandardScaler on TRAIN set only
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # SMOTE on TRAIN set only
    smote = SMOTE(random_state=42)
    X_train_res, y_train_res = smote.fit_resample(X_train_scaled, y_train)

    print(f"Train samples before SMOTE: {len(X_train)}, after SMOTE: {len(X_train_res)}")

    # Save preprocessor artifact
    os.makedirs(models_dir, exist_ok=True)
    preprocessor_path = os.path.join(models_dir, "preprocessor.joblib")
    preprocessor_dict = {
        "scaler": scaler,
        "feature_names": FEATURE_NAMES
    }
    joblib.dump(preprocessor_dict, preprocessor_path)
    print(f"Saved preprocessor artifact to {preprocessor_path}")

    return {
        "X_train_res": X_train_res,
        "y_train_res": y_train_res,
        "X_test_scaled": X_test_scaled,
        "y_test": y_test,
        "scaler": scaler,
        "X_train_df": X_train,
        "X_test_df": X_test,
        "df": df
    }

if __name__ == "__main__":
    run_preprocessing()
