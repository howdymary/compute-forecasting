"""Real binary/driver serialization and zero-budget boundary, before long search."""
import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import canonical
out=ROOT/"artifacts/phase3/core5_repair_001";from phase3.core5_input import load_input
raw=load_input(out,0);plan=json.loads((out/"support_plan.json").read_text());expected=plan["partition_counts"][0]
r=json.loads(subprocess.run([str(ROOT/".build/core5_repair"),"0","0","1370001",str(out/"schema_checkpoint.txt")],input=raw,text=True,capture_output=True,check=True).stdout)
assert r["planned"]==expected and r["processed"]==0 and not r["all_planned_neighborhoods_processed"]
assert len(r["primary_status_codes"])==len(r["secondary_status_codes"])==r["processed"]
p=out/"schema_witness.txt";p.write_text(canonical(r["winner"]));v=verify(p);assert v["cardinality"]==226
(out/"schema_test.json").write_text(json.dumps({"passed":True,"expected_neighborhood_count":plan["supported_quintuples"],"case_count":16,"zero_budget_processed":0,"verification":v},indent=2));print("CORE5_SCHEMA_TEST passed",flush=True)
