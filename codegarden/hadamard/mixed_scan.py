"""Joint row/column Schur-complement proposals, accepted only by both frozen exact checkers."""
import hashlib,itertools,json,pathlib,time,urllib.request
import numpy as np,sympy as sp
import scan as H
K=pathlib.Path(__file__).resolve().parent;C=H.C;C.BRANCH="codegarden-hadamard-mixed-001";C.OUT=K.parent/"artifacts/hadamard/mixed_001";C.OUT.mkdir(parents=True,exist_ok=True)
def complement(A,inv,i,j):
 n=len(A);I=np.delete(np.arange(n),i);J=np.delete(np.arange(n),j);p=inv[j,i]
 if abs(p)<1e-12:return None
 T=inv[np.ix_(J,I)]-np.outer(inv[J,i],inv[j,I])/p
 return I,J,p,T
def tests():
 rng=np.random.default_rng(5100900);rows=[]
 for n in [3,5,7]:
  while True:
   A=rng.choice([-1,1],size=(n,n));d=H.determinant(A.tolist())
   if d:break
  inv=np.linalg.inv(A.astype(float));cases=0
  for i in range(n):
   for j in range(n):
    parts=complement(A,inv,i,j)
    if parts is None:continue
    I,J,p,T=parts
    assert np.max(np.abs(T@A[np.ix_(I,J)]-np.eye(n-1)))<1e-9
    for _ in range(4):
     r=rng.choice([-1,1],size=n-1);c=rng.choice([-1,1],size=n-1);a=int(rng.choice([-1,1]));B=A.copy();B[i,J]=r;B[I,j]=c;B[i,j]=a
     assert abs(abs(H.determinant(B.tolist())/d)-abs(p*(a-r@T@c)))<1e-9;cases+=1
    allc=np.array(list(itertools.product([-1,1],repeat=n-1)));opt=float(np.max(np.sum(np.abs(allc@T.T),axis=1)))
    if n<=5:
     allr=allc;bilinear=allr@T@allc.T;assert abs(opt-np.max(np.abs(bilinear)))<1e-9
  rows.append({"n":n,"schur_exact_ratio_cases":cases,"complement_inverse_agrees":True,"small_binary_optimum_identity":n<=5})
 return rows
def main():
 for rel,h in json.loads((K/"manifest.json").read_text()).items():assert hashlib.sha256((K/rel).read_bytes()).hexdigest()==h
 C.save("tests.json",tests());C.publish()
 meta=json.load(urllib.request.urlopen("https://einsteinarena.com/api/problems/hadamard-det-51",timeout=30));assert hashlib.sha256(meta["verifier"].encode()).hexdigest()==hashlib.sha256((K/"official.py").read_bytes()).hexdigest()
 row=json.load(urllib.request.urlopen("https://einsteinarena.com/api/solutions/best?problem_id=27&limit=1",timeout=30))[0];data=row["data"];checked=H.verify(data);D=int(checked["determinant"]);assert D==abs(int(sp.Matrix(data["matrix"]).det_bareis()))
 ns={};exec(compile((K/"official.py").read_text(),"official","exec"),ns);baseline=ns["evaluate"](data);assert abs(baseline-row["score"])<1e-12
 A=np.asarray(data["matrix"],dtype=np.int8);inv=np.linalg.inv(A.astype(float));C.save("baseline.json",data);C.save("baseline_verification.json",{"official_score":baseline,"independent":checked,"leader_id":row["id"]});C.publish()
 start=time.monotonic();deadline=start+240;rng=np.random.default_rng(5100901);events=[];trials=0;pairs=0;skipped=0;best_ratio=1.;winner=None;last=start;sweeps=0
 while time.monotonic()<deadline and winner is None:
  ids=rng.permutation(51*51)
  for id_ in ids:
   if time.monotonic()>deadline or winner:break
   i,j=divmod(int(id_),51);parts=complement(A,inv,i,j)
   if parts is None:skipped+=1;continue
   I,J,p,T=parts;pairs+=1
   # Batch independent binary alternating maximizations; no relaxation changes validity.
   X=rng.choice([-1,1],size=(64,50)).astype(np.int8);X[0]=A[I,j]
   for k in range(1,9):
    X[k]=A[I,j];X[k,rng.choice(50,size=k,replace=False)]*=-1
   for iteration in range(40):
    R=np.where(X@T.T>=0,1,-1).astype(np.int8);Y=np.where(R@T>=0,1,-1).astype(np.int8)
    if np.array_equal(X,Y):break
    X=Y
   R=np.where(X@T.T>=0,1,-1).astype(np.int8);ratios=abs(p)*(1+np.einsum("ij,ij->i",R,X@T.T));b=int(np.argmax(ratios));ratio=float(ratios[b]);trials+=len(X)
   best_ratio=max(best_ratio,ratio)
   if ratio>1+1e-10:
    B=A.copy();B[i,J]=R[b];B[I,j]=X[b];B[i,j]=-1
    d=abs(int(sp.Matrix(B.tolist()).det_bareis()))
    events.append({"row":i,"column":j,"float_ratio":ratio,"exact_determinant":str(d),"seconds":time.monotonic()-start})
    if d>D:
     obj={"matrix":B.tolist()};v=H.verify(obj);score=ns["evaluate"](obj);assert int(v["determinant"])==d and score>baseline
     winner={"official_score":score,"independent":v,"move":events[-1]};C.save("best.json",obj);C.save("best_verification.json",winner);C.publish()
   if time.monotonic()-last>40:
    C.save("checkpoint.json",{"pairs_visited":pairs,"binary_restarts":trials,"max_float_ratio":best_ratio,"seconds":time.monotonic()-start,"record_claim":False});C.publish();last=time.monotonic()
  sweeps+=1
 summary={"status":"completed","source_sha":C.SOURCE,"baseline":baseline,"best_verified_score":winner["official_score"] if winner else baseline,"new_leader_candidate":winner is not None,"seed":5100901,"seconds_limit":240,"wall_seconds":time.monotonic()-start,"pairs_visited":pairs,"binary_restarts":trials,"skipped_singular_complements":skipped,"sweeps":sweeps,"max_float_ratio":best_ratio,"scope":"Joint one-row/one-column replacements use binary alternating maximization in a fixed 50x50 complement. Bounded random restarts and floating proposals are not exhaustive or a proof of optimality.","record_claim":False}
 C.save("events.json",events);C.save("summary.json",summary);C.publish();print("HADAMARD_MIXED_FINAL",json.dumps(summary),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  import traceback;traceback.print_exc();C.save("fatal.json",{"error":str(e)[:1500]})
  try:C.publish()
  except Exception:traceback.print_exc()
  raise
