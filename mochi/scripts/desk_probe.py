"""Readiness checks; no secret values enter logs or artifacts."""
import asyncio,json,os
from pathlib import Path
import httpx,modal

app=modal.App('mochi-desk-v3-readiness')
@app.function(image=modal.Image.debian_slim(python_version='3.11').pip_install('httpx==0.28.1'),cpu=.25,memory=256,timeout=30)
def remote_probe():return {'service':'Modal','executed':True}

async def run():
    out=Path('mochi/artifacts/desk-v3');out.mkdir(parents=True,exist_ok=True);status={}
    print('PROBE: past.dev',flush=True)
    async with httpx.AsyncClient(timeout=60) as client:
        response=await client.get('https://api.past.dev/api/v1/usage',headers={'Authorization':'Bearer '+os.environ['PAST_API_KEY']});status['past.dev']={'http_status':response.status_code};response.raise_for_status()
        print('PROBE: Exa',flush=True)
        response=await client.post('https://api.exa.ai/search',headers={'x-api-key':os.environ['EXA_API_KEY']},json={'query':'planar robotic pushing control rectangular object orientation','numResults':1});status['Exa']={'http_status':response.status_code};response.raise_for_status()
    import tinker
    print('PROBE: Tinker',flush=True)
    caps=await asyncio.wait_for(tinker.ServiceClient().get_server_capabilities_async(),180);names=[x.model_name for x in caps.supported_models];status['Tinker']={'authenticated':True,'base_model_available':'Qwen/Qwen3.5-4B' in names}
    print('PROBE: Modal',flush=True)
    async with app.run():status['Modal']=await remote_probe.remote.aio()
    (out/'readiness.json').write_text(json.dumps(status,indent=2));print(json.dumps(status))
if __name__=='__main__':
    with modal.enable_output():asyncio.run(run())
