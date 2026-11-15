"""Exact bipartite recombination with full-universe external augmentations."""
import hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,pool_hash,digest_words
check_integrity();case=int(sys.argv[1]);out=ROOT/"artifacts/phase3/union_external_003"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((ROOT/"phase3/union_external_plan.json").read_text());p=plan["cases"][case];A=p["a"]["words"];B=p["b"]["words"];receipts=[]
for label,C in [("a",A),("b",B)]:
 q=out/("parent_"+label+".txt");q.write_text(canonical(C));v=verify(q);assert v["cardinality"]==225;receipts.append(v)
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known=set()
def rev(w):return int(format(w,"016b")[::-1],2)
for C in info["codes"]:
 for comp in [False,True]:
  for reverse in [False,True]:known.add(tuple(sorted((rev(w) if reverse else w)^(65535 if comp else 0) for w in C)))
kp=out/"known_codes.txt";kp.write_text("\n".join("226 "+" ".join(map(str,C)) for C in sorted(known))+"\n")
oldp=ROOT/"artifacts/phase3/union_external_002"/str(case)/"report.json";old=json.loads(oldp.read_text());assert old["source_sha"]=="e5b3aa1c0a6bd69fd2107c79d7506e5f619a5435" and old["parent_sha256"]==[digest_words(A),digest_words(B)] and not old["found227_unverified"]
unfinished=[l for l in old["levels"] if not l["complete"]];prefix=0;poolfile="-"
if unfinished:
 active=unfinished[0];assert active==old["levels"][-1] and all(l["complete"] for l in old["levels"][:-1]);firstK=active["outside_limit"]
 if active["filter_complete"]:
  prefix=active["completed_roots"];path=out/"expected_resume_pool.txt";path.write_text(str(len(active["search_order"]))+" "+" ".join(map(str,active["search_order"]))+"\n");poolfile=str(path)
else:firstK=max(l["outside_limit"] for l in old["levels"])+1
lastK=min(10,max(8,firstK+1))
boundtests=json.loads((ROOT/"artifacts/phase3/union_external_003/bound_tests.json").read_text());assert boundtests["passed"]
t=time.monotonic();test=json.loads(subprocess.run([str(ROOT/".build/union_external3"),"--test"],text=True,capture_output=True,check=True).stdout);assert test["passed"]
r=json.loads(subprocess.run([str(ROOT/".build/union_external3"),"600",str(kp),str(firstK),str(lastK),str(prefix),poolfile],input=canonical(A)+canonical(B),text=True,capture_output=True,check=True,timeout=900).stdout);best=225;solutions=[]
for i,C in enumerate(r.pop("solutions_unverified")):
 q=out/("candidate_"+str(i)+".txt");q.write_text(canonical(C));v=verify(q);assert v["cardinality"]>=226
 if len(C)==226:assert tuple(sorted(C)) not in known
 best=max(best,len(C));solutions.append({"witness":q.name,"verification":v})
 if len(C)>=227:print("VERIFIED_227",q,flush=True)
universe=set(A)|set(B)
for level in r["levels"]:
 if level["outside_limit"]==firstK and poolfile!="-" and level["filter_complete"]:assert level["search_order"]==active["search_order"] and level["prior_completed_roots"]==prefix
 assert level["completed_roots"]==level["prior_completed_roots"]+level["new_completed_roots"]
 level["candidate_pool_sha256"]=pool_hash(level["candidate_pool"]);level["search_order_sha256"]=pool_hash(level["search_order"]);level["proof_artifact"]=None
r.update(smaller_limit_prerequisite_sha256=hashlib.sha256(oldp.read_bytes()).hexdigest(),prior_outside_limits=[2,3]+[l["outside_limit"] for l in old["levels"] if l["complete"]],resumed_level=firstK,resumed_completed_root_prefix=prefix,previous_search_cpu_seconds=old["cpu_seconds"],new_bound_tests=boundtests,retained_global_best_verified=max(226,best),best_method_independently_verified=best,source_sha=os.environ["GITHUB_SHA"],case=case,plan_sha256=hashlib.sha256((ROOT/"phase3/union_external_plan.json").read_bytes()).hexdigest(),parent_sha256=[digest_words(A),digest_words(B)],parent_verifications=receipts,union_pool_sha256=pool_hash(sorted(set(A)|set(B))),initial_extra_universe_sha256=pool_hash([w for w in range(65536) if w not in universe]),tests=test,solutions=solutions,best_independently_verified=best,wall_including_verification=time.monotonic()-t,formal_absence_certificate=False,novel226_sampling="Witnesses at non-goal nodes are sampled every17nodes, cap16. Every reachable227 target is checked; no exhaustive novelty claim.")
(out/"report.json").write_text(json.dumps(r,indent=2));print("UNION_EXTERNAL",json.dumps({k:r[k] for k in ["case","union_size","common","union_alpha","matching_calls","nodes","cheap_matching_bound_prunes","timed_out","cpu_seconds","best_method_independently_verified","retained_global_best_verified"]}|{"levels":[{k:l[k] for k in ["outside_limit","complete","completed_roots"]}|{"pool_count":len(l["candidate_pool"])} for l in r["levels"]]}),flush=True)
