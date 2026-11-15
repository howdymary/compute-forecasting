import copy,json,pathlib
import numpy as np
import pytest
from fractions import Fraction
import verify,verify_independent,search
ROOT=pathlib.Path(__file__).resolve().parent
def toy():
    return {"base":7,"counts":[1],"laws":[{"points":[[0,0],[1,1]],"weights":[[1,2],[1,2]]}],"claimed_lower_bound":[0,1]}
def test_reject_wrong_mass():
    c=toy();c["laws"][0]["weights"][0]=[1,3]
    with pytest.raises(ValueError):verify.validate(c)
    with pytest.raises(AssertionError):verify_independent.check(c)
def test_reject_duplicate():
    c=toy();c["laws"][0]["points"][1]=[0,0]
    with pytest.raises(ValueError):verify.validate(c)
    with pytest.raises(AssertionError):verify_independent.check(c)
def test_reject_unproved_base():
    c=toy();c["base"]=2
    with pytest.raises(ValueError):verify.validate(c)
    with pytest.raises(AssertionError):verify_independent.check(c)
def test_reject_boolean_count():
    c=toy();c["counts"]=[True]
    with pytest.raises(ValueError):verify.validate(c)
def test_target_collision_allowed_and_zero_entropy():
    c=toy();lo,hi,_=verify.measure(c)
    assert lo==0 and hi==0
    assert verify_independent.check(c)==(0,0)
def test_entropy_gradient():
    p=np.array([0.2,0.3,0.5]);m=search.maps([[0,0],[1,0],[0,1]])
    h,g=search.entropies(p,m)
    for i in range(3):
        pp=p.copy();pp[i]+=1e-7
        hh,_=search.entropies(pp,m)
        assert np.max(abs((hh-h)/1e-7-g[:,i]))<1e-5
def test_exact_logarithm_enclosures():
    lo,hi=verify_independent.logarithm(Fraction(1,2))
    l2,u2=verify_independent.logarithm(Fraction(2))
    assert lo==-u2 and hi==-l2 and hi>lo
    assert float(lo)<-0.69 and float(hi)>-0.70
def test_tensorisation_not_mixture():
    a={"points":[[0,0],[1,0]],"weights":[[1,2],[1,2]]}
    b={"points":[[0,0],[0,1]],"weights":[[1,2],[1,2]]}
    c={"base":7,"counts":[1,1],"laws":[a,b]}
    lo,hi,_=verify.measure(c)
    # H(X-Y)=2log2, max is 2log2, ratio=1.
    assert bool(lo<1.00000000000001) and bool(hi>0.99999999999999)
def test_rounding_exact():
    c=toy();r=search.certificate(c["laws"],[np.array([0.123,0.877])],[1])
    verify.validate(r)
