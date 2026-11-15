"""Compute full-universe symmetric fractional guidance and independently verify a dual."""
import gzip,hashlib,json,os,pathlib,resource,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence
from supervisor import check_integrity
from phase3.orbit_lp_model import quotient,lift_primal,dual_certificate,reverse
import numpy as np
from scipy.optimize import linprog
check_integrity();case=int(sys.argv[1]);method=["highs-ds","highs-ipm"][case];out=ROOT/"artifacts/phase3/orbit_lp_001"/str(case);out.mkdir(parents=True,exist_ok=True);inc=Incidence(16);MASK=inc.N-1;DMASK=inc.M-1;rv=[reverse(w,16) for w in range(inc.N)];rd=[reverse(d,14) for d in range(inc.M)]
for w in range(inc.N):
 assert set(inc.desc[w^MASK])=={d^DMASK for d in inc.desc[w]} and set(inc.desc[rv[w]])=={rd[d] for d in inc.desc[w]}
A,b,W,wi,ws,D,di,matrix_hash=quotient(inc);assert A.shape==(4160,16512)
(out/"environment.txt").write_text(subprocess.run([sys.executable,"-m","pip","freeze"],text=True,capture_output=True,check=True).stdout)
report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"method":method,"length":16,"word_orbits":len(W),"descendant_orbits":len(D),"nonzeros":A.nnz,"matrix_sha256":matrix_hash,"full_universe_words":65536,"all_group_generator_incidence_checks":131072,"wall_limit_seconds":300,"scope":"Full fractional descendant packing under exact complement/reversal quotient. A fractional optimum is neither an integer code size nor an integer optimality proof. A dual is trusted only after exact independent full-universe verification. No new-global-record claim."}
before=resource.getrusage(resource.RUSAGE_SELF);t=time.monotonic();r=linprog(-np.ones(len(W)),A_ub=A,b_ub=b,bounds=(0,None),method=method,options={"time_limit":300});after=resource.getrusage(resource.RUSAGE_SELF)
report.update(status=int(r.status),message=str(r.message),numerically_optimal=bool(r.success),solver_wall_seconds=time.monotonic()-t,solver_process_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,numerical_fractional_objective=-float(r.fun) if r.fun is not None else None,iterations=int(r.nit or 0),crossover_iterations=int(getattr(r,"crossover_nit",0)))
if r.x is not None and np.all(np.isfinite(r.x)):
 x=lift_primal(np.maximum(0,r.x),wi,ws);loads=np.zeros(inc.M)
 for w,value in enumerate(x):
  for d in inc.desc[w]:loads[d]+=value
 report["full_primal_max_load"]=float(max(loads));report["full_primal_sum"]=float(x.sum());report["numerically_feasible_primal"]=bool(min(x)>=-1e-8 and max(loads)<=1+1e-7)
 guide={"source_sha":os.environ["GITHUB_SHA"],"length":16,"method":method,"numerical_fractional_objective":report["numerical_fractional_objective"],"numerically_feasible":report["numerically_feasible_primal"],"word_mass":[float(v) for v in x],"role":"Optional stochastic-search guidance; not a code witness or permanent candidate exclusion."};raw=json.dumps(guide,separators=(",",":")).encode();z=gzip.compress(raw,mtime=0);(out/"fractional_guide.json.gz").write_bytes(z);report["guide_json_sha256"]=hashlib.sha256(raw).hexdigest();report["guide_gzip_sha256"]=hashlib.sha256(z).hexdigest()
marginals=getattr(getattr(r,"ineqlin",None),"marginals",None)
if marginals is not None and np.all(np.isfinite(marginals)):
 cert=dual_certificate(inc,marginals,di);cert.update(source_sha=os.environ["GITHUB_SHA"],model_matrix_sha256=matrix_hash,solver_status=int(r.status));p=out/"dual_certificate.json";p.write_text(json.dumps(cert,indent=2));v=subprocess.run([sys.executable,"-B",str(ROOT/"phase3/verify_dual_certificate.py"),str(p)],text=True,capture_output=True,check=True,timeout=300);verified=json.loads(v.stdout);assert verified["valid_dual_certificate"] and verified["integer_upper_bound"]>=226;(out/"dual_verification.json").write_text(json.dumps(verified,indent=2));report["independently_verified_integer_upper_bound"]=verified["integer_upper_bound"];report["dual_certificate_sha256"]=verified["certificate_sha256"]
(out/"report.json").write_text(json.dumps(report,indent=2));print("ORBIT_LP_RESULT",json.dumps(report),flush=True)
