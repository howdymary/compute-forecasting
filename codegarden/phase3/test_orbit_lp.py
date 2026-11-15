"""Compare quotient and full LPs on small lengths, and check the group action literally."""
import importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence
from phase3.orbit_lp_model import quotient,lift_primal,reverse
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);rows=[]
for n in [4,6,8]:
 inc=Incidence(n);A,b,W,wi,ws,R,di,h=quotient(inc);q=linprog(-np.ones(len(W)),A_ub=A,b_ub=b,bounds=(0,None),method="highs",options={"time_limit":20});assert q.success
 fullrows=[];fullcols=[]
 for w in range(inc.N):
  for d in inc.desc[w]:fullrows.append(d);fullcols.append(w)
 F=csc_matrix((np.ones(len(fullrows)),(fullrows,fullcols)),shape=(inc.M,inc.N));p=linprog(-np.ones(inc.N),A_ub=F,b_ub=np.ones(inc.M),bounds=(0,None),method="highs",options={"time_limit":20});assert p.success and abs(q.fun-p.fun)<1e-7
 x=lift_primal(q.x,wi,ws);assert abs(float(x.sum())+q.fun)<1e-7 and max(F@x)<=1+1e-7
 for w in range(inc.N):
  word=format(w,"0%db"%n);ds=set(D.descendants(word));assert {int(s,2) for s in ds}==set(inc.desc[w])
  assert set(D.descendants(word[::-1]))=={s[::-1] for s in ds}
  complement=lambda s:"".join("1" if c=="0" else "0" for c in s)
  assert set(D.descendants(complement(word)))=={complement(s) for s in ds}
 rows.append({"length":n,"full_variables":inc.N,"quotient_variables":len(W),"full_fractional_optimum":-p.fun,"quotient_fractional_optimum":-q.fun,"all_literal_symmetries_checked":inc.N*2})
print(json.dumps({"passed":True,"full_vs_quotient":rows,"meaning":"Fractional objectives are not code cardinalities."}))
