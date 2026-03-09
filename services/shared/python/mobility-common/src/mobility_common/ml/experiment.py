"""
Experiment tracking client for managing ML experiment runs.

Wraps MLflow's tracking API to provide a simplified interface for
creating experiments, logging parameters, metrics, and artifacts,
and querying run history.

Falls back to an in-memory experiment store when MLflow is not
installed or unreachable, following the same graceful-degradation
pattern used throughout the mobility platform.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Optional dependency: mlflow ──
try:
    import mlflow
    from mlflow.tracking import MlflowClient as _MlflowClient
    _HAS_MLFLOW = True
except ImportError:
    _HAS_MLFLOW = False


class ExperimentClient:
    """Simplified experiment tracking backed by MLflow.

    Parameters
    ----------
    tracking_uri : str
        MLflow tracking server URI (e.g. ``"http://localhost:5000"``).
        Ignored in mock mode.

    Notes
    -----
    When MLflow is not installed the client stores experiment metadata
    in plain Python dictionaries.  This allows service code to develop
    and test without a running MLflow server.
    """

    def __init__(self, tracking_uri: str = "http://localhost:5000") -> None:
        self.tracking_uri = tracking_uri
        self._client: Any = None
        self._use_mock = True

        # Mock storage
        self._mock_experiments: Dict[str, Dict[str, Any]] = {}
        self._mock_runs: Dict[str, Dict[str, Any]] = {}

        if _HAS_MLFLOW:
            try:
                mlflow.set_tracking_uri(tracking_uri)
                self._client = _MlflowClient(tracking_uri=tracking_uri)
                self._use_mock = False
                logger.info(
                    "ExperimentClient connected to MLflow at %s", tracking_uri
                )
            except Exception as exc:
                logger.warning(
                    "MLflow connection failed (%s) — running in mock mode", exc
                )
        else:
            logger.warning(
                "mlflow package not installed — ExperimentClient running in mock mode"
            )

    # ── Experiment management ──

    def create_experiment(
        self,
        name: str,
        description: str = "",
    ) -> str:
        """Create a new experiment.

        Parameters
        ----------
        name : str
            Human-readable experiment name.
        description : str
            Optional description of the experiment's purpose.

        Returns
        -------
        str
            Unique experiment identifier.
        """
        if not self._use_mock:
            try:
                # MLflow returns existing id if name already exists
                experiment_id = self._client.create_experiment(
                    name, tags={"description": description}
                )
                logger.info(
                    "Created experiment '%s' (id=%s)", name, experiment_id
                )
                return str(experiment_id)
            except Exception as exc:
                logger.warning(
                    "MLflow create_experiment failed (%s) — using mock", exc
                )

        # Mock fallback
        experiment_id = str(uuid.uuid4().hex[:12])
        self._mock_experiments[experiment_id] = {
            "experiment_id": experiment_id,
            "name": name,
            "description": description,
            "created_at": time.time(),
        }
        logger.info(
            "Mock created experiment '%s' (id=%s)", name, experiment_id
        )
        return experiment_id

    # ── Run lifecycle ──

    def start_run(
        self,
        experiment_id: str,
        run_name: str = "",
    ) -> str:
        """Start a new experiment run.

        Parameters
        ----------
        experiment_id : str
            Experiment to associate the run with.
        run_name : str
            Optional human-readable run name.

        Returns
        -------
        str
            Unique run identifier.
        """
        if not self._use_mock:
            try:
                run = self._client.create_run(
                    experiment_id,
                    run_name=run_name or None,
                )
                run_id = run.info.run_id
                logger.info(
                    "Started run '%s' (id=%s) in experiment %s",
                    run_name,
                    run_id,
                    experiment_id,
                )
                return run_id
            except Exception as exc:
                logger.warning(
                    "MLflow start_run failed (%s) — using mock", exc
                )

        # Mock fallback
        run_id = str(uuid.uuid4().hex[:16])
        self._mock_runs[run_id] = {
            "run_id": run_id,
            "experiment_id": experiment_id,
            "run_name": run_name,
            "status": "RUNNING",
            "start_time": time.time(),
            "end_time": None,
            "params": {},
            "metrics": {},
            "artifacts": {},
        }
        logger.info(
            "Mock started run '%s' (id=%s) in experiment %s",
            run_name,
            run_id,
            experiment_id,
        )
        return run_id

    def log_params(
        self,
        run_id: str,
        params_dict: Dict[str, Any],
    ) -> None:
        """Log one or more parameters to a run.

        Parameters
        ----------
        run_id : str
            Run identifier.
        params_dict : dict
            Mapping of parameter name to value.  Values are stringified
            before logging.
        """
        if not self._use_mock:
            try:
                for key, value in params_dict.items():
                    self._client.log_param(run_id, key, str(value))
                logger.debug(
                    "Logged %d params to run %s", len(params_dict), run_id
                )
                return
            except Exception as exc:
                logger.warning(
                    "MLflow log_params failed (%s) — using mock", exc
                )

        # Mock fallback
        if run_id in self._mock_runs:
            self._mock_runs[run_id]["params"].update(
                {k: str(v) for k, v in params_dict.items()}
            )
        logger.debug("Mock logged %d params to run %s", len(params_dict), run_id)

    def log_metrics(
        self,
        run_id: str,
        metrics_dict: Dict[str, float],
        step: Optional[int] = None,
    ) -> None:
        """Log one or more metrics to a run.

        Parameters
        ----------
        run_id : str
            Run identifier.
        metrics_dict : dict
            Mapping of metric name to numeric value.
        step : int or None
            Optional step number for tracking metric history.
        """
        if not self._use_mock:
            try:
                for key, value in metrics_dict.items():
                    self._client.log_metric(
                        run_id, key, value, step=step or 0
                    )
                logger.debug(
                    "Logged %d metrics to run %s (step=%s)",
                    len(metrics_dict),
                    run_id,
                    step,
                )
                return
            except Exception as exc:
                logger.warning(
                    "MLflow log_metrics failed (%s) — using mock", exc
                )

        # Mock fallback
        if run_id in self._mock_runs:
            run = self._mock_runs[run_id]
            for key, value in metrics_dict.items():
                if key not in run["metrics"]:
                    run["metrics"][key] = []
                run["metrics"][key].append({
                    "value": value,
                    "step": step,
                    "timestamp": time.time(),
                })
        logger.debug(
            "Mock logged %d metrics to run %s (step=%s)",
            len(metrics_dict),
            run_id,
            step,
        )

    def log_artifact(
        self,
        run_id: str,
        artifact_path: str,
        content: str,
    ) -> None:
        """Log a text artifact to a run.

        Parameters
        ----------
        run_id : str
            Run identifier.
        artifact_path : str
            Path under the run's artifact directory (e.g. ``"model/config.json"``).
        content : str
            Text content of the artifact.
        """
        if not self._use_mock:
            try:
                import tempfile
                import os

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=os.path.basename(artifact_path),
                    delete=False,
                ) as f:
                    f.write(content)
                    tmp_path = f.name
                try:
                    self._client.log_artifact(run_id, tmp_path, artifact_path)
                finally:
                    os.unlink(tmp_path)
                logger.debug(
                    "Logged artifact '%s' to run %s", artifact_path, run_id
                )
                return
            except Exception as exc:
                logger.warning(
                    "MLflow log_artifact failed (%s) — using mock", exc
                )

        # Mock fallback
        if run_id in self._mock_runs:
            self._mock_runs[run_id]["artifacts"][artifact_path] = content
        logger.debug(
            "Mock logged artifact '%s' to run %s", artifact_path, run_id
        )

    def end_run(
        self,
        run_id: str,
        status: str = "FINISHED",
    ) -> None:
        """End an experiment run.

        Parameters
        ----------
        run_id : str
            Run identifier.
        status : str
            Terminal status.  One of ``"FINISHED"``, ``"FAILED"``,
            ``"KILLED"`` (default ``"FINISHED"``).
        """
        if not self._use_mock:
            try:
                self._client.set_terminated(run_id, status=status)
                logger.info("Ended run %s with status %s", run_id, status)
                return
            except Exception as exc:
                logger.warning(
                    "MLflow end_run failed (%s) — using mock", exc
                )

        # Mock fallback
        if run_id in self._mock_runs:
            self._mock_runs[run_id]["status"] = status
            self._mock_runs[run_id]["end_time"] = time.time()
        logger.info("Mock ended run %s with status %s", run_id, status)

    # ── Query ──

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata and results for a specific run.

        Parameters
        ----------
        run_id : str
            Run identifier.

        Returns
        -------
        dict or None
            Run metadata including params, metrics, status, and timing.
            ``None`` if the run is not found.
        """
        if not self._use_mock:
            try:
                run = self._client.get_run(run_id)
                info = run.info
                data = run.data
                # Flatten metric history to latest values
                metrics = {k: v for k, v in data.metrics.items()}
                return {
                    "run_id": info.run_id,
                    "experiment_id": info.experiment_id,
                    "run_name": info.run_name or "",
                    "status": info.status,
                    "start_time": info.start_time,
                    "end_time": info.end_time,
                    "params": dict(data.params),
                    "metrics": metrics,
                }
            except Exception as exc:
                logger.warning("MLflow get_run failed (%s) — using mock", exc)

        # Mock fallback
        run_data = self._mock_runs.get(run_id)
        if run_data is None:
            return None
        # Flatten metric history to latest value
        flat_metrics = {}
        for key, history in run_data.get("metrics", {}).items():
            if history:
                flat_metrics[key] = history[-1]["value"]
        return {
            "run_id": run_data["run_id"],
            "experiment_id": run_data["experiment_id"],
            "run_name": run_data["run_name"],
            "status": run_data["status"],
            "start_time": run_data["start_time"],
            "end_time": run_data["end_time"],
            "params": dict(run_data.get("params", {})),
            "metrics": flat_metrics,
        }

    def list_runs(self, experiment_id: str) -> List[Dict[str, Any]]:
        """List all runs for an experiment.

        Parameters
        ----------
        experiment_id : str
            Experiment identifier.

        Returns
        -------
        list[dict]
            List of run metadata dicts, ordered by start time descending.
        """
        if not self._use_mock:
            try:
                runs = self._client.search_runs(
                    experiment_ids=[experiment_id],
                    order_by=["start_time DESC"],
                )
                result = []
                for run in runs:
                    info = run.info
                    data = run.data
                    result.append({
                        "run_id": info.run_id,
                        "run_name": info.run_name or "",
                        "status": info.status,
                        "start_time": info.start_time,
                        "end_time": info.end_time,
                        "params": dict(data.params),
                        "metrics": {k: v for k, v in data.metrics.items()},
                    })
                return result
            except Exception as exc:
                logger.warning(
                    "MLflow list_runs failed (%s) — using mock", exc
                )

        # Mock fallback
        result: List[Dict[str, Any]] = []
        for run_data in self._mock_runs.values():
            if run_data["experiment_id"] == experiment_id:
                flat_metrics = {}
                for key, history in run_data.get("metrics", {}).items():
                    if history:
                        flat_metrics[key] = history[-1]["value"]
                result.append({
                    "run_id": run_data["run_id"],
                    "run_name": run_data["run_name"],
                    "status": run_data["status"],
                    "start_time": run_data["start_time"],
                    "end_time": run_data["end_time"],
                    "params": dict(run_data.get("params", {})),
                    "metrics": flat_metrics,
                })
        # Sort by start_time descending
        result.sort(key=lambda r: r.get("start_time", 0), reverse=True)
        return result
