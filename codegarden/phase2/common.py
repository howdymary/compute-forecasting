import datetime as dt,hashlib,json,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
OUT=ROOT/"artifacts/phase2";OUT.mkdir(parents=True,exist_ok=True)
ACTIONS=["ruin32","ruin8","ejection3","weight_band","exchange23","ruin64"]
def canonical(words):return "\n".join(sorted(words))+"\n"
def sha(words):return hashlib.sha256(canonical(words).encode()).hexdigest()
def orbit(words):
 return min(sha(words),sha(["".join("1" if b=="0" else "0" for b in w) for w in words]),
  sha([w[::-1] for w in words]),sha(["".join("1" if b=="0" else "0" for b in w[::-1]) for w in words]))
def save(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2));return p
def check_words(words,name):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(canonical(words));return verify(p)
def kernel(words,seed,seconds,arm=0,policy="fixed",checkpoint="",target=227):
 p=subprocess.run([str(ROOT/".build/kernel_v2"),str(seconds),str(seed),policy,str(checkpoint),str(target),str(arm)],
  input=canonical(words),text=True,capture_output=True,timeout=max(30,seconds*2+25),check=True)
 r=json.loads(p.stdout);r["words"]=[format(w,"016b") for w in r["best"]]
 return r
def state(words,recent=(),stagnation=0,remaining=120):
 return {"length":16,"starting_cardinality":len(words),"weight_histogram":[sum(w.count("1")==k for w in words) for k in range(17)],
  "stagnation_cpu_seconds":round(stagnation,3),"recent_verified_results":list(recent)[-6:],"remaining_search_cpu_seconds":remaining}
def before_cutoff():
 spec=json.loads((ROOT/"budget/shared-allocation.json").read_text())
 return dt.datetime.now(dt.timezone.utc)<dt.datetime.fromisoformat(spec["no_new_billable_after"].replace("Z","+00:00"))
