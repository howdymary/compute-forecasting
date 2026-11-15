"""Read the existing completed C2 volume; never restart the searches."""
import hashlib,importlib.util,json,os,pathlib,subprocess,sys
import numpy as np,modal
ROOT=pathlib.Path(__file__).resolve().parents[1];K=ROOT/"c2";sys.path.insert(0,str(ROOT))
sp=importlib.util.spec_from_file_location("c2_recovery_publish",ROOT/"side_services/cycle.py");C=importlib.util.module_from_spec(sp);sp.loader.exec_module(C)
C.BRANCH="codegarden-c2-recovery-001";C.OUT=ROOT/"artifacts/c2/recovery_001";C.OUT.mkdir(parents=True,exist_ok=True);C.ledger.rows=[]
W=ROOT/"artifacts/c2_witnesses"/os.environ["GITHUB_RUN_ID"];W.mkdir(parents=True,exist_ok=True)
def main():
 for rel,h in json.loads((K/"manifest.json").read_text())["files"].items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h
 spec=importlib.util.spec_from_file_location("c2_recovery_official",K/"official.py");O=importlib.util.module_from_spec(spec);spec.loader.exec_module(O)
 volume=modal.Volume.from_name("codegarden-c2-results-43763414376",create_if_missing=False)
 entries=list(volume.iterdir("/",recursive=True));paths=[e.path.lstrip("/") for e in entries if e.path.endswith("/result.json")]
 C.save("volume_inventory.json",{"volume":"codegarden-c2-results-43763414376","result_paths":paths,"search_rerun":False});C.publish()
 assert len(paths)==2,"Expected both existing terminal results"
 baseline=0.9636615620620854;best=baseline;results=[]
 for rel in paths:
  row=json.loads(b"".join(volume.read_file(rel)));label=row["spec"]["label"];C.save("raw/"+label+".json",row)
  p=W/(label+".npy")
  with p.open("wb") as stream:
   for chunk in volume.read_file(row["best_rel"]):stream.write(chunk)
  assert hashlib.sha256(p.read_bytes()).hexdigest()==row["best_npy_sha256"]
  f=np.load(p,allow_pickle=False);assert f.ndim==1 and 1<=len(f)<=2000000 and np.isfinite(f).all() and np.min(f)>=0 and f.max()>0
  values=np.rint(f/f.max()*(1<<32)).astype(np.uint64).tolist();text=str(len(values))+"\n"+" ".join(map(str,values))+"\n"
  (W/(label+".txt")).write_text(text);(W/(label+".json")).write_text(json.dumps({"values":values},separators=(",",":")))
  r=subprocess.run([str(K/".build/exact")],input=text,text=True,capture_output=True,check=True,timeout=180);exact=json.loads(r.stdout);score=O.evaluate({"values":values});assert abs(score-exact["score"])<1e-10
  row["verification"]={"exact_certificate":exact,"official_score":score,"witness_sha256":hashlib.sha256(text.encode()).hexdigest()};row["recovery_source_sha"]=C.SOURCE
  C.save("workers/"+label+".json",row);results.append(row);C.publish()
  if exact["score"]>best:
   best=exact["score"]
   if best>baseline+1e-9:
    (W/"candidate.txt").write_text(text);(W/"candidate.json").write_text(json.dumps({"values":values},separators=(",",":")));(W/"candidate_target.json").write_text(json.dumps({"baseline":baseline,"source_run_id":43763414376}))
 summary={"status":"recovered_and_exactly_verified","source_run_id":43763414376,"search_rerun":False,"baseline":baseline,"best_reproduced_or_verified":best,"best_exact_verified":max(r["verification"]["exact_certificate"]["score"] for r in results),"workers":[{"label":r["spec"]["label"],"profile":r["profile"],"native":r["best_gpu"],"exact":r["verification"]["exact_certificate"]["score"],"evaluations":r["evaluations"],"seconds":r["wall_seconds"]} for r in results],"new_verified_candidate":best>baseline+1e-9,"arena_min_improvement_met":best>baseline+1e-5,"record_claim":False}
 C.save("summary.json",summary);C.publish()
 if summary["new_verified_candidate"]:
  with open(os.environ["GITHUB_OUTPUT"],"a") as stream:stream.write("has_candidate=true\n")
 print("C2_RECOVERY_FINAL",json.dumps(summary),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  import traceback;traceback.print_exc();C.save("fatal.json",{"error":str(e)[:1500]});C.publish();raise
