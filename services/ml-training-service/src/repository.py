"""
ML Training repository — in-memory pre-seeded training data.

Seeds model architectures and completed training jobs with epoch-by-epoch
metrics. In production, this would persist to PostgreSQL + MLflow.
"""

import uuid
from typing import Optional

from models import TrainingJob, ModelArchitecture, TrainingMetrics


class TrainingRepository:
    """In-memory training data store with pre-seeded sample data."""

    def __init__(self, seed: bool = True):
        self._jobs: dict[str, TrainingJob] = {}
        self._architectures: dict[str, ModelArchitecture] = {}

        if seed:
            self._seed_data()

    def _seed_data(self):
        """Pre-populate with model architectures and completed training jobs."""
        # ── Model Architectures ──
        archs = [
            ModelArchitecture(
                name="fare_predictor_rf",
                type="random_forest",
                description="Random Forest regressor for fare prediction based on trip features",
                default_hyperparameters={
                    "n_estimators": 100,
                    "max_depth": 12,
                    "min_samples_split": 5,
                    "min_samples_leaf": 2,
                },
            ),
            ModelArchitecture(
                name="fare_predictor_nn",
                type="neural_network",
                description="Feed-forward neural network for fare prediction with embeddings",
                default_hyperparameters={
                    "hidden_layers": [128, 64, 32],
                    "learning_rate": 0.001,
                    "batch_size": 256,
                    "epochs": 50,
                    "dropout": 0.2,
                },
            ),
            ModelArchitecture(
                name="demand_predictor_gb",
                type="gradient_boosting",
                description="Gradient Boosting model for zone-level demand prediction",
                default_hyperparameters={
                    "n_estimators": 200,
                    "max_depth": 8,
                    "learning_rate": 0.05,
                    "subsample": 0.8,
                },
            ),
            ModelArchitecture(
                name="eta_predictor_nn",
                type="neural_network",
                description="LSTM-based neural network for ETA prediction using route sequences",
                default_hyperparameters={
                    "lstm_units": 64,
                    "dense_units": 32,
                    "learning_rate": 0.0005,
                    "batch_size": 128,
                    "epochs": 30,
                    "sequence_length": 10,
                },
            ),
        ]
        for arch in archs:
            self._architectures[arch.name] = arch

        # ── Completed Training Jobs ──
        jobs_data = [
            {
                "id": "job-001",
                "model_type": "fare_predictor_rf",
                "hyperparameters": {"n_estimators": 150, "max_depth": 15},
                "dataset_id": "fare_training_v1",
                "status": "completed",
                "created_at": "2024-01-10T08:00:00Z",
                "started_at": "2024-01-10T08:01:00Z",
                "completed_at": "2024-01-10T08:15:00Z",
                "logs": [
                    "Loading dataset fare_training_v1...",
                    "Dataset loaded: 150000 samples",
                    "Starting Random Forest training with 150 estimators",
                    "Training complete. Final RMSE: 2.34",
                    "Model saved to model registry.",
                ],
                "metrics_epochs": 1,
                "base_train_loss": 3.2,
                "base_val_loss": 3.8,
            },
            {
                "id": "job-002",
                "model_type": "fare_predictor_nn",
                "hyperparameters": {"hidden_layers": [128, 64, 32], "learning_rate": 0.001, "epochs": 10},
                "dataset_id": "fare_training_v1",
                "status": "completed",
                "created_at": "2024-01-11T09:00:00Z",
                "started_at": "2024-01-11T09:02:00Z",
                "completed_at": "2024-01-11T09:45:00Z",
                "logs": [
                    "Loading dataset fare_training_v1...",
                    "Dataset loaded: 150000 samples",
                    "Building neural network: [128, 64, 32]",
                    "Epoch 10/10 — train_loss: 1.82, val_loss: 2.01",
                    "Training complete. Best val_loss: 1.95",
                    "Model saved to model registry.",
                ],
                "metrics_epochs": 10,
                "base_train_loss": 5.1,
                "base_val_loss": 5.8,
            },
            {
                "id": "job-003",
                "model_type": "demand_predictor_gb",
                "hyperparameters": {"n_estimators": 200, "max_depth": 8, "learning_rate": 0.05},
                "dataset_id": "demand_training_v1",
                "status": "completed",
                "created_at": "2024-01-12T10:00:00Z",
                "started_at": "2024-01-12T10:01:00Z",
                "completed_at": "2024-01-12T10:20:00Z",
                "logs": [
                    "Loading dataset demand_training_v1...",
                    "Dataset loaded: 80000 samples",
                    "Starting Gradient Boosting training",
                    "Training complete. Final MAE: 4.12",
                    "Model saved to model registry.",
                ],
                "metrics_epochs": 1,
                "base_train_loss": 6.5,
                "base_val_loss": 7.2,
            },
            {
                "id": "job-004",
                "model_type": "eta_predictor_nn",
                "hyperparameters": {"lstm_units": 64, "learning_rate": 0.0005, "epochs": 8},
                "dataset_id": "eta_training_v1",
                "status": "completed",
                "created_at": "2024-01-13T11:00:00Z",
                "started_at": "2024-01-13T11:03:00Z",
                "completed_at": "2024-01-13T12:00:00Z",
                "logs": [
                    "Loading dataset eta_training_v1...",
                    "Dataset loaded: 200000 samples",
                    "Building LSTM network with 64 units",
                    "Epoch 8/8 — train_loss: 1.15, val_loss: 1.32",
                    "Training complete. Best val_loss: 1.28",
                    "Model saved to model registry.",
                ],
                "metrics_epochs": 8,
                "base_train_loss": 4.8,
                "base_val_loss": 5.3,
            },
            {
                "id": "job-005",
                "model_type": "fare_predictor_nn",
                "hyperparameters": {"hidden_layers": [256, 128, 64], "learning_rate": 0.0005, "epochs": 15},
                "dataset_id": "fare_training_v1",
                "status": "running",
                "created_at": "2024-01-14T14:00:00Z",
                "started_at": "2024-01-14T14:02:00Z",
                "completed_at": None,
                "logs": [
                    "Loading dataset fare_training_v1...",
                    "Dataset loaded: 150000 samples",
                    "Building neural network: [256, 128, 64]",
                    "Epoch 5/15 — train_loss: 2.45, val_loss: 2.78",
                ],
                "metrics_epochs": 5,
                "base_train_loss": 5.5,
                "base_val_loss": 6.2,
            },
        ]

        for jd in jobs_data:
            n_epochs = jd.pop("metrics_epochs")
            base_tl = jd.pop("base_train_loss")
            base_vl = jd.pop("base_val_loss")

            metrics = []
            for e in range(1, n_epochs + 1):
                decay = 0.7 ** e
                metrics.append(TrainingMetrics(
                    epoch=e,
                    train_loss=round(base_tl * decay, 4),
                    val_loss=round(base_vl * decay, 4),
                    train_metric=round(1.0 - base_tl * decay / 10, 4),
                    val_metric=round(1.0 - base_vl * decay / 10, 4),
                ))

            jd["metrics"] = metrics
            job = TrainingJob(**jd)
            self._jobs[job.id] = job

    # ── Architecture operations ──

    def list_architectures(self) -> list[ModelArchitecture]:
        """Return all registered model architectures."""
        return list(self._architectures.values())

    def get_architecture(self, name: str) -> Optional[ModelArchitecture]:
        """Return a single architecture by name."""
        return self._architectures.get(name)

    # ── Job operations ──

    def create_job(self, model_type: str, hyperparameters: dict, dataset_id: str) -> TrainingJob:
        """Create a new training job in pending status."""
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        job = TrainingJob(
            id=job_id,
            model_type=model_type,
            hyperparameters=hyperparameters,
            dataset_id=dataset_id,
            status="pending",
            created_at="2024-01-15T10:00:00Z",
            logs=[f"Job {job_id} created. Queued for training."],
        )
        self._jobs[job_id] = job
        return job

    def list_jobs(self, status: Optional[str] = None) -> list[TrainingJob]:
        """List all training jobs, optionally filtered by status."""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    def get_job(self, job_id: str) -> Optional[TrainingJob]:
        """Return a single job by ID."""
        return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> Optional[TrainingJob]:
        """Cancel a running or pending job. Returns None if not found."""
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if job.status in ("pending", "running"):
            job.status = "cancelled"
            job.logs.append(f"Job {job_id} cancelled by user.")
        return job


# Singleton repository instance
repo = TrainingRepository(seed=True)
