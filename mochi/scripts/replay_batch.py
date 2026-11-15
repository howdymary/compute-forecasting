"""Record a disclosed development highlight with the already frozen V1 policy."""
import asyncio,json,time,hashlib
from pathlib import Path
from dataclasses import asdict
import modal
from mochi.remote import image
from mochi.simulation import ROOT,Policy
app=modal.App('mochi-cinematic-replays')
@app.function(image=image,cpu=1,memory=1024,max_containers=2,timeout=180)
def record(policy,seed):
    from mochi.simulation import Policy,rollout
    started=time.perf_counter();r=rollout(Policy(**policy),seed,record=True)
    r['remote_receipt']={'provider':'Modal','duration_seconds':time.perf_counter()-started,'cpu_requested':1,'memory_mib':1024}
    return r
async def main():
    source=ROOT/'web/data/report.json';report=json.loads(source.read_text());pairs=report['evaluation']['development']['paired_results']
    candidates=[(a['final_distance_m']-b['final_distance_m'],a['scenario']['seed']) for a,b in zip(pairs['baseline'],pairs['selected']) if not a['success'] and b['success']]
    seed=max(candidates)[1];out=ROOT/'artifacts/cinematic-replays';out.mkdir(parents=True,exist_ok=True)
    async with app.run():
        before,after=[r async for r in record.starmap.aio([(asdict(Policy()),seed),(report['selected'],seed)])]
    assert not before['success'] and after['success']
    for name,value in [('baseline',before),('selected',after)]:
        (out/(name+'.json')).write_text(json.dumps(value,indent=2,allow_nan=False))
    meta={'source_run':report['run_id'],'source_report_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'seed':seed,'scope':'Development illustration deliberately selected for the largest final-distance improvement among successful selected-policy development trials. Not held-out evidence.','rollouts':2,'provider':'Modal','before_distance_m':before['final_distance_m'],'after_distance_m':after['final_distance_m']}
    (out/'provenance.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta))
if __name__=='__main__':
    with modal.enable_output():asyncio.run(main())
