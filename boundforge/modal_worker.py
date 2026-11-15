"""CPU numerical search on Modal; no credentials or verifiers enter workers."""
import pathlib,sys
import modal
HERE=pathlib.Path(__file__).resolve().parent
app=modal.App("boundforge-research")
image=(modal.Image.debian_slim(python_version="3.11")
       .pip_install("numpy==2.2.6","scipy==1.15.3","mpmath==1.3.0")
       .add_local_file(str(HERE/"search.py"),"/root/boundforge/search.py")
       .add_local_file(str(HERE/"precision.py"),"/root/boundforge/precision.py"))
@app.function(image=image,cpu=2,memory=1024,timeout=100,max_containers=4)
def optimize_worker(candidate,seconds):
    import os
    os.environ["OPENBLAS_NUM_THREADS"]="1"
    sys.path.insert(0,"/root/boundforge")
    import search
    return search.optimize(candidate,seconds=min(60,max(1,seconds)))
def remote_optimize(candidate,seconds):
    return optimize_worker.remote(candidate,seconds)

@app.function(image=image,cpu=2,memory=2048,timeout=180,max_containers=2)
def precision_worker(candidate,addition):
    sys.path.insert(0,"/root/boundforge")
    import precision
    return precision.newton(candidate,addition,seconds=130)
