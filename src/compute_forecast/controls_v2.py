"""Additional adaptive control with complete categorical configuration metadata."""
from __future__ import annotations
import math
from .campaign_v2 import REGISTRY,BY_ID
from .policy_v2 import INITIAL,finish,summary
def configuration_vector(identifier):
    c=BY_ID[identifier]
    families=sorted({x["family"] for x in REGISTRY});aux=sorted({x.get("aux","none") for x in REGISTRY});spaces=sorted({x.get("space","none") for x in REGISTRY})
    references=["none","last_value","last_value_empirical","drift","seasonal_naive"]
    ref=identifier if c["family"]=="reference" else "none"
    return [float(c["family"]==x) for x in families]+[float(c.get("aux","none")==x) for x in aux]+[float(c.get("space","none")==x) for x in spaces]+[float(ref==x) for x in references]+[c.get("days",0)/56,math.log1p(c.get("alpha",0))/5,c.get("leaves",0)/7,c.get("weight",0),c.get("smoothing",0)]
def select_trials(task):
    import numpy as np
    from scipy.special import ndtr
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern
    candidates=[c["id"] for c in REGISTRY if c["id"] not in INITIAL];revealed=list(INITIAL)
    for _ in range(4):
        remaining=[c for c in candidates if c not in revealed]
        gp=GaussianProcessRegressor(kernel=Matern(length_scale=1.0,nu=2.5),alpha=1e-5,optimizer=None,normalize_y=True)
        y=np.array([task["validation"][c]["loss"]/task["scale"] for c in revealed])
        gp.fit([configuration_vector(c) for c in revealed],y)
        mu,std=gp.predict([configuration_vector(c) for c in remaining],return_std=True);std=np.maximum(std,1e-12)
        z=(y.min()-mu)/std;ei=(y.min()-mu)*ndtr(z)+std*np.exp(-z*z/2)/math.sqrt(2*math.pi)
        revealed.append(remaining[int(np.argmax(ei))])
    return revealed
def evaluate(tasks):
    report=summary("gp_complete_configuration_encoding",[finish(t,select_trials(t)) for t in tasks])
    report.update(encoding="One-hot family, auxiliary mode, target space and reference identity; normalized numeric parameters",feedback_cache_hit=True,new_numerical_execution=False,scope="Additional retrospective control; same kernel, acquisition, initial trials, candidate order and six-trial budget as the original GP control")
    return report
