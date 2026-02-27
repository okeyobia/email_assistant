from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from utils.config import AppConfig

LOGGER = logging.getLogger(__name__)


class MLClassifier:
    """Thin wrapper around an optional NLP model."""

    def __init__(self, model_path: Optional[Path] = None, transformer_model: Optional[str] = None):
        self._model_path = model_path
        self._transformer_model = transformer_model
        self._sklearn_pipeline = None
        self._transformer_pipeline = None
        if model_path:
            self._load_sklearn_pipeline(model_path)
        elif transformer_model:
            self._load_transformer_pipeline(transformer_model)

    @property
    def is_ready(self) -> bool:
        return bool(self._sklearn_pipeline or self._transformer_pipeline)

    def predict(self, text: str) -> Optional[str]:
        if not text or not self.is_ready:
            return None
        if self._sklearn_pipeline is not None:
            prediction = self._sklearn_pipeline.predict([text])[0]
            LOGGER.debug("ML pipeline prediction: %s", prediction)
            return str(prediction)
        if self._transformer_pipeline is not None:
            result = self._transformer_pipeline(text, truncation=True)
            if isinstance(result, list) and result:
                LOGGER.debug("Transformer prediction: %s", result[0])
                return str(result[0].get("label"))
        return None

    def _load_sklearn_pipeline(self, model_path: Path) -> None:
        try:
            from joblib import load
        except ImportError as exc:
            raise RuntimeError("Install the 'ml' extra to use sklearn models") from exc
        if not model_path.exists():
            LOGGER.warning("ML model path %s does not exist", model_path)
            return
        self._sklearn_pipeline = load(model_path)
        LOGGER.info("Loaded scikit-learn pipeline from %s", model_path)

    def _load_transformer_pipeline(self, model_name: str) -> None:
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError(
                "transformers is required for transformer-based classification"
            ) from exc
        self._transformer_pipeline = pipeline("text-classification", model=model_name)
        LOGGER.info("Loaded transformer pipeline %s", model_name)

    @classmethod
    def from_config(cls, config: AppConfig) -> "MLClassifier | None":
        if not config.model_path and not config.transformer_model:
            return None
        return cls(model_path=config.model_path, transformer_model=config.transformer_model)
