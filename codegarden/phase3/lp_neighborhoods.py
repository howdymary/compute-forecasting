"""LP-guided repair selection and an optional independently checked rational dual bound."""
import datetime as dt,hashlib,importlib.util,json,math,os,pathlib,random,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,pool_hash,digest_words
from supervisor import verify
from cp_sat import solve
def main():
 import numpy as np
 from scipy.optimize import linprog
 from scipy.sparse import csc_matrix,vstack
 out=ROOT/"artifacts/phase3/lp_neighborhoods_001";out.mkdir(parents=True,exist_ok=True)
 accepted=verify(ROOT/"artifacts/best_code.txt");base=sorted(int(w,2) for w in (ROOT/"artifacts/best_code.txt").read_text().splitlines())
 target=accepted["cardinality"]+1;inc=Incidence(16);lengths=np.array(inc.sizes,dtype=np.int32);indptr=np.r_[0,np.cumsum(lengths,dtype=np.int64)]
 indices=np.fromiter((d for children in inc.desc for d in children),dtype=np.int32,count=int(indptr[-1]))
 A=csc_matrix((np.ones(len(indices)),indices,indptr),shape=(16384,65536));ones=np.ones(16384)
 t=time.perf_counter();lp=linprog(-np.ones(65536),A_ub=A,b_ub=ones,bounds=(0,None),method="highs",options={"time_limit":60})
 upper={"status":int(lp.status),"message":lp.message,"wall_seconds":time.perf_counter()-t,"numerical_objective":-float(lp.fun) if lp.fun is not None else None,
  "meaning":"Fractional packing objective is not a code cardinality or an integer optimality proof."}
 if lp.success:
  Q=100000000;weights=np.maximum(0,np.ceil(-np.asarray(lp.ineqlin.marginals)*Q)).astype(np.int64)
  cover=[sum(int(weights[d]) for d in inc.desc[w]) for w in range(65536)];deficit=max(0,Q-min(cover))
  if deficit:weights+=deficit
  spec=importlib.util.spec_from_file_location("lp_dual_protected_strings",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
  for w in range(65536):assert sum(int(weights[int(d,2)]) for d in D.descendants(format(w,"016b")))>=Q
  total=sum(map(int,weights));bound=total//Q;assert bound>=accepted["cardinality"]
  certificate={"denominator":Q,"descendant_weights":[int(w) for w in weights],"total_weight":total,"integer_upper_bound":bound,
   "all_65536_words_independently_checked":True,"generator":"Protected string deletion implementation, no LP incidence imported",
   "proof":"Nonnegative descendant weights cover every word with total at least denominator. Disjoint descendant sets imply |C|*denominator <= total weight.",
   "source_sha":os.environ["GITHUB_SHA"],"numerical_repair_added_to_each_weight":deficit}
  (out/"dual_certificate.json").write_text(json.dumps(certificate,indent=2));upper["independent_integer_upper_bound"]=bound
 (out/"upper_relaxation.json").write_text(json.dumps(upper,indent=2))
 print("LP_UPPER "+json.dumps(upper),flush=True)
 # Reuse only previously independently checked exact fixed-outside/pool/target scopes.
 closed={};old=ROOT/"artifacts/phase2/conflict_repairs"
 if (old/"report.json").exists() and (old/"independent_audit.json").exists():
  audit=json.loads((old/"independent_audit.json").read_text());ids={r["id"] for r in audit["rows"] if r["no_target_repair"]}
  for r in json.loads((old/"report.json").read_text())["rows"]:
   if r["id"] in ids and r["incumbent_witness_sha256"]==accepted["reports"][0]["witness_sha256"]:closed[(digest_words(r["fixed_outside"]),r["candidate_pool_sha256"],r["target"])]=r["id"]
 blockers=inc.blockers(base);rows=[];lp_rows=[];base_set=set(base)
 eq=csc_matrix(np.ones((1,65536)))
 for experiment in range(3):
  rng=random.Random(985000+experiment);c=np.zeros(65536);cost={w:1+(rng.random()-.5)*.5 for w in base}
  for w,value in cost.items():c[w]=-value
  started=time.perf_counter();r=linprog(c,A_ub=A,b_ub=ones,A_eq=eq,b_eq=np.array([target]),bounds=(0,None),method="highs",options={"time_limit":40})
  record={"id":experiment,"seed":985000+experiment,"status":int(r.status),"message":r.message,"seconds":time.perf_counter()-started}
  if r.x is None:lp_rows.append(record);continue
  x=np.maximum(0,np.asarray(r.x));feasible=bool(np.max(A@x)<=1+1e-6 and abs(float(x.sum())-target)<1e-5)
  record["numerically_feasible_fractional_target"]=feasible
  if not feasible:lp_rows.append(record);continue
  delta={w:max(0.,1-float(x[w])) for w in base};record["fractional_removed_root_mass"]=sum(delta.values())
  support=[w for w in range(65536) if w not in base_set and x[w]>1e-7]
  record["positive_outside_support"]=[[w,float(x[w])] for w in support];record["root_removal_fractions"]=[[w,delta[w]] for w in base]
  ranked=sorted(base,key=lambda w:(-delta[w],w));removed=set(ranked[:4]);mask=sum(1<<base.index(w) for w in removed)
  for size in [8,12,20,32,64,96,144]:
   while len(removed)<size:
    pressure={w:delta[w]*.0001 for w in base if w not in removed}
    for w in support:
     left=blockers[w]&~mask;degree=left.bit_count()
     if not degree:continue
     benefit=float(x[w])/(degree*degree)
     while left:
      bit=left&-left;j=bit.bit_length()-1;v=base[j]
      if v in pressure:pressure[v]+=benefit
      left^=bit
    chosen=max(pressure,key=lambda w:(pressure[w],delta[w],-w));removed.add(chosen);mask|=1<<base.index(chosen)
   fixed=[w for w in base if w not in removed];full=inc.compatible_pool(fixed);pool=full
   if len(full)>5000:
    rest=[w for w in full if w not in removed];rng.shuffle(rest);pool=sorted(removed|set(rest[:5000-len(removed)]))
   requested=target-len(fixed);key=(digest_words(fixed),pool_hash(pool),requested)
   if key in closed:
    receipt={"status":"REUSED_INDEPENDENTLY_CHECKED_INFEASIBILITY","source_row_id":closed[key],"source":"phase2/conflict_repairs/report.json","candidate_pool_sha256":key[1]}
    trial=None
   elif len(pool)<requested:
    receipt={"status":"INFEASIBLE_BY_CARDINALITY","candidate_pool_sha256":key[1],"proof":"There are fewer candidates than the required number of selected words."};trial=None
   else:trial,receipt=solve(inc,pool,requested,sorted(removed),seconds=3,seed=985000+experiment*200+size,workers=1)
   receipt.update({"lp_id":experiment,"removed":sorted(removed),"fixed_outside":fixed,"fixed_outside_sha256":key[0],"candidate_pool":pool,
    "candidate_pool_before_cap":len(full),"target_in_pool":requested,"global_target":target,"source_sha":os.environ["GITHUB_SHA"]})
   if trial:
    words=fixed+trial;p=out/("worker_lp_"+str(experiment)+"_"+str(size)+".txt");p.write_text(canonical(words));receipt["independent_verification"]=verify(p)
   rows.append(receipt);(out/"repairs.json").write_text(json.dumps(rows,indent=2))
   print("LP_REPAIR "+json.dumps({"lp":experiment,"removed":size,"pool":len(pool),"target":requested,"status":receipt["status"],"verified":receipt.get("independent_verification",{}).get("cardinality")}),flush=True)
   if trial:
    lp_rows.append(record);(out/"lp_guides.json").write_text(json.dumps(lp_rows,indent=2));return
  lp_rows.append(record);(out/"lp_guides.json").write_text(json.dumps(lp_rows,indent=2))
 (out/"status.json").write_text(json.dumps({"status":"completed","source_sha":os.environ["GITHUB_SHA"],"exact_repairs":len(rows),
  "lp_cases":len(lp_rows),"baseline":accepted,"no_global_improvement":True,"conclusion":"No improving witness in these recorded LP-guided pools; LP numerics and timeouts are not a global impossibility proof."},indent=2))
if __name__=="__main__":main()
