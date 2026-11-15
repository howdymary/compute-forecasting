"""Regression: multiple conflict edges sharing one word still yield a valid226 code."""
import importlib.util,itertools,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical
check_integrity();out=ROOT/"artifacts/phase3/corequota_002/hub_tests";out.mkdir(parents=True,exist_ok=True);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());C=info["codes"][0];spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
owner={}
for w in C:
 for d in D.descendants(format(w,"016b")):owner[d]=w
tests=[]
for target_edges in [2,3]:
 for w in range(65536):
  if w in C:continue
  B={owner[d] for d in D.descendants(format(w,"016b")) if d in owner}
  if len(B)==target_edges:break
 else:raise AssertionError("fixture missing")
 near=C+[w];r=json.loads(subprocess.run([str(ROOT/".build/corequota2"),"--hub-test"],input=" ".join(map(str,near)),text=True,capture_output=True,check=True).stdout);assert r["pair_conflicts"]==target_edges and r["projections"]==[sorted(C)]
 p=out/("known_recovery_"+str(target_edges)+".txt");p.write_text(canonical(r["projections"][0]));v=verify(p);assert v["cardinality"]==226
 tests.append({"edges":target_edges,"pivot":w,"core_conflicts":sorted(B),"verification":v,"kind":"Known226 recovery for regression, not new research result"})
(out/"report.json").write_text(json.dumps(tests,indent=2));print("COREQUOTA_HUB_TESTS",len(tests),"known-code regressions passed",flush=True)
