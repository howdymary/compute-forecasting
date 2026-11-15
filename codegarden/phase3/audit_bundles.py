"""Independent protected-string removal enumeration and CP checks of restricted claims."""
import argparse,hashlib,importlib.util,itertools,json,os,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",choices=["component2","root5"],required=True);a=ap.parse_args();check_integrity()
 out=ROOT/"artifacts/phase3/bundle_audit_001"/a.mode;out.mkdir(parents=True,exist_ok=True)
 spec=importlib.util.spec_from_file_location("protected_string_oracle",ROOT/"protected/verify_descendants.py");vd=importlib.util.module_from_spec(spec);spec.loader.exec_module(vd)
 ds=[set(vd.descendants(format(w,"016b"))) for w in range(65536)]
 source=ROOT/"artifacts/phase3/bundle_002/neutral2";paths=sorted(source.glob("state_*.txt"));codes=[sorted(int(w,2) for w in p.read_text().split()) for p in paths]
 assert len(codes)==32
 def h(C):return hashlib.sha256("".join(format(w,"016b")+"\n" for w in sorted(C)).encode()).hexdigest()
 known={h(C) for C in codes};rows=[];started=time.monotonic()
 if a.mode=="component2":
  for file,C in zip(paths,codes):
   checked=verify(file);selected=set(C);owner={d:w for w in C for d in ds[w]};groups={};neighbors=set();augmentations=0;removals=0
   for w,D in enumerate(ds):
    if w in selected:continue
    B=frozenset(owner[d] for d in D if d in owner)
    if len(B)<=2:groups.setdefault(B,[]).append(w)
   for k in range(3):
    for removed in itertools.combinations(C,k):
     removals+=1;R=set(removed);pool=[]
     for size in range(k+1):
      for B in itertools.combinations(removed,size):pool.extend(groups.get(frozenset(B),[]))
     def visit(at,chosen,used):
      nonlocal augmentations
      if len(chosen)>k:augmentations+=1;return
      if len(chosen)==k and chosen:neighbors.add(h(selected-R|set(chosen)))
      for j in range(at,len(pool)):
       w=pool[j]
       if not ds[w]&used:visit(j+1,chosen+[w],used|ds[w])
     visit(0,[],set())
   assert augmentations==0 and neighbors<=known,(augmentations,neighbors-known)
   rows.append({"incumbent_sha256":checked["reports"][0]["witness_sha256"],"removal_sets_all_sizes_0_to_2":removals,
    "neutral_neighbors":sorted(neighbors),"augmentations":augmentations,"complete":True})
   (out/"report.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"status":"running" if len(rows)<32 else "completed",
    "states":rows,"component_size":32,"independent_method":"Explicit removal subsets, protected string D2, no bundle kernel imports",
    "scope":"Complete only for the 32 specified codes and removal radius two","wall_seconds":time.monotonic()-started},indent=2))
   print("BUNDLE_AUDIT",len(rows),flush=True)
 else:
  from ortools.sat.python import cp_model
  C=codes[0];S=set(C);owner={d:w for w in C for d in ds[w]};k=5
  pool=C+[w for w,D in enumerate(ds) if w not in S and len({owner[d] for d in D if d in owner})<=k]
  pool=sorted(pool);model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for w in pool};at={}
  for w,x in xs.items():
   for d in ds[w]:at.setdefault(d,[]).append(x)
  for group in at.values():
   if len(group)>1:model.add_at_most_one(group)
  model.add(sum(xs[w] for w in C)>=len(C)-k);model.add(sum(xs.values())>=len(C)+1)
  solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=180;solver.parameters.num_search_workers=2
  status=solver.solve(model);report={"source_sha":os.environ["GITHUB_SHA"],"incumbent":C,"incumbent_sha256":h(C),"removed_at_most":k,
   "pool":pool,"candidate_pool_sha256":hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in pool)).hexdigest(),
   "target":len(C)+1,"status":solver.status_name(status),"seconds_limit":180,"workers":2,
   "model_sha256":hashlib.sha256(str(model.proto).encode()).hexdigest(),"complete":status==cp_model.INFEASIBLE,
   "proof_artifact":None,"scope":"Independent CP encoding of all improving exchanges removing at most five words from this root; UNKNOWN is no proof."}
  if status in [cp_model.FEASIBLE,cp_model.OPTIMAL]:
   candidate=[w for w,x in xs.items() if solver.value(x)];path=out/"candidate.txt";path.write_text("".join(format(w,"016b")+"\n" for w in sorted(candidate)));report["verification"]=verify(path)
  (out/"report.json").write_text(json.dumps(report,indent=2));print("BUNDLE_ROOT_AUDIT",report["status"],flush=True)
if __name__=="__main__":main()
