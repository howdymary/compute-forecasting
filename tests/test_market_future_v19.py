from copy import deepcopy
import pytest
from compute_forecast.market_future_v19 import weekly_index,snapshots,score
from compute_forecast.probability_v18 import digest
from pathlib import Path
import json
P=json.loads(Path("configs/market-state-v19-prospective.json").read_text())
def test_separate_registered_schedule():
    assert weekly_index("2026-12-06",P) is None
    assert weekly_index("2026-12-20",P)==0
    assert weekly_index("2027-04-04",P)==15
    assert weekly_index("2027-04-11",P) is None
def test_late_capture_cannot_be_origin_input():
    x={"status":"captured","eligible_for_origin":True,"observed_day":"2026-12-20","retrieved_at":"2026-12-21T00:00:01+00:00"}
    assert not snapshots([x],"2026-12-20T23:59:59+00:00",P)
def test_first_vintage_not_later_revision():
    a={"status":"captured","eligible_for_origin":True,"observed_day":"2026-12-20","retrieved_at":"2026-12-20T17:40:00+00:00","value":1}
    b={**a,"retrieved_at":"2026-12-20T18:40:00+00:00","value":2}
    assert snapshots([b,a],"2026-12-20T23:59:59+00:00",P)["2026-12-20"]["value"]==1
def test_same_day_collection_required():
    a={"status":"captured","eligible_for_origin":True,"observed_day":"2026-12-19","retrieved_at":"2026-12-20T17:40:00+00:00"}
    assert not snapshots([a],"2026-12-20T23:59:59+00:00",P)
