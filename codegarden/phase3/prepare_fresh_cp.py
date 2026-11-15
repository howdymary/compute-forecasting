"""Source-audit unfiltered completed225rank8families before conditional proposal caps."""
import hashlib,json,os,pathlib,sys,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words
from supervisor import check_integrity,verify
check_integrity();out=ROOT/"artifacts/phase3/fresh_cp_001";out.mkdir(parents=True,exist_ok=True);ref="3e860a365a979143fd92150743f18f46131640a5";root="https://raw.githubusercontent.com/"+os.environ["GITHUB_REPOSITORY"]+"/"+ref+"/codegarden/artifacts/phase3/fresh8_resume_001/"
def get(path):
 with urllib.request.urlopen(root+path,timeout=60) as response:return response.read()
raw=get("coverage.json");coverage=json.loads(raw);assert coverage["source_sha"]=="54ad79cfe9a450e464808d752490e3d980c1c76d";sets=[];receipts=[];rev=lambda w:int(format(w,"016b")[::-1],2)
for row in coverage["parents"]:
 assert row["all_root_coverage_complete"] and not row["uncovered_roots"] and not row["duplicate_completed_roots"] and not row["positive_verifications"]
 if row["goal_filter_enabled"]:continue
 source=get("sources/"+str(row["parent"])+"/starting.txt");C=sorted(int(w,2) for w in source.decode().split());assert len(C)==225 and hashlib.sha256(source).hexdigest()==row["source_incumbent_sha256"]
 receipts.append({"parent":row["parent"],"witness_sha256":digest_words(C),"coverage_roots":row["pool_size"],"goal_filter_enabled":False})
 for comp in [False,True]:
  for reverse in [False,True]:
   S=sorted((rev(w) if reverse else w)^(65535 if comp else 0) for w in C);path=out/("cut_seed_"+str(len(sets))+".txt");path.write_text(canonical(S));v=verify(path);assert v["cardinality"]==225
   sets.append({"words":S,"limit":216,"source_parent":row["parent"],"complement":comp,"reversal":reverse,"verification":v})
assert len(receipts)==6 and len(sets)==24
report={"passed":True,"source_sha":os.environ["GITHUB_SHA"],"coverage_url":root+"coverage.json","coverage_sha256":hashlib.sha256(raw).hexdigest(),"coverage_source_sha":coverage["source_sha"],"receipts":receipts,"sets":sets,"lemma":"If no unfiltered strict improving exchange removing at most8words exists from a225word seed, a valid code of size>=226 can share at most216seed words. Otherwise its outside words give a strict exchange; a positive disjoint-blocker component suffices. Complement/reversal transfer. Only unfiltered completed families included.","assurance":"Conditional on completed native computation, kernel and coverage audit. Not a formal independent absence certificate. Apply only in a treatment model, retain uncut control; never modify either positive verifier."}
(out/"cuts.json").write_text(json.dumps(report,indent=2));print("FRESH_CP_CUT_AUDIT",len(receipts),len(sets),report["coverage_sha256"],flush=True)
