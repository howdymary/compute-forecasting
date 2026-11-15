"""Independent domain checks and protected acceptance around exact two-choice lifting."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,pool_hash,digest_words
check_integrity();case=int(sys.argv[1]);out=ROOT/"artifacts/phase3/coordinate_lift_001"/str(case);out.mkdir(parents=True,exist_ok=True)
p=ROOT/"artifacts/best_code.txt";v=verify(p);assert v["cardinality"]==226 and v["reports"][0]["witness_sha256"]=="417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa"
C=[int(w,2) for w in p.read_text().split()];test=json.loads(subprocess.run([str(ROOT/".build/coordinate_lift"),"--test"],text=True,capture_output=True,check=True).stdout);assert test["passed"]
r=json.loads(subprocess.run([str(ROOT/".build/coordinate_lift"),str(case),"600"],input=p.read_text(),text=True,capture_output=True,check=True,timeout=900).stdout)
for row in r["contexts"]:
 b=row["insert"];expected=[]
 for w in p.read_text().split():
  short=w[:case]+w[case+1:]
  for bit in "01":expected.append(int(short[:b]+bit+short[b:],2))
 assert row["variants"]==expected
 row["variant_order_sha256"]=hashlib.sha256(json.dumps(row["variants"],separators=(",",":")).encode()).hexdigest()
 row["implication_graph_sha256"]=hashlib.sha256(json.dumps(row["implication_rows_hex"],separators=(",",":")).encode()).hexdigest()
 if row["neutral226"]:
  q=out/("neutral_"+str(b)+".txt");q.write_text(canonical(row["neutral226"]));row["neutral_verification"]=verify(q)
 if row["candidate227"]:
  q=out/("candidate227_"+str(b)+".txt");q.write_text(canonical(row["candidate227"]));row["verification"]=verify(q);assert row["verification"]["cardinality"]==227;print("VERIFIED_227",q,flush=True)
summaries=[]
for row in r.pop("contexts"):
 b=row["insert"];path=out/("context_"+str(b)+".json");path.write_text(json.dumps(row,indent=2))
 summaries.append({k:row[k] for k in ["insert","base_satisfiable","complete","queries","direct_pruned","closure_pruned","variant_order_sha256","implication_graph_sha256"]}|{"context_file":path.name,"context_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"neutral226_verified":bool(row.get("neutral_verification")),"candidate227_verified":bool(row.get("verification"))})
r["contexts"]=summaries
r.update(source_sha=os.environ["GITHUB_SHA"],checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),starting_witness_sha256=digest_words(C),full_extra_candidate_pool_sha256=pool_hash(list(range(65536))),tests=test,coordinate_convention="zero-based from left/MSB",retained_global_best_verified=227 if r["found_unverified"] else 226,formal_absence_certificate=False)
(out/"report.json").write_text(json.dumps(r,indent=2));print("COORDINATE_LIFT",json.dumps({k:r[k] for k in ["puncture","complete","total_queries","cpu_seconds","retained_global_best_verified"]}),flush=True)
