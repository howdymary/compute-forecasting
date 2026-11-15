"""Bounded full-matrix exchanges. Floating ratios propose; two exact checkers accept."""
import hashlib,importlib.util,json,os,pathlib,subprocess,sys,time,urllib.request
import numpy as np
import sympy as sp
ROOT=pathlib.Path(__file__).resolve().parents[1];K=ROOT/"hadamard";sys.path.insert(0,str(ROOT));sys.path.insert(0,str(K))
from independent import determinant,verify,validate
spec=importlib.util.spec_from_file_location("hadamard_publish",ROOT/"side_services/cycle.py");C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
C.BRANCH="codegarden-hadamard-scan-001";C.OUT=ROOT/"artifacts/hadamard/scan_001";C.OUT.mkdir(parents=True,exist_ok=True);C.ledger.rows=[]
rng=np.random.default_rng(5100701);tests_rng=np.random.default_rng(5100700)
stats={"single_evaluations":0,"pair_evaluations":0,"triple_evaluations":0};deadline=float("inf")
def digest(A):return hashlib.sha256(np.asarray(A,dtype=np.int8).tobytes()).hexdigest()
def proposal(A,pairs=True):
 n=len(A);N=n*n;I,J=np.divmod(np.arange(N),n)
 try:inv=np.linalg.inv(A.astype(np.float64))
 except np.linalg.LinAlgError:return [],0.
 a=A.ravel().astype(float);s=1-2*a*inv.T.ravel();stats["single_evaluations"]+=N
 p=int(np.argmax(np.abs(s)));best=abs(s[p]);move=[p]
 if pairs:
  for start in range(0,N,96):
   if time.monotonic()>deadline:break
   P=np.arange(start,min(N,start+96))
   r=s[P,None]*s[None,:]-4*a[P,None]*a[None,:]*inv[J[P,None],I[None,:]]*inv[J[None,:],I[P,None]]
   r=np.abs(r);r[np.arange(N)[None,:]<=P[:,None]]=0
   stats["pair_evaluations"]+=int(sum(N-int(p)-1 for p in P))
   row,col=np.unravel_index(int(np.argmax(r)),r.shape)
   if r[row,col]>best:best=float(r[row,col]);move=[int(P[row]),int(col)]
 return move,float(best)
def flip(A,move):
 B=A.copy()
 for p in move:B.flat[p]*=-1
 return B
def polish(A,pair_rounds=4):
 trace=[]
 for outer in range(pair_rounds):
  for _ in range(80):
   if time.monotonic()>deadline:return A,trace
   move,r=proposal(A,False)
   if r<=1+1e-11:break
   A=flip(A,move);trace.append(move)
  move,r=proposal(A,True)
  if r<=1+1e-11:break
  A=flip(A,move);trace.append(move)
 return A,trace
def triple(A,count):
 n=len(A);N=n*n
 try:inv=np.linalg.inv(A.astype(float))
 except np.linalg.LinAlgError:return A,None
 ids=rng.integers(0,N,size=(count,3));ids=ids[(ids[:,0]!=ids[:,1])&(ids[:,0]!=ids[:,2])&(ids[:,1]!=ids[:,2])]
 I=ids//n;J=ids%n;delta=-2*A.ravel()[ids].astype(float);M=np.empty((len(ids),3,3))
 for i in range(3):
  for j in range(3):M[:,i,j]=inv[J[:,i],I[:,j]]*delta[:,j]+int(i==j)
 ratios=np.abs(np.linalg.det(M));stats["triple_evaluations"]+=len(ids)
 best=int(np.argmax(ratios));row={"sample_sha256":hashlib.sha256(ids.astype("<u4").tobytes()).hexdigest(),"sample_count":len(ids),"ratio":float(ratios[best]),"move":ids[best].tolist()}
 return (flip(A,row["move"]) if ratios[best]>1+1e-11 else A.copy()),row
def tests():
 rows=[]
 for n in [3,5,7]:
  while True:
   A=tests_rng.choice([-1,1],size=(n,n));d=determinant(A.tolist())
   if d:break
  inv=np.linalg.inv(A.astype(float))
  for _ in range(16):
   move=tests_rng.choice(n*n,size=2,replace=False).tolist();B=flip(A,move)
   p,q=move;i,j=divmod(p,n);k,l=divmod(q,n);d1=-2*A.flat[p];d2=-2*A.flat[q]
   ratio=(1+d1*inv[j,i])*(1+d2*inv[l,k])-d1*d2*inv[j,k]*inv[l,i]
   exact=determinant(B.tolist());assert abs(exact/d-ratio)<1e-10
  for _ in range(8):
   move=tests_rng.choice(n*n,size=3,replace=False).tolist();ids=np.asarray(move);ii,jj=ids//n,ids%n;delta=-2*A.ravel()[ids]
   M=np.eye(3)+inv[jj[:,None],ii[None,:]]*delta[None,:]
   assert abs(determinant(flip(A,move).tolist())/d-np.linalg.det(M))<1e-10
  assert abs(int(sp.Matrix(A.tolist()).det_bareis()))==abs(d)
  rows.append({"n":n,"pair_lemma_cases":16,"triple_lemma_cases":8,"two_exact_methods_agree":True})
 return rows
def main():
 global deadline
 for rel,h in json.loads((K/"manifest.json").read_text()).items():assert hashlib.sha256((K/rel).read_bytes()).hexdigest()==h
 C.save("tests.json",tests());C.publish()
 meta=json.load(urllib.request.urlopen("https://einsteinarena.com/api/problems/hadamard-det-51",timeout=30))
 expected=hashlib.sha256((K/"official.py").read_bytes()).hexdigest();assert hashlib.sha256(meta["verifier"].encode()).hexdigest()==expected
 row=json.load(urllib.request.urlopen("https://einsteinarena.com/api/solutions/best?problem_id=27&limit=1",timeout=30))[0];base=row["data"];validate(base["matrix"])
 ns={};exec(compile((K/"official.py").read_text(),"frozen_hadamard_official","exec"),ns)
 report=verify(base);baseline_D=int(report["determinant"]);official_D=abs(int(sp.Matrix(base["matrix"]).det_bareis()));assert baseline_D==official_D
 baseline_score=ns["evaluate"](base);assert abs(baseline_score-row["score"])<1e-12
 best=np.asarray(base["matrix"],dtype=np.int8);best_D=baseline_D;best_score=baseline_score;events=[];C.save("baseline.json",base);C.save("baseline_verification.json",{"official_score":baseline_score,"independent":report,"leader_id":row["id"],"author":row["agentName"]});C.publish()
 start=time.monotonic();deadline=start+120;restart=0;bank=[best.copy()]
 while time.monotonic()<deadline:
  parent=best.copy() if restart%3 else bank[int(rng.integers(len(bank)))].copy();parent_hash=digest(parent);destroy=[]
  if restart:
   k=int(rng.choice([2,3,4,6,8,12]));destroy=rng.choice(51*51,size=k,replace=False).tolist();parent=flip(parent,destroy)
  A,trace=polish(parent);sample=None
  if restart%4==0 and time.monotonic()<deadline:A,sample=triple(A,100000);A,more=polish(A,2);trace+=more
  D=abs(int(sp.Matrix(A.tolist()).det_bareis()));score=ns["_log10_exact"](D) if D else 0.
  event={"restart":restart,"parent_sha256":parent_hash,"destroy":destroy,"trace":trace,"final_sha256":digest(A),"exact_det":str(D),"score":score,"triple_sample":sample,"seconds":time.monotonic()-start}
  if D>best_D:
   data={"matrix":A.tolist()};checked=verify(data);assert int(checked["determinant"])==D
   best=A.copy();best_D=D;best_score=score;event["independent_verification"]=checked;C.save("best.json",data);C.save("best_verification.json",{"official_score":score,"independent":checked});C.publish()
  if D*1000>=baseline_D*999 and all(digest(A)!=digest(B) for B in bank):
   bank.append(A.copy())
   if len(bank)>8:bank.pop(0)
  events.append(event);restart+=1
  if best_score>baseline_score:break
 summary={"status":"completed","source_sha":C.SOURCE,"problem":"hadamard-det-51","baseline":baseline_score,"best_verified_score":best_score,"baseline_det":str(baseline_D),"best_exact_det":str(best_D),"new_leader_candidate":best_score>baseline_score,"seed":5100701,"seconds_limit":120,"wall_seconds":time.monotonic()-start,"restarts":restart,"stats":stats,"scope":"Floating determinant-ratio scan and bounded perturb/repair; no exact absence proof or neighborhood optimality claimed.","global_record_claim":False}
 C.save("events.json",events);C.save("summary.json",summary);C.publish();print("HADAMARD_SCAN_FINAL",json.dumps(summary),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  import traceback;traceback.print_exc();C.save("fatal.json",{"error":str(e)[:1500]})
  try:C.publish()
  except Exception:traceback.print_exc()
  raise
