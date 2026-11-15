"""Load immutable native pool models and source-scoped completed two-blocker results."""
import hashlib,json,os,pathlib,sys,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import check_integrity,verify
check_integrity();OUT=ROOT/"artifacts/phase3/corridor_cp_001";OUT.mkdir(parents=True,exist_ok=True);ref="244cb4f9d894fd8aca8c8e1131019cfe6aa03d0b";expected="3160937c2b7f9252477d31991fbf7030fd39ccf4";base="https://raw.githubusercontent.com/"+os.environ["GITHUB_REPOSITORY"]+"/"+ref+"/codegarden/artifacts/phase3/low_blocker_001/"
def get(path):
 with urllib.request.urlopen(base+path,timeout=60) as response:return response.read()
raw=get("plan.json");old=json.loads(raw);assert old["source_sha"]==expected;(OUT/"previous_plan.json").write_bytes(raw);known=get("known226.txt");assert hashlib.sha256(known).hexdigest()==old["known226_sha256"];(OUT/"known226.txt").write_bytes(known);families=[]
for parent in [0,2,3,4]:
 row=old["cases"][parent];br=get("workers/"+str(parent)+"/report.json");report=json.loads(br);assert report["source_sha"]==expected and report["case"]==parent and report["starting_sha256"]==row["starting_sha256"] and not report["positive"]
 q2=row["models"][0];r2=report["results"][0];assert q2["blocker_threshold"]==r2["blocker_threshold"]==2 and r2["complete"] and not r2["limited"] and not r2["found"] and r2["pool_sha256"]==q2["pool_sha256"] and r2["fixed_sha256"]==q2["fixed_sha256"]
 (OUT/("native_parent_"+str(parent)+".json")).write_bytes(br);p=OUT/("hint_"+str(parent)+".txt");p.write_text(canonical(row["starting_words"]));v=verify(p);assert v["reports"][0]["witness_sha256"]==row["starting_sha256"]
 for q in row["models"][1:]:
  high=sorted(set(q["outside_pool"])-set(q2["outside_pool"]));assert high and pool_hash(q["pool"])==q["pool_sha256"] and digest_words(q["fixed"])==q["fixed_sha256"]
  families.append({"pair":len(families),"source_parent":parent,"blocker_threshold":q["blocker_threshold"],"fixed":q["fixed"],"pool":q["pool"],"outside_high":high,"outside_high_sha256":pool_hash(high),"fixed_sha256":q["fixed_sha256"],"pool_sha256":q["pool_sha256"],"hint_words":row["starting_words"],"hint_verification":v,"native_closed_two_blocker_report_sha256":hashlib.sha256(br).hexdigest(),"native_two_blocker_pool_sha256":q2["pool_sha256"]})
plan={"source_sha":os.environ["GITHUB_SHA"],"native_input_commit":ref,"native_input_source":expected,"previous_plan_sha256":hashlib.sha256(raw).hexdigest(),"families":families,"known226_sha256":hashlib.sha256(known).hexdigest(),"wall_limit_seconds":150,"workers":2,"scope":"Eight finite corridor pools, four parent codes at blocker thresholds3and4. Same fixed/pool/hint/seed per paired150-wall/two-worker CP-SAT solve, no objective or artificial227ceiling; seek any valid unknown code of size>=226. Control exact known226goal exclusions only; treatment additionally requires at least one outside word beyond the completed low2universe. This cut is conditional on native local closure; control positives violating it are retained and flagged. No global upper bound or formal absence certificate."}
(OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("CORRIDOR_CP_PLAN",json.dumps([{"pair":q["pair"],"parent":q["source_parent"],"b":q["blocker_threshold"],"fixed":len(q["fixed"]),"pool":len(q["pool"]),"high":len(q["outside_high"])} for q in families]),flush=True)
