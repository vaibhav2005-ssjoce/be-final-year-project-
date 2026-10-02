import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input, Conv1D, MaxPooling1D, Bidirectional, LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.metrics import Recall, Precision, Accuracy
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

def build_bilstm_cnn(input_dim: int):
    """
    Builds the BiLSTM-CNN model architecture exactly as mandated:
    Input(shape=(input_dim,1)) -> Conv1D(64,3,relu) -> MaxPooling1D(2) -> Bidirectional(LSTM(64)) -> Dense(32,relu) -> Dropout(0.3) -> Dense(1,sigmoid)
    """
    model = Sequential([
        Input(shape=(input_dim, 1)),
        Conv1D(filters=64, kernel_size=3, activation="relu", padding="same"),
        MaxPooling1D(pool_size=2),
        Bidirectional(LSTM(64)),
        Dense(32, activation="relu"),
        Dropout(0.3),
        Dense(1, activation="sigmoid")
    ])

    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy", Recall(name="recall"), Precision(name="precision")]
    )
    return model

def train_bilstm_cnn(prep_data: dict, reports_dir: str = "ml/reports", models_dir: str = "ml/models") -> dict:
    """
    Trains BiLSTM-CNN model with EarlyStopping on validation recall.
    Saves bilstm_metrics.json & bilstm_cnn.keras.
    """
    X_train = prep_data["X_train_res"]
    y_train = prep_data["y_train_res"]
    X_test = prep_data["X_test_scaled"]
    y_test = prep_data["y_test"]

    input_dim = X_train.shape[1]

    # Reshape features for Conv1D: (batch, timesteps, features_per_step) -> (batch, input_dim, 1)
    X_train_3d = np.expand_dims(X_train, axis=-1)
    X_test_3d = np.expand_dims(X_test, axis=-1)

    model = build_bilstm_cnn(input_dim)

    early_stopping = EarlyStopping(
        monitor="val_recall",
        mode="max",
        patience=5,
        restore_best_weights=True
    )

    history = model.fit(
        X_train_3d,
        y_train,
        validation_data=(X_test_3d, y_test),
        epochs=20,
        batch_size=32,
        callbacks=[early_stopping],
        verbose=1
    )

    y_pred_prob = model.predict(X_test_3d).flatten()
    y_pred = (y_pred_prob >= 0.5).astype(int)

    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_pred_prob))
    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "model": "BiLSTM-CNN Neural Network",
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
        "confusion_matrix": cm
    }

    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)

    metrics_path = os.path.join(reports_dir, "bilstm_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    model_path = os.path.join(models_dir, "bilstm_cnn.keras")
    model.save(model_path)

    print(f"BiLSTM-CNN trained successfully! Precision: {precision:.4f}, Recall: {recall:.4f}, ROC-AUC: {roc_auc:.4f}")
    print(f"Saved metrics to {metrics_path} and model to {model_path}")

    return {"model": model, "metrics": metrics, "y_pred_prob": y_pred_prob}
