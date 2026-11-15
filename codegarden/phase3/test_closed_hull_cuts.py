"""Closed-family cuts preserve225-like hints and apply to every larger candidate."""
import json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ortools.sat.python import cp_model
from phase3.adaptive_hulls import attach_closed
rows=[]
for mask,feasible in [(7,True),(15,False),(27,True),(31,False)]:
 model=cp_model.CpModel();xs={i:model.new_bool_var("x"+str(i)) for i in range(5)};attach_closed(model,xs,set(),[{"id":"abstract_closed_family","fixed":[0,1,2]}],threshold=4)
 for i,x in xs.items():model.add(x==int(bool(mask&(1<<i))))
 solver=cp_model.CpSolver();status=solver.solve(model);actual=status in [cp_model.FEASIBLE,cp_model.OPTIMAL];assert actual==feasible
 rows.append({"mask":mask,"feasible":actual,"passed":True,"scope":"Abstract Boolean logic fixture, not a binary deletion-code construction."})
out=ROOT/"artifacts/phase3/adaptive_hulls_001";out.mkdir(parents=True,exist_ok=True);(out/"closed_cut_tests.json").write_text(json.dumps(rows,indent=2));print("CLOSED_HULL_CUT_TESTS",len(rows),flush=True)
