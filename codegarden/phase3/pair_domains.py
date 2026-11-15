"""Export explicit finite two-choice domains and independently check positive constructions."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,pool_hash,digest_words
check_integrity();case=int(sys.argv[1]);out=ROOT/"artifacts/phase3/pair_domains_001"/str(case);out.mkdir(parents=True,exist_ok=True)
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known=set()
def rev(w):return int(format(w,"016b")[::-1],2)
for C in info["codes"]:
 for comp in [False,True]:
  for reverse in [False,True]:known.add(tuple(sorted((rev(w) if reverse else w)^(65535 if comp else 0) for w in C)))
kp=out/"known_codes.txt";kp.write_text("\n".join("226 "+" ".join(map(str,C)) for C in sorted(known))+"\n")
C=info["codes"][case%len(info["codes"])];start=out/"starting.txt";start.write_text(canonical(C));v=verify(start);assert v["cardinality"]==226
test=json.loads(subprocess.run([str(ROOT/".build/pair_domains"),"--test"],text=True,capture_output=True,check=True).stdout);assert test["passed"]
r=json.loads(subprocess.run([str(ROOT/".build/pair_domains"),str(case//2),str(case),"1500","600",str(kp)],input=canonical(C),text=True,capture_output=True,check=True,timeout=900).stdout)
best=226;novel=[];groups=[]
for row in r.pop("contexts"):
 alternatives=row["alternative_words"];assert len(alternatives)==226 and all(0<=w<65536 for w in alternatives)
 row["ordered_domain_sha256"]=hashlib.sha256(json.dumps(list(zip(C,alternatives)),separators=(",",":")).encode()).hexdigest()
 for key in ["novel226_unverified","candidate227_unverified"]:
  if row[key]:
   q=out/(key+"_"+str(row["iteration"])+".txt");q.write_text(canonical(row[key]));row[key+"_verification"]=verify(q);best=max(best,row[key+"_verification"]["cardinality"])
   if key.startswith("novel"):assert tuple(sorted(row[key])) not in known;novel.append(q.name)
   if len(row[key])>=227:print("VERIFIED_227",q,flush=True)
 groups.append(row)
(out/"domains.jsonl").write_text("".join(json.dumps(row,separators=(",",":"))+"\n" for row in groups))
r.update(source_sha=os.environ["GITHUB_SHA"],case=case,starting_witness_sha256=digest_words(C),full_extra_candidate_pool_sha256=pool_hash(list(range(65536))),domains_sha256=hashlib.sha256((out/"domains.jsonl").read_bytes()).hexdigest(),bruteforce_tests=test,best_independently_verified=best,novel226_witnesses=novel,usable_alternative_histogram={str(k):sum(row["usable_alternatives"]==k for row in groups) for k in sorted({row["usable_alternatives"] for row in groups})},formal_absence_certificate=False)
(out/"report.json").write_text(json.dumps(r,indent=2));print("PAIR_DOMAINS",json.dumps(r),flush=True)
