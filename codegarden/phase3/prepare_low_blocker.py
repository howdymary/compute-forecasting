"""Unlock entire low-blocker corridors, without a bound on number of exchanged words."""
import hashlib,json,os,pathlib,random,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
check_integrity();OUT=ROOT/"artifacts/phase3/low_blocker_001";OUT.mkdir(parents=True,exist_ok=True)
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());fresh=json.loads((ROOT/"phase3/fresh225_plan.json").read_text());seeds=[{"label":"arena226","words":info["codes"][0]}]+[{"label":"fresh225_"+str(r["case"]),"words":r["words"]} for r in fresh["cases"]];profile=json.loads((ROOT/"phase3/aap_profile_2026-11-15.json").read_text());inc=Incidence(16);cases=[]
rev=lambda w:int(format(w,"016b")[::-1],2)
def images(C):return [sorted(C),sorted(65535^w for w in C),sorted(rev(w) for w in C),sorted(65535^rev(w) for w in C)]
known=sorted({tuple(K) for C in info["codes"] for K in images(C)});kp=OUT/"known226.txt";kp.write_text("".join("226 "+" ".join(map(str,K))+"\n" for K in known))
for case,row in enumerate(seeds):
 C=sorted(row["words"]);path=OUT/("seed_"+str(case)+".txt");path.write_text(canonical(C));v=verify(path);assert v["cardinality"]==len(C)
 owner=[-1]*inc.M
 for i,w in enumerate(C):
  for d in inc.desc[w]:assert owner[d]<0;owner[d]=i
 selected=set(C);outside={2:[],3:[],4:[]};blockers={}
 for w in range(inc.N):
  if w in selected:continue
  B=set()
  for d in inc.desc[w]:
   if owner[d]>=0:B.add(owner[d])
   if len(B)>4:break
  if len(B)<=4:
   blockers[w]=sorted(B)
   for b in [2,3,4]:
    if len(B)<=b:outside[b].append(w)
 assert digest_words(C)==profile["rows"][case]["starting_sha256"] and pool_hash(outside[2])==profile["rows"][case]["candidate_pool_sha256"]
 models=[]
 for b in [2,3,4]:
  affected={i for w in outside[b] for i in blockers[w]};F=sorted(w for i,w in enumerate(C) if i not in affected);P=outside[b]+[w for i,w in enumerate(C) if i in affected];random.Random(1532001+case*10+b).shuffle(P);occupied=inc.occupied(F);assert set(C)<=set(F)|set(P) and all(not occupied&inc.masks[w] for w in P) and len(P)<=10000
  models.append({"query":case*10+b,"blocker_threshold":b,"outside_pool":outside[b],"outside_pool_sha256":pool_hash(outside[b]),"fixed":F,"pool":P,"fixed_sha256":digest_words(F),"pool_sha256":pool_hash(P),"ordered_pool_sha256":hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in P)).hexdigest(),"target_total":226,"native_cpu_limit_seconds":60,"max_words_removed_bound":None})
 cases.append({"case":case,"label":row["label"],"starting_verification":v,"starting_sha256":digest_words(C),"starting_words":C,"models":models})
plan={"source_sha":os.environ["GITHUB_SHA"],"cases":cases,"known226_count":len(known),"known226_sha256":hashlib.sha256(kp.read_bytes()).hexdigest(),"literature":{"query":"maximum independent set path relinking set packing algorithm paper","primary_source":"https://mauricio.resende.info/doc/metaMIS.pdf","section":"3.2–3.4","extracted_method":"One-tight and two-tight neighbor interstate graph supports alternating augmenting paths. Our exact-pool adaptation optimizes all low-blocker words simultaneously, without a path-length or exchange-radius cap.","profile_authority":"phase3/aap_profile_2026-11-15.json"},"hypothesis":"The two-tight graph has stub-reachable components of77–107incumbent vertices, so short-radius closure does not cover all such corridors. Solve the whole induced packing family, then widen blocker thresholds2to3to4 after exact closure or budget stagnation.","scope":"Only original incumbent plus all outside words having at most the recorded blocker threshold relative to that incumbent. Fixed vertices are those touched by none of these outside words. An unlimited number of affected incumbent words may be exchanged. Exact known226arrays excluded, larger supersets retained. Complete negatives concern this finite goal model only;60CPU-second timeouts remain open, no formal absence certificate or global bound."}
(OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("LOW_BLOCKER_PLAN",json.dumps([{"case":r["case"],"sizes":[{"b":m["blocker_threshold"],"outside":len(m["outside_pool"]),"fixed":len(m["fixed"]),"pool":len(m["pool"])} for m in r["models"]]} for r in cases]),flush=True)
