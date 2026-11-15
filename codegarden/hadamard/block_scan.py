"""Large row-block neighborhoods from inverse-column projections; exact gates remain frozen."""
import itertools,hashlib,json,pathlib,time,urllib.request
import numpy as np,sympy as sp
import scan as H
K=pathlib.Path(__file__).resolve().parent;C=H.C;C.BRANCH="codegarden-hadamard-block-001";C.OUT=K.parent/"artifacts/hadamard/block_001";C.OUT.mkdir(parents=True,exist_ok=True)
def best_two(V):
 a=np.unique(np.mod(np.arctan2(V[:,1],V[:,0])+np.pi/2,np.pi));mid=(a+np.r_[a[1:],a[0]+np.pi])/2
 R=np.where(np.cos(mid)[:,None]*V[:,0]+np.sin(mid)[:,None]*V[:,1]>=0,1,-1).astype(np.int8);P=R@V
 areas=np.abs(P[:,0,None]*P[None,:,1]-P[:,1,None]*P[None,:,0]);i,j=np.unravel_index(int(np.argmax(areas)),areas.shape)
 return R[[i,j]],float(areas[i,j])
def tests():
 rng=np.random.default_rng(5100800);rows=[]
 for n in [3,5,7]:
  while True:
   A=rng.choice([-1,1],size=(n,n));D=H.determinant(A.tolist())
   if D:break
  inv=np.linalg.inv(A.astype(float));V=inv[:,[0,1]];R,value=best_two(V);B=A.copy();B[[0,1]]=R
  assert abs(abs(H.determinant(B.tolist())/D)-value)<1e-9
  all_rows=np.array(list(itertools.product([-1,1],repeat=n)));P=all_rows@V;brute=np.max(np.abs(P[:,0,None]*P[None,:,1]-P[:,1,None]*P[None,:,0]));assert abs(brute-value)<1e-9
  for _ in range(8):
   X=rng.choice([-1,1],size=(3,n));B=A.copy();B[:3]=X
   assert abs(H.determinant(B.tolist())/D-np.linalg.det(X@inv[:,:3]))<1e-9
  rows.append({"n":n,"row_pair_vertex_max_matches_full_small_enumeration":True,"rank3_lemma_cases":8})
 return rows
def main():
 for rel,h in json.loads((K/"manifest.json").read_text()).items():assert hashlib.sha256((K/rel).read_bytes()).hexdigest()==h
 C.save("tests.json",tests());C.publish()
 meta=json.load(urllib.request.urlopen("https://einsteinarena.com/api/problems/hadamard-det-51",timeout=30));assert hashlib.sha256(meta["verifier"].encode()).hexdigest()==hashlib.sha256((K/"official.py").read_bytes()).hexdigest()
 row=json.load(urllib.request.urlopen("https://einsteinarena.com/api/solutions/best?problem_id=27&limit=1",timeout=30))[0];data=row["data"];checked=H.verify(data);D=int(checked["determinant"]);assert D==abs(int(sp.Matrix(data["matrix"]).det_bareis()))
 ns={};exec(compile((K/"official.py").read_text(),"official","exec"),ns);baseline=ns["evaluate"](data);assert abs(baseline-row["score"])<1e-12
 A=np.asarray(data["matrix"],dtype=np.int8);C.save("baseline.json",data);C.save("baseline_verification.json",{"official_score":baseline,"independent":checked,"leader_id":row["id"]});C.publish()
 start=time.monotonic();deadline=start+180;rng=np.random.default_rng(5100801);events=[];pairs=0;triples=0;best_numeric=1.;winner=None
 def accept(B,info):
  nonlocal winner
  d=abs(int(sp.Matrix(B.tolist()).det_bareis()))
  if d<=D:return False
  obj={"matrix":B.tolist()};v=H.verify(obj);assert int(v["determinant"])==d;score=ns["evaluate"](obj);assert score>baseline
  winner={"official_score":score,"independent":v,"move":info};C.save("best.json",obj);C.save("best_verification.json",winner);C.publish();return True
 # Optimize two complete rows or columns via a 2D zonotope vertex proposal.
 for transpose in [False,True]:
  T=A.T.copy() if transpose else A.copy();inv=np.linalg.inv(T.astype(float));candidate=None;best_ratio=1.
  for i in range(51):
   for j in range(i+1,51):
    if time.monotonic()>deadline:break
    R,ratio=best_two(inv[:,[i,j]]);pairs+=1
    if ratio>best_ratio:best_ratio=ratio;candidate=(i,j,R.copy())
   if time.monotonic()>deadline:break
  best_numeric=max(best_numeric,best_ratio);events.append({"type":"column_pairs" if transpose else "row_pairs","max_float_ratio":best_ratio,"seconds":time.monotonic()-start})
  if best_ratio>1+1e-10 and candidate:
   i,j,R=candidate;B=T.copy();B[[i,j]]=R
   if accept(B.T.copy() if transpose else B,{"type":events[-1]["type"],"indices":[i,j],"ratio":best_ratio}):break
 if winner is None:
  inv=np.linalg.inv(A.astype(float))
  while time.monotonic()<deadline:
   I=np.sort(rng.choice(51,size=3,replace=False));U=inv[:,I];X=A[I].copy()
   if triples%4:X=rng.choice([-1,1],size=(3,51)).astype(np.int8)
   previous=-1.;ratio=0.
   for iteration in range(12):
    if time.monotonic()>deadline:break
    t=iteration%3;others=[k for k in range(3) if k!=t];q=X[t]@U
    if np.linalg.norm(q)<1e-12:X[t]=rng.choice([-1,1],size=51);continue
    plane=np.linalg.svd(q.reshape(1,3),full_matrices=True)[2][1:].T
    X[others]=best_two(U@plane)[0];P=X@U;normal=np.cross(P[others[0]],P[others[1]]);X[t]=np.where(U@normal>=0,1,-1)
    ratio=abs(float(np.linalg.det(X@U)));best_numeric=max(best_numeric,ratio)
    if ratio>1+1e-10:
     B=A.copy();B[I]=X
     if accept(B,{"type":"rank3_block","indices":I.tolist(),"iteration":iteration,"trial":triples,"ratio":ratio}):break
    if iteration>=4 and ratio<=previous+1e-12:break
    previous=ratio
   triples+=1
   if triples<=20 or triples%100==0:events.append({"type":"rank3_trial","trial":triples,"indices":I.tolist(),"last_ratio":ratio,"seconds":time.monotonic()-start})
   if winner:break
 summary={"status":"completed","source_sha":C.SOURCE,"baseline":baseline,"best_verified_score":winner["official_score"] if winner else baseline,"new_leader_candidate":winner is not None,"seed":5100801,"seconds_limit":180,"wall_seconds":time.monotonic()-start,"row_or_column_pairs":pairs,"rank3_trials":triples,"max_float_ratio":best_numeric,"scope":"Floating inverse projections generate two- and three-row block replacements. Exact independent determinants alone accept gains. No proof of neighborhood or global optimality.","record_claim":False}
 C.save("events.json",events);C.save("summary.json",summary);C.publish();print("HADAMARD_BLOCK_FINAL",json.dumps(summary),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  import traceback;traceback.print_exc();C.save("fatal.json",{"error":str(e)[:1500]})
  try:C.publish()
  except Exception:traceback.print_exc()
  raise
