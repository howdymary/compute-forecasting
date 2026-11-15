"""Continue only completed random-policy checkpoints; preserve cumulative versus new work."""
import hashlib,json,os,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical
check_integrity();OUT=ROOT/"artifacts/phase3/adaptive_hulls_001";expected="3d395631dd7368b92ea2406120f0a7481b6d01e0067f6c8737e99939743a5415";assert hashlib.sha256((ROOT/"phase3/adaptive_hulls.py").read_bytes()).hexdigest()==expected;rows=[]
for case in [0,2,4,6]:
 p=OUT/str(case);raw=(p/"checkpoint.json").read_bytes();s=json.loads(raw);r=json.loads((p/"report.json").read_text());assert s["engine_sha256"]==expected and s["case"]==case and s["best_in_family_verified"]==225 and r["source_sha"]=="8853af608e27f63a9db6072a42c824ff3d44c6cb" and r["mode"]=="random_one" and r["novel226"] is None
 q=p/"resumption_starting.txt";q.write_text(canonical(s["incumbent"]));v=verify(q);assert v["cardinality"]==225 and set(s["current_fixed"])<=set(s["incumbent"])
 rows.append({"case":case,"checkpoint_sha256":hashlib.sha256(raw).hexdigest(),"engine_sha256":expected,"old_trials":r["trials"],"old_completed_families":r["completed225_families"],"old_fixed_count":len(s["current_fixed"]),"starting_verification":v})
plan={"source_sha":os.environ["GITHUB_SHA"],"source_checkpoint_commit":"c24343245d469bb9dd0e1d4dd4023026bcbe60c5","cases":rows,"hypothesis":"Random one-word relaxation completed more progressively enlarged families than top-unlock adaptation. Continue its four verified225 checkpoints into previously unsearched relaxations; do not rerun completed child fixed sets.","new_wall_allowance_per_case":600,"solver_threads":2,"scope":"This is continuation, not a new independent comparison. Native report counts are cumulative; subtract this frozen old-trial ledger to measure new work. No paid calls."}
(OUT/"resumption_plan.json").write_text(json.dumps(plan,indent=2));print("RANDOM_RESUME_PLAN",json.dumps({"cases":[r["case"] for r in rows],"fixed":[r["old_fixed_count"] for r in rows]}),flush=True)
