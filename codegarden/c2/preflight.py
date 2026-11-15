"""CPU-only backup preflight: reproduce live C2, then certify an explicit integer approximation."""
import hashlib,importlib.util,json,pathlib,random,subprocess,time,urllib.request
from fractions import Fraction
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT.parent/"artifacts/c2/preflight_001";OUT.mkdir(parents=True,exist_ok=True)
BINARY=ROOT/".build/exact";rng=random.Random(630001)
def exact(values):
 text=str(len(values))+"\n"+" ".join(map(str,values))+"\n"
 r=subprocess.run([str(BINARY)],input=text,text=True,capture_output=True,timeout=180)
 if r.returncode:raise RuntimeError(r.stderr)
 return json.loads(r.stdout)
tests=[]
for n in [1,2,3,7,16,31,64,128]:
 for case in range(3):
  a=[rng.randrange(1<<32) for _ in range(n)]
  if case==1:a=[x if i%3==0 else 0 for i,x in enumerate(a)]
  c=[sum(a[i]*a[k-i] for i in range(n) if 0<=k-i<n) for k in range(2*n-1)]
  N=2*sum(v*v for v in c)+sum(x*y for x,y in zip(c,c[1:]));D=3*sum(c)*max(c);oracle=Fraction(N,D);result=exact(a)
  assert int(result["numerator"])==oracle.numerator and int(result["denominator"])==oracle.denominator
  tests.append({"n":n,"exact_fraction_agrees":True})
for a in [[1<<32],[1<<32,1<<32],[1<<32,0,1<<32],[1<<32]*128]:
 c=[sum(a[i]*a[k-i] for i in range(len(a)) if 0<=k-i<len(a)) for k in range(2*len(a)-1)]
 oracle=Fraction(2*sum(v*v for v in c)+sum(x*y for x,y in zip(c,c[1:])),3*sum(c)*max(c));r=exact(a)
 assert (int(r["numerator"]),int(r["denominator"]))==(oracle.numerator,oracle.denominator)
 tests.append({"n":len(a),"boundary_coefficients":True,"exact_fraction_agrees":True})
for payload in ["0\n","2\n0 0\n","2\n1 -1\n","2\n1 4294967297\n","2\n1 2 3\n"]:
 r=subprocess.run([str(BINARY)],input=payload,text=True,capture_output=True,timeout=10);assert r.returncode!=0
(OUT/"tests.json").write_text(json.dumps({"schoolbook_and_exact_fraction_cases":tests,"invalid_inputs_rejected":5},indent=2))
root="https://einsteinarena.com"
problem_raw=urllib.request.urlopen(root+"/api/problems/second-autocorrelation-inequality",timeout=60).read();problem=json.loads(problem_raw)
official=ROOT/"official.py";expected=hashlib.sha256(official.read_bytes()).hexdigest()
assert hashlib.sha256(problem["verifier"].encode()).hexdigest()==expected,"Live verifier changed; inspect before continuing"
raw=urllib.request.urlopen(root+"/api/solutions/best?problem_id=3&limit=1",timeout=90).read();leader=json.loads(raw)[0]
(OUT/"baseline_api_response.json").write_bytes(raw)
f=np.asarray(leader["data"]["values"],dtype=np.float64);assert f.ndim==1 and 1<=len(f)<=2000000 and np.isfinite(f).all()
sp=importlib.util.spec_from_file_location("c2_frozen_official",official);O=importlib.util.module_from_spec(sp);sp.loader.exec_module(O)
score=O.evaluate(leader["data"]);assert abs(score-leader["score"])<1e-10
f=np.maximum(f,0);assert f.max()>0;a=np.rint(f/f.max()*(1<<32)).astype(np.uint64)
quantized={"values":a.tolist()};(OUT/"integer_witness.json").write_text(json.dumps(quantized,separators=(",",":")))
txt=str(len(a))+"\n"+" ".join(map(str,quantized["values"]))+"\n";(OUT/"integer_witness.txt").write_text(txt)
started=time.monotonic();r=subprocess.run([str(BINARY)],input=txt,text=True,capture_output=True,timeout=180)
if r.returncode:raise RuntimeError(r.stderr)
certificate=json.loads(r.stdout);official_integer=O.evaluate(quantized);rational=Fraction(int(certificate["numerator"]),int(certificate["denominator"]))
assert abs(float(rational)-official_integer)<1e-10
(OUT/"exact_certificate.json").write_text(json.dumps(certificate,indent=2))
summary={"status":"baseline_reproduced_and_integer_approximation_certified","problem":"second-autocorrelation-inequality","leader_id":leader["id"],"author":leader["agentName"],"n":len(f),"live_score":leader["score"],"reproduced_official_score":score,"integer_score_exact":float(rational),"integer_score_official":official_integer,"quantization_change":float(rational)-score,"quantization_scale":1<<32,"official_verifier_sha256":expected,"baseline_response_sha256":hashlib.sha256(raw).hexdigest(),"integer_witness_sha256":hashlib.sha256((OUT/"integer_witness.json").read_bytes()).hexdigest(),"binary_sha256":hashlib.sha256(BINARY.read_bytes()).hexdigest(),"exact_certificate_seconds":time.monotonic()-started,"schoolbook_fixture_count":len(tests),"record_claim":False,"provider_calls":0,"gpu_search_started":False,"note":"Quantization produces a nearby explicit integer construction; it is not claimed to be identical to the floating leader. Integer NTT/CRT proves its score independently of FFT rounding."}
(OUT/"summary.json").write_text(json.dumps(summary,indent=2));print("C2_PREFLIGHT_RESULT "+json.dumps(summary),flush=True)
