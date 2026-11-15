import math
import pytest
pytest.importorskip("modal")
from datetime import date,timedelta
from compute_forecast.price_free_v2 import availability_features
def test_price_free_predictors_cannot_read_price_levels():
    at=date(2026,7,24);a={at-timedelta(days=k):1+k for k in range(30)};b={k:v*100 for k,v in a.items()}
    panel={at:{"coverage":.8,"log_configs":4,"provider_hhi":.3,"log_index":99,"change_1":87}}
    x=availability_features(a,at,panel);y=availability_features(b,at,panel)
    assert x==y and x[-3:]==[.8,4,.3] and 99 not in x and 87 not in x
