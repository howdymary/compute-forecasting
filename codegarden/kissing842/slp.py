"""Bounded sequential linear programming for the Arena842 overlap penalty; not a kissing-number proof."""
import hashlib,importlib.util,json,os,pathlib,sys,time,urllib.request
from decimal import Decimal
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
K=pathlib.Path(__file__).resolve().parent;ROOT=K.parent;sys.path.insert(0,str(ROOT));sys.path.insert(0,str(K))
from independent import enclosure,tests
sp=importlib.util.spec_from_file_location("k842_publish",ROOT/"side_services/cycle.py");C=importlib.util.module_from_spec(sp);sp.loader.exec_module(C)
C.BRANCH="codegarden-k842-slp-001";C.OUT=ROOT/"artifacts/k842/slp_001";C.OUT.mkdir(parents=True,exist_ok=True);C.ledger.rows=[]
def freeze():
 for name,h in json.loads((K/"manifest.json").read_text()).items():assert hashlib.sha256((K/name).read_bytes()).hexdigest()==h
def module():
 sp=importlib.util.spec_from_file_location("k842_frozen",K/"official.py");m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def fast(U):
 i,j=np.triu_indices(len(U),1);r=np.linalg.norm(U[i]-U[j],axis=1);return float(np.maximum(0,2-2*r).sum())
def design(U,radius):
 n,d=U.shape;i,j=np.triu_indices(n,1);D=U[i]-U[j];r=np.linalg.norm(D,axis=1);keep=2*r<=2+8*np.sqrt(d)*radius
 i=i[keep];j=j[keep];r=r[keep];assert np.min(r)>1e-12
 dot=np.einsum("ij,ij->i",U[i],U[j]);gi=2*(U[j]-dot[:,None]*U[i])/r[:,None];gj=2*(U[i]-dot[:,None]*U[j])/r[:,None]
 M=len(i);ids=np.arange(M);rows=np.r_[np.repeat(ids,d),np.repeat(ids,d),ids];cols=np.r_[(i[:,None]*d+np.arange(d)).ravel(),(j[:,None]*d+np.arange(d)).ravel(),n*d+ids];val=np.r_[gi.ravel(),gj.ravel(),-np.ones(M)]
 A=sparse.coo_matrix((val,(rows,cols)),shape=(M,n*d+M)).tocsr();b=-(2-2*r);cost=np.r_[np.zeros(n*d),np.ones(M)]
 return A,b,cost,[(-radius,radius)]*(n*d)+[(0,None)]*M,M
def derivative_tests():
 rng=np.random.default_rng(842001);U=rng.normal(size=(9,4));U/=np.linalg.norm(U,axis=1)[:,None];i,j=0,1
 dot=U[i]@U[j];r=np.linalg.norm(U[i]-U[j]);g=2*(U[j]-dot*U[i])/r;v=rng.normal(size=4);h=1e-6
 def f(t):
  x=U[i]+t*v;x/=np.linalg.norm(x);return 2-2*np.linalg.norm(x-U[j])
 measured=(f(h)-f(-h))/(2*h);assert abs(measured-g@v)<1e-7
 return {"normalized_distance_derivative_finite_difference":True,"error":abs(measured-g@v)}
def main():
 freeze();O=module();C.save("tests.json",{"interval":tests(),"derivative":derivative_tests()});C.publish()
 p=json.load(urllib.request.urlopen("https://einsteinarena.com/api/problems/kissing-number-d12-842",timeout=30));assert hashlib.sha256(p["verifier"].encode()).hexdigest()==json.loads((K/"manifest.json").read_text())["official.py"]
 row=json.load(urllib.request.urlopen("https://einsteinarena.com/api/solutions/best?problem_id=25&limit=1",timeout=30))[0];base=row["data"];score=O.evaluate(base);assert abs(score-row["score"])<1e-12
 cert=enclosure(base);assert Decimal(cert["lower"])-Decimal("1e-12")<=Decimal(str(score))<=Decimal(cert["upper"])+Decimal("1e-12")
 C.save("baseline.json",base);C.save("baseline_verification.json",{"leader_id":row["id"],"author":row["agentName"],"official_score":score,"independent":cert});C.publish()
 try:
  C.ledger.reserve("exa","codegarden",.1);q="sequential linear programming sphere packing Torquato Jiao trust region nonoverlap constraints"
  r=C.http("https://api.exa.ai/search",os.environ["EXA_API_KEY"],{"query":q,"type":"auto","numResults":3},header="x-api-key")
  C.save("exa_method.json",{"query":q,"request_id":r.get("requestId"),"sources":[{"url":x["url"],"title":x.get("title")} for x in r.get("results",[])],"adaptation":"Tangent-normalized center distances, hinge slack variables and a bounded trust box; actual nonlinear penalty and independent outward intervals accept proposals, not LP objective."});C.publish()
 except Exception as e:C.save("exa_unavailable.json",{"error":str(e)[:400]})
 U=np.asarray(base["vectors"],dtype=float);U/=np.linalg.norm(U,axis=1)[:,None];best=fast(U);baseline_fast=best
 start=time.monotonic();deadline=start+240;radius=1e-4;events=[];winner=None;iteration=0
 while time.monotonic()<deadline-3 and iteration<24:
  A,b,c,bounds,M=design(U,radius);remaining=deadline-time.monotonic()
  if remaining<3:break
  began=time.monotonic();res=linprog(c,A_ub=A,b_ub=b,bounds=bounds,method="highs",options={"time_limit":min(40.,remaining),"dual_feasibility_tolerance":1e-9,"primal_feasibility_tolerance":1e-9})
  event={"iteration":iteration,"radius":radius,"contact_constraints":M,"solver_status":int(res.status),"solver_message":res.message,"solve_seconds":time.monotonic()-began,"before":best,"lp_objective":float(res.fun) if res.fun is not None else None}
  improved=False
  if res.x is not None:
   delta=res.x[:U.size].reshape(U.shape);candidate=None;chosen=0.
   for step in [1.,.5,.25,.125,.0625,.03125,.015625,.0078125]:
    V=U+step*delta;V/=np.linalg.norm(V,axis=1)[:,None];loss=fast(V)
    if loss<best-1e-11:best=loss;candidate=V.copy();chosen=step
   if candidate is not None:U=candidate;improved=True;radius=min(radius*1.4,.005)
   else:radius*=.35
   event.update({"after":best,"accepted_step":chosen,"max_delta":float(np.max(np.abs(delta)))})
  else:radius*=.35
  events.append(event);iteration+=1
  C.save("iterations.json",events);C.save("checkpoint.json",{"best_float":best,"baseline_official":score,"iteration":iteration,"radius":radius,"seconds":time.monotonic()-start,"record_claim":False});C.publish()
  if best<score-1e-7:
   obj={"vectors":U.tolist()};raw=json.dumps(obj,separators=(",",":"));obj=json.loads(raw);actual=O.evaluate(obj);independent=enclosure(obj)
   if actual<score-1e-7 and Decimal(independent["upper"])<Decimal(cert["lower"])-Decimal("1e-7"):
    winner={"official_score":actual,"baseline":score,"independent":independent,"witness_sha256":hashlib.sha256(raw.encode()).hexdigest(),"positive_penalty_is_not_a_kissing_configuration":True}
    C.save("best.json",obj);C.save("best_verification.json",winner);C.publish();break
   C.save("candidate_rejected.json",{"official":actual,"independent":independent,"float":best})
  if radius<1e-10:break
 summary={"status":"completed","source_sha":C.SOURCE,"baseline":score,"baseline_fast":baseline_fast,"best_float":best,"best_verified_score":winner["official_score"] if winner else score,"new_leader_candidate":winner is not None,"iterations":iteration,"wall_seconds":time.monotonic()-start,"search_seconds_limit":240,"record_claim":False,"kissing_number_record_claim":False,"scope":"Local constrained LP repairs of normalized overlap penalty. Nonzero penalties are not valid nonoverlapping kissing configurations. Solver timeout/no local gain is not an impossibility result."}
 C.save("summary.json",summary);C.publish();print("K842_SLP_FINAL",json.dumps(summary),flush=True)
 if winner:
  with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write("has_candidate=true\n")
if __name__=="__main__":
 try:main()
 except Exception as e:
  import traceback;traceback.print_exc();C.save("fatal.json",{"error":str(e)[:1500]})
  try:C.publish()
  except Exception:traceback.print_exc()
  raise
