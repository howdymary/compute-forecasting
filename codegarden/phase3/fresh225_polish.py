"""Polish provenance-pinned portfolio-novel225seeds; filter known goals only if reachable."""
import hashlib,json,os,pathlib,resource,subprocess,sys,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import check_integrity,verify
check_integrity();case=int(sys.argv[1]);out=ROOT/"artifacts/phase3/fresh225_polish_001"/str(case);out.mkdir(parents=True,exist_ok=True)
planpath=ROOT/"phase3/fresh225_plan.json";plan=json.loads(planpath.read_text());row=plan["cases"][case];C=row["words"][:];assert digest_words(C)==row["sha256"] and len(C)==225
rev=lambda w:int(format(w,"016b")[::-1],2)
def images(C):return [sorted(C),sorted(65535^w for w in C),sorted(rev(w) for w in C),sorted(65535^rev(w) for w in C)]
origin=row["origins"][0];url="https://raw.githubusercontent.com/"+os.environ["GITHUB_REPOSITORY"]+"/"+plan["source_revision"]+"/"+origin["path"]
with urllib.request.urlopen(url,timeout=60) as response:raw=response.read()
assert hashlib.sha256(raw).hexdigest()==origin["projection_sha256"];sourceWords=[int(w,2) for w in raw.decode().split()];assert min(images(sourceWords))==C
(out/"source_projection.txt").write_bytes(raw);startpath=out/"starting.txt";startpath.write_text(canonical(C));starting=verify(startpath);assert starting["cardinality"]==225
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known={tuple(T) for K in info["codes"] for T in images(K)};kp=out/"known226.txt";kp.write_text("".join("226 "+" ".join(map(str,K))+"\n" for K in sorted(known)));knownsets=[set(K) for K in known]
k=3;steps=[];novel226=[];budget=600;wall_start=time.monotonic();ru0=resource.getrusage(resource.RUSAGE_SELF);ch0=resource.getrusage(resource.RUSAGE_CHILDREN);best=len(C);ending=startpath
def used_cpu():
 ru=resource.getrusage(resource.RUSAGE_SELF);ch=resource.getrusage(resource.RUSAGE_CHILDREN)
 return ru.ru_utime+ru.ru_stime-ru0.ru_utime-ru0.ru_stime+ch.ru_utime+ch.ru_stime-ch0.ru_utime-ch0.ru_stime
while k<=12 and best<227 and used_cpu()<budget-4 and time.monotonic()-wall_start<1100:
 remaining=budget-used_cpu();seconds=min({3:2,4:3,5:5,6:10,7:20,8:30,9:60,10:120,11:180,12:300}[k],remaining-3)
 if seconds<.1:break
 before=C[:];path=out/("incumbent_"+str(len(steps))+".txt");path.write_text(canonical(C));maxoverlap=max(len(set(C)&K) for K in knownsets);filtered=len(C)==225 and maxoverlap>=len(C)-k
 env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0",CODEGARDEN_KNOWN_GOAL_CODES=str(kp) if filtered else "")
 ch=resource.getrusage(resource.RUSAGE_CHILDREN);b=time.monotonic();r=json.loads(subprocess.run([str(ROOT/".build/bundle_novel"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+90,env=env).stdout);after=resource.getrusage(resource.RUSAGE_CHILDREN)
 pool=r.pop("candidate_pool");assert len(pool)==len(set(pool));r.pop("neighbors");poolpath=out/("candidate_pool_"+str(len(steps))+".txt");poolpath.write_text("\n".join(map(str,pool))+"\n")
 r.update(incumbent_sha256=digest_words(before),incumbent_file=path.name,candidate_pool_file=poolpath.name,candidate_pool_sha256=pool_hash(pool),search_order_sha256=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in pool)).hexdigest(),search_order_encoding="uint32_be_in_recorded_order",goal_filter_enabled=filtered,max_overlap_known226=maxoverlap,native_nominal_seconds=seconds,child_process_cpu_seconds=after.ru_utime+after.ru_stime-ch.ru_utime-ch.ru_stime,process_wall_seconds=time.monotonic()-b,proof_artifact=None)
 if r["found"]:
  assert set(r["removed"])<=set(C) and len(set(r["added"]))==len(r["added"])
  C=sorted(set(C)-set(r["removed"])|set(r["added"]));assert len(C)>len(before);ending=out/("candidate_"+str(len(steps))+".txt");ending.write_text(canonical(C));checked=verify(ending);r["verification"]=checked;best=max(best,len(C))
  if len(C)==226:
   assert tuple(C) not in known;novel226.append({"path":ending.name,"verification":checked});print("VERIFIED_NEW226",ending,flush=True)
  if len(C)>=227:print("VERIFIED_227",ending,flush=True)
 steps.append(r);(out/"steps.json").write_text(json.dumps(steps,indent=2));print("FRESH225_STEP",case,k,r["found"],r["complete"],len(C),r["child_process_cpu_seconds"],flush=True)
 if r["found"]:k=3
 elif r["memory_limited"]:break
 else:k+=1
final=out/"ending.txt";final.write_text(canonical(C));accepted=verify(final);ru1=resource.getrusage(resource.RUSAGE_SELF);ch1=resource.getrusage(resource.RUSAGE_CHILDREN)
report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"source_guided_case":row["source_case"],"plan_sha256":hashlib.sha256(planpath.read_bytes()).hexdigest(),"source_projection_url":url,"source_projection_sha256":origin["projection_sha256"],"starting_verification":starting,"starting_sha256":row["sha256"],"ending_verification":accepted,"best_method_independently_verified":len(C),"retained_global_best_verified":max(226,len(C)),"novel226":novel226,"steps":steps,"search_and_controller_cpu_seconds":used_cpu(),"controller_self_cpu_seconds":ru1.ru_utime+ru1.ru_stime-ru0.ru_utime-ru0.ru_stime,"all_children_cpu_seconds":ch1.ru_utime+ch1.ru_stime-ch0.ru_utime-ch0.ru_stime,"wall_including_search":time.monotonic()-wall_start,"nominal_total_process_cpu_budget":budget,"scope":"Seven representative portfolio-novel225families, not independent four-projection replicas. Sequential bounded exchanges K3..12, all65536candidate words and no dominance/learnednogood exclusions. Known226goal filtering enabled only when overlap proves one could be reached. Unfiltered completed searches cover strict improving connected-component neighborhoods under the documented lemma. Filtered completion only covers enumerated connected bundles/saturated pools, not all novel codes in a radius. Time/node/memory caps remain open. Source-pinned native small exhaustive tests are not formal independent absence certificates. Every positive code uses both protected verifiers; fresh verifier-only goal acceptance still required."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("FRESH225_POLISH",json.dumps({"case":case,"source_guided_case":row["source_case"],"best":len(C),"novel226":len(novel226),"process_cpu":report["search_and_controller_cpu_seconds"],"steps":[{"k":r["k"],"filtered":r["goal_filter_enabled"],"complete":r["complete"],"found":r["found"]} for r in steps]}),flush=True)
