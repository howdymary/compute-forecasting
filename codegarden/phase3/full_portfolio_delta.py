"""Exact pair unions incident to new guided/neutral canonical parents."""
import concurrent.futures,hashlib,json,os,pathlib,resource,subprocess,sys,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words
from supervisor import check_integrity,verify
check_integrity();out=ROOT/"artifacts/phase3/full_portfolio_delta_001";out.mkdir(parents=True,exist_ok=True);begin=time.monotonic();ch0=resource.getrusage(resource.RUSAGE_CHILDREN);ru0=resource.getrusage(resource.RUSAGE_SELF)
base="https://raw.githubusercontent.com/"+os.environ["GITHUB_REPOSITORY"]+"/";oldref="4252ffa87a7e36f07596cec4295a831a330fe4cf";guideref="86690a8b87d6bb84f4f53a63211d49b89fea0582";neutralref="7d32eeea9b19f794f341005612db9f64ba2178f6"
def fetch(url):
 with urllib.request.urlopen(url,timeout=60) as response:return response.read()
def readparents(raw):
 rows=[]
 for line in raw.decode().splitlines():
  a=list(map(int,line.split()));assert a[0]==len(a)-1;rows.append(sorted(a[1:]))
 return rows
rev=lambda w:int(format(w,"016b")[::-1],2)
def images(C):return [tuple(sorted(C)),tuple(sorted(65535^w for w in C)),tuple(sorted(rev(w) for w in C)),tuple(sorted(65535^rev(w) for w in C))]
def orbit(C):return min(images(C))
url=base+oldref+"/codegarden/artifacts/phase3/recombine_001/0/parents.txt";raw=fetch(url);assert hashlib.sha256(raw).hexdigest()=="292c01d7811661522dfb1a4d4407efc99488a8db490453f6a1af55ca8c0f70d3";old=readparents(raw);old_orbits={orbit(C) for C in old};sources=[{"url":url,"sha256":hashlib.sha256(raw).hexdigest()}];proposals={}
for half in [0,1]:
 url=base+guideref+"/codegarden/artifacts/phase3/guided_frontier_delta_001/"+str(half)+"/parents.txt";raw=fetch(url);sources.append({"url":url,"sha256":hashlib.sha256(raw).hexdigest()})
 for C in readparents(raw):
  if len(C)==225 and orbit(C) not in old_orbits:proposals.setdefault(orbit(C),[]).append({"kind":"guided","url":url})
def neutral_inputs(case):
 url=base+neutralref+"/codegarden/artifacts/phase3/neutral_hybrid_001/"+str(case)+"/report.json";raw=fetch(url);r=json.loads(raw);assert r["source_sha"]=="941d63d920a6f6658b809d2996d13c50115b9dc0" and r["case"]==case;rows=[]
 for row in r["projection225_bank"]:
  u=base+neutralref+"/codegarden/artifacts/phase3/neutral_hybrid_001/"+str(case)+"/"+row["path"];b=fetch(u);assert hashlib.sha256(b).hexdigest()==row["sha256"];C=sorted(int(w,2) for w in b.decode().split());assert len(C)==225
  rows.append((orbit(C),{"kind":"neutral","case":case,"url":u,"sha256":row["sha256"]}))
 return {"url":url,"sha256":hashlib.sha256(raw).hexdigest()},rows
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
 for receipt,rows in executor.map(neutral_inputs,range(8)):
  sources.append(receipt)
  for C,origin in rows:
   if C not in old_orbits:proposals.setdefault(C,[]).append(origin)
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known226={orbit(C) for C in info["codes"]};active={};seed_receipts=[];positives=[];fresh226orbits=set();inc=Incidence(16);best=225
for C,origins in proposals.items():
 path=out/("seed225_"+str(len(seed_receipts))+".txt");path.write_text(canonical(C));v=verify(path);assert v["cardinality"]==225;active[C]=list(C);seed_receipts.append({"path":path.name,"sha256":digest_words(C),"verification":v,"origins":origins})
 P=inc.compatible_pool(C);Q=list(C);mask=inc.occupied(Q)
 for w in sorted(P,key=lambda w:(len(inc.desc[w]),w)):
  if not mask&inc.masks[w]:Q.append(w);mask|=inc.masks[w]
 if len(Q)>225:
  q=out/("direct_extension_"+str(len(positives))+".txt");q.write_text(canonical(Q));checked=verify(q);fresh=orbit(Q) not in known226
  if fresh and len(Q)==226:fresh226orbits.add(orbit(Q))
  positives.append({"path":q.name,"verification":checked,"new_orbit_against_known226":fresh});best=max(best,len(Q))
  if orbit(Q) not in old_orbits:active[orbit(Q)]=list(orbit(Q))
  print("VERIFIED_227" if len(Q)>=227 else "VERIFIED_DIRECT_EXTENSION",q,flush=True)
  if len(Q)>=227:break
passive={T:list(T) for C in old for T in images(C)}
for C in active:
 for T in images(C):
  if T!=C:passive[T]=list(T)
for C in active:assert C not in passive
oldlist=sorted(passive.values(),key=lambda C:(-len(C),digest_words(C)));newlist=sorted(active.values(),key=lambda C:(-len(C),digest_words(C)));parents=oldlist+newlist
for C in parents:inc.occupied(C)
text="".join(str(len(C))+" "+" ".join(map(str,C))+"\n" for C in parents);(out/"parents.txt").write_text(text)
manifest={"source_sha":os.environ["GITHUB_SHA"],"sources":sources,"earlier_parent_count":len(old),"earlier225_orbits":len({orbit(C) for C in old if len(C)==225}),"active_canonical_parents":len(newlist),"passive_parent_prefix":len(oldlist),"seed_verifications":seed_receipts,"active_hashes":[digest_words(C) for C in newlist],"parents_sha256":hashlib.sha256(text.encode()).hexdigest(),"scope":"Passive prefix includes older codes in all four orientations and noncanonical images of new active codes. Search only pairs incident to an active canonical new code. Any pair of complement/reversal images has an equivalent pair with first code canonical. No old-old exhaustion or global novelty claim."}
(out/"manifest.json").write_text(json.dumps(manifest,indent=2));print("FULL_PORTFOLIO_PLAN",len(oldlist),len(newlist),flush=True)
native=None
if best<227 and newlist:
 native=json.loads(subprocess.run([str(ROOT/".build/frontier_delta"),"400","64",str(out/"checkpoint.txt"),str(len(oldlist))],input=text,text=True,capture_output=True,check=True,timeout=650).stdout);(out/"native.json").write_text(json.dumps(native,indent=2))
 for i,C in enumerate(native["novel226_candidates"]+([native["winner"]] if len(native["winner"])>=227 else [])):
  path=out/("candidate_"+str(i)+".txt");path.write_text(canonical(C));v=verify(path);assert v["cardinality"]>=226;fresh=orbit(C) not in known226;assert len(C)>=227 or fresh
  if fresh and len(C)==226:fresh226orbits.add(orbit(C))
  positives.append({"path":path.name,"verification":v,"new_orbit_against_known226":fresh});best=max(best,len(C));print("VERIFIED_227" if len(C)>=227 else "VERIFIED_NEW226",path,flush=True)
ru=resource.getrusage(resource.RUSAGE_SELF);ch=resource.getrusage(resource.RUSAGE_CHILDREN);summary={k:v for k,v in native.items() if k not in ["winner","novel226_candidates"]} if native else None
report={"source_sha":os.environ["GITHUB_SHA"],"active_canonical_parents":len(newlist),"passive_parent_prefix":len(oldlist),"native_status":summary,"positive_verifications":positives,"best_method_independently_verified":best,"retained_global_best_verified":max(226,best),"novel226_orbits":len(fresh226orbits),"wall_seconds":time.monotonic()-begin,"controller_self_cpu_seconds":ru.ru_utime+ru.ru_stime-ru0.ru_utime-ru0.ru_stime,"all_children_cpu_seconds":ch.ru_utime+ch.ru_stime-ch0.ru_utime-ch0.ru_stime,"scope":"Full recorded old portfolio versus newly harvested guided/neutral canonical parents, all relative complement/reversal orientations represented.400nativeCPU cap after incidence preprocessing; actual process usage includes setup/verification separately. Pair completeness only on explicitly represented searched pairs. No outside-word augmentation, formal absence certificate or global bound. Positive goal promotion requires fresh verifier-only acceptance."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("FULL_PORTFOLIO_DELTA",json.dumps({"active":len(newlist),"best":best,"novel226_orbits":report["novel226_orbits"],"native":summary}),flush=True)
