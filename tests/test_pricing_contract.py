"""Numerical and publication invariants for the pricing interface."""
import math
import pytest
from compute_forecast.pricing_contract import scenario_path,build
@pytest.mark.parametrize("rate,months,expected",[(-.35,36,27.4625),(-.15,24,72.25),(.05,36,115.7625),(-.4,36,21.6)])
def test_published_annual_assumptions_have_correct_compounded_endpoints(rate,months,expected):
    path=scenario_path(rate,months)
    assert path[0]=={"month":0,"value":100}
    assert math.isclose(path[-1]["value"],expected,rel_tol=1e-12)
@pytest.mark.parametrize("rate,months,start",[(float("nan"),12,100),(-1,24,100),(.05,13,100),(.05,36,0),(float("inf"),12,100)])
def test_invalid_scenarios_are_rejected(rate,months,start):
    with pytest.raises(ValueError):scenario_path(rate,months,start)
def test_forecast_bytes_cannot_be_replaced():
    metadata={"dataset_sha256":"f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c","history_publication_permitted":False}
    with pytest.raises(ValueError,match="Frozen CSV hash mismatch"):build(metadata,b"changed",{},"a"*40)
def test_unapproved_historical_publication_is_rejected_before_forecast_parsing():
    metadata={"dataset_sha256":"f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c","history_publication_permitted":True}
    with pytest.raises(ValueError,match="publication boundary"):build(metadata,b"",{},"a"*40)
