"""Normalize completed Mochi status after a legacy custom-type pickle.

TorchVersion is a str subclass whose pickle imports torch. Lightweight status
servers intentionally do not install torch. Numerical status should be plain JSON.
No model, experiment, memory record or credential is changed.
"""
import json
import modal
from mochi.curriculum.remote import base_image
app=modal.App('mochi-progress-maintenance')
@app.function(image=base_image,cpu=.5,memory=1024,timeout=120,serialized=True)
def normalize():
    store=modal.Dict.from_name('mochi-curriculum-v7-progress');report=store.get('latest',{})
    if report.get('status') not in ['completed','incomplete']:
        return {'normalized':False,'reason':'Active producer retained','status':report.get('status')}
    plain=json.loads(json.dumps(report));store.put('latest',plain)
    return {'normalized':True,'status':plain['status'],'optimizer_updates_completed':plain.get('optimizer_updates_completed')}
@app.local_entrypoint()
def main():print(json.dumps(normalize.remote()))
