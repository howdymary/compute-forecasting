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

def test_old_evidence_is_archived_not_appended(tmp_path,monkeypatch):
    from providers import prepare_output
    monkeypatch.setenv("GITHUB_RUN_ID","isolated-check")
    (tmp_path/"trace.jsonl").write_text("prior-source\n")
    (tmp_path/".gitkeep").write_text("")
    prepare_output(tmp_path)
    assert not (tmp_path/"trace.jsonl").exists()
    assert (tmp_path/"previous-source/isolated-check/trace.jsonl").read_text()=="prior-source\n"
    assert (tmp_path/".gitkeep").exists()
def test_unknown_cost_stays_reserved_and_shared_workers_cannot_exceed_cap(tmp_path):
    from providers import Ledger,Disabled
    first=Ledger(tmp_path)
    second=Ledger(tmp_path)
    # Conservative historical past usage is 69; cap is 200.
    token=first.reserve("past",100,observed=1000)
    first.settle(token,None)
    with pytest.raises(Disabled):second.reserve("past",40,observed=1000)
    assert first.db.execute("select actual from reservations where id=?",(token,)).fetchone()[0] is None
def test_new_credits_do_not_increase_initial_allowance(tmp_path):
    from providers import Ledger,Disabled
    ledger=Ledger(tmp_path)
    with pytest.raises(Disabled):ledger.reserve("past",1000000,observed=1000000000)
