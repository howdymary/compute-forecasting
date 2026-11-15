"""Parallel compiled CPU research with durable, independent witness checks."""
import hashlib,importlib.util,json,os,pathlib,subprocess,sys,time,uuid
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from providers import Ledger
from supervisor import verify
def main():
    import modal
    out=ROOT/"artifacts/native";out.mkdir(parents=True,exist_ok=True)
    ledger=Ledger(out);reserve_build=ledger.reserve("modal","codegarden",1)
    seeds=[9101,9201,9301,9401];seconds=120;tasks=[(s,p) for s in seeds for p in ["fixed","adaptive"]]
    reservation=ledger.reserve("modal","codegarden",len(tasks)*seconds*.002)
    image=modal.Image.debian_slim(python_version="3.11").apt_install("g++")
    image=image.add_local_file(str(ROOT/"kernel.cpp"),"/opt/codegarden/kernel.cpp",copy=True)
    image=image.run_commands("g++ -O3 -std=c++17 /opt/codegarden/kernel.cpp -o /opt/codegarden/kernel")
    for rel in ["protected/verify_descendants.py","protected/verify_lcs.py"]:
        image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
    app=modal.App("codegarden-native-search-v1",tags={"project":"codegarden"})
    volume=modal.Volume.from_name("codegarden-native-results-v1",create_if_missing=True)
    @app.function(serialized=True,image=image,cpu=1,memory=768,timeout=240,max_containers=4,volumes={"/codegarden/results":volume})
    def worker(words,seed,policy,seconds):
        import threading
        run_id=uuid.uuid4().hex;path=pathlib.Path("/codegarden/results")/run_id;path.mkdir()
        checkpoint=path/"checkpoint.txt";stopped=threading.Event();commits=[]
        def checkpoint_commit():
            while not stopped.wait(20):
                try:volume.commit();commits.append(time.time())
                except Exception:pass
        thread=threading.Thread(target=checkpoint_commit,daemon=True);thread.start()
        start=time.perf_counter()
        try:
            p=subprocess.run(["/opt/codegarden/kernel",str(seconds),str(seed),policy,str(checkpoint),"227"],
              input="\n".join(words)+"\n",text=True,capture_output=True,timeout=seconds+30,check=True)
            result=json.loads(p.stdout)
        finally:stopped.set();thread.join(timeout=3)
        def load(name,rel):
            spec=importlib.util.spec_from_file_location(name,"/opt/codegarden/"+rel)
            m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
        D=load("native_desc","protected/verify_descendants.py");L=load("native_lcs","protected/verify_lcs.py")
        final=[format(w,"016b") for w in result["best"]]
        result["descendant_verification"]=D.verify(final);result["lcs_verification"]=L.verify(final)
        result["words"]=final;result["runtime_seconds"]=time.perf_counter()-start
        result["kernel_sha256"]=hashlib.sha256(pathlib.Path("/opt/codegarden/kernel.cpp").read_bytes()).hexdigest()
        result["resources"]={"cpu":1,"memory_mb":768};result["durable_checkpoint_commits"]=len(commits)
        for i,code in enumerate(result["archive"]):
            text=[format(w,"016b") for w in code];D.verify(text)
            (path/("incumbent_"+str(i)+".txt")).write_text("\n".join(sorted(text))+"\n")
        (path/"result.json").write_text(json.dumps(result));(path/"witness.txt").write_text("\n".join(sorted(final))+"\n")
        volume.commit();result["durable_run_id"]=run_id;return result
    base=(ROOT/"artifacts/best_code.txt").read_text().splitlines();verify(ROOT/"artifacts/best_code.txt")
    with app.run():
        results=list(worker.map([base]*len(tasks),[s for s,p in tasks],[p for s,p in tasks],[seconds]*len(tasks)))
    for i,r in enumerate(results):
        path=out/("worker_"+str(i)+".txt");path.write_text("\n".join(sorted(r["words"]))+"\n")
        r["fresh_host_verification"]=verify(path)
    report={"source_sha":os.getenv("GITHUB_SHA"),"workers":results,"budget":ledger.summary(),
      "best_verified":max(r["fresh_host_verification"]["cardinality"] for r in results),
      "evaluation":"paired seeds, same 120-second maximum, stop on first 227; CPU platforms may differ",
      "scope":"native fixed versus adaptive operator controller; not a Tinker weight comparison",
      "actual_provider_cost":None,"cost_status":"reservations retained pending provider billing reconciliation"}
    (out/"report.json").write_text(json.dumps(report))
    print("NATIVE_FINAL "+json.dumps({"best_verified":report["best_verified"],
      "workers":[{"seed":r["seed"],"policy":r["policy"],"size":r["fresh_host_verification"]["cardinality"],
       "seconds":r["seconds"],"iterations":r["iterations"]} for r in results],"budget":report["budget"]}),flush=True)
if __name__=="__main__":main()
