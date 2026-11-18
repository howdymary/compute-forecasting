"""Public numerical status only; provider error details stay in execution artifacts."""
import modal
app=modal.App('mochi-curriculum-v7-monitor')
@app.function(image=modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1'),cpu=.25,memory=256,max_containers=1,serialized=True)
@modal.fastapi_endpoint(method='GET')
def state():
    report=modal.Dict.from_name('mochi-curriculum-v7-progress',create_if_missing=True).get('latest',{'status':'waiting'})
    public={k:report.get(k) for k in ['study','status','phase','created_at','completed_at','source_sha','optimizer_updates_completed','rollouts','selected_checkpoint','checkpoints','held_out','held_out_isolated_contact','held_out_isolated_walking','paired_outcomes','paired_full_success_gain','error_type']}
    services=report.get('services',{});calls=services.get('calls',[])
    public['services']={'eligibility':services.get('eligibility',{}),'usage':{'writes':sum(c['method']=='POST' and c['kind']=='ingest' for c in calls),'recalls':sum(c['method']=='POST' and c['kind']=='recall' for c in calls),'ingestion_polls':sum(c['method']=='GET' and c['kind']=='ingest' for c in calls),'authoritative_credit_usage':None}}
    public['recovery']={k:report.get('recovery',{}).get(k) for k in ['training_run','evaluation_run','extra_optimizer_updates','saved_state_inference_probe_passed']}
    return public
