"""Rank-five supported-core neighborhoods, with explicit lower-depth prerequisites."""
import collections,hashlib,importlib.util,itertools,json,math,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import digest_words
from supervisor import check_integrity
from phase3.core4_prepare import supported
OUT=ROOT/"artifacts/phase3/core5_repair_001";OUT.mkdir(parents=True,exist_ok=True)
def supported5(p,s4):
 extension=collections.defaultdict(int)
 for patterns in p.values():
  for B in patterns:
   R=B
   while R:
    bit=R&-R;R-=bit;extension[B^bit]|=bit
 out=set(p.get(5,set()))
 for S in s4:
  T=S
  while True:
   v=extension.get(T,0)&~S
   while v:
    bit=v&-v;v-=bit;out.add(S|bit)
   if not T:break
   T=(T-1)&S
 for A,B in itertools.combinations(p.get(3,set()),2):
  U=A|B
  if U.bit_count()==5:out.add(U)
 for A in p.get(3,set()):
  for B in p.get(2,set()):
   U=A|B
   if U.bit_count()==5:out.add(U)
 return out
def main():
 check_integrity();info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=sorted(set.intersection(*(set(C) for C in info["codes"])));root=sorted(info["codes"][0]);idx={w:i for i,w in enumerate(core)}
 prior=ROOT/"artifacts/phase3/core4_repair_001";plan=json.loads((prior/"support_plan.json").read_text());assert plan["supported_quadruples"]==203077
 certs=[]
 for case in range(4):
  q=prior/str(case);r=json.loads((q/"report.json").read_text());n=r["native"];assert r["source_sha"]=="201693e19aaf506da5c7ec94ef31c35bb5c2db5c"
  expected=(203077+3-case)//4
  assert n["planned"]==n["processed"]==n["primary_complete_no227"]==expected and n["primary_timeouts"]==n["pool_cap_skips"]==0
  codes="".join(p.read_text() for p in sorted(q.glob("primary_statuses_*.txt")));assert len(codes)==expected and set(codes)=={"I"}
  certs.append({"case":case,"queries":expected,"report_sha256":hashlib.sha256((q/"report.json").read_bytes()).hexdigest(),"primary_statuses_sha256":hashlib.sha256(codes.encode()).hexdigest()})
 rng=random.Random(1390001);tests=[]
 for test in range(150):
  n=5+rng.randrange(5);p={k:set() for k in range(1,6)}
  for k in p:
   for C in itertools.combinations(range(n),k):
    if rng.random()<.25:p[k].add(sum(1<<v for v in C))
  _,s4=supported(p);actual=supported5(p,s4);expected=set()
  for C in itertools.combinations(range(n),5):
   S=sum(1<<v for v in C);cover=0
   for patterns in p.values():
    for B in patterns:
     if B&S==B:cover|=B
   if cover==S:expected.add(S)
  assert actual==expected,(test,len(actual),len(expected))
  tests.append({"test":test,"ground_size":n,"passed":True})
 (OUT/"support_identity_tests.json").write_text(json.dumps(tests,indent=2))
 raw="226 "+" ".join(map(str,root))+"\n216 "+" ".join(map(str,core))+"\n";(OUT/"root_core.txt").write_text(raw)
 native=json.loads(subprocess.run([str(ROOT/".build/core5_repair"),"--patterns5"],input=raw,text=True,capture_output=True,check=True).stdout);native_map={w:tuple(B) for w,B in native["words"]}
 spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);owner={}
 for w in core:
  for d in D.descendants(format(w,"016b")):owner[d]=w
 direct={};pairs=list(itertools.combinations(range(16),2));start=time.monotonic();core_set=set(core)
 for w in range(65536):
  if w in core_set:continue
  s=format(w,"016b");B=set()
  for i,j in pairs:
   v=owner.get(s[:i]+s[i+1:j]+s[j+1:])
   if v is not None:
    B.add(v)
    if len(B)>5:break
  if len(B)<=5:direct[w]=tuple(sorted(B))
 assert native_map==direct
 p={k:set() for k in range(1,6)}
 for B in direct.values():
  if B:p[len(B)].add(sum(1<<idx[w] for w in B))
 s3,s4=supported(p);assert len(s4)==203077
 s5=supported5(p,s4);assert len(s5)<=4000000
 ordered=sorted(s5);counts=[];hashes=[]
 for case in range(16):
  lines=[]
  for S in ordered[case::16]:
   C=[]
   while S:
    bit=S&-S;S-=bit;C.append(bit.bit_length()-1)
   assert len(C)==5
   lines.append("".join(format(v,"02x") for v in C))
  text=str(len(lines))+"\n"+"\n".join(lines)+"\n";path=OUT/("supported_"+str(case)+".txt");path.write_text(text);counts.append(len(lines));hashes.append(hashlib.sha256(text.encode()).hexdigest())
 (OUT/"blocker_words.json").write_text(json.dumps(native["words"],separators=(",",":")))
 report={"source_sha":os.environ["GITHUB_SHA"],"prior_source_revision":"d5eb573fe4e87b90d192b3346abb6e1fd2c9c367","core":core,"core_sha256":digest_words(core),"prior_certificates":certs,"independent_blocker_word_count":len(direct),"distinct_blocker_patterns":{k:len(v) for k,v in p.items()},"supported_quintuples":len(s5),"all_quintuples":math.comb(216,5),"unsupported_quintuples_eliminated":math.comb(216,5)-len(s5),"partition_counts":counts,"partition_sha256":hashes,"generation_seconds":time.monotonic()-start,
 "proof":"Outside w is compatible with core minus S iff B(w) is a subset of S. Unsupported S has an eligible removed vertex that can be reinserted, contradicting completed lower-depth No227, including for an alleged226 code forbidding S. Any supported five-set containing a supported four-subset is generated by the one-vertex extension map. If it has no supported four-subset: a size-five pattern suffices; a size-four pattern is excluded; a size-three pattern plus any other pattern reaching outside it must cover all five (otherwise it would generate a supported four-subset). This gives unions of two triples or a triple and a pair. If all patterns have size at most two, a minimal union attaining five has a prefix union of size four, or jumps from three to five via a disjoint pair; that pair and an earlier pair already form a forbidden supported four-subset. Thus the generator is exhaustive. Checked on150 random small hypergraphs. Five-removal queries use the full compatible universe.",
 "encoding":"Each partition starts with a decimal count. Following lines are five sorted one-byte indices into the216-word core, encoded as ten hexadecimal characters. Partition=global sorted support-mask index modulo16. Not binary codewords.",
 "scope":"Only rank-five shared-core repair families; conditional on completed lower depths. Completeness requires every supported query finish without improvement. No global bound."}
 (OUT/"support_plan.json").write_text(json.dumps(report,indent=2));print("CORE5_SUPPORT_PLAN",json.dumps({k:report[k] for k in ["supported_quintuples","all_quintuples","unsupported_quintuples_eliminated","generation_seconds"]}),flush=True)
if __name__=="__main__":main()
