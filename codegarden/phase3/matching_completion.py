"""Outside-set search with exact valid bipartite completion; positive outputs independently checked."""
import hashlib,json,os,pathlib,resource,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import check_integrity,verify
controller_start=time.monotonic();ru0=resource.getrusage(resource.RUSAGE_SELF);child0=resource.getrusage(resource.RUSAGE_CHILDREN);check_integrity();case=int(sys.argv[1]);out=ROOT/"artifacts/phase3/matching_completion_001"/str(case);out.mkdir(parents=True,exist_ok=True)
planpath=ROOT/"phase3/union_external_plan.json";plan=json.loads(planpath.read_text());p=plan["cases"][case//2];A=p["a"]["words"];B=p["b"]["words"];parent_receipts=[]
for label,C in [("a",A),("b",B)]:
 path=out/("parent_"+label+".txt");path.write_text(canonical(C));v=verify(path);assert v["cardinality"]==225;parent_receipts.append(v)
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));rev=lambda w:int(format(w,"016b")[::-1],2)
def images(C):return [sorted(C),sorted(65535^w for w in C),sorted(rev(w) for w in C),sorted(65535^rev(w) for w in C)]
def orbit(C):return min(tuple(T) for T in images(C))
coreimages=images(core);cp=out/"cores.txt";cp.write_text("".join("216 "+" ".join(map(str,C))+"\n" for C in coreimages))
known={tuple(T) for C in info["codes"] for T in images(C)};known_orbits={orbit(C) for C in info["codes"]};kp=out/"known226.txt";kp.write_text("".join("226 "+" ".join(map(str,C))+"\n" for C in sorted(known)))
mode="fixed_outside8" if case%2==0 else "stagnation_outside8_to16";seed=1517001+case//2
start=time.monotonic();r=json.loads(subprocess.run([str(ROOT/".build/matching_completion"),"300",str(seed),str(case%2),str(out/"checkpoint_verified_only_after_checks.txt"),str(kp),str(cp)],input=canonical(A)+canonical(B),text=True,capture_output=True,check=True,timeout=420).stdout);(out/"native.json").write_text(json.dumps(r,indent=2))
bestpath=out/"best.txt";bestpath.write_text(canonical(r["best"]));v=verify(bestpath);assert v["cardinality"]==r["best_size_unverified"] and set(r["best_outside"])<=set(r["best"]) and not(set(r["best_outside"])&(set(A)|set(B)))
positives=[];fresh226=set();seen=set()
for i,C in enumerate(r["novel226_candidates"]+([r["best"]] if len(r["best"])>=227 else [])):
 if digest_words(C) in seen:continue
 seen.add(digest_words(C));path=out/("candidate_"+str(i)+".txt");path.write_text(canonical(C));checked=verify(path);assert checked["cardinality"]>=226
 fresh=orbit(C) not in known_orbits
 if len(C)==226:assert fresh;fresh226.add(orbit(C))
 positives.append({"path":path.name,"verification":checked,"new_orbit_against_known226":fresh})
 if len(C)>=227:print("VERIFIED_227",path,flush=True)
 else:print("VERIFIED_NEW226",path,flush=True)
bank=[];old225orbits={orbit(row[label]["words"]) for row in plan["cases"] for label in ["a","b"]}
for i,C in enumerate(r["bank225_unverified"]):
 path=out/("projection225_"+str(i)+".txt");path.write_text(canonical(C));checked=verify(path);assert checked["cardinality"]==225
 bank.append({"path":path.name,"sha256":digest_words(C),"verification":checked,"new_orbit_against_plan_parents":orbit(C) not in old225orbits})
events=out/"checkpoint_verified_only_after_checks.txt.events.jsonl";switches=[json.loads(line) for line in events.read_text().splitlines()]
ru1=resource.getrusage(resource.RUSAGE_SELF);child1=resource.getrusage(resource.RUSAGE_CHILDREN)
report={"controller_self_cpu_seconds":ru1.ru_utime+ru1.ru_stime-ru0.ru_utime-ru0.ru_stime,"all_children_cpu_seconds":child1.ru_utime+child1.ru_stime-child0.ru_utime-child0.ru_stime,"controller_wall_including_parents_and_verification":time.monotonic()-controller_start,"source_sha":os.environ["GITHUB_SHA"],"case":case,"pair":case//2,"seed":seed,"mode":mode,"plan_sha256":hashlib.sha256(planpath.read_bytes()).hexdigest(),"parent_sha256":[digest_words(A),digest_words(B)],"parent_verifications":parent_receipts,"union_pool_sha256":pool_hash(sorted(set(A)|set(B))),"best_method_independently_verified":v["cardinality"],"best_verification":v,"retained_global_best_verified":max(226,v["cardinality"]),"novel226_orbits":len(fresh226),"positive_verifications":positives,"bank225":bank,"neighborhood_switches":switches,"wall_including_verification":time.monotonic()-start,"native_status":{k:value for k,value in r.items() if k not in ["best","novel226_candidates","bank225_unverified"]},"scope":"Eight paired fixed8 versus empirical-stagnation8..16 outside-word policies, same parent pair/seed and300nativeCPU nominal limits. Every completion is a valid code from the residual two-parent union plus mutually compatible outside words. Alternating core-availability upper-count penalty is heuristic only and is not enforced by either acceptance verifier. No mathematical exhaustion/global absence claim. Fresh verifier-only job required before goal promotion. Supporting bank/orbit metrics are not a cardinality improvement."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("MATCHING_COMPLETION",json.dumps({"case":case,"mode":mode,"best":v["cardinality"],"novel226_orbits":len(fresh226),"bank225":len(bank),"new225_plan_orbits":sum(row["new_orbit_against_plan_parents"] for row in bank),"switches":len(switches),"cycles":r["cycles"],"matching_calls":r["matching_calls"],"search_cpu_seconds":r["search_cpu_seconds"]}),flush=True)
