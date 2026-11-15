import pathlib,sys
import modal
HERE=pathlib.Path(__file__).resolve().parent
app=modal.App("boundforge-structural-v2")
image=(modal.Image.debian_slim(python_version="3.11").pip_install("numpy==2.2.6","scipy==1.15.3")
 .add_local_file(str(HERE/"constructions.py"),"/root/boundforge/constructions.py"))
@app.function(image=image,cpu=2,memory=1024,timeout=75,max_containers=6)
def run_case(spec,nu):
    sys.path.insert(0,"/root/boundforge")
    import constructions
    pts=spec.get("points")
    if pts is None:pts=constructions.support(spec["expr"],24)
    return constructions.optimize(pts,nu,spec["seed"],seconds=25,initial=spec.get("initial"),maxiter=160)
