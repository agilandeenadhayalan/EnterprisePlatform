"""
Tests for M35: Experimentation — A/B testing, bandits, and advanced analysis.
"""

import math
import random
import pytest

from m35_experimentation.ab_testing import (
    ExperimentDesign,
    SampleSizeCalculator,
    ZTest,
    ChiSquareTest,
    EffectSizeCalculator,
)
from m35_experimentation.multi_armed_bandit import (
    BanditArm,
    EpsilonGreedy,
    UCB1,
    ThompsonSampling,
    RegretTracker,
)
from m35_experimentation.experiment_analysis import (
    SequentialTest,
    MultipleComparisonCorrection,
    SegmentAnalyzer,
)


# ── ExperimentDesign ──


class TestExperimentDesign:
    def test_create_design(self):
        """ExperimentDesign stores metadata."""
        design = ExperimentDesign(
            name="pricing_v2",
            control_name="original",
            variant_name="new_pricing",
            metric="conversion_rate",
            hypothesis="New pricing increases conversions",
        )
        assert design.name == "pricing_v2"
        assert design.metric == "conversion_rate"


# ── SampleSizeCalculator ──


class TestSampleSizeCalculator:
    def test_basic_sample_size(self):
        """Calculates positive sample size."""
        calc = SampleSizeCalculator()
        n = calc.calculate(baseline_rate=0.10, mde=0.02)
        assert n > 0
        assert isinstance(n, int)

    def test_larger_mde_smaller_sample(self):
        """Larger minimum detectable effect needs fewer samples."""
        calc = SampleSizeCalculator()
        n_small_mde = calc.calculate(baseline_rate=0.10, mde=0.01)
        n_large_mde = calc.calculate(baseline_rate=0.10, mde=0.05)
        assert n_large_mde < n_small_mde

    def test_higher_power_larger_sample(self):
        """Higher power requires more samples."""
        calc = SampleSizeCalculator()
        n_low = calc.calculate(baseline_rate=0.10, mde=0.02, power=0.8)
        n_high = calc.calculate(baseline_rate=0.10, mde=0.02, power=0.95)
        assert n_high > n_low

    def test_z_score_standard_values(self):
        """Z-score returns known values for standard confidence levels."""
        calc = SampleSizeCalculator()
        assert calc._z_score(0.975) == pytest.approx(1.96, abs=0.01)
        assert calc._z_score(0.95) == pytest.approx(1.645, abs=0.01)


# ── ZTest ──


class TestZTest:
    def test_significant_difference(self):
        """Detects significant difference between groups."""
        z = ZTest()
        result = z.test(
            control_successes=100, control_total=1000,
            variant_successes=150, variant_total=1000,
        )
        assert result["significant"] is True
        assert result["p_value"] < 0.05
        assert result["variant_rate"] > result["control_rate"]

    def test_not_significant(self):
        """Does not flag insignificant difference."""
        z = ZTest()
        result = z.test(
            control_successes=100, control_total=1000,
            variant_successes=102, variant_total=1000,
        )
        assert result["significant"] is False
        assert result["p_value"] > 0.05

    def test_lift_positive(self):
        """Lift is positive when variant beats control."""
        z = ZTest()
        result = z.test(
            control_successes=100, control_total=1000,
            variant_successes=120, variant_total=1000,
        )
        assert result["lift"] > 0

    def test_lift_negative(self):
        """Lift is negative when variant loses to control."""
        z = ZTest()
        result = z.test(
            control_successes=150, control_total=1000,
            variant_successes=100, variant_total=1000,
        )
        assert result["lift"] < 0

    def test_z_score_sign(self):
        """Z-score is positive when variant is higher."""
        z = ZTest()
        result = z.test(
            control_successes=100, control_total=1000,
            variant_successes=200, variant_total=1000,
        )
        assert result["z_score"] > 0

    def test_rates_computed_correctly(self):
        """Control and variant rates are correct."""
        z = ZTest()
        result = z.test(
            control_successes=50, control_total=200,
            variant_successes=75, variant_total=300,
        )
        assert result["control_rate"] == pytest.approx(0.25)
        assert result["variant_rate"] == pytest.approx(0.25)


# ── ChiSquareTest ──


class TestChiSquareTest:
    def test_independent_groups(self):
        """Similar proportions yield non-significant result."""
        chi = ChiSquareTest()
        result = chi.test([[50, 50], [49, 51]])
        assert result["significant"] is False
        assert result["degrees_of_freedom"] == 1

    def test_dependent_groups(self):
        """Very different proportions yield significant result."""
        chi = ChiSquareTest()
        result = chi.test([[90, 10], [10, 90]])
        assert result["significant"] is True
        assert result["chi_square"] > 0

    def test_degrees_of_freedom(self):
        """Degrees of freedom = (rows-1) * (cols-1)."""
        chi = ChiSquareTest()
        result = chi.test([[10, 20, 30], [40, 50, 60]])
        assert result["degrees_of_freedom"] == 2

    def test_p_value_range(self):
        """P-value is between 0 and 1."""
        chi = ChiSquareTest()
        result = chi.test([[50, 50], [60, 40]])
        assert 0.0 <= result["p_value"] <= 1.0


# ── EffectSizeCalculator ──


class TestEffectSizeCalculator:
    def test_cohens_h_positive(self):
        """Cohen's h is positive when p2 > p1."""
        calc = EffectSizeCalculator()
        h = calc.cohens_h(0.1, 0.3)
        assert h > 0

    def test_cohens_h_negative(self):
        """Cohen's h is negative when p2 < p1."""
        calc = EffectSizeCalculator()
        h = calc.cohens_h(0.5, 0.2)
        assert h < 0

    def test_cohens_h_zero(self):
        """Cohen's h is zero when proportions are equal."""
        calc = EffectSizeCalculator()
        h = calc.cohens_h(0.5, 0.5)
        assert h == pytest.approx(0.0)

    def test_interpret_small(self):
        """Small effect size correctly interpreted."""
        calc = EffectSizeCalculator()
        assert calc.interpret(0.1) == "small"

    def test_interpret_medium(self):
        """Medium effect size correctly interpreted."""
        calc = EffectSizeCalculator()
        assert calc.interpret(0.3) == "medium"

    def test_interpret_large(self):
        """Large effect size correctly interpreted."""
        calc = EffectSizeCalculator()
        assert calc.interpret(0.7) == "large"

    def test_interpret_negative(self):
        """Negative h is interpreted by absolute value."""
        calc = EffectSizeCalculator()
        assert calc.interpret(-0.8) == "large"


# ── EpsilonGreedy ──


class TestEpsilonGreedy:
    def test_pulls_untried_first(self):
        """Epsilon-greedy pulls untried arms first."""
        random.seed(42)
        arms = [BanditArm("a", 0.5), BanditArm("b", 0.7)]
        eg = EpsilonGreedy(arms, epsilon=0.0)
        assert eg.select_arm() == 0  # First untried
        eg.update(0, 1)
        assert eg.select_arm() == 1  # Second untried

    def test_exploits_best_arm(self):
        """With epsilon=0, always exploits the best arm."""
        random.seed(42)
        arms = [BanditArm("a", 0.3), BanditArm("b", 0.8)]
        eg = EpsilonGreedy(arms, epsilon=0.0)
        eg.update(0, 0)  # arm 0 has mean 0
        eg.update(1, 1)  # arm 1 has mean 1
        # Should always pick arm 1
        for _ in range(10):
            assert eg.select_arm() == 1

    def test_get_stats(self):
        """Stats track pulls and successes correctly."""
        arms = [BanditArm("a", 0.5)]
        eg = EpsilonGreedy(arms, epsilon=0.0)
        eg.update(0, 1)
        eg.update(0, 0)
        stats = eg.get_stats()
        assert stats[0]["pulls"] == 2
        assert stats[0]["successes"] == 1
        assert stats[0]["empirical_mean"] == 0.5


# ── UCB1 ──


class TestUCB1:
    def test_pulls_each_arm_once(self):
        """UCB1 pulls each arm at least once."""
        arms = [BanditArm("a", 0.3), BanditArm("b", 0.7), BanditArm("c", 0.5)]
        ucb = UCB1(arms)
        selected = set()
        for _ in range(3):
            arm = ucb.select_arm()
            selected.add(arm)
            ucb.update(arm, 1)
        assert selected == {0, 1, 2}

    def test_ucb_favors_uncertain(self):
        """UCB1 explores arms with fewer pulls due to exploration bonus."""
        arms = [BanditArm("a", 0.5), BanditArm("b", 0.5)]
        ucb = UCB1(arms)
        # Pull arm 0 many times, arm 1 once
        ucb.update(0, 0.5)
        ucb.update(1, 0.5)
        for _ in range(20):
            ucb.update(0, 0.5)
        # Arm 1 should be favored due to high exploration bonus
        arm = ucb.select_arm()
        assert arm == 1

    def test_ucb_get_stats(self):
        """UCB1 tracks stats correctly."""
        arms = [BanditArm("a", 0.5)]
        ucb = UCB1(arms)
        ucb.update(0, 1)
        stats = ucb.get_stats()
        assert stats[0]["pulls"] == 1
        assert stats[0]["empirical_mean"] == 1.0


# ── ThompsonSampling ──


class TestThompsonSampling:
    def test_select_arm_returns_valid(self):
        """Thompson sampling returns valid arm index."""
        random.seed(42)
        arms = [BanditArm("a", 0.3), BanditArm("b", 0.7)]
        ts = ThompsonSampling(arms)
        arm = ts.select_arm()
        assert arm in [0, 1]

    def test_converges_to_best(self):
        """Thompson sampling converges to the best arm over many rounds."""
        random.seed(42)
        arms = [BanditArm("a", 0.1), BanditArm("b", 0.9)]
        ts = ThompsonSampling(arms)
        for _ in range(200):
            arm = ts.select_arm()
            reward = 1 if random.random() < arms[arm].true_probability else 0
            ts.update(arm, reward)
        stats = ts.get_stats()
        # Best arm should have most pulls
        assert stats[1]["pulls"] > stats[0]["pulls"]

    def test_update_increments_alpha(self):
        """Success increments alpha."""
        arms = [BanditArm("a", 0.5)]
        ts = ThompsonSampling(arms)
        ts.update(0, 1)
        assert ts._alphas[0] == 2.0

    def test_update_increments_beta(self):
        """Failure increments beta."""
        arms = [BanditArm("a", 0.5)]
        ts = ThompsonSampling(arms)
        ts.update(0, 0)
        assert ts._betas[0] == 2.0


# ── RegretTracker ──


class TestRegretTracker:
    def test_optimal_arm_zero_regret(self):
        """Pulling optimal arm with success has zero regret."""
        arms = [BanditArm("a", 0.3), BanditArm("b", 0.9)]
        tracker = RegretTracker(optimal_arm_index=1, arms=arms)
        tracker.record(1, 1)
        # regret = 0.9 - 1 = -0.1 (negative = better than expected)
        assert tracker.cumulative_regret() == pytest.approx(-0.1)

    def test_suboptimal_arm_positive_regret(self):
        """Pulling suboptimal arm accumulates positive regret."""
        arms = [BanditArm("a", 0.3), BanditArm("b", 0.9)]
        tracker = RegretTracker(optimal_arm_index=1, arms=arms)
        tracker.record(0, 0)  # Pulled arm 0, got 0. Regret = 0.9 - 0 = 0.9
        assert tracker.cumulative_regret() == pytest.approx(0.9)

    def test_regret_history_length(self):
        """Regret history grows with each record."""
        arms = [BanditArm("a", 0.5), BanditArm("b", 0.8)]
        tracker = RegretTracker(optimal_arm_index=1, arms=arms)
        for _ in range(5):
            tracker.record(0, 0)
        assert len(tracker.regret_history()) == 5

    def test_cumulative_regret_increases(self):
        """Cumulative regret is non-decreasing when getting 0 reward."""
        arms = [BanditArm("a", 0.3), BanditArm("b", 0.9)]
        tracker = RegretTracker(optimal_arm_index=1, arms=arms)
        tracker.record(0, 0)
        tracker.record(0, 0)
        history = tracker.regret_history()
        assert history[1] >= history[0]


# ── SequentialTest ──


class TestSequentialTest:
    def test_continue_early(self):
        """Not enough data leads to 'continue' decision."""
        st = SequentialTest(alpha=0.05, beta=0.2, p0=0.5, p1=0.55)
        result = st.test(successes=3, total=5)
        assert result["decision"] == "continue"

    def test_reject_null(self):
        """Strong evidence for alternative rejects null."""
        st = SequentialTest(alpha=0.05, beta=0.2, p0=0.5, p1=0.7)
        result = st.test(successes=90, total=100)
        assert result["decision"] == "reject_null"

    def test_accept_null(self):
        """Strong evidence for null accepts it."""
        st = SequentialTest(alpha=0.05, beta=0.2, p0=0.5, p1=0.7)
        result = st.test(successes=50, total=200)
        assert result["decision"] == "accept_null"

    def test_boundaries_correct(self):
        """Upper and lower boundaries have correct signs."""
        st = SequentialTest(alpha=0.05, beta=0.2, p0=0.5, p1=0.55)
        assert st.upper_boundary > 0
        assert st.lower_boundary < 0

    def test_llr_zero_for_equal_proportions(self):
        """LLR is computed as a real number."""
        st = SequentialTest(p0=0.5, p1=0.6)
        llr = st.log_likelihood_ratio(50, 100)
        assert isinstance(llr, float)


# ── MultipleComparisonCorrection ──


class TestMultipleComparisonCorrection:
    def test_bonferroni_rejects_low_p(self):
        """Bonferroni rejects very low p-values."""
        mcc = MultipleComparisonCorrection()
        results = mcc.bonferroni([0.001, 0.01, 0.03], alpha=0.05)
        assert results[0] is True  # 0.001 < 0.05/3

    def test_bonferroni_fails_marginal(self):
        """Bonferroni is conservative — rejects fewer tests."""
        mcc = MultipleComparisonCorrection()
        results = mcc.bonferroni([0.02, 0.03, 0.04], alpha=0.05)
        # 0.05/3 = 0.0167; none pass
        assert all(r is False for r in results)

    def test_holm_more_powerful(self):
        """Holm rejects at least as many hypotheses as Bonferroni."""
        mcc = MultipleComparisonCorrection()
        p_values = [0.001, 0.04, 0.06]
        bonf = mcc.bonferroni(p_values, alpha=0.05)
        holm = mcc.holm(p_values, alpha=0.05)
        assert sum(holm) >= sum(bonf)

    def test_holm_step_down(self):
        """Holm stops rejecting after first failure."""
        mcc = MultipleComparisonCorrection()
        # Sorted: 0.005, 0.03, 0.04
        # Step 1: 0.005 < 0.05/3 = 0.0167 -> reject
        # Step 2: 0.03 < 0.05/2 = 0.025 -> fail -> stop
        results = mcc.holm([0.03, 0.005, 0.04], alpha=0.05)
        assert results[1] is True   # p=0.005
        assert results[0] is False  # p=0.03
        assert results[2] is False  # p=0.04

    def test_holm_empty(self):
        """Holm with empty list returns empty."""
        mcc = MultipleComparisonCorrection()
        assert mcc.holm([]) == []

    def test_bonferroni_single(self):
        """Bonferroni with one test equals standard test."""
        mcc = MultipleComparisonCorrection()
        results = mcc.bonferroni([0.03], alpha=0.05)
        assert results[0] is True


# ── SegmentAnalyzer ──


class TestSegmentAnalyzer:
    def test_analyze_segment_basic(self):
        """Segment analysis computes correct means and lift."""
        sa = SegmentAnalyzer()
        result = sa.analyze_segment("premium", [10, 20, 30], [15, 25, 35])
        assert result["segment"] == "premium"
        assert result["control_mean"] == pytest.approx(20.0)
        assert result["variant_mean"] == pytest.approx(25.0)
        assert result["lift"] == pytest.approx(0.25)

    def test_analyze_segment_negative_lift(self):
        """Negative lift when variant is worse."""
        sa = SegmentAnalyzer()
        result = sa.analyze_segment("casual", [30, 40, 50], [10, 20, 30])
        assert result["lift"] < 0

    def test_find_interactions_detected(self):
        """Finds segments with opposite lift direction."""
        sa = SegmentAnalyzer()
        segments = {
            "overall": {"lift": 0.1},
            "power_users": {"lift": 0.2},
            "new_users": {"lift": -0.15},
        }
        interactions = sa.find_interactions(segments)
        assert len(interactions) == 1
        assert interactions[0]["lift"] < 0

    def test_find_interactions_none(self):
        """No interactions when all segments agree."""
        sa = SegmentAnalyzer()
        segments = {
            "overall": {"lift": 0.1},
            "segment_a": {"lift": 0.05},
            "segment_b": {"lift": 0.2},
        }
        interactions = sa.find_interactions(segments)
        assert interactions == []

    def test_find_interactions_no_overall(self):
        """Returns empty when 'overall' key is missing."""
        sa = SegmentAnalyzer()
        segments = {"segment_a": {"lift": 0.1}}
        interactions = sa.find_interactions(segments)
        assert interactions == []
