"""
Weather Impact Modeling — How weather affects ride demand.

WHY THIS MATTERS:
Weather is one of the strongest external drivers of ride demand. Rain
increases demand (people avoid walking), extreme heat or cold increases
demand, and storms can both increase demand and reduce supply (fewer
drivers). Production systems integrate real-time weather data to adjust
demand forecasts.

Key concepts:
  - WeatherCondition: categorical weather state.
  - WeatherFeatures: numerical weather attributes.
  - WeatherImpactModel: maps weather conditions to demand multipliers.
  - Seasonal decomposition: separate a time series into trend, seasonal,
    and residual components using moving averages.
"""

from enum import Enum


class WeatherCondition(Enum):
    """Categorical weather states affecting ride demand.

    Each condition has a different impact on demand. Rain and snow
    significantly increase demand, while storms may reduce it due to
    safety concerns.
    """
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    SNOW = "snow"
    STORM = "storm"
    HEAT = "heat"
    FOG = "fog"


class WeatherFeatures:
    """Numerical weather attributes for a location and time.

    These features can be used as inputs to ML models. The to_vector()
    method converts them to a list suitable for model input.
    """

    def __init__(
        self,
        condition: WeatherCondition,
        temperature: float,
        humidity: float,
        wind_speed: float,
        precipitation: float,
    ):
        self.condition = condition
        self.temperature = temperature
        self.humidity = humidity
        self.wind_speed = wind_speed
        self.precipitation = precipitation

    def to_vector(self) -> list[float]:
        """Convert to a numeric feature vector.

        Encodes the condition as its index in the enum (0-7), plus the
        four continuous features. This is a simple encoding — production
        systems use one-hot encoding for the condition.
        """
        condition_values = list(WeatherCondition)
        condition_idx = condition_values.index(self.condition)
        return [
            float(condition_idx),
            self.temperature,
            self.humidity,
            self.wind_speed,
            self.precipitation,
        ]


class WeatherImpactModel:
    """Maps weather conditions to demand impact coefficients.

    The impact coefficient is a multiplier applied to base demand:
      - 1.0 = no change
      - 1.3 = 30% increase in demand
      - 0.7 = 30% decrease in demand

    These coefficients are calibrated from historical data in production.
    """

    # Default impact coefficients calibrated from typical ride-hailing data
    _DEFAULT_IMPACTS = {
        WeatherCondition.CLEAR: 1.0,
        WeatherCondition.CLOUDY: 1.05,
        WeatherCondition.RAIN: 1.3,
        WeatherCondition.HEAVY_RAIN: 1.5,
        WeatherCondition.SNOW: 1.4,
        WeatherCondition.STORM: 0.7,
        WeatherCondition.HEAT: 1.2,
        WeatherCondition.FOG: 1.1,
    }

    def __init__(self, custom_impacts: dict = None):
        self._impacts = dict(self._DEFAULT_IMPACTS)
        if custom_impacts:
            self._impacts.update(custom_impacts)

    def get_impact(self, condition: WeatherCondition) -> float:
        """Return the demand impact coefficient for a weather condition."""
        return self._impacts.get(condition, 1.0)

    def apply_weather(self, base_demand: float, weather: WeatherFeatures) -> float:
        """Adjust base demand by the weather impact coefficient.

        Returns base_demand * impact_coefficient. For example, if base
        demand is 100 and it's raining (impact 1.3), returns 130.
        """
        impact = self.get_impact(weather.condition)
        return base_demand * impact

    def seasonal_decomposition(
        self, daily_demands: list[float], period: int
    ) -> dict:
        """Decompose a daily demand series into trend, seasonal, and residual.

        Uses a centered moving average to extract the trend, then
        computes seasonal as the average deviation from trend for each
        position in the period, and residual as the remainder.

        Args:
            daily_demands: list of daily demand values.
            period: the seasonal period (e.g., 7 for weekly).

        Returns:
            {"trend": list, "seasonal": list, "residual": list}
            Trend values at the edges (where the window doesn't fit) are None.
        """
        n = len(daily_demands)
        if n < period:
            raise ValueError(f"Need at least {period} data points, got {n}")

        # Step 1: Centered moving average for trend
        half = period // 2
        trend = [None] * n
        for i in range(half, n - half):
            window = daily_demands[i - half: i + half + 1]
            if period % 2 == 0:
                # For even periods, average period+1 elements but weight first/last by 0.5
                window = daily_demands[i - half: i + half + 1]
                if len(window) == period + 1:
                    trend[i] = (0.5 * window[0] + sum(window[1:-1]) + 0.5 * window[-1]) / period
                else:
                    trend[i] = sum(window) / len(window)
            else:
                trend[i] = sum(window) / len(window)

        # Step 2: Detrended series
        detrended = [None] * n
        for i in range(n):
            if trend[i] is not None:
                detrended[i] = daily_demands[i] - trend[i]

        # Step 3: Seasonal component — average detrended values for each position in period
        seasonal_avgs = []
        for pos in range(period):
            vals = [detrended[i] for i in range(pos, n, period) if detrended[i] is not None]
            seasonal_avgs.append(sum(vals) / len(vals) if vals else 0.0)

        seasonal = [seasonal_avgs[i % period] for i in range(n)]

        # Step 4: Residual = original - trend - seasonal
        residual = [None] * n
        for i in range(n):
            if trend[i] is not None:
                residual[i] = daily_demands[i] - trend[i] - seasonal[i]

        return {"trend": trend, "seasonal": seasonal, "residual": residual}
