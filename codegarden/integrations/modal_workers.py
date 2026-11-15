"""Isolated CPU workers. Entry point refuses an unallocated provider reservation."""
import hashlib,json,os,pathlib,time,uuid
def run_workers(start_words,seeds,seconds,ledger,preferred_action=0):
    import modal
    reservation=ledger.reserve("modal","codegarden",max(1.0,len(seeds)*seconds*.002))
    # Conservative reservation includes cold-start uncertainty; reconcile actual billing later.
    app=modal.App("codegarden-search-v1",tags={"project":"codegarden"})
    image=modal.Image.debian_slim(python_version="3.11")
    for rel in ["search.py","protected/verify_descendants.py","protected/verify_lcs.py"]:
        image=image.add_local_file("codegarden/"+rel,"/opt/codegarden/"+rel)
    volume=modal.Volume.from_name("codegarden-research-v1",create_if_missing=True)
    @app.function(serialized=True,image=image,cpu=1,memory=1024,timeout=300,max_containers=2,
                  volumes={"/codegarden/results":volume})
    def worker(words,seed,budget,preferred):
        import importlib.util,sys
        root=pathlib.Path("/opt/codegarden")
        def load(name,path):
            spec=importlib.util.spec_from_file_location(name,path)
            m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
        S=load("cg_search",root/"search.py")
        D=load("cg_desc",root/"protected/verify_descendants.py")
        L=load("cg_lcs",root/"protected/verify_lcs.py")
        D.verify(words);assert L.verify(words)["valid"]
        start=time.perf_counter();inc=S.Incidence(16)
        S.ARMS=[S.ARMS[preferred]]+[a for i,a in enumerate(S.ARMS) if i!=preferred]
        result=S.run(inc,[int(w,2) for w in words],seed,seconds=budget,max_cycles=100000)
        out=[format(x,"016b") for x in result["best"]]
        result.update({"descendant_verification":D.verify(out),"lcs_verification":L.verify(out),
          "seed":seed,"resources":{"cpu":1,"memory_mb":1024},"runtime_seconds":time.perf_counter()-start,
          "source_sha256":hashlib.sha256((root/"search.py").read_bytes()).hexdigest(),
          "starting_witness_sha256":D.verify(words)["witness_sha256"],"billed_cost_usd":None})
        run_id=uuid.uuid4().hex;path=pathlib.Path("/codegarden/results")/run_id;path.mkdir()
        (path/"experiment.json").write_text(json.dumps(result))
        (path/"witness.txt").write_text("".join(w+"\n" for w in sorted(out)))
        volume.commit()
        return {"run_id":run_id,"best_size":len(out),"words":out,"verification":result["descendant_verification"],
                "lcs":result["lcs_verification"],"runtime_seconds":result["runtime_seconds"],
                "durable_paths":[str(path/"experiment.json"),str(path/"witness.txt")]}
    with app.run():
        reports=list(worker.map([start_words]*len(seeds),seeds,[seconds]*len(seeds),[preferred_action]*len(seeds)))
    ledger.settle(reservation,None) # keep reservation until actual provider usage is available
    return {"project":"codegarden","app":"codegarden-search-v1","reservation_id":reservation,
            "workers":reports,"actual_cost_usd":None,"cost_status":"pending_provider_receipt"}
