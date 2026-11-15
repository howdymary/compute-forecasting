"""Explicitly enumerate the one-for-one component, with a hard state cap."""
import hashlib,json,math,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words,pool_hash
from supervisor import verify
def main():
 out=ROOT/"artifacts/phase2/plateau_component";out.mkdir(parents=True,exist_ok=True);inc=Incidence(16)
 first=sorted(int(w,2) for w in (ROOT/"artifacts/best_code.txt").read_text().splitlines());queue=[first];seen={tuple(first):0};rows=[];cap=64;truncated=False
 for index,code in enumerate(queue):
  if index>=cap:truncated=True;break
  selected=set(code);blocks=inc.blockers(code);neighbors=[];free=[]
  for w,mask in enumerate(blocks):
   if w in selected:continue
   if not mask:free.append(w);continue
   if mask.bit_count()!=1:continue
   old=code[mask.bit_length()-1];nextcode=sorted(selected-{old}|{w});tup=tuple(nextcode)
   if tup not in seen:
    if len(queue)>=cap:truncated=True;continue
    seen[tup]=len(queue);queue.append(nextcode)
   neighbors.append({"remove":old,"add":w,"neighbor_witness_sha256":digest_words(nextcode),"neighbor_id":seen[tup]})
  path=out/("worker_state_"+str(index)+".txt");path.write_text(canonical(code))
  rows.append({"id":index,"witness_sha256":digest_words(code),"independent_verification":verify(path),"all_neutral_neighbors":neighbors,
   "compatible_new_words_without_removal":free,"candidate_universe_sha256":pool_hash(range(65536))})
 report={"source_sha":os.environ["GITHUB_SHA"],"starting_witness_sha256":digest_words(first),"state_cap":cap,"states":rows,
  "complete_component":not truncated and len(rows)==len(queue),"scope":"Connected component under exactly one incumbent removal and one different word addition, preserving cardinality. Enumeration only; not global optimality."}
 sweeps=[]
 # The root has already been exhaustively checked. Test any other reached states.
 for i,code in enumerate(queue[1:5],1):
  for k,limit in [(1,10),(2,10),(3,30),(4,150)]:
   r=json.loads(subprocess.run([str(ROOT/".build/radius_sweep"),"16",str(k),str(limit)],input=canonical(code),text=True,capture_output=True,timeout=limit+20,check=True).stdout)
   r.update({"state_id":i,"incumbent_witness_sha256":digest_words(code),"candidate_universe_sha256":pool_hash(range(65536)),
    "total_removal_sets":math.comb(len(code),k),"source_sha":os.environ["GITHUB_SHA"],
    "restriction":"Exactly k removed and k+1 new words outside this specific state"})
   if r["found"]:
    trial=sorted(set(code)-set(r["removed"])|set(r["added"]));p=out/("worker_gain_"+str(i)+"_"+str(k)+".txt");p.write_text(canonical(trial));r["independent_verification"]=verify(p)
   sweeps.append(r)
  if len(queue)>2:break # Explicit bounded follow-up; no claim to sweep every large component.
 report["additional_state_sweeps"]=sweeps;(out/"report.json").write_text(json.dumps(report,indent=2))
 print("PLATEAU_COMPONENT "+json.dumps({"states":len(rows),"complete":report["complete_component"],"sweeps":[{k:r[k] for k in ["state_id","k","found","complete","removal_sets_checked"]} for r in sweeps]}),flush=True)
 repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-radius34";head=os.environ["SOURCE_SHA"]
 def api(path,payload=None,method=None):
  args=["gh","api",path]
  if payload is not None:args+=["--method",method or "POST","--input","-"]
  p=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(p.stdout)
 assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
 parent=api("repos/"+repo+"/git/commits/"+head);entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in list(out.glob("*.json"))+list(out.glob("*.txt"))]
 t=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
 c=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":t["sha"],"message":"Record exact one-for-one plateau component and augmentation checks around reached states"})
 api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":c["sha"],"force":False},"PATCH")
if __name__=="__main__":main()
