"""Exact blocker-pattern reduction, checked against independent string deletions."""
import collections,hashlib,importlib.util,itertools,json,math,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words
from supervisor import check_integrity,verify
OUT=ROOT/"artifacts/phase3/core4_repair_001";OUT.mkdir(parents=True,exist_ok=True)
def supported(p):
 p1,p2,p3,p4=[set(p.get(i,set())) for i in [1,2,3,4]];s3=set(p3)
 for a,b,c in itertools.combinations(p1,3):s3.add(a|b|c)
 for a in p2:
  for b in p1:
   u=a|b
   if u.bit_count()==3:s3.add(u)
 for a,b in itertools.combinations(p2,2):
  u=a|b
  if u.bit_count()==3:s3.add(u)
 s4=set(p4);small=list(p1|p2|p3)
 for a in s3:
  for b in small:
   u=a|b
   if u.bit_count()==4:s4.add(u)
 for a,b in itertools.combinations(p2,2):
  u=a|b
  if u.bit_count()==4:s4.add(u)
 return s3,s4
def main():
 check_integrity();info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=sorted(set.intersection(*(set(C) for C in info["codes"])));root=sorted(info["codes"][0]);core_index={w:i for i,w in enumerate(core)}
 # Lower-depth full-universe results are prerequisites, not hypothetical observations.
 certs=[]
 for case in range(4):
  p=ROOT/"artifacts/phase3/core3_repair_001"/str(case);r=json.loads((p/"report.json").read_text());n=r["native"]
  assert r["source_sha"]=="294ecfa8f9b70b6356f862d84ce30c7c605a5c6d"
  assert n["planned"]==n["processed"]==n["primary_complete_no227"]==414090 and n["primary_timeouts"]==n["pool_cap_skips"]==0
  paths=sorted(p.glob("primary_statuses_*.txt"));raw="".join(path.read_text() for path in paths);assert len(raw)==414090 and set(raw)=={"I"}
  certs.append({"case":case,"report_sha256":hashlib.sha256((p/"report.json").read_bytes()).hexdigest(),"primary_statuses_sha256":hashlib.sha256(raw.encode()).hexdigest(),"queries":len(raw)})
 # Check the finite union-generation identity independently on random small hypergraphs.
 rng=random.Random(1380001);tests=[]
 for test in range(100):
  n=4+rng.randrange(5);p={k:set() for k in range(1,5)}
  for k in p:
   for C in itertools.combinations(range(n),k):
    if rng.random()<.3:p[k].add(sum(1<<v for v in C))
  s3,s4=supported(p)
  for k,actual in [(3,s3),(4,s4)]:
   expected=set()
   for C in itertools.combinations(range(n),k):
    S=sum(1<<v for v in C);cover=0
    for B in set.union(*p.values()):
     if B&S==B:cover|=B
    if cover==S:expected.add(S)
   assert actual==expected
  tests.append({"test":test,"ground_size":n,"passed":True})
 (OUT/"support_identity_tests.json").write_text(json.dumps(tests,indent=2))
 raw="226 "+" ".join(map(str,root))+"\n216 "+" ".join(map(str,core))+"\n";(OUT/"root_core.txt").write_text(raw)
 native=json.loads(subprocess.run([str(ROOT/".build/core4_repair"),"--patterns4"],input=raw,text=True,capture_output=True,check=True).stdout);native_map={w:tuple(B) for w,B in native["words"]}
 spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);owner={}
 for w in core:
  for d in D.descendants(format(w,"016b")):owner[d]=w
 pairs=list(itertools.combinations(range(16),2));direct={};start=time.monotonic();core_set=set(core)
 for w in range(65536):
  if w in core_set:continue
  s=format(w,"016b");B=set()
  for i,j in pairs:
   v=owner.get(s[:i]+s[i+1:j]+s[j+1:])
   if v is not None:
    B.add(v)
    if len(B)>4:break
  if len(B)<=4:direct[w]=tuple(sorted(B))
 assert direct==native_map,"Independent blocker maps disagree"
 p={k:set() for k in range(1,5)}
 for B in direct.values():
  if B:p[len(B)].add(sum(1<<core_index[w] for w in B))
 s3,s4=supported(p);assert len(s4)<=2000000
 # Verify the complete triple support set by direct subset inspection as a second check.
 direct3=set()
 for C in itertools.combinations(range(216),3):
  S=sum(1<<i for i in C);cover=0
  for k in [1,2,3]:
   for sub in itertools.combinations(C,k):
    B=sum(1<<i for i in sub)
    if B in p[k]:cover|=B
  if cover==S:direct3.add(S)
 assert direct3==s3
 tuples=[]
 for S in s4:
  C=[]
  while S:
   bit=S&-S;S-=bit;C.append(core[bit.bit_length()-1])
  tuples.append(tuple(C))
 tuples.sort();lines=str(len(tuples))+"\n"+"".join("4 "+" ".join(map(str,C))+"\n" for C in tuples);(OUT/"supported_neighborhoods.txt").write_text(lines)
 (OUT/"blocker_words.json").write_text(json.dumps(native["words"],separators=(",",":")))
 report={"source_sha":os.environ["GITHUB_SHA"],"prior_source_revision":"3187b1f72d49a12590d669f04c990486ef976ae9","core":core,"core_sha256":digest_words(core),"prior_complete_triple_queries":sum(r["queries"] for r in certs),"prior_certificates":certs,"independent_blocker_word_count":len(direct),"distinct_blocker_patterns":{k:len(v) for k,v in p.items()},"supported_triples":len(s3),"supported_quadruples":len(tuples),"all_quadruples":math.comb(216,4),"unsupported_quadruples_eliminated":math.comb(216,4)-len(tuples),"neighborhood_input_sha256":hashlib.sha256(lines.encode()).hexdigest(),"generation_seconds":time.monotonic()-start,
  "proof":"For fixed core minus S, an outside word is available iff its core-blocker set is a subset of S. If those eligible blocker sets do not cover S, some removed core word is compatible with every available outside word and with every core word. A227-word code could therefore include or reinsert it, giving a227-word subcode with at most three removed core words, contrary to the completed prerequisites. The same argument excludes226-word codes forbidding all removed core words. Supported sets are precisely unions of eligible blocker patterns; the rank-four union-generation identity is proved by considering a generating prefix of size three or a union of two disjoint pairs, and is independently brute checked on100 small hypergraphs.",
  "scope":"Only shared-core removal neighborhoods of size four. Full conditional coverage requires every supported query to complete without improvement; timeouts/caps leave that conclusion open. No global optimality claim."}
 (OUT/"support_plan.json").write_text(json.dumps(report,indent=2));print("CORE4_SUPPORT_PLAN",json.dumps({k:report[k] for k in ["supported_triples","supported_quadruples","all_quadruples","unsupported_quadruples_eliminated","generation_seconds"]}),flush=True)
if __name__=="__main__":main()
