"""
Model Warmup
=============

When a model is first loaded, the initial predictions are often slower
than subsequent ones because of:

1. **Lazy initialization**: Many frameworks defer memory allocation,
   kernel compilation (GPU), and graph optimization until the first
   forward pass.

2. **Cache cold start**: CPU caches, memory pages, and JIT-compiled
   code are not populated until they're first accessed.

3. **Resource allocation**: Thread pools, memory arenas, and device
   contexts may be created on first use.

The solution is "warmup" -- running a few dummy predictions during
service startup, BEFORE accepting real traffic. This ensures that
the first real request gets the same fast response time as all
subsequent requests.

Typical warmup process:
1. Load model from disk/storage.
2. Run 5-10 predictions with representative inputs.
3. Discard warmup results.
4. Mark model as "warm" and start accepting traffic.
"""

from __future__ import annotations

import time


class ModelWarmer:
    """Pre-loads models and runs warm-up predictions to avoid cold-start latency.

    Usage:
        warmer = ModelWarmer()
        warmer.register_model(
            "surge_v2",
            predict_fn=model.predict,
            warmup_inputs=[{"distance": 5.0}, {"distance": 10.0}],
        )
        stats = warmer.warmup("surge_v2")
        # -> {"avg_warmup_latency_ms": 12.5, "num_warmup_calls": 2, "name": "surge_v2"}

        if warmer.is_warm("surge_v2"):
            # Safe to serve traffic
            ...
    """

    def __init__(self) -> None:
        self._models: dict[str, dict] = {}
        self._warm_status: dict[str, bool] = {}

    def register_model(
        self,
        name: str,
        predict_fn,
        warmup_inputs: list[dict],
    ) -> None:
        """Register a model for warmup.

        Args:
            name: Unique name for this model.
            predict_fn: Callable that takes a dict of features and returns
                        a prediction. This is the model's inference function.
            warmup_inputs: List of representative input dicts to use for
                          warmup predictions. Should cover typical input
                          patterns (different feature ranges, edge cases).

        Raises:
            ValueError: If warmup_inputs is empty.
        """
        if not warmup_inputs:
            raise ValueError("warmup_inputs must not be empty")

        self._models[name] = {
            "predict_fn": predict_fn,
            "warmup_inputs": warmup_inputs,
        }
        self._warm_status[name] = False

    def warmup(self, name: str) -> dict:
        """Run warmup predictions for a specific model.

        Calls the model's predict_fn with each warmup input, measuring
        latency. Results are discarded -- only timing matters.

        Args:
            name: Name of the model to warm up.

        Returns:
            Dict with 'name', 'avg_warmup_latency_ms', 'num_warmup_calls',
            and 'total_warmup_ms'.

        Raises:
            KeyError: If no model with this name is registered.
        """
        if name not in self._models:
            raise KeyError(f"Model {name!r} not registered")

        model_info = self._models[name]
        predict_fn = model_info["predict_fn"]
        warmup_inputs = model_info["warmup_inputs"]

        latencies_ms = []
        for input_data in warmup_inputs:
            start = time.perf_counter()
            _ = predict_fn(input_data)  # Result is intentionally discarded
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)

        self._warm_status[name] = True

        total_ms = sum(latencies_ms)
        avg_ms = total_ms / len(latencies_ms)

        return {
            "name": name,
            "avg_warmup_latency_ms": avg_ms,
            "num_warmup_calls": len(latencies_ms),
            "total_warmup_ms": total_ms,
        }

    def warmup_all(self) -> dict:
        """Run warmup for all registered models.

        Returns:
            Dict mapping model name to warmup stats.
        """
        results = {}
        for name in self._models:
            results[name] = self.warmup(name)
        return results

    def is_warm(self, name: str) -> bool:
        """Check if a model has been warmed up.

        Args:
            name: Model name.

        Returns:
            True if warmup() has been called for this model.

        Raises:
            KeyError: If no model with this name is registered.
        """
        if name not in self._models:
            raise KeyError(f"Model {name!r} not registered")
        return self._warm_status.get(name, False)
