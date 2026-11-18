"""Public numerical status only. No keys or canonical model paths."""
import modal
app=modal.App('mochi-curriculum-v7-monitor')
@app.function(image=modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1'),cpu=.25,memory=256,max_containers=1,serialized=True)
@modal.fastapi_endpoint(method='GET')
def state():return modal.Dict.from_name('mochi-curriculum-v7-progress',create_if_missing=True).get('latest',{'status':'waiting'})
