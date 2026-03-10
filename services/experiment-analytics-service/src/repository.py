"""
In-memory experiment analytics repository with pre-seeded data.
"""

import uuid
import math
from datetime import datetime, timezone

from models import ExperimentAnalysis, SegmentAnalysis, AnalysisReport


class ExperimentAnalyticsRepository:
    """In-memory store for experiment analyses and reports."""

    def __init__(self, seed: bool = False):
        self.analyses: list[ExperimentAnalysis] = []
        self.reports: list[AnalysisReport] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        analyses = [
            ExperimentAnalysis("analysis-001", "exp-001", "conversion_rate", 0.12, 0.15, 0.003, True, 0.25, 5000, now),
            ExperimentAnalysis("analysis-002", "exp-001", "avg_ride_time", 22.5, 20.1, 0.01, True, -0.18, 5000, now),
            ExperimentAnalysis("analysis-003", "exp-002", "revenue_per_user", 45.0, 47.2, 0.04, True, 0.11, 3000, now),
            ExperimentAnalysis("analysis-004", "exp-002", "churn_rate", 0.08, 0.075, 0.15, False, -0.06, 3000, now),
            ExperimentAnalysis("analysis-005", "exp-003", "app_load_time", 2.1, 2.05, 0.42, False, -0.02, 8000, now),
            ExperimentAnalysis("analysis-006", "exp-003", "bounce_rate", 0.35, 0.33, 0.08, False, -0.06, 8000, now),
        ]
        self.analyses.extend(analyses)

        reports = [
            AnalysisReport("report-001", "exp-001", [
                {"metric": "conversion_rate", "significant": True, "effect_size": 0.25},
                {"metric": "avg_ride_time", "significant": True, "effect_size": -0.18},
            ], [
                {"segment": "new_users", "lift": 0.30, "significant": True},
                {"segment": "returning_users", "lift": 0.12, "significant": False},
            ], "Roll out to all users. Significant improvement in conversion rate.", now),
            AnalysisReport("report-002", "exp-002", [
                {"metric": "revenue_per_user", "significant": True, "effect_size": 0.11},
                {"metric": "churn_rate", "significant": False, "effect_size": -0.06},
            ], [
                {"segment": "premium_users", "lift": 0.15, "significant": True},
            ], "Continue experiment. Revenue improvement is promising but churn needs monitoring.", now),
            AnalysisReport("report-003", "exp-003", [
                {"metric": "app_load_time", "significant": False, "effect_size": -0.02},
                {"metric": "bounce_rate", "significant": False, "effect_size": -0.06},
            ], [], "No significant results. Consider increasing sample size or running longer.", now),
        ]
        self.reports.extend(reports)

    # ── Analysis ──

    def analyze_experiment(self, data: dict) -> ExperimentAnalysis:
        analysis_id = f"analysis-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        control = data["control_data"]
        variant = data["variant_data"]

        control_mean = sum(control) / len(control) if control else 0
        variant_mean = sum(variant) / len(variant) if variant else 0
        sample_size = len(control) + len(variant)

        # Simple z-test approximation
        control_var = sum((x - control_mean) ** 2 for x in control) / len(control) if len(control) > 1 else 1
        variant_var = sum((x - variant_mean) ** 2 for x in variant) / len(variant) if len(variant) > 1 else 1

        pooled_se = math.sqrt(control_var / len(control) + variant_var / len(variant)) if control and variant else 1
        z_score = abs(variant_mean - control_mean) / pooled_se if pooled_se > 0 else 0

        # Approximate p-value from z-score
        p_value = max(0.001, min(1.0, math.exp(-0.5 * z_score * z_score)))
        significant = p_value < 0.05

        # Effect size (Cohen's d approximation)
        pooled_std = math.sqrt((control_var + variant_var) / 2) if control_var + variant_var > 0 else 1
        effect_size = (variant_mean - control_mean) / pooled_std if pooled_std > 0 else 0

        analysis = ExperimentAnalysis(
            id=analysis_id,
            experiment_id=data["experiment_id"],
            metric_name=data["metric_name"],
            control_mean=round(control_mean, 4),
            variant_mean=round(variant_mean, 4),
            p_value=round(p_value, 4),
            significant=significant,
            effect_size=round(effect_size, 4),
            sample_size=sample_size,
            created_at=now,
        )
        self.analyses.append(analysis)
        return analysis

    def segment_analysis(self, data: dict) -> list[dict]:
        segments_result = []
        for seg_name, seg_data in data["segments"].items():
            control_mean = seg_data.get("control_mean", 0)
            variant_mean = seg_data.get("variant_mean", 0)
            lift = (variant_mean - control_mean) / control_mean if control_mean > 0 else 0
            significant = abs(lift) > 0.1
            seg = SegmentAnalysis(seg_name, control_mean, variant_mean, round(lift, 4), significant)
            segments_result.append(seg.to_dict())
        return segments_result

    # ── List / Get ──

    def list_analyses(self, experiment_id: str | None = None) -> list[ExperimentAnalysis]:
        result = list(self.analyses)
        if experiment_id:
            result = [a for a in result if a.experiment_id == experiment_id]
        return result

    def get_analysis(self, analysis_id: str) -> ExperimentAnalysis | None:
        for a in self.analyses:
            if a.id == analysis_id:
                return a
        return None

    def list_reports(self) -> list[AnalysisReport]:
        return list(self.reports)

    def get_report(self, report_id: str) -> AnalysisReport | None:
        for r in self.reports:
            if r.id == report_id:
                return r
        return None

    # ── Stats ──

    def get_stats(self) -> dict:
        significant_count = sum(1 for a in self.analyses if a.significant)
        total_effect = sum(abs(a.effect_size) for a in self.analyses)
        avg_effect = total_effect / len(self.analyses) if self.analyses else 0.0
        return {
            "total_analyses": len(self.analyses),
            "significant_count": significant_count,
            "avg_effect_size": round(avg_effect, 4),
        }


REPO_CLASS = ExperimentAnalyticsRepository
repo = ExperimentAnalyticsRepository(seed=True)
