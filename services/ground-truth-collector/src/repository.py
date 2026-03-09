"""
In-memory ground truth collector repository with pre-seeded data.
"""

import random
import uuid
from models import GroundTruthLabel, Prediction, PredictionGroundTruthPair, LabelCoverage


class GroundTruthRepository:
    """In-memory store for predictions, labels, and joins."""

    def __init__(self, seed: bool = False):
        self.predictions: list[Prediction] = []
        self.labels: list[GroundTruthLabel] = []
        self.pairs: list[PredictionGroundTruthPair] = []
        if seed:
            self._seed()

    def _seed(self):
        rng = random.Random(42)
        model_names = ["fare_predictor", "eta_predictor", "demand_predictor"]
        days = ["2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06",
                "2026-03-07", "2026-03-08", "2026-03-09"]

        # 50 predictions per model = 150 total
        for model in model_names:
            for i in range(50):
                pred_id = f"{model}-pred-{i:03d}"
                day = days[i % len(days)]
                hour = rng.randint(6, 22)
                if model == "fare_predictor":
                    predicted = round(rng.gauss(15.0, 5.0), 2)
                elif model == "eta_predictor":
                    predicted = round(rng.gauss(12.0, 3.0), 2)
                else:
                    predicted = round(rng.gauss(50.0, 15.0), 2)

                self.predictions.append(Prediction(
                    prediction_id=pred_id,
                    model_name=model,
                    predicted_value=predicted,
                    timestamp=f"{day}T{hour:02d}:00:00Z",
                ))

        # ~70% of predictions get ground truth labels
        for pred in self.predictions:
            if rng.random() < 0.70:
                noise = rng.gauss(0, 1.5)
                actual = round(pred.predicted_value + noise, 2)
                delay = rng.randint(600, 7200)
                self.labels.append(GroundTruthLabel(
                    prediction_id=pred.prediction_id,
                    model_name=pred.model_name,
                    actual_value=actual,
                    label_timestamp=pred.timestamp,
                    delay_seconds=float(delay),
                ))

        # Pre-compute joins
        self._compute_joins()

    def _compute_joins(self):
        """Join predictions with labels."""
        self.pairs.clear()
        label_map = {l.prediction_id: l for l in self.labels}
        for pred in self.predictions:
            if pred.prediction_id in label_map:
                label = label_map[pred.prediction_id]
                error = round(abs(pred.predicted_value - label.actual_value), 4)
                self.pairs.append(PredictionGroundTruthPair(
                    prediction_id=pred.prediction_id,
                    predicted_value=pred.predicted_value,
                    actual_value=label.actual_value,
                    error=error,
                    model_name=pred.model_name,
                ))

    # ── Labels ──

    def submit_labels(self, label_items: list[dict]) -> int:
        count = 0
        for item in label_items:
            label = GroundTruthLabel(
                prediction_id=item["prediction_id"],
                model_name=item["model_name"],
                actual_value=item["actual_value"],
            )
            self.labels.append(label)
            count += 1
        return count

    def list_labels(self, model_name: str | None = None, limit: int = 50) -> list[GroundTruthLabel]:
        results = self.labels
        if model_name:
            results = [l for l in results if l.model_name == model_name]
        return results[:limit]

    # ── Join ──

    def join_predictions(self, model_name: str) -> list[PredictionGroundTruthPair]:
        self._compute_joins()
        return [p for p in self.pairs if p.model_name == model_name]

    # ── Coverage ──

    def get_coverage(self) -> list[LabelCoverage]:
        model_names = sorted({p.model_name for p in self.predictions})
        result = []
        for model in model_names:
            total = sum(1 for p in self.predictions if p.model_name == model)
            labeled_ids = {l.prediction_id for l in self.labels if l.model_name == model}
            pred_ids = {p.prediction_id for p in self.predictions if p.model_name == model}
            labeled = len(labeled_ids & pred_ids)
            pct = round(labeled / total * 100, 1) if total > 0 else 0.0
            result.append(LabelCoverage(
                model_name=model,
                total_predictions=total,
                labeled_predictions=labeled,
                coverage_pct=pct,
            ))
        return result

    # ── Performance over time ──

    def get_performance(self) -> list[dict]:
        self._compute_joins()
        model_names = sorted({p.model_name for p in self.pairs})
        result = []
        for model in model_names:
            model_pairs = [p for p in self.pairs if p.model_name == model]
            if not model_pairs:
                continue
            overall_mae = round(sum(p.error for p in model_pairs) / len(model_pairs), 4)

            # Bucket by prediction timestamp day
            buckets: dict[str, list[float]] = {}
            pred_map = {p.prediction_id: p for p in self.predictions}
            for pair in model_pairs:
                pred = pred_map.get(pair.prediction_id)
                if pred:
                    day = pred.timestamp[:10]
                    buckets.setdefault(day, []).append(pair.error)

            bucket_list = []
            for day in sorted(buckets.keys()):
                errs = buckets[day]
                bucket_list.append({
                    "bucket": day,
                    "mae": round(sum(errs) / len(errs), 4),
                    "count": len(errs),
                })

            result.append({
                "model_name": model,
                "overall_mae": overall_mae,
                "buckets": bucket_list,
            })
        return result


REPO_CLASS = GroundTruthRepository
repo = GroundTruthRepository(seed=True)
