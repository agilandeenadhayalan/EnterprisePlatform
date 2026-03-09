"""
Request Batching for Model Inference
======================================

When serving ML models in production, individual requests arrive
continuously. Processing them one-at-a-time is inefficient because:

1. **GPU utilization**: GPUs are designed for parallel computation.
   A single inference uses <1% of GPU capacity. Batching fills the
   GPU, getting 10-100x more throughput.

2. **Overhead amortization**: Loading model weights, allocating memory,
   and framework overhead is paid once per batch, not once per request.

3. **Latency tradeoff**: Batching adds a small delay (waiting for the
   batch to fill), but the per-request inference time drops because
   the batch is processed in parallel.

The RequestBatcher collects individual requests and flushes them as a
batch when either:
- max_batch_size requests have accumulated, OR
- max_wait_ms milliseconds have elapsed since the first request

This ensures both high throughput (large batches) and bounded latency
(requests never wait too long).
"""

from __future__ import annotations


class RequestBatcher:
    """Collects individual inference requests and groups them into micro-batches.

    Usage:
        batcher = RequestBatcher(max_batch_size=32, max_wait_ms=50.0)

        # Add requests as they arrive
        batcher.add_request("req_1", {"distance": 5.2}, timestamp=1000.0)
        batcher.add_request("req_2", {"distance": 3.1}, timestamp=1000.02)

        # Check if we should flush (batch full or timeout)
        if batcher.should_flush(current_time=1000.06):
            batch = batcher.flush()
            # Send batch to model for inference
    """

    def __init__(
        self,
        max_batch_size: int = 32,
        max_wait_ms: float = 50.0,
    ) -> None:
        """Initialize the request batcher.

        Args:
            max_batch_size: Maximum requests per batch before flushing.
            max_wait_ms: Maximum milliseconds to wait before flushing.
        """
        if max_batch_size < 1:
            raise ValueError("max_batch_size must be >= 1")
        if max_wait_ms <= 0:
            raise ValueError("max_wait_ms must be positive")

        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms

        self._pending: list[dict] = []
        self._first_request_time: float | None = None

        # Statistics
        self._total_batches: int = 0
        self._total_requests: int = 0
        self._total_wait_ms: float = 0.0

    def add_request(
        self,
        request_id: str,
        features: dict,
        timestamp: float,
    ) -> None:
        """Add an inference request to the pending batch.

        Args:
            request_id: Unique identifier for this request.
            features: Input features for the model.
            timestamp: When the request arrived (unix timestamp in seconds).
        """
        if self._first_request_time is None:
            self._first_request_time = timestamp

        self._pending.append({
            "request_id": request_id,
            "features": features,
            "timestamp": timestamp,
        })

    def should_flush(self, current_time: float) -> bool:
        """Check if the batch should be flushed.

        Returns True if:
        - The batch has reached max_batch_size, OR
        - max_wait_ms has elapsed since the first request in the batch.

        Args:
            current_time: Current unix timestamp in seconds.
        """
        if not self._pending:
            return False

        # Batch is full
        if len(self._pending) >= self.max_batch_size:
            return True

        # Timeout elapsed
        if self._first_request_time is not None:
            elapsed_ms = (current_time - self._first_request_time) * 1000
            if elapsed_ms >= self.max_wait_ms:
                return True

        return False

    def flush(self) -> list[dict]:
        """Flush the pending requests as a batch.

        Returns:
            List of request dicts that were in the batch.
            Returns empty list if no pending requests.
        """
        if not self._pending:
            return []

        batch = list(self._pending)
        batch_size = len(batch)

        # Update statistics
        self._total_batches += 1
        self._total_requests += batch_size

        if self._first_request_time is not None and batch:
            last_time = batch[-1]["timestamp"]
            wait_ms = (last_time - self._first_request_time) * 1000
            self._total_wait_ms += max(0.0, wait_ms)

        # Clear pending
        self._pending = []
        self._first_request_time = None

        return batch

    def pending_count(self) -> int:
        """Return the number of requests waiting in the batch."""
        return len(self._pending)

    def stats(self) -> dict:
        """Return batching statistics.

        Returns:
            Dict with batch_count, total_requests, avg_batch_size, avg_wait_ms.
        """
        return {
            "batch_count": self._total_batches,
            "total_requests": self._total_requests,
            "avg_batch_size": (
                self._total_requests / self._total_batches
                if self._total_batches > 0
                else 0.0
            ),
            "avg_wait_ms": (
                self._total_wait_ms / self._total_batches
                if self._total_batches > 0
                else 0.0
            ),
        }
