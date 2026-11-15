"""Public, credential-free replay site; isolated from the forecasting deployment."""
from pathlib import Path
import modal

WEB=Path(__file__).resolve().parents[1]/'web'
image=modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1').add_local_dir(WEB,remote_path='/web',copy=True)
app=modal.App('mochi-policy-studio')

@app.function(image=image,serialized=True,cpu=.25,memory=512,max_containers=2,scaledown_window=60)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    application=FastAPI()
    @application.get('/api/health')
    def health():return {'status':'ok','service':'mochi-policy-studio','mode':'recorded simulation replay'}
    application.mount('/',StaticFiles(directory='/web',html=True),name='web')
    return application
