"""Explicit checkpoint migration into a paired random/minimum-growth experiment."""
import hashlib,json,os,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import Incidence,canonical,digest_words,pool_hash
check_integrity()
OLD=ROOT/"artifacts/phase3/adaptive_hulls_001";OUT=ROOT/"artifacts/phase3/min_growth_hulls_001";OUT.mkdir(parents=True,exist_ok=True)
old_engine="3d395631dd7368b92ea2406120f0a7481b6d01e0067f6c8737e99939743a5415"
new_engine=hashlib.sha256((ROOT/"phase3/min_growth_hulls.py").read_bytes()).hexdigest()
inc=Incidence(16);parents=[];migrations=[]
for oldcase in range(8):
 p=OLD/str(oldcase);raw=(p/"checkpoint.json").read_bytes();state=json.loads(raw);r=json.loads((p/"report.json").read_text())
 assert state["engine_sha256"]==old_engine and state["case"]==oldcase and state["best_in_family_verified"]==225 and r["source_sha"]=="8853af608e27f63a9db6072a42c824ff3d44c6cb" and r["novel226"] is None
 F=state["current_fixed"];C=state["incumbent"];assert set(F)<=set(C)
 q=OUT/("parent_"+str(oldcase)+".txt");q.write_text(canonical(C));v=verify(q);assert v["cardinality"]==225
 history=state["history"];byid={t["id"]:t for t in history};assert len(byid)==len(history)
 for cert in state["certificates"]:
  if cert["id"].startswith("parent_"):continue
  t=byid[cert["id"]];assert t["status"]=="OPTIMAL" and t["fixed"]==cert["fixed"] and t["model_sha256"]==cert["model_sha256"] and t["pool_sha256"]==cert["pool_sha256"]
 assert any(set(cert["fixed"])<=set(F) for cert in state["certificates"])
 parent={"parent_case":oldcase,"fixed":F,"words":C,"parent_pool_sha256":pool_hash(inc.compatible_pool(F)),"parent_report_sha256":hashlib.sha256((p/"report.json").read_bytes()).hexdigest(),"parent_model_sha256":None,"parent_source":"8853af608e27f63a9db6072a42c824ff3d44c6cb","verification":v}
 parents.append(parent)
 for condition in range(2):
  case=2*oldcase+condition;new=json.loads(json.dumps(state));new.update(source_sha=os.environ["GITHUB_SHA"],engine_sha256=new_engine,case=case,mode="random_one" if condition==0 else "minimum_growth",batch=1,fast=0)
  d=OUT/str(case);d.mkdir(parents=True,exist_ok=True);(d/"checkpoint.json").write_text(json.dumps(new,indent=2))
  migrations.append({"case":case,"starting_old_case":oldcase,"condition":new["mode"],"old_checkpoint_sha256":hashlib.sha256(raw).hexdigest(),"old_engine_sha256":old_engine,"new_engine_sha256":new_engine,"starting_fixed_count":len(F),"starting_witness_sha256":digest_words(C),"carried_trials":len(history),"carried_closed":sum(t["status"]=="OPTIMAL" for t in history),"carried_open":state["open_trials"],"proof_scope":"Retain frozen exact-goal225 receipts and their explicit fixed sets; this is an engine migration, not a same-engine resume."})
plan={"source_sha":os.environ["GITHUB_SHA"],"source_checkpoint_commit":"c24343245d469bb9dd0e1d4dd4023026bcbe60c5","parents":parents,"migrations":migrations,"hypothesis":"Small-growth expansions may close faster than maximum-unlock expansions. Compare minimum newly eligible candidate weight against one-word random unfixing from eight identical-per-pair225 checkpoint states.","search_wall_budget":600,"solver_workers":2,"comparability":"Eight paired starts, correlated ancestry from four original families. Equal600loop-wall/two-thread caps, actual wall and self/child CPU separately reported. Both policies have a broad fallback when the narrow proposal prefix is exhausted. No LLM or training calls.","scope":"Cardinality primary. OPTIMAL closes only the explicitly encoded family under conditional inherited exclusions. UNKNOWN/FEASIBLE and proposal exhaustion do not prove impossibility."}
(OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("MIN_GROWTH_PLAN",json.dumps({"pairs":8,"fixed_sizes":[len(p["fixed"]) for p in parents]}),flush=True)
