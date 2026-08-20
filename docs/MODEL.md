# Model provenance

The bundled artifact is the 30-second Random Forest pipeline produced by the associated anomaly-detection research project. It contains:

- one-hot service preprocessing;
- the fitted Random Forest classifier;
- the ordered behavioural feature contract;
- a threshold selected using validation anomaly F1;
- the 30-second window duration.

The worker calculates a SHA-256 fingerprint of the artifact and writes the first 12 hexadecimal characters to every prediction as `model_version`.

The artifact was trained on controlled synthetic cloud-style telemetry. Its inclusion makes the engineering system immediately reproducible; it is not evidence that the model is calibrated for an unseen organisation. Replacing it requires validation of the feature schema, window duration, threshold, and operational error costs.
