"""Independent acceptance in a fresh job; no search modules, model or mutable manifest trusted."""
import datetime,hashlib,json,os,pathlib,subprocess,sys,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/isolated_acceptance_001";OUT.mkdir(parents=True,exist_ok=True)
TRUSTED_COMMIT="ce5eab1859c271686876ee5c2d21c0e0a5316d67"
EXPECTED={"verify_descendants.py":"3c844b9c56e05a7f7e309bdf7d7ab094e098b4a70fd50189f6db92b1181b63fb","verify_lcs.py":"e45ec0ee5d9eaa592b0fe676ce0f2fd727edcfdeecc964748de8a4d8a8109fd5"}
def fetch(commit,path):
 assert len(commit)==40 and set(commit)<=set("0123456789abcdef") and path.startswith("codegarden/") and ".." not in pathlib.PurePosixPath(path).parts
 url="https://raw.githubusercontent.com/howdymary/compute-forecasting/"+commit+"/"+path
 for attempt in range(3):
  try:return urllib.request.urlopen(url,timeout=40).read()
  except Exception:
   if attempt==2:raise
   time.sleep(1)
verifiers=OUT/"frozen_verifiers";verifiers.mkdir(exist_ok=True)
for name,sha in EXPECTED.items():
 raw=fetch(TRUSTED_COMMIT,"codegarden/protected/"+name);assert hashlib.sha256(raw).hexdigest()==sha;(verifiers/name).write_bytes(raw)
def check_frozen():
 for name,sha in EXPECTED.items():assert hashlib.sha256((verifiers/name).read_bytes()).hexdigest()==sha
plan=json.loads((ROOT/"phase3/isolated_acceptance_plan.json").read_text());results=[]
for item in plan["witnesses"]:
 raw=fetch(item["commit"],item["path"]);assert hashlib.sha256(raw).hexdigest()==item["sha256"];p=OUT/(item["label"]+".txt");p.write_bytes(raw);reports=[]
 for name in EXPECTED:
  check_frozen();proc=subprocess.run([sys.executable,"-I","-B",str(verifiers/name),str(p)],text=True,capture_output=True,timeout=120)
  report=json.loads(proc.stdout);assert proc.returncode==0 and report["valid"] and report["cardinality"]==item["cardinality"] and report["witness_sha256"]==item["sha256"];reports.append(report)
 assert reports[0]["cardinality"]==reports[1]["cardinality"] and reports[0]["witness_sha256"]==reports[1]["witness_sha256"];results.append({"source":item,"accepted":True,"reports":reports})
check_frozen()
report={"controller_source_sha":os.environ["GITHUB_SHA"],"checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"trusted_verifier_commit":TRUSTED_COMMIT,"trusted_verifier_sha256":EXPECTED,"search_proposer_executed_in_this_job":False,"search_modules_imported":False,"mutable_search_manifest_used":False,"python_isolation":"-I -B for each verifier subprocess","witnesses":results,"best_independently_verified":max(r["reports"][0]["cardinality"] for r in results),"target227_achieved":any(r["reports"][0]["cardinality"]>=227 for r in results),"scope":"Fresh immutable-source verifier-only replay. This plan checks reproduced226 and recovered225 witnesses; it claims no larger code or global record. Future candidates require an explicit pinned plan and the same frozen acceptance."}
(OUT/"report.json").write_text(json.dumps(report,indent=2));print("ISOLATED_ACCEPTANCE",json.dumps({"witnesses":len(results),"best":report["best_independently_verified"],"target227":report["target227_achieved"]}),flush=True)
