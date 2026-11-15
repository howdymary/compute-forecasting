"""Collective one-bit-per-parent mutation plus a fixed extra word."""
import argparse,hashlib,itertools,json,os,pathlib,random,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,pool_hash,digest_words
from supervisor import verify,check_integrity
from ortools.sat.python import cp_model
def balls(C,n):return [[w]+[w^(1<<i) for i in range(n)] for w in sorted(C)]
def solve(C,n,v,ds,seconds=20,seed=0):
 groups=balls(C,n);assert len(set(w for g in groups for w in g))==sum(map(len,groups))
 assert v not in {w for g in groups for w in g}
 occupied=set(ds[v]);groups=[[w for w in g if not occupied&set(ds[w])] for g in groups]
 if any(not g for g in groups):return {"status":"INFEASIBLE_EMPTY_PARENT_DOMAIN","complete":True,"groups":groups,"word":v,"proof":"At least one required parent ball has no word compatible with fixed extra word"}
 model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for g in groups for w in g};at={}
 for g in groups:model.add_exactly_one(xs[w] for w in g)
 for w,x in xs.items():
  for d in ds[w]:at.setdefault(d,[]).append(x)
 for group in at.values():
  if len(group)>1:model.add_at_most_one(group)
 for w,x in xs.items():model.add_hint(x,int(w in C))
 assert not model.validate()
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds;solver.parameters.num_search_workers=1;solver.parameters.random_seed=seed
 t=time.monotonic();status=solver.solve(model)
 r={"word":v,"groups":groups,"pool_sha256":pool_hash(sorted(xs)),"model_sha256":hashlib.sha256(str(model.proto).encode()).hexdigest(),"status":solver.status_name(status),
  "complete":status==cp_model.INFEASIBLE,"seconds_limit":seconds,"wall_seconds":time.monotonic()-t,"branches":solver.num_branches,"conflicts":solver.num_conflicts}
 if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:r["candidate"]=sorted([v]+[w for w,x in xs.items() if solver.value(x)])
 return r
def test():
 import importlib.util
 spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 rows=[];rng=random.Random(1200000)
 examples=[(5,[0]),(5,[0,31]),(6,[0,7]),(6,[0,7,56]),(6,[0,7,56,63])]
 for n,C in examples:
  ds={w:set(D.descendants(format(w,"0%db"%n))) for w in range(1<<n)};union={w for g in balls(C,n) for w in g};values=[v for v in ds if v not in union];rng.shuffle(values)
  for v in values[:12]:
   allowed=[[w for w in g if not ds[w]&ds[v]] for g in balls(C,n)]
   def rec(i,used):
    if i==len(allowed):return True
    return any(not ds[w]&used and rec(i+1,used|ds[w]) for w in allowed[i])
   expected=rec(0,set(ds[v]));r=solve(C,n,v,ds,5,1200000+v);assert ("candidate" in r)==expected and (expected or r["complete"]),(n,C,v,r)
   if expected:D.verify([format(w,"0%db"%n) for w in r["candidate"]],n)
   rows.append({"n":n,"C":C,"extra":v,"expected_feasible":expected,"status":r["status"]})
 out=ROOT/"artifacts/phase3"/os.environ.get("CODEGARDEN_BATCH","hamming_csp_001");out.mkdir(parents=True,exist_ok=True);(out/"tests.json").write_text(json.dumps(rows,indent=2));print("HAMMING_CSP_TESTS",len(rows),flush=True)
def prepare():
 out=ROOT/"artifacts/phase3"/os.environ.get("CODEGARDEN_BATCH","hamming_csp_001");base=out/"preflight/baseline.txt";v=verify(base);C={int(w,2) for w in base.read_text().split()};assert len(C)==226
 inc=Incidence(16);groups=balls(C,16);universe={w for g in groups for w in g};assert len(universe)==226*17
 at=[{} for _ in range(16384)]
 for i,g in enumerate(groups):
  for j,w in enumerate(g):
   for d in inc.desc[w]:at[d][i]=at[d].get(i,0)|(1<<j)
 candidates=[];ALL=(1<<17)-1;blocked_all=0
 for w in range(65536):
  if w in universe:continue
  blocked={}
  for d in inc.desc[w]:
   for i,mask in at[d].items():blocked[i]=blocked.get(i,0)|mask
  if any(mask==ALL for mask in blocked.values()):blocked_all+=1;continue
  available=226*17-sum(mask.bit_count() for mask in blocked.values());min_domain=min([17-mask.bit_count() for mask in blocked.values()]+[17])
  original_blockers=sum(bool(mask&1) for mask in blocked.values())
  candidates.append({"word":w,"available":available,"minimum_domain":min_domain,"original_blockers":original_blockers})
 # Stratify by insertion blocker count, keeping high domain freedom inside each stratum.
 buckets={}
 for r in candidates:buckets.setdefault(r["original_blockers"],[]).append(r)
 for bucket in buckets.values():bucket.sort(key=lambda r:(-r["minimum_domain"],-r["available"],r["word"]))
 selected=[];depth=0
 while len(selected)<128 and any(depth<len(b) for b in buckets.values()):
  for k in sorted(buckets):
   if depth<len(buckets[k]):selected.append(buckets[k][depth])
   if len(selected)>=128:break
  depth+=1
 rng=random.Random(1200001);rng.shuffle(selected)
 plan={"source_sha":os.environ["GITHUB_SHA"],"starting_verification":v,"parent_ball_count":226,"ball_radius":1,"ball_size":17,"union_size":len(universe),
  "candidate_extra_count":len(candidates),"empty_domain_rejected":blocked_all,"strata":{k:len(b) for k,b in buckets.items()},"selected":selected,
  "all_extra_words_sha256":pool_hash([r["word"] for r in candidates]),
  "lemma":"Two words in one radius-one Hamming ball differ in at most two coordinates, hence share a length14 descendant. Valid parent words have Hamming distance at least3, so these balls are disjoint. A227-code in their union plus one extra word must select exactly one per ball and the extra word.",
  "scope":"Collective mutation of all226 parent words by at most one bit, plus one fixed extra word; no fixed-outside assumption. This is not the global universe of all possible227 codes."}
 (out/"plan.json").write_text(json.dumps(plan,indent=2));print("HAMMING_CSP_PLAN",json.dumps({k:plan[k] for k in ["candidate_extra_count","empty_domain_rejected","strata"]}),flush=True)
def run(case):
 out=ROOT/"artifacts/phase3"/os.environ.get("CODEGARDEN_BATCH","hamming_csp_001")/str(case);out.mkdir(parents=True,exist_ok=True)
 plan=json.loads((out.parent/"plan.json").read_text());base=out.parent/"preflight/baseline.txt";accepted=verify(base);C={int(w,2) for w in base.read_text().split()};inc=Incidence(16);rows=[];best=226
 for i,pivot in enumerate(plan["selected"][case::8]):
  r=solve(C,16,pivot["word"],inc.desc,20,1201000+case*100+i);r["pivot_features"]=pivot
  if "candidate" in r:
   p=out/("candidate_"+str(i)+".txt");p.write_text(canonical(r["candidate"]));r["independent_verification"]=verify(p);best=r["independent_verification"]["cardinality"];assert best==227
  rows.append(r);(out/"report.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"case":case,"rows":rows,"best_verified":best,"scope":plan["scope"],"starting_verification":accepted},indent=2))
  print("HAMMING_CSP",json.dumps({"case":case,"attempt":i,"extra":pivot["word"],"status":r["status"],"best":best}),flush=True)
  if best>=227:break
def main():
 check_integrity();ap=argparse.ArgumentParser();ap.add_argument("--prepare",action="store_true");ap.add_argument("--test",action="store_true");ap.add_argument("--case",type=int);a=ap.parse_args()
 if a.test:test()
 elif a.prepare:prepare()
 else:run(a.case)
if __name__=="__main__":main()
