"""Known exact-size no-goods must not exclude a larger superset or a different tie."""
import json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ortools.sat.python import cp_model
from phase3.core_hulls import add_known_goal_exclusions
rows=[]
for mask,feasible in [(15,False),(31,True),(23,True)]:
 m=cp_model.CpModel();xs={i:m.new_bool_var("x"+str(i)) for i in range(5)};add_known_goal_exclusions(m,xs,set(),[[0,1,2,3]],target=4)
 for i,x in xs.items():m.add(x==int(bool(mask&(1<<i))))
 s=cp_model.CpSolver();st=s.solve(m);actual=st in [cp_model.FEASIBLE,cp_model.OPTIMAL];assert actual==feasible
 rows.append({"mask":mask,"feasible":actual,"passed":True,"scope":"Abstract Boolean goal-filter fixture, not a binary deletion code."})
out=ROOT/"artifacts/phase3/core_hulls_001";out.mkdir(parents=True,exist_ok=True);(out/"goal_filter_tests.json").write_text(json.dumps(rows,indent=2));print("CORE_HULL_GOAL_TESTS",len(rows),flush=True)
