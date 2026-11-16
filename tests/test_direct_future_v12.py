from datetime import date,timedelta
import pytest
from compute_forecast.direct_future_v12 import asof,issuance_status,tasks_at,score
def proto():return {"study_id":"synthetic-direct-fixture","history_calendar_days":42,"min_price_days":20,"horizons":[1,3,7],"issuance_deadline_minutes_after_origin":30}
def test_late_or_early_forecast_cannot_be_eligible():
    p=proto()
    assert issuance_status("2026-11-22","2026-11-23T00:05:00Z",p)=="eligible"
    assert issuance_status("2026-11-22","2026-11-23T00:31:00Z",p)=="missed_issuance_deadline"
    assert issuance_status("2026-11-22","2026-11-22T23:00:00Z",p)=="before_origin_cutoff"
def test_first_vintage_and_cutoff_are_preserved():
    a={"eligible":True,"captured_at":"2026-11-22T18:00:00Z","prices":{"date":"2026-11-22","rows":[]}}
    revised={**a,"captured_at":"2026-11-22T20:00:00Z"}
    later={**a,"captured_at":"2026-11-23T18:00:00Z","prices":{"date":"2026-11-23","rows":[]}}
    assert asof([revised,later,a],"2026-11-22T23:59:59Z")==[a]
def test_truth_is_pending_without_observations():
    p=proto();c={"status":"issued","origin":"2026-11-22","issued_at":"2026-11-23T00:05:00Z","rows":[{"series_id":"synthetic-a100","target_date":"2026-11-23","horizon_days":1}]}
    r=score(c,[],"2026-11-24T00:00:00Z",p)
    assert r["status"]=="pending" and not r["cells"]
def test_no_future_quote_can_enter_model_task():
    p=proto();snapshots=[]
    for i in range(22):
        day=(date(2026,11,1)+timedelta(days=i)).isoformat()
        snapshots.append({"eligible":True,"captured_at":day+"T18:00:00Z","prices":{"date":day,"rows":[{"id":"synthetic","date":day,"value":2.0,"contract":{"gpu":"a100"},"family":"A100"}]}})
    tasks,failures=tasks_at(snapshots,"2026-11-22",p)
    assert not failures and len(tasks)==1 and max(r["date"] for r in tasks[0]["context"])=="2026-11-22"
