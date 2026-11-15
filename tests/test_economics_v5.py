"""Synthetic cashflow contract tests; these are not market observations."""
import pytest
from compute_forecast.economics_v5 import calculate
def test_constant_cashflow_has_closed_form_and_no_double_counting():
    r=calculate(1,0,24,utilization=1,realization=1,fees=0,active_w=0,idle_w=0,host_w=0,pue=1,electricity=0,other_opex=0,discount=0,life=48,haircut=1)
    assert r["present_value_operating_cashflows"]==pytest.approx(8760*2)
    assert r["income_based_residual_proxy"]==pytest.approx(8760*2)
    assert r["combined_present_value_proxy"]==pytest.approx(8760*4)
def test_zero_utilization_does_not_create_income_or_negative_resale():
    r=calculate(1,-.15,36,utilization=0)
    assert all(p["gross_revenue"]==0 for p in r["points"])
    assert r["present_value_operating_cashflows"]<0 and r["income_based_residual_proxy"]==0
def test_discounting_and_remaining_life_are_separate():
    a=calculate(2,-.15,24,discount=0)
    b=calculate(2,-.15,24,discount=.2)
    assert b["combined_present_value_proxy"]<a["combined_present_value_proxy"]
    assert b["discounted_residual_proxy"]==pytest.approx(b["income_based_residual_proxy"]/1.2**2)
def test_compounding_and_input_domain():
    assert calculate(2,-.25,24)["points"][-1]["rental_rate"]==pytest.approx(2*.75**2)
    with pytest.raises(ValueError):calculate(1,-1)
    with pytest.raises(ValueError):calculate(1,0,utilization=1.1)
