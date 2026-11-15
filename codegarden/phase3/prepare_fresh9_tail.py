"""Resume exact per-modulo prefixes; never flatten partial shards into a global prefix."""
import hashlib,json,os,pathlib,sys,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity,verify
from search import pool_hash,digest_words
check_integrity();OUT=ROOT/"artifacts/phase3/fresh9_tail_001";OUT.mkdir(parents=True,exist_ok=True);ref="5a84a1b265dfeffad2b60ae39d10234862f99d71";expected_source="07114a0f6beca42959baeec94c26747bc2d07c8b";root="https://raw.githubusercontent.com/"+os.environ["GITHUB_REPOSITORY"]+"/"+ref+"/codegarden/artifacts/phase3/fresh9_resume_001/"
def get(path):
 with urllib.request.urlopen(root+path,timeout=60) as response:return response.read()
raw=get("coverage.json");coverage=json.loads(raw);pr=get("plan.json");previous=json.loads(pr);assert coverage["exchange_rank"]==9 and coverage["source_sha"]==previous["source_sha"]==expected_source
assert hashlib.sha256((ROOT/"phase3/bundle_colored.cpp").read_bytes()).hexdigest()==previous["colored_kernel_sha256"]
(OUT/"previous_coverage.json").write_bytes(raw);(OUT/"previous_plan.json").write_bytes(pr);workers=[];parents=[]
for parent in range(7):
 p=previous["cases"][parent];c=coverage["parents"][parent];assert p["case"]==c["parent"]==parent and not c["positive_verifications"] and not c["duplicate_completed_roots"] and p["starting_sha256"]==c["source_incumbent_sha256"]
 dest=OUT/"sources"/str(parent);dest.mkdir(parents=True,exist_ok=True)
 for name in ["starting.txt","known226.txt","candidate_pool.txt"]:(dest/name).write_bytes(get("sources/"+str(parent)+"/"+name))
 C=[int(w,2) for w in (dest/"starting.txt").read_text().split()];v=verify(dest/"starting.txt");assert v["cardinality"]==225 and digest_words(C)==p["starting_sha256"]
 P=list(map(int,(dest/"candidate_pool.txt").read_text().split()));assert len(P)==p["pool_size"]==c["pool_size"] and pool_hash(P)==p["pool_sha256"] and hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in P)).hexdigest()==p["ordered_pool_sha256"]
 parents.append(p);uncovered=set(c["uncovered_roots"])
 for shard in range(4):
  case=parent*4+shard;oldraw=get("workers/"+str(case)+"/report.json");old=json.loads(oldraw);assert old["source_sha"]==expected_source and old["case"]==case and old["parent"]==parent and old["shard"]==shard and old["status"]=="SEARCHED" and not old["positive"] and old["native"]["k"]==9
  (OUT/"previous_workers").mkdir(exist_ok=True);(OUT/"previous_workers"/(str(case)+".json")).write_bytes(oldraw)
  E=[i for i in range(p["old_completed_prefix"],len(P)) if i%4==shard];done=old["new_completed_roots"];assert len(E)==old["expected_suffix_roots"] and 0<=done<=len(E)
  remaining=E[done:];assert remaining==sorted(i for i in uncovered if i%4==shard)
  workers.append({"case":case,"parent":parent,"shard":shard,"previous_completed_mod_roots":done,"new_root_begin":remaining[0] if remaining else len(P),"remaining_roots":len(remaining),"eligible":bool(remaining),"reason":"unfinished_source_modulo_suffix" if remaining else "source_shard_already_closed","previous_report_sha256":hashlib.sha256(oldraw).hexdigest()})
plan={"source_sha":os.environ["GITHUB_SHA"],"exchange_rank":9,"previous_source":expected_source,"previous_commit":ref,"previous_coverage_sha256":hashlib.sha256(raw).hexdigest(),"colored_kernel_sha256":previous["colored_kernel_sha256"],"parents":parents,"workers":workers,"native_cpu_per_active_worker":150,"scope":"Preserve original global completed prefix and every first-pass modulo4completed prefix separately. Only each still-open modulo suffix is retried; interrupted root itself is not closed. No model, candidate or goal-filter change; literal seed/order guards retained. Conditional native coverage, not formal absence proof."}
(OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("FRESH9_TAIL_PLAN",json.dumps([{"case":w["case"],"begin":w["new_root_begin"],"left":w["remaining_roots"],"eligible":w["eligible"]} for w in workers]),flush=True)
