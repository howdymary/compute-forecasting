"""Publication privacy and official per-cell aggregation contracts."""
import pytest
pytest.importorskip("modal")
from compute_forecast.experimental_v2 import sanitize,aggregate_grid
from compute_forecast.campaign_v2 import protocol
def test_private_checkpoint_identifiers_cannot_be_published():
    with pytest.raises(ValueError):sanitize({"checkpoints":["tinker://private/weights/model"]})
def test_derived_metric_pooling_uses_cells_not_mean_of_series():
    cases=[{"series_id":"A","horizon_days":h,"loss":.02,"baseline_loss":.04,"covered":h!=7,"width":.1} for h in (1,3,7)]
    grid={"registry":[{"id":"reference","family":"reference"}],"origins":[{"origin":protocol()["evaluation_origins"][0],"status":"completed","methods":[{"config_id":"reference","cases":cases,"fallbacks":{},"quantile_order_repairs":0}]}]}
    row=aggregate_grid(grid)["rows"][0]
    assert row["pinball"]==pytest.approx(.02) and row["skill"]==pytest.approx(.5)
    assert row["coverage"]==pytest.approx(2/3) and set(row["by_horizon"])=={"1","3","7"}
def test_experimental_page_has_no_write_endpoint_or_recording():
    from compute_forecast.experimental_ui_v2 import HTML
    assert HTML.count("<script>")==1 and HTML.count("</script>")==1
    assert "fetch('/api/experimental'" in HTML
    assert "MediaRecorder" not in HTML and "method:'POST'" not in HTML
