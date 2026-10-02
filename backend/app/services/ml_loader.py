import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Union
from backend.app.core.config import settings
from ml.features import build_features
from ml.explainability import get_top_shap_contributions

class ModelManager:
    _instance = None

    def __init__(self, models_dir: str = "ml/models"):
        self.models_dir = models_dir
        self.preprocessor = None
        self.xgb_model = None
        self.bilstm_model = None
        self.is_loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ModelManager()
        return cls._instance

    def load_models(self):
        preprocessor_path = os.path.join(self.models_dir, "preprocessor.joblib")
        xgb_path = os.path.join(self.models_dir, "xgboost.joblib")

        if not os.path.exists(preprocessor_path):
            raise FileNotFoundError(f"Missing required ML artifact: {preprocessor_path}. Please run ml/train_all.py first.")
        if not os.path.exists(xgb_path):
            raise FileNotFoundError(f"Missing required ML artifact: {xgb_path}. Please run ml/train_all.py first.")

        self.preprocessor = joblib.load(preprocessor_path)
        self.xgb_model = joblib.load(xgb_path)

        bilstm_path = os.path.join(self.models_dir, "bilstm_cnn.keras")
        if os.path.exists(bilstm_path):
            try:
                import tensorflow as tf
                self.bilstm_model = tf.keras.models.load_model(bilstm_path)
            except Exception as e:
                print(f"Warning: Could not load BiLSTM-CNN model: {e}")

        self.is_loaded = True
        print(f"ML models loaded successfully from {self.models_dir}")

    def predict_probability(self, transaction: Union[Dict[str, Any], Any], user_history: List[Union[Dict[str, Any], Any]]) -> float:
        if not self.is_loaded:
            self.load_models()

        feat_df = build_features(transaction, user_history)
        scaler = self.preprocessor["scaler"]
        scaled_feats = scaler.transform(feat_df)

        model_type = settings.MODEL_FOR_SCORING.lower()
        if model_type == "bilstm_cnn" and self.bilstm_model is not None:
            scaled_3d = np.expand_dims(scaled_feats, axis=-1)
            prob = float(self.bilstm_model.predict(scaled_3d, verbose=0).flatten()[0])
        else:
            prob = float(self.xgb_model.predict_proba(scaled_feats)[0, 1])

        return float(np.clip(prob, 0.0, 1.0))

    def get_shap_explanation(self, transaction: Union[Dict[str, Any], Any], user_history: List[Union[Dict[str, Any], Any]]) -> list:
        if not self.is_loaded:
            self.load_models()

        feat_df = build_features(transaction, user_history)
        scaler = self.preprocessor["scaler"]
        return get_top_shap_contributions(self.xgb_model, scaler, feat_df, top_k=8)

model_manager = ModelManager.get_instance()
