"""Transparent conditional rental cashflows and income-based residual scenarios."""
import math
def calculate(anchor,annual_change,months=36,utilization=.6,realization=.85,fees=.1,active_w=700,idle_w=100,host_w=100,pue=1.2,electricity=.12,other_opex=20,discount=.12,life=48,haircut=.7):
    values=locals().copy()
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values.values()):raise ValueError("Finite numeric assumptions required")
    if anchor<=0 or not -1<annual_change<=1 or months not in (24,36) or not 36<=life<=120 or not 0<=utilization<=1 or not 0<=realization<=1 or not 0<=fees<1 or not 0<=haircut<=1 or not 0<=discount<=1 or not 0<=idle_w<=active_w<=3000 or host_w<0 or not 1<=pue<=3 or not 0<=electricity<=2 or other_opex<0:raise ValueError("Assumptions outside supported bounds")
    hours=8760/12
    kw=(idle_w+utilization*(active_w-idle_w)+host_w)*pue/1000
    energy=kw*hours*electricity
    points=[]
    for m in range(0,life+1):
        rate=anchor*(1+annual_change)**(m/12)
        gross=rate*hours*utilization*realization
        net=gross*(1-fees)-energy-other_opex
        denom=rate*hours*realization*(1-fees)-(active_w-idle_w)*pue/1000*hours*electricity
        threshold=((idle_w+host_w)*pue/1000*hours*electricity+other_opex)/denom if denom>0 else None
        if threshold is not None and threshold>1:threshold=None
        points.append({"month":m,"rental_rate":rate,"rental_index":100*rate/anchor,"gross_revenue":gross,"energy_cost":energy,"other_opex":other_opex,"net_cashflow":net,"operating_break_even_utilization":threshold})
    pv=sum(p["net_cashflow"]/(1+discount)**(p["month"]/12) for p in points if 1<=p["month"]<=months)
    residual=haircut*max(0,sum(p["net_cashflow"]/(1+discount)**((p["month"]-months)/12) for p in points if months<p["month"]<=life))
    discounted_residual=residual/(1+discount)**(months/12)
    return {"kind":"conditional_income_scenario_not_observed_resale","assumptions":values,"points":points[:months+1],"present_value_operating_cashflows":pv,"income_based_residual_proxy":residual,"discounted_residual_proxy":discounted_residual,"combined_present_value_proxy":pv+discounted_residual,"double_counting_rule":"Operating PV ends at the horizon; terminal proxy includes only the remaining months to assumed useful life.","hours_per_month":hours,"limitations":["Advertised rate is not realized revenue","Per-GPU allocated power and all operating assumptions are user-adjustable; not a whole-server appraisal","Income-based residual is a scenario proxy, not an observed transaction or calibrated resale forecast"]}
