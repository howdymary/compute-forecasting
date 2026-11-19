"""Resolve a completed qualified parent without downloading private archives."""
import hashlib
import json
import os

import modal

from ..curriculum.world import ROOT
from ..integrations import digest
from ..maintenance.checkpoints_by_date import inventory


def ready_for_new_training(job,report,allow_evaluation_overlap):
    if job['status']=='completed':
        return True
    authorized=report.get('protocol',{}).get('training',{}).get('updates') if report else None
    return bool(allow_evaluation_overlap and authorized==16 and report.get('optimizer_updates_completed')==authorized)


async def load_parent(cfg):
    import tinker
    status_path=ROOT/'.cache/v15-predecessor-status.json'
    status=json.loads(status_path.read_text())
    trains=[j for j in status['jobs'] if j['name']=='train']
    assert len(trains)==1
    previous=await modal.Dict.from_name('mochi-terrain-v13-progress').get.aio('mochi-t13-'+str(cfg['predecessor_run']))
    assert ready_for_new_training(trains[0],previous,cfg['execution']['allow_evaluation_overlap']), 'The predecessor still has authorized optimizer work remaining'
    reasons=[]
    if trains[0]['status']!='completed':
        reasons.append('All16 predecessor optimizer updates completed; its physical evaluation continues independently. Restore only an already completed qualified parent.')
    if previous and previous.get('status')=='completed' and previous.get('held_out_opened'):
        held=previous.get('held_out',{})
        selected=held.get('selected',{})
        parent=held.get('parent',{})
        qualified=(selected.get('smooth_complete_successes',0)>=parent.get('smooth_complete_successes',0)
            and selected.get('complete_successes',0)>0
            and selected.get('falls',1e9)<=parent.get('falls',0)
            and selected.get('invalid_contacts',1e9)<=parent.get('invalid_contacts',0))
        if qualified:
            source='Completed qualified V13 selection'
        else:
            reasons.append('Completed V13 selection did not pass the declared parent qualification')
            previous=None
    else:
        reasons.append('V13 has no completed evaluated selection')
        previous=None
    if previous is None:
        path=ROOT/'web/desk/terrain-training/report.json'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==cfg['fallback_report_sha256']
        previous=json.loads(path.read_text())
        assert previous['status']=='completed' and previous['held_out_opened']
        source='Completed V12 development-selected update 1'
    checkpoint=previous['selected_checkpoint']
    records=await inventory(tinker.RestClient())
    matches=[r for r in records if digest(r.tinker_path)==checkpoint['checkpoint_id']]
    assert len(matches)==1, 'Selected canonical optimizer state is absent or ambiguous'
    selection={'source':source,'checkpoint_id':checkpoint['checkpoint_id'],
        'selected_update':checkpoint['update'],'cumulative_updates':checkpoint['cumulative_updates'],
        'reasons':reasons,'predecessor_run':cfg['predecessor_run'],
        'predecessor_train_conclusion':trains[0]['conclusion'],
        'credential_status':{k:bool(os.environ.get(k)) for k in ['TINKER_API_KEY','MODAL_TOKEN_ID','MODAL_TOKEN_SECRET','EXA_API_KEY','PAST_API_KEY']}}
    return previous,matches[0].tinker_path,selection
