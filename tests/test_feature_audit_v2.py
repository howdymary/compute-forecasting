import pytest
pytest.importorskip("modal")
pytest.importorskip("numpy")
from compute_forecast.feature_audit_v2 import missing_counts
def test_auxiliary_imputation_is_distinguished_from_target_missingness():
    nan=float("nan");row=[1,nan,2,3,4,5,nan,1,2,3,4,5,6]
    counts=missing_counts([row,row],row,True)
    assert counts["missing_training_cells"]==4
    assert counts["missing_auxiliary_training_cells"]==2
    assert counts["entirely_missing_columns"]==2
