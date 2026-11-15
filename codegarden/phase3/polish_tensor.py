"""Bounded connected repairs from diverse verified high-cardinality tensor projections."""
import hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import canonical,pool_hash,digest_words
def run(out):
 report=json.loads((out/"projections/report.json").read_text());pool={}
 for row in report["rows"]:
  for item in row["projections"]:
   v=item["verification"]
   if v["cardinality"]<224 or item["known226_orbit"]:continue
   pool[v["reports"][0]["witness_sha256"]]=item
 selected=sorted(pool.values(),key=lambda r:(-r["verification"]["cardinality"],r["verification"]["reports"][0]["witness_sha256"]))[:8];rows=[];best=226
 for index,item in enumerate(selected):
  path=out/"projections"/item["witness"];C={int(w,2) for w in path.read_text().split()};steps=[]
  for round in range(3):
   advanced=False
   for k,seconds in [(6,5),(7,10),(8,20)]:
    r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+80,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="")).stdout)
    r["pool_sha256"]=pool_hash(r.pop("candidate_pool"));r.pop("neighbors")
    if r["found"]:
     C=C-set(r["removed"])|set(r["added"]);p=out/("polished_"+str(index)+"_"+str(round)+".txt");p.write_text(canonical(C));r["verification"]=verify(p);best=max(best,len(C));advanced=True
    steps.append(r)
    if advanced:break
   if best>=227 or not advanced:break
  rows.append({"starting_witness":item["witness"],"steps":steps,"ending_size":len(C)})
  if best>=227:break
 result={"source_sha":os.environ["GITHUB_SHA"],"selected":len(selected),"rows":rows,"best_verified":best,"scope":"These bounded repairs of sampled verified projections only; no global optimality."}
 (out/"polish.json").write_text(json.dumps(result,indent=2));return result
