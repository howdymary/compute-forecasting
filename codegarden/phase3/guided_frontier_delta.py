"""Harvest each exact worker archive; independently verify projections and delta unions."""
import datetime,hashlib,io,itertools,json,os,pathlib,subprocess,sys,time,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity,verify
from search import canonical,digest_words
check_integrity();half=int(sys.argv[1]);assert half in [0,1];out=ROOT/"artifacts/phase3/guided_frontier_delta_001"/str(half);out.mkdir(parents=True,exist_ok=True)
repo=os.environ["GITHUB_REPOSITORY"];runid=43731234570;source="88bc4d09e3cf7bd9e05ac9b95e6353fce9896bbd";cases=list(range(8*half,8*half+8))
def api(path,raw=False):
 r=subprocess.run(["gh","api",path],capture_output=True,check=True);return r.stdout if raw else json.loads(r.stdout)
rev=lambda w:int(format(w,"016b")[::-1],2)
def images(C):return [sorted(C),sorted(65535^w for w in C),sorted(rev(w) for w in C),sorted(65535^rev(w) for w in C)]
def orbit(C):return min(tuple(A) for A in images(C))
def valid(C):
 if len(C)!=len(set(C)) or any(w<0 or w>=65536 for w in C):return False
 owners=set()
 for w in C:
  x=format(w,"016b");desc={x[:i]+x[i+1:j]+x[j+1:] for i in range(16) for j in range(i+1,16)}
  if owners&desc:return False
  owners.update(desc)
 return True
old={}
plan=json.loads((ROOT/"phase3/union_external_plan.json").read_text());knowninfo=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text())
for row in plan["cases"]:
 for label in ["a","b"]:
  for C in images(row[label]["words"]):old[tuple(C)]=C
for row in json.loads((ROOT/"phase3/weighted_plan.json").read_text())["cases"]:
 for C in images(row["words"]):old[tuple(C)]=C
for C in knowninfo["codes"]:
 for A in images(C):old[tuple(A)]=A
old_orbits={orbit(C) for C in old.values()};known226={orbit(C) for C in knowninfo["codes"]};parents=dict(old);rows=[];seen_projection={};pending=set(cases);begin=time.monotonic()
while pending:
 run=api("repos/"+repo+"/actions/runs/"+str(runid));assert run["head_sha"]==source
 artifacts=api("repos/"+repo+"/actions/runs/"+str(runid)+"/artifacts?per_page=100")["artifacts"];named={a["name"]:a for a in artifacts}
 for case in sorted(pending.copy()):
  name="codegarden-guided-"+str(case)
  if name not in named:continue
  a=named[name];assert not a["expired"] and a["workflow_run"]["head_sha"]==source
  raw=api("repos/"+repo+"/actions/artifacts/"+str(a["id"])+"/zip",True);sha=hashlib.sha256(raw).hexdigest();assert a.get("digest")=="sha256:"+sha
  z=zipfile.ZipFile(io.BytesIO(raw));prefix=str(case)+"/"
  for filename in z.namelist():
   path=pathlib.PurePosixPath(filename);assert not path.is_absolute() and ".." not in path.parts
  nr=z.read(prefix+"native.json");rp=z.read(prefix+"report.json");n=json.loads(nr);r=json.loads(rp);assert r["source_sha"]==source and r["case"]==case and r["minimum_pair_conflicts"]==n["minimum_pair_conflicts"]
  saved=out/"sources"/str(case);saved.mkdir(parents=True,exist_ok=True);(saved/"native.json").write_bytes(nr);(saved/"report.json").write_bytes(rp)
  rawC=n["best"];assert len(rawC)==len(set(rawC))==227
  # Independent literal descendants identify the small conflicting endpoint set.
  D={w:{format(w,"016b")[:i]+format(w,"016b")[i+1:j]+format(w,"016b")[j+1:] for i in range(16) for j in range(i+1,16)} for w in rawC}
  edges=[(a,b) for i,a in enumerate(rawC) for b in rawC[i+1:] if D[a]&D[b]];assert len(edges)==n["minimum_pair_conflicts"];V=sorted(set(w for e in edges for w in e));projections=[]
  for remove in itertools.combinations(V,2):
   C=sorted(set(rawC)-set(remove))
   if len(C)!=225 or not valid(C):continue
   key=tuple(C)
   if key not in seen_projection:
    path=out/("projection225_"+str(len(seen_projection))+".txt");path.write_text(canonical(C));v=verify(path);assert v["cardinality"]==225
    seen_projection[key]={"path":path.name,"verification":v,"sha256":digest_words(C),"new_orbit_against_input_bank":orbit(C) not in old_orbits}
   projections.append(seen_projection[key])
   for A in images(C):parents[tuple(A)]=A
  for j,C in enumerate(n["novel226_candidates"]+([n["exact_repair227"]] if n["exact_repair227"] else [])):
   path=out/("upstream_positive_"+str(case)+"_"+str(j)+".txt");path.write_text(canonical(C));v=verify(path);assert v["cardinality"]>=226
   for A in images(C):parents[tuple(A)]=A
   if len(C)>=227:print("VERIFIED_227_UPSTREAM",path,flush=True)
  rows.append({"case":case,"artifact_id":a["id"],"artifact_name":name,"archive_sha256":sha,"native_sha256":hashlib.sha256(nr).hexdigest(),"report_sha256":hashlib.sha256(rp).hexdigest(),"minimum_pair_conflicts":len(edges),"projections":projections});pending.remove(case)
  print("FRONTIER_HARVESTED",case,len(projections),len(parents)-len(old),flush=True)
 if not pending:break
 if run["status"]=="completed" and run["conclusion"]!="success":raise RuntimeError("Upstream failed; missing cases not inferred")
 if time.monotonic()-begin>1500:raise RuntimeError("Upstream checkpoints unavailable within bounded waiting budget")
 time.sleep(15)
old_list=sorted(old.values(),key=lambda C:(-len(C),digest_words(C)));new_list=sorted([C for key,C in parents.items() if key not in old],key=lambda C:(-len(C),digest_words(C)));allparents=old_list+new_list
for C in allparents:
 assert valid(C)
text="".join(str(len(C))+" "+" ".join(map(str,C))+"\n" for C in allparents);(out/"parents.txt").write_text(text)
manifest={"source_sha":os.environ["GITHUB_SHA"],"upstream_run":runid,"upstream_source":source,"half":half,"archive_receipts":rows,"old_parent_count":len(old_list),"delta_parent_count":len(new_list),"parents_sha256":hashlib.sha256(text.encode()).hexdigest(),"old_parent_hashes":[digest_words(C) for C in old_list],"delta_parent_hashes":[digest_words(C) for C in new_list],"verified225_projections":list(seen_projection.values()),"new225_orbits_against_input_bank":len({orbit(C) for C in seen_projection if orbit(C) not in old_orbits}),"scope":"Each case read only from its own named source-pinned archive; no flattened sibling overwrite. Orbit novelty only against explicit input bank, not literature or global novelty."}
(out/"manifest.json").write_text(json.dumps(manifest,indent=2))
native=json.loads(subprocess.run([str(ROOT/".build/frontier_delta"),"400","64",str(out/"checkpoint.txt"),str(len(old_list))],input=text,text=True,capture_output=True,check=True,timeout=600).stdout);(out/"native.json").write_text(json.dumps(native,indent=2));positives=[];fresh226orbits=set();best=226
for i,C in enumerate(native["novel226_candidates"]+([native["winner"]] if len(native["winner"])>=227 else [])):
 path=out/("candidate_"+str(i)+".txt");path.write_text(canonical(C));v=verify(path);assert v["cardinality"]>=226;fresh=orbit(C) not in known226
 if fresh and len(C)==226:fresh226orbits.add(orbit(C))
 positives.append({"path":path.name,"verification":v,"new_orbit_against_known226":fresh});best=max(best,len(C))
 if len(C)>=227:print("VERIFIED_227",path,flush=True)
report={"source_sha":os.environ["GITHUB_SHA"],"half":half,"observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"old_parent_count":len(old_list),"delta_parent_count":len(new_list),"verified225_projections":len(seen_projection),"new225_orbits_against_input_bank":manifest["new225_orbits_against_input_bank"],"native_status":{k:v for k,v in native.items() if k not in ["winner","novel226_candidates"]},"positive_verifications":positives,"best_independently_verified":best,"novel226_orbits":len(fresh226orbits),"retained226_is_reproduction":best==226,"scope":"Exact bipartite unions incident to at least one newly harvested parent or subsequently added candidate, within recorded400CPU and64archive caps. Old-old pairs intentionally skipped; no claim all historical pairs were exhausted.400CPU starts after incidence preprocessing. No outside-word augmentation or global absence conclusion. Positive acceptance uses both unchanged protected verifiers; fresh verifier-only goal acceptance still required."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("GUIDED_FRONTIER_DELTA",json.dumps({k:report[k] for k in ["half","old_parent_count","delta_parent_count","verified225_projections","new225_orbits_against_input_bank","best_independently_verified","novel226_orbits"]}|{"native":report["native_status"]}),flush=True)
