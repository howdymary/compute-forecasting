"""Scope-keyed durable cache. A miss never implies infeasibility."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase2"
def key(scope):
 return hashlib.sha256(json.dumps(scope,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def build():
 entries={}
 for filename in ["root_sweeps.json","radius34/sweeps.json","plateau_component/report.json"]:
  path=OUT/filename
  if not path.exists():continue
  data=json.loads(path.read_text())
  for r in (data["additional_state_sweeps"] if isinstance(data,dict) else data):
   if not r["complete"] or r["found"]:continue
   scope={"incumbent_sha256":r.get("incumbent_sha256",r.get("incumbent_witness_sha256")),
    "candidate_universe_sha256":r["candidate_universe_sha256"],"k":r["k"],
    "method":"exact_k_new_word_exchange","restriction":"Exactly k removed and k+1 new words outside original incumbent"}
   entries[key(scope)]={"scope":scope,"conclusion":"No improving exchange within this exact scope",
    "artifact":"codegarden/artifacts/phase2/"+filename,"proof_artifact":None,"evidence":"Completed enumeration; independently brute-force-tested implementation"}
 audit=OUT/"conflict_repairs/independent_audit.json"
 report=OUT/"conflict_repairs/report.json"
 if audit.exists() and report.exists():
  checked=json.loads(audit.read_text());assert checked["status"]=="passed"
  ids={r["id"] for r in checked["rows"] if r["no_target_repair"]}
  for r in json.loads(report.read_text())["rows"]:
   if r["id"] not in ids:continue
   fixed=hashlib.sha256("".join(format(w,"016b")+"\n" for w in sorted(r["fixed_outside"])).encode()).hexdigest()
   scope={"incumbent_sha256":r["incumbent_witness_sha256"],"fixed_outside_sha256":fixed,
    "candidate_pool_sha256":r["candidate_pool_sha256"],"target":r["target"],
    "method":"independently_verified_full_compatible_repair_pool"}
   entries[key(scope)]={"scope":scope,"conclusion":"No target repair in this full fixed-outside pool",
    "artifact":"codegarden/artifacts/phase2/conflict_repairs/report.json","row_id":r["id"],
    "audit":"codegarden/artifacts/phase2/conflict_repairs/independent_audit.json"}
 return entries
def lookup(entries,scope):
 return entries.get(key(scope))
def main():
 entries=build();positive=0;changed=0
 for entry in list(entries.values()):
  assert lookup(entries,entry["scope"]) is not None;positive+=1
  altered={**entry["scope"],"incumbent_sha256":"different-incumbent"}
  assert lookup(entries,altered) is None;changed+=1
 result={"entries":entries,"reuse_checks":positive,"changed_incumbent_misses":changed,
  "rule":"Every exact scope field must match. UNKNOWN and timeout reports are never indexed."}
 (OUT/"exhaustion_index.json").write_text(json.dumps(result,indent=2));print("EXHAUSTION_INDEX "+str(len(entries)))
if __name__=="__main__":main()
