import pytest
pytest.importorskip("modal")
np=pytest.importorskip("numpy")
from compute_forecast.matched_price_v2 import ridge_with_price_mask
def test_removed_price_values_cannot_change_a_prediction_but_missingness_is_retained():
    rows=np.array([[i%2,1,1,1,.8,.9,3,.5,*[float(i+j) for j in range(9)]] for i in range(30)],dtype=float)
    rows[::3,9]=np.nan
    query=rows[-1].copy();targets=np.arange(30,dtype=float)
    changed=rows.copy();changed[:,8:]*=100
    qchanged=query.copy();qchanged[8:]*=100
    a=ridge_with_price_mask(rows,targets,query,True);b=ridge_with_price_mask(changed,targets,qchanged,True)
    assert a==pytest.approx(b,abs=1e-12)
    assert ridge_with_price_mask(rows,targets,query,False)!=pytest.approx(a,abs=1e-6)
