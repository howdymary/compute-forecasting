"""Internal scoring helpers; official aggregation is deliberately not assumed."""
import math
from collections import defaultdict
from .contracts import Forecast


def pinball_loss(actual: float, predicted: float, quantile: float) -> float:
    if not 0 < quantile < 1:
        raise ValueError("quantile must lie strictly between zero and one")
    if not all(math.isfinite(x) for x in (actual, predicted, quantile)):
        raise ValueError("scoring requires finite values")
    error = actual - predicted
    return (quantile - float(error < 0)) * error


def diagnostic_skill(candidate_loss: float, baseline_loss: float) -> float | None:
    if not all(math.isfinite(x) and x >= 0 for x in (candidate_loss, baseline_loss)):
        raise ValueError("losses must be finite and nonnegative")
    if baseline_loss == 0:
        return None
    return 1 - candidate_loss / baseline_loss


def validate_forecast_groups(rows: list[Forecast]) -> None:
    groups = defaultdict(dict)
    for row in rows:
        key = (row.target_key, row.origin_ts, row.horizon_days, row.config_id, row.run_id)
        if row.quantile in groups[key]:
            raise ValueError("duplicate forecast cell")
        groups[key][row.quantile] = row.value
    for values in groups.values():
        if set(values) != {0.1, 0.5, 0.9}:
            raise ValueError("forecast group is missing quantiles")
        if not values[0.1] <= values[0.5] <= values[0.9]:
            raise ValueError("crossed quantiles")
