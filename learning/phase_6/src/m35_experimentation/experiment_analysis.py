"""
Advanced Experiment Analysis — sequential testing, multiple comparisons, segments.

WHY THIS MATTERS:
Real experiments are messier than textbook A/B tests:
  - Sequential testing: you want to stop early if the result is
    clearly significant (or clearly not), saving time and traffic.
  - Multiple comparisons: testing 10 variants inflates your false
    positive rate unless you correct for it (Bonferroni, Holm).
  - Segment analysis: the overall result may hide that your change
    helps power users but hurts new users.

Key concepts:
  - SPRT (Sequential Probability Ratio Test): Wald's test that
    accumulates evidence as data arrives and makes accept/reject/
    continue decisions.
  - Bonferroni correction: divide alpha by the number of tests.
    Simple but conservative.
  - Holm step-down: more powerful than Bonferroni — tests p-values
    in order and stops rejecting when one fails.
  - Segment interactions: when the treatment effect direction differs
    across segments, the overall result is misleading (Simpson's paradox).
"""

import math


class SequentialTest:
    """Wald's Sequential Probability Ratio Test (SPRT).

    Instead of waiting for a fixed sample size, SPRT accumulates
    evidence after each observation and decides:
      - Reject H0 (the variant is different)
      - Accept H0 (no significant difference)
      - Continue (not enough evidence yet)

    Boundaries:
      Upper boundary = ln((1-beta)/alpha)   -> reject H0
      Lower boundary = ln(beta/(1-alpha))   -> accept H0
    """

    def __init__(
        self,
        alpha: float = 0.05,
        beta: float = 0.2,
        p0: float = 0.5,
        p1: float = 0.55,
    ):
        """Initialize SPRT.

        Args:
            alpha: Type I error rate (false positive)
            beta: Type II error rate (false negative)
            p0: null hypothesis proportion
            p1: alternative hypothesis proportion
        """
        self.alpha = alpha
        self.beta = beta
        self.p0 = p0
        self.p1 = p1
        self.upper_boundary = math.log((1 - beta) / alpha)
        self.lower_boundary = math.log(beta / (1 - alpha))

    def log_likelihood_ratio(self, successes: int, total: int) -> float:
        """Compute log-likelihood ratio for observed data.

        LLR = successes * log(p1/p0) + failures * log((1-p1)/(1-p0))
        """
        failures = total - successes

        if self.p0 <= 0 or self.p0 >= 1 or self.p1 <= 0 or self.p1 >= 1:
            return 0.0

        llr = 0.0
        if successes > 0:
            llr += successes * math.log(self.p1 / self.p0)
        if failures > 0:
            llr += failures * math.log((1 - self.p1) / (1 - self.p0))

        return llr

    def test(self, successes: int, total: int) -> dict:
        """Run sequential test on accumulated data.

        Returns:
            dict with decision ("accept_null", "reject_null", or "continue"),
            llr, upper_boundary, lower_boundary
        """
        llr = self.log_likelihood_ratio(successes, total)

        if llr >= self.upper_boundary:
            decision = "reject_null"
        elif llr <= self.lower_boundary:
            decision = "accept_null"
        else:
            decision = "continue"

        return {
            "decision": decision,
            "llr": llr,
            "upper_boundary": self.upper_boundary,
            "lower_boundary": self.lower_boundary,
        }


class MultipleComparisonCorrection:
    """Corrections for multiple hypothesis testing.

    When you test N hypotheses at alpha=0.05, you expect N*0.05 false
    positives by chance. These corrections control the family-wise
    error rate (FWER) — the probability of at least one false positive
    across all tests.
    """

    def bonferroni(self, p_values: list[float], alpha: float = 0.05) -> list[bool]:
        """Bonferroni correction: reject if p < alpha/n.

        Most conservative correction. Divides the significance level
        by the number of tests. Simple but can miss real effects when
        there are many tests.
        """
        n = len(p_values)
        adjusted_alpha = alpha / n if n > 0 else alpha
        return [p < adjusted_alpha for p in p_values]

    def holm(self, p_values: list[float], alpha: float = 0.05) -> list[bool]:
        """Holm step-down correction.

        More powerful than Bonferroni. Sort p-values from smallest to
        largest, then test sequentially: reject p_i if p_i < alpha/(n-i).
        Stop rejecting as soon as a test fails.

        Returns:
            List of bools in the ORIGINAL order of p_values.
        """
        n = len(p_values)
        if n == 0:
            return []

        # Sort by p-value, keeping track of original indices
        indexed = sorted(enumerate(p_values), key=lambda x: x[1])

        results = [False] * n
        for rank, (orig_idx, p) in enumerate(indexed):
            adjusted_alpha = alpha / (n - rank)
            if p < adjusted_alpha:
                results[orig_idx] = True
            else:
                # Stop rejecting — all remaining are also not rejected
                break

        return results


class SegmentAnalyzer:
    """Analyze experiment results by user segments.

    Overall results can mask heterogeneous treatment effects.
    A pricing change might increase revenue from business users but
    decrease it for casual users. Segment analysis reveals these
    interactions so you can make informed decisions.
    """

    def analyze_segment(
        self,
        segment_name: str,
        control_data: list,
        variant_data: list,
    ) -> dict:
        """Analyze experiment results for a single segment.

        Args:
            segment_name: name of the segment (e.g., "power_users")
            control_data: list of metric values for control group
            variant_data: list of metric values for variant group

        Returns:
            dict with segment, control_mean, variant_mean, lift, significant
        """
        control_mean = sum(control_data) / len(control_data) if control_data else 0.0
        variant_mean = sum(variant_data) / len(variant_data) if variant_data else 0.0

        lift = (variant_mean - control_mean) / control_mean if control_mean != 0 else 0.0

        # Simple significance check using z-test for means
        significant = False
        if control_data and variant_data and len(control_data) > 1 and len(variant_data) > 1:
            n1 = len(control_data)
            n2 = len(variant_data)
            var1 = sum((x - control_mean) ** 2 for x in control_data) / (n1 - 1)
            var2 = sum((x - variant_mean) ** 2 for x in variant_data) / (n2 - 1)
            se = math.sqrt(var1 / n1 + var2 / n2)
            if se > 0:
                z = abs(variant_mean - control_mean) / se
                p_value = math.erfc(z / math.sqrt(2))
                significant = p_value < 0.05

        return {
            "segment": segment_name,
            "control_mean": control_mean,
            "variant_mean": variant_mean,
            "lift": lift,
            "significant": significant,
        }

    def find_interactions(self, segments: dict[str, dict]) -> list[dict]:
        """Find segments where treatment effect direction differs from overall.

        An interaction exists when a segment's lift has a different sign
        than the overall lift, suggesting the treatment affects different
        segments differently (Simpson's paradox).

        Args:
            segments: dict mapping segment name to analyze_segment result.
                      Must include an "overall" key.

        Returns:
            List of segment result dicts where lift direction differs
            from overall.
        """
        if "overall" not in segments:
            return []

        overall_lift = segments["overall"]["lift"]
        interactions = []

        for name, result in segments.items():
            if name == "overall":
                continue
            segment_lift = result["lift"]
            # Interaction: different sign (one positive, one negative)
            if overall_lift * segment_lift < 0:
                interactions.append(result)

        return interactions
