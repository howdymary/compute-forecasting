"""Exactly scoped root exchanges, with durable non-timeout exhaustion cache."""
import hashlib,json,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import canonical,pool_hash
def main():
 out=ROOT/"artifacts/phase2";out.mkdir(parents=True,exist_ok=True)
 path=ROOT/"artifacts/best_code.txt";accepted=verify(path);words=path.read_text().splitlines();inc=[int(w,2) for w in words]
 entries=[];cache={}
 for k in [1,2]:
  p=subprocess.run([str(ROOT/".build/kernel_v2"),"--augment","16",str(k),"8"],input="\n".join(words)+"\n",
    text=True,capture_output=True,timeout=15,check=True);r=json.loads(p.stdout)
  context={"incumbent_sha256":accepted["reports"][0]["witness_sha256"],"method":"exact_k_new_word_exchange","k":k,
    "candidate_universe_sha256":pool_hash(range(65536)),
    "restrictions":"Remove exactly k incumbents and add k+1 distinct words outside the original incumbent; full 65536-word universe"}
  key=hashlib.sha256(json.dumps(context,sort_keys=True).encode()).hexdigest()
  r.update(context);r["context_key"]=key;r["starting_words"]=words
  r["proof_artifact"]=None;r["evidence"]="Complete compiled enumeration report" if r["complete"] else "Feasible move" if r["found"] else "Budget-limited scan; not exhaustion"
  if r["complete"]:cache[key]={"scope":context,"result_path":"codegarden/artifacts/phase2/root_sweeps.json","conclusion":r["status"]}
  if r["found"]:
   new=[w for w in inc if w not in r["removed"]]+r["added"];candidate=out/("worker_root_"+str(k)+".txt");candidate.write_text(canonical(new))
   r["independent_verification"]=verify(candidate)
  entries.append(r)
 (out/"root_sweeps.json").write_text(json.dumps(entries,indent=2));(out/"exhaustion_cache.json").write_text(json.dumps(cache,indent=2))
 print("ROOT_SWEEPS "+json.dumps([{"k":r["k"],"found":r["found"],"complete":r["complete"],"status":r["status"],"checks":r["checks"],"sets":r["removal_sets_checked"]} for r in entries]),flush=True)
if __name__=="__main__":main()
