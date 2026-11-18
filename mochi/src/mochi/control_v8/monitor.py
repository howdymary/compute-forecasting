"""Credential-free numerical progress; no model paths or memory payloads."""
import modal
app=modal.App('mochi-control-v8-monitor')
image=modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1')
@app.function(image=image,serialized=True,cpu=.25,memory=256,max_containers=1)
@modal.fastapi_endpoint(method='GET')
def status():
 r=modal.Dict.from_name('mochi-control-v8-progress',create_if_missing=True).get('latest',{})
 public={k:r.get(k) for k in ['study','status','phase','source_sha','optimizer_updates_completed','parent_optimizer_updates','new_optimizer_updates','training_study','rollouts','new_modal_rollouts','data_audit','checkpoints','selected_checkpoint','held_out','error_type']};last=(r.get('training_log') or [{}])[-1]
 public.update(training_domains=list(last.get('domain_counts',{})),latest_training_receipt=last,memory=r.get('services',{}).get('eligibility',{}),exa_searches=len(r.get('services',{}).get('sources',[])),updated_at=last.get('at'),error='See the workflow execution log' if r.get('error') else None);return public

@app.function(image=image,serialized=True,cpu=.25,memory=256,max_containers=1)
@modal.fastapi_endpoint(method='GET')
def clearance_status():
 r=modal.Dict.from_name('mochi-control-clearance-progress',create_if_missing=True).get('latest',{})
 public={k:r.get(k) for k in ['study','status','phase','source_sha','optimizer_updates_completed','parent_optimizer_updates','new_optimizer_updates','training_study','rollouts','new_modal_rollouts','data_audit','checkpoints','selected_checkpoint','held_out','error_type']};last=(r.get('training_log') or [{}])[-1]
 public.update(training_domains=list(last.get('domain_counts',{})),latest_training_receipt=last,memory=r.get('services',{}).get('eligibility',{}),exa_searches=len(r.get('services',{}).get('sources',[])),updated_at=last.get('at'),error='See the workflow execution log' if r.get('error') else None);return public
