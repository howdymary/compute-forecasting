"""Independent exhaustive assignments test fixed constants and larger-code eligibility."""
import json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ortools.sat.python import cp_model
from phase3.fresh_cp_model import add_closed_overlap_cuts
from phase3.core_hulls import add_known_goal_exclusions
tested=0
for fixed in [set(),{0}]:
 for mask in range(128):
  if not fixed<={i for i in range(7) if mask&(1<<i)}:continue
  m=cp_model.CpModel();xs={i:m.new_bool_var("x"+str(i)) for i in range(7) if i not in fixed};total=sum(xs.values())+len(fixed);m.add(total>=4);m.add(total<=6)
  add_known_goal_exclusions(m,xs,fixed,[list(range(5))],target=5);add_closed_overlap_cuts(m,xs,fixed,[{"words":[4,5,6],"limit":2}],baseline=4)
  for i,x in xs.items():m.add(x==int(bool(mask&(1<<i))))
  B={i for i in range(7) if mask&(1<<i)};expected=fixed<=B and 4<=len(B)<=6 and B!=set(range(5)) and (len(B)<=4 or len(B&{4,5,6})<=2)
  s=cp_model.CpSolver();s.parameters.num_search_workers=1;st=s.solve(m);actual=st in [cp_model.OPTIMAL,cp_model.FEASIBLE];assert actual==expected,(fixed,mask,expected,st);tested+=1
out=ROOT/"artifacts/phase3/fresh_cp_001";out.mkdir(parents=True,exist_ok=True);(out/"model_logic_tests.json").write_text(json.dumps({"passed":True,"assignments":tested,"includes_larger_supersets_of_excluded_known_code":True,"scope":"Abstract Boolean fixtures, not binary-code witnesses."},indent=2));print("FRESH_CP_LOGIC_TESTS",tested,flush=True)
