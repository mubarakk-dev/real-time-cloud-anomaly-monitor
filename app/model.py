import warnings
from hashlib import sha256
from pathlib import Path
from time import perf_counter

import joblib
import pandas as pd


class ModelRuntime:
    def __init__(self, artifact_path: str):
        path = Path(artifact_path)
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Setting the shape on a NumPy array has been deprecated.*",
                category=DeprecationWarning,
                module="joblib.numpy_pickle",
            )
            artifact = joblib.load(path)
        self.pipeline = artifact["pipeline"]
        self.threshold = float(artifact["threshold"])
        self.features = list(artifact["features"])
        self.window_seconds = int(artifact["window_seconds"])
        self.version = sha256(path.read_bytes()).hexdigest()[:12]

    def predict(self, features: dict) -> tuple[float, bool, float]:
        started = perf_counter()
        score = float(self.pipeline.predict_proba(pd.DataFrame([features])[self.features])[:, 1][0])
        elapsed_ms = (perf_counter() - started) * 1000
        return score, score >= self.threshold, elapsed_ms
