"""
A/B Test Statistics — sample sizing, z-tests, chi-square, effect sizes.

WHY THIS MATTERS:
Ride-sharing platforms constantly experiment: new pricing algorithms,
driver matching strategies, UI changes. Without proper statistical
tests, you can't tell if a change actually improved the metric or if
you're just seeing random noise. Getting this wrong means shipping
features that hurt users or missing features that would help.

Key concepts:
  - Sample size: how many observations you need to reliably detect an
    effect. Under-powering wastes the experiment; over-powering wastes
    time and traffic.
  - Z-test for proportions: is the difference in conversion rates
    between control and variant statistically significant?
  - Chi-square test: generalized independence test for contingency tables.
  - Cohen's h: standardized effect size for proportions — tells you
    whether a significant difference is practically meaningful.
"""

import math
from dataclasses import dataclass


@dataclass
class ExperimentDesign:
    """Setup for an A/B experiment.

    Attributes:
        name: experiment identifier
        control_name: name of the control group
        variant_name: name of the variant group
        metric: what you're measuring (e.g., "conversion_rate")
        hypothesis: what you expect to happen
    """
    name: str
    control_name: str
    variant_name: str
    metric: str
    hypothesis: str


class SampleSizeCalculator:
    """Calculate required sample size for A/B tests.

    Uses the formula for two-proportion z-test:
      n = 2 * ((z_alpha + z_beta) / mde)^2 * p * (1-p)

    where p = baseline_rate, mde = minimum detectable effect,
    z_alpha and z_beta come from the desired significance level
    and statistical power.
    """

    def _z_score(self, confidence: float) -> float:
        """Approximate z-score from confidence level.

        Uses a rational approximation of the inverse normal CDF.
        Good enough for common values (0.8, 0.9, 0.95, 0.99).
        """
        # Common lookup for standard values
        z_table = {
            0.80: 0.8416,
            0.85: 1.0364,
            0.90: 1.2816,
            0.95: 1.6449,
            0.975: 1.9600,
            0.99: 2.3263,
            0.995: 2.5758,
        }

        if confidence in z_table:
            return z_table[confidence]

        # Abramowitz and Stegun approximation for inverse normal
        # For one-tailed: use confidence directly
        # For two-tailed alpha: confidence = 1 - alpha/2
        p = confidence
        if p >= 1.0:
            return 3.5
        if p <= 0.0:
            return -3.5

        # Rational approximation
        if p < 0.5:
            p = 1 - p
            sign = -1
        else:
            sign = 1

        t = math.sqrt(-2 * math.log(1 - p))
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        z = t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t)
        return sign * z

    def calculate(
        self,
        baseline_rate: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.8,
    ) -> int:
        """Calculate required sample size per group.

        Args:
            baseline_rate: expected conversion rate for control (e.g., 0.10)
            mde: minimum detectable effect (absolute difference, e.g., 0.02)
            alpha: significance level (default 0.05 for 95% confidence)
            power: statistical power (default 0.8 = 80% chance of detecting
                   a real effect)

        Returns:
            Required sample size per group (rounded up).
        """
        z_alpha = self._z_score(1 - alpha / 2)  # two-tailed
        z_beta = self._z_score(power)

        p = baseline_rate
        n = 2 * ((z_alpha + z_beta) / mde) ** 2 * p * (1 - p)

        return math.ceil(n)


class ZTest:
    """Two-proportion z-test for A/B testing.

    Tests whether the conversion rates in two groups are significantly
    different. The pooled proportion is used under the null hypothesis
    that both groups have the same rate.
    """

    def test(
        self,
        control_successes: int,
        control_total: int,
        variant_successes: int,
        variant_total: int,
        alpha: float = 0.05,
    ) -> dict:
        """Run two-proportion z-test.

        Args:
            control_successes: number of successes in control
            control_total: total observations in control
            variant_successes: number of successes in variant
            variant_total: total observations in variant
            alpha: significance level (default 0.05)

        Returns:
            dict with z_score, p_value, significant, control_rate,
            variant_rate, lift
        """
        p1 = control_successes / control_total
        p2 = variant_successes / variant_total

        # Pooled proportion under H0
        p_pool = (control_successes + variant_successes) / (control_total + variant_total)
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / control_total + 1 / variant_total))

        if se == 0:
            z = 0.0
        else:
            z = (p2 - p1) / se

        # Two-tailed p-value using complementary error function
        p_value = math.erfc(abs(z) / math.sqrt(2))

        lift = (p2 - p1) / p1 if p1 > 0 else 0.0

        return {
            "z_score": z,
            "p_value": p_value,
            "significant": p_value < alpha,
            "control_rate": p1,
            "variant_rate": p2,
            "lift": lift,
        }


class ChiSquareTest:
    """Chi-square test of independence for contingency tables.

    Tests whether two categorical variables are independent. For A/B
    testing, this generalizes the z-test to multi-cell tables (e.g.,
    testing multiple variants simultaneously).
    """

    def test(self, observed: list[list[int]], alpha: float = 0.05) -> dict:
        """Run chi-square independence test on a 2D contingency table.

        Args:
            observed: 2D list of observed counts (e.g., [[a, b], [c, d]])
            alpha: significance level (default 0.05)

        Returns:
            dict with chi_square, p_value, significant, degrees_of_freedom
        """
        rows = len(observed)
        cols = len(observed[0])

        # Row and column totals
        row_totals = [sum(row) for row in observed]
        col_totals = [sum(observed[r][c] for r in range(rows)) for c in range(cols)]
        total = sum(row_totals)

        if total == 0:
            return {
                "chi_square": 0.0,
                "p_value": 1.0,
                "significant": False,
                "degrees_of_freedom": (rows - 1) * (cols - 1),
            }

        # Compute chi-square statistic
        chi_sq = 0.0
        for r in range(rows):
            for c in range(cols):
                expected = row_totals[r] * col_totals[c] / total
                if expected > 0:
                    chi_sq += (observed[r][c] - expected) ** 2 / expected

        df = (rows - 1) * (cols - 1)

        # Approximate p-value using chi-square survival function
        # For df=1, chi-square is approximately normal squared
        p_value = self._chi2_survival(chi_sq, df)

        return {
            "chi_square": chi_sq,
            "p_value": p_value,
            "significant": p_value < alpha,
            "degrees_of_freedom": df,
        }

    def _chi2_survival(self, x: float, df: int) -> float:
        """Approximate chi-square survival function P(X > x).

        Uses the regularized incomplete gamma function approximation.
        For df=1, this simplifies to erfc(sqrt(x/2)).
        For higher df, uses a Wilson-Hilferty normal approximation.
        """
        if x <= 0:
            return 1.0
        if df == 1:
            return math.erfc(math.sqrt(x / 2))
        if df == 2:
            return math.exp(-x / 2)

        # Wilson-Hilferty approximation
        z = ((x / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
        # Convert z to survival probability
        p = 0.5 * math.erfc(z / math.sqrt(2))
        return max(0.0, min(1.0, p))


class EffectSizeCalculator:
    """Cohen's h effect size for proportions.

    Statistical significance alone doesn't tell you if a difference
    matters in practice. Cohen's h quantifies the size of the effect
    so you can decide whether a 0.1% improvement is worth the
    engineering effort to ship.
    """

    def cohens_h(self, p1: float, p2: float) -> float:
        """Compute Cohen's h for two proportions.

        h = 2 * arcsin(sqrt(p2)) - 2 * arcsin(sqrt(p1))

        Positive h means p2 > p1 (variant beats control).
        """
        return 2 * math.asin(math.sqrt(p2)) - 2 * math.asin(math.sqrt(p1))

    def interpret(self, h: float) -> str:
        """Interpret Cohen's h effect size.

        |h| < 0.2  -> "small"
        |h| < 0.5  -> "medium"
        |h| >= 0.5 -> "large"
        """
        abs_h = abs(h)
        if abs_h < 0.2:
            return "small"
        elif abs_h < 0.5:
            return "medium"
        else:
            return "large"
