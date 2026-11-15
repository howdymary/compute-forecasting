import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import pytest,numpy as np
import constructions as c
def test_target_injective():
    for p in c.structured()+c.random_programs():
        pts=c.support(p["expr"])
        assert len({x-y for x,y in pts})==49
def test_expression_boundaries():
    for expr in [["div","d",0],["mod",1,0],["open","d"],["mul",32,["mul",32,["mul",32,32]]]]:
        with pytest.raises(ValueError):c.support(expr)
def test_free_energy_gradient():
    pts=[[0,0],[1,0],[0,1]];p=np.array([.2,.3,.5]);ids=c.maps(pts)
    h,g=c.hs(p,ids);nu=np.array([.4,.5,.4,.3]);gp=g[0]-nu@g[1:]
    for i in range(3):
        z=p.copy();z[i]+=1e-7;hh,_=c.hs(z,ids)
        assert abs(((hh[0]-nu@hh[1:])-(h[0]-nu@h[1:]))/1e-7-gp[i])<1e-5
def test_general_bank_lp_and_exact_mass():
    law=c.rational_law([[0,0],[1,0]],np.array([.2,.8]))
    cert,stats=c.compose([law,law,law])
    from fractions import Fraction
    assert all(sum(Fraction(a,b) for a,b in l["weights"])==1 for l in cert["laws"])
    assert all(n>0 for n in cert["counts"])

def test_entropy_floor_resolves_known_collapse():
    from nondegenerate import optimize
    # All five projections are injective: F=(1-sum(nu))*H(p)=-0.6H(p).
    # Under H>=1, the constrained maximum is -0.6, unlike point-mass F=0.
    pts=[[2*d,d] for d in range(-2,3)]
    r=optimize(pts,[.4,.5,.4,.3],101,seconds=3)
    assert r["numerical_entropy_feasible"] and r["nondegenerate"]
    assert abs(r["free_energy"]+.6)<1e-5
    assert r["cpu_seconds"]>0
