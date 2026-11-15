"""Actual zero-budget CLI contract, including protected witness acceptance."""
import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import canonical
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=sorted(set.intersection(*(set(C) for C in info["codes"])));C=info["codes"][0];raw="226 "+" ".join(map(str,C))+"\n216 "+" ".join(map(str,core))+"\n";out=ROOT/"artifacts/phase3/compound_pivot_001";out.mkdir(parents=True,exist_ok=True)
r=json.loads(subprocess.run([str(ROOT/".build/compound_pivot"),"0","0","1410001",str(out/"schema_checkpoint.txt")],input=raw,text=True,capture_output=True,check=True).stdout);assert r["trials"]==r["processed"]==0 and r["new226_candidates"]==[]
p=out/"schema_witness.txt";p.write_text(canonical(r["winner"]));v=verify(p);assert v["cardinality"]==226
(out/"schema_test.json").write_text(json.dumps({"passed":True,"verification":v},indent=2));print("COMPOUND_SCHEMA_TEST passed",flush=True)
