"""Four bounded physical tests after rejecting the clock-assisted reference."""
import asyncio,json,os,time
import modal
from .remote import image
from ..curriculum.world import ROOT

app=modal.App('mochi-balanced-v11-clock-clearance')

@app.function(image=image,cpu=1,memory=2048,max_containers=4,timeout=600)
def trial(parameters):
    from .sequence import run
    started=time.perf_counter()
    row=run(31000,True,alarm_x=-.365,alarm_y=.015,capture_margin=.001,
            forward_descent=True,descent_speed=.03,native_stand=True,drawer_profile='B',**parameters)
    row['receipt']={'provider':'Modal','cpu':1,'physical_rollouts':1,'duration_seconds':time.perf_counter()-started}
    row['parameters']=parameters
    return row

async def main():
    out=ROOT/'artifacts/balance-v11-clearance';out.mkdir(parents=True,exist_ok=True)
    status=await modal.Dict.from_name('mochi-balanced-v11-progress').get.aio('latest')
    assert status['audit_memory']['next_experiment']=='strict-lower-speed-and-gait-continuity-four-probe'
    store=modal.Dict.from_name('mochi-balanced-v11-budget');usage=await store.get.aio('usage')
    assert usage is not None and usage['optimizer_updates']==0
    assert usage['modal_rollouts']+4<=256 and usage['modal_cpu_hours']+4*600/3600<=8
    usage['modal_rollouts']+=4;usage['modal_cpu_hours']+=4*600/3600;await store.put.aio('usage',usage)
    parameters=[{'speed':speed,'warm_resume':False} for speed in [.045,.05]]
    report={'study':'mochi-balanced-v11-clearance','source_sha':os.getenv('GITHUB_SHA'),
            'training_gate_open':False,'optimizer_updates_completed':0,'planned_rollouts':4,'results':[]}
    try:
        async with app.run():
            for batch in range(2):
                async for row in trial.map.aio(parameters,order_outputs=True):
                    i=len(report['results']);(out/f'trial-{i}.json').write_text(json.dumps(row,separators=(',',':')))
                    report['results'].append({'parameters':row['parameters'],'complete':row['complete_sequence_success'],
                        'failure':row['failure'],'duration_s':row['episode']['duration'],
                        'ascent_passed':any(a.get('book_top') and a['book_top']['instant_valid'] for a in row['arrivals']),
                        'contact_failures':row['episode']['contact_failures'],'receipt':row['receipt']})
                    (out/'progress.json').write_text(json.dumps(report,indent=2))
                if batch==0:
                    parameters=([{'speed':r['parameters']['speed'],'warm_resume':True} for r in report['results']]
                                if any(r['ascent_passed'] for r in report['results']) else
                                [{'speed':speed,'warm_resume':False,'native_feedback':0.} for speed in [.05,.055]])
        usage['modal_cpu_hours']+=sum(r['receipt']['duration_seconds'] for r in report['results'])/3600-4*600/3600
        await store.put.aio('usage',usage);report['status']='completed';report['budget_usage_or_reserved']=usage
    finally:
        (out/'report.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':asyncio.run(main())
