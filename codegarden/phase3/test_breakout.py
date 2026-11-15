"""Check native incremental fields and energies against protected literal-string descendants."""
import collections,importlib.util,json,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity
check_integrity();spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);rng=random.Random(1270001);checks=0
for case in range(12):
 n=5 if case<4 else 6;C=rng.sample(range(1<<n),5+case%6);desc={w:{int(d,2) for d in D.descendants(format(w,"0%db"%n))} for w in range(1<<n)}
 rows=json.loads(subprocess.run([str(ROOT/".build/breakout"),"--trace",str(n),"40",str(1271001+case)],input=" ".join(map(str,C)),text=True,capture_output=True,check=True).stdout)
 for row in rows:
  occ=collections.Counter(d for w in row["words"] for d in desc[w]);weights=row["weights"]
  assert len(set(row["words"]))==len(C)
  assert row["energy"]==sum(v*(v-1)//2 for v in occ.values())
  assert row["weighted_energy"]==sum(weights[d]*v*(v-1)//2 for d,v in occ.items())
  for w in range(1<<n):
   assert row["field"][w]==sum(weights[d]*occ[d] for d in desc[w])
   assert row["selfweight"][w]==sum(weights[d] for d in desc[w])
  checks+=1
out=ROOT/"artifacts/phase3/breakout_001";out.mkdir(parents=True,exist_ok=True);(out/"tests.json").write_text(json.dumps({"random_move_states":checks,"independent_literal_string_checks":True,"seed":1270001},indent=2));print("BREAKOUT_TESTS",checks,flush=True)
