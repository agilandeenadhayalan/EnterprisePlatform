"""
Model Registry client for managing ML model lifecycle.

Wraps MLflow's model registry to provide a simplified interface for
registering, versioning, and promoting models through lifecycle stages
(none -> staging -> production -> archived).

Falls back to an in-memory registry when MLflow is not installed or
unreachable, following the same graceful-degradation pattern as the
ClickHouse and Kafka client wrappers.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Optional dependency: mlflow ──
try:
    import mlflow
    from mlflow.tracking import MlflowClient as _MlflowClient
    _HAS_MLFLOW = True
except ImportError:
    _HAS_MLFLOW = False

# Valid lifecycle stages
_VALID_STAGES = {"none", "staging", "production", "archived"}


class ModelRegistryClient:
    """Simplified model registry backed by MLflow.

    Parameters
    ----------
    tracking_uri : str
        MLflow tracking server URI (e.g. ``"http://localhost:5000"``).
        Ignored in mock mode.

    Notes
    -----
    When MLflow is not installed the client stores model metadata in
    plain Python dictionaries so that downstream services can develop
    and test without a running MLflow server.
    """

    def __init__(self, tracking_uri: str = "http://localhost:5000") -> None:
        self.tracking_uri = tracking_uri
        self._client: Any = None
        self._use_mock = True

        # Mock storage
        self._mock_models: Dict[str, List[Dict[str, Any]]] = {}
        self._mock_version_counter: Dict[str, int] = {}

        if _HAS_MLFLOW:
            try:
                mlflow.set_tracking_uri(tracking_uri)
                self._client = _MlflowClient(tracking_uri=tracking_uri)
                self._use_mock = False
                logger.info(
                    "ModelRegistry connected to MLflow at %s", tracking_uri
                )
            except Exception as exc:
                logger.warning(
                    "MLflow connection failed (%s) — running in mock mode", exc
                )
        else:
            logger.warning(
                "mlflow package not installed — ModelRegistry running in mock mode"
            )

    # ── Registration ──

    def register_model(
        self,
        name: str,
        run_id: str,
        description: str = "",
    ) -> Dict[str, Any]:
        """Register a new model version from a completed run.

        Parameters
        ----------
        name : str
            Registered model name (will be created if it does not exist).
        run_id : str
            MLflow run id that produced the model artifacts.
        description : str
            Human-readable description of this model version.

        Returns
        -------
        dict
            Model version metadata with keys ``name``, ``version``,
            ``run_id``, ``description``, ``stage``, ``created_at``.
        """
        if not self._use_mock:
            try:
                # Ensure registered model exists
                try:
                    self._client.get_registered_model(name)
                except Exception:
                    self._client.create_registered_model(
                        name, description=description
                    )

                mv = self._client.create_model_version(
                    name=name,
                    source=f"runs:/{run_id}/model",
                    run_id=run_id,
                    description=description,
                )
                version_info = {
                    "name": mv.name,
                    "version": mv.version,
                    "run_id": mv.run_id,
                    "description": mv.description or "",
                    "stage": mv.current_stage,
                    "created_at": str(mv.creation_timestamp),
                }
                logger.info(
                    "Registered model %s version %s", name, mv.version
                )
                return version_info
            except Exception as exc:
                logger.warning(
                    "MLflow register_model failed (%s) — using mock", exc
                )

        # Mock fallback
        if name not in self._mock_models:
            self._mock_models[name] = []
            self._mock_version_counter[name] = 0

        self._mock_version_counter[name] += 1
        version = self._mock_version_counter[name]

        version_info: Dict[str, Any] = {
            "name": name,
            "version": version,
            "run_id": run_id,
            "description": description,
            "stage": "none",
            "created_at": str(int(time.time() * 1000)),
        }
        self._mock_models[name].append(version_info)
        logger.info("Mock registered model %s version %d", name, version)
        return version_info

    # ── Retrieval ──

    def get_model(
        self,
        name: str,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get metadata for a registered model.

        Parameters
        ----------
        name : str
            Registered model name.
        version : int or None
            Specific version number.  If ``None``, returns the latest version.

        Returns
        -------
        dict or None
            Model version metadata, or ``None`` if not found.
        """
        if not self._use_mock:
            try:
                if version is not None:
                    mv = self._client.get_model_version(name, str(version))
                else:
                    versions = self._client.get_latest_versions(name)
                    if not versions:
                        return None
                    mv = versions[-1]
                return {
                    "name": mv.name,
                    "version": mv.version,
                    "run_id": mv.run_id,
                    "description": mv.description or "",
                    "stage": mv.current_stage,
                    "created_at": str(mv.creation_timestamp),
                }
            except Exception as exc:
                logger.warning("MLflow get_model failed (%s) — using mock", exc)

        # Mock fallback
        versions_list = self._mock_models.get(name, [])
        if not versions_list:
            return None
        if version is not None:
            for v in versions_list:
                if v["version"] == version:
                    return dict(v)
            return None
        return dict(versions_list[-1])

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models with their latest version info.

        Returns
        -------
        list[dict]
            One entry per registered model with ``name``, ``latest_version``,
            ``latest_stage``, and ``description``.
        """
        if not self._use_mock:
            try:
                models = self._client.search_registered_models()
                result = []
                for m in models:
                    latest = m.latest_versions[-1] if m.latest_versions else None
                    result.append({
                        "name": m.name,
                        "description": m.description or "",
                        "latest_version": latest.version if latest else None,
                        "latest_stage": latest.current_stage if latest else "none",
                    })
                return result
            except Exception as exc:
                logger.warning(
                    "MLflow list_models failed (%s) — using mock", exc
                )

        # Mock fallback
        result: List[Dict[str, Any]] = []
        for name, versions in self._mock_models.items():
            latest = versions[-1] if versions else None
            result.append({
                "name": name,
                "description": latest["description"] if latest else "",
                "latest_version": latest["version"] if latest else None,
                "latest_stage": latest["stage"] if latest else "none",
            })
        return result

    # ── Lifecycle management ──

    def transition_stage(
        self,
        name: str,
        version: int,
        stage: str,
    ) -> None:
        """Transition a model version to a new lifecycle stage.

        Parameters
        ----------
        name : str
            Registered model name.
        version : int
            Model version number.
        stage : str
            Target stage.  One of ``"none"``, ``"staging"``,
            ``"production"``, ``"archived"``.

        Raises
        ------
        ValueError
            If *stage* is not one of the valid lifecycle stages.
        """
        stage_lower = stage.lower()
        if stage_lower not in _VALID_STAGES:
            raise ValueError(
                f"Invalid stage '{stage}'. Must be one of {_VALID_STAGES}"
            )

        if not self._use_mock:
            try:
                self._client.transition_model_version_stage(
                    name=name,
                    version=str(version),
                    stage=stage_lower.capitalize() if stage_lower != "none" else "None",
                )
                logger.info(
                    "Model %s v%d transitioned to %s", name, version, stage_lower
                )
                return
            except Exception as exc:
                logger.warning(
                    "MLflow transition_stage failed (%s) — using mock", exc
                )

        # Mock fallback
        versions_list = self._mock_models.get(name, [])
        for v in versions_list:
            if v["version"] == version:
                v["stage"] = stage_lower
                logger.info(
                    "Mock model %s v%d transitioned to %s",
                    name,
                    version,
                    stage_lower,
                )
                return
        logger.warning("Model %s version %d not found in mock store", name, version)

    def get_production_model(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the current production version of a model.

        Parameters
        ----------
        name : str
            Registered model name.

        Returns
        -------
        dict or None
            Model version info for the production model, or ``None`` if no
            version is in production.
        """
        if not self._use_mock:
            try:
                versions = self._client.get_latest_versions(
                    name, stages=["Production"]
                )
                if versions:
                    mv = versions[0]
                    return {
                        "name": mv.name,
                        "version": mv.version,
                        "run_id": mv.run_id,
                        "description": mv.description or "",
                        "stage": mv.current_stage,
                        "created_at": str(mv.creation_timestamp),
                    }
                return None
            except Exception as exc:
                logger.warning(
                    "MLflow get_production_model failed (%s) — using mock", exc
                )

        # Mock fallback
        versions_list = self._mock_models.get(name, [])
        for v in reversed(versions_list):
            if v.get("stage") == "production":
                return dict(v)
        return None
