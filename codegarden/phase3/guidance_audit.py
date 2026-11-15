"""Convert source-pinned scoped union exhaustion into OPTIONAL proposal constraints.
This audits receipts and continuation coverage, not formal absence certificates.
Acceptance verifiers do not consume this file or these constraints.
"""
import concurrent.futures,hashlib,json,pathlib,sys,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity,verify
from search import canonical,digest_words,pool_hash
check_integrity();out=ROOT/"artifacts/phase3/guided_hybrid_001";out.mkdir(parents=True,exist_ok=True)
planpath=ROOT/"phase3/union_external_plan.json";plan=json.loads(planpath.read_text())
stages=[
 ("559eed6a143663d25186e2c9770b61abcaf41df4","union_external_001","f54584e7088915cc9e8cd8863a155dcb984bb6fd"),
 ("931c3eb67b506dea80defc927b516613cfcf72a3","union_external_002","e5b3aa1c0a6bd69fd2107c79d7506e5f619a5435"),
 ("c0fcf14e4e718d0528aaa6741ad5fc09ddeccee5","union_external_003","005ce3f7bdbfb470ffa011a28716b76009ed24be"),
 ("e12acea6c67cc128d4ae70d6b14c7fa4ddc89049","union_external_004","3b8068c00d94fdc90e127b096506e62705b116a2")]
def fetch(arg):
 stage,i=arg;commit,prefix,source=stages[stage];url="https://raw.githubusercontent.com/howdymary/compute-forecasting/"+commit+"/codegarden/artifacts/phase3/"+prefix+"/"+str(i)+"/report.json"
 with urllib.request.urlopen(url,timeout=60) as response:raw=response.read()
 return (stage,i),(raw,json.loads(raw),url)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:data=dict(executor.map(fetch,[(s,i) for s in range(4) for i in range(16)]))
receipts=[];sets=[]
rev=lambda w:int(format(w,"016b")[::-1],2)
for i,p in enumerate(plan["cases"]):
 A=p["a"]["words"];B=p["b"]["words"];U=sorted(set(A)|set(B));parents=[digest_words(A),digest_words(B)];closed=set();previous=None
 for label,C in [("a",A),("b",B)]:
  path=out/("parent_"+str(i)+"_"+label+".txt");path.write_text(canonical(C));assert verify(path)["cardinality"]==225
 for stage in range(4):
  raw,r,url=data[stage,i];assert r["case"]==i and r["source_sha"]==stages[stage][2] and not r["found227_unverified"]
  assert r["parent_sha256"]==parents and r["plan_sha256"]==hashlib.sha256(planpath.read_bytes()).hexdigest() and r["union_pool_sha256"]==pool_hash(U) and r["union_alpha"]==225
  if stage:
   oldraw,old,_=data[stage-1,i];assert r["smaller_limit_prerequisite_sha256"]==hashlib.sha256(oldraw).hexdigest()
   if stage>=2:
    active=next((l for l in old["levels"] if not l["complete"]),None)
    first=r["levels"][0];expected=active["completed_roots"] if active and active["filter_complete"] else 0
    assert r["resumed_completed_root_prefix"]==expected
    if active and active["filter_complete"]:
     assert first["outside_limit"]==active["outside_limit"] and first["search_order"]==active["search_order"] and first["prior_completed_roots"]==expected
  for level in r["levels"]:
   P=level["candidate_pool"];order=level["search_order"];assert len(P)==len(set(P)) and sorted(P)==sorted(order)
   assert level["candidate_pool_sha256"]==pool_hash(P)
   if stage==3:
    expected=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in order)).hexdigest()
    assert level["search_order_sha256"]==expected
   else:assert level["search_order_sha256"]==pool_hash(order)
   if "prior_completed_roots" in level:assert level["completed_roots"]==level["prior_completed_roots"]+level["new_completed_roots"]
   assert 0<=level["completed_roots"]<=len(order)
   if level["complete"]:
    assert level["filter_complete"] and level["completed_roots"]==len(order)
    closed.add(level["outside_limit"])
  receipts.append({"case":i,"stage":stage+1,"url":url,"report_sha256":hashlib.sha256(raw).hexdigest(),"source_sha":r["source_sha"],"closed_levels_in_this_receipt":[l["outside_limit"] for l in r["levels"] if l["complete"]],"formal_independent_absence_certificate":False})
 assert set(range(2,8))<=closed,closed
 # Ordinary union alpha225 excludes outside0/1; explicit completed levels cover2..7.
 for complement in [False,True]:
  for reverse in [False,True]:
   V=sorted((rev(w) if reverse else w)^(65535 if complement else 0) for w in U)
   sets.append({"case":i,"complement":complement,"reversal":reverse,"words":V,"limit":219,"completed_outside_limit":7})
# Deduplicate identical constraints. These remain conditional guidance only.
unique={tuple(row["words"]):row for row in sets};sets=list(unique.values());assert 1<=len(sets)<=64
path=out/"guidance.txt";path.write_text(str(len(sets))+"\n"+"".join(str(len(r["words"]))+" "+str(r["limit"])+" "+" ".join(map(str,r["words"]))+"\n" for r in sets))
report={"passed":True,"guidance_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"sets":sets,"receipts":receipts,"mathematical_scope":"For a valid227-word code C, if all families with <=7 outside words from U have been excluded, |C intersect U|<=219. Ordinary union independence225 excludes0/1 outside; source-pinned finite computations exclude2..7. Complement and reversal preserve D2-disjointness. No conclusion about8+ outside. Conditional on native search correctness and coverage audits; not a formal independently checkable absence certificate.","policy_scope":"Guided treatment proposals only. Unguided control retained. Exact repair does not enforce these cuts. Both independent acceptance verifiers remain unchanged.","historical_hash_note":"Stages1..3 mislabeled a sorted-set pool hash as search-order hash. Complete recorded orders were retained and compared literally across continuation; stage4 uses ordered BE32 hash."}
(out/"guidance_audit.json").write_text(json.dumps(report,indent=2));print("GUIDANCE_AUDIT",len(sets),len(receipts),report["guidance_sha256"],flush=True)
