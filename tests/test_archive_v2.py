import pytest
pytest.importorskip("modal")
from compute_forecast.archive_v2 import validate_public
def test_bundle_refuses_private_checkpoint_paths_and_credentials():
    for value in ({"state_path":"private"},{"nested":{"api_key":"credential"}},{"value":"tinker://private/sampler_weights/state"}):
        with pytest.raises(ValueError):validate_public(value)
def test_derived_metrics_and_public_checkpoint_identifiers_remain_publishable():
    validate_public({"seed":17,"checkpoint_id":"a"*20,"pinball":.01,"traces":[{"cache_hit":True,"config_id":"last_value"}]})
