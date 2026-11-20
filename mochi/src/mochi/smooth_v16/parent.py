"""Restore only the verified, completed V15 optimizer checkpoint."""
import os
import modal
from ..integrations import digest
from ..maintenance.checkpoints_by_date import inventory

async def load_parent(cfg):
    import tinker
    previous=await modal.Dict.from_name('mochi-efficient-v15-progress').get.aio('mochi-t15-44625135986')
    assert previous['status']=='completed' and previous['held_out_opened']
    assert previous['source_sha']=='87ba8d482efd13c789bb200ae9424924e0f77ad1'
    cp=previous['selected_checkpoint']
    assert cp['update']==16 and cp['checkpoint_id']=='63463997da27066bfabda9a834fbd05d627b4dd362720c764077a3d20dd74ebe'
    assert previous['held_out']['selected']['qualified_complete_successes']==4
    matches=[r for r in await inventory(tinker.RestClient()) if digest(r.tinker_path)==cp['checkpoint_id']]
    assert len(matches)==1,'Verified parent optimizer state missing or ambiguous'
    return previous,matches[0].tinker_path,{'source':'Completed V15 selected update16','checkpoint_id':cp['checkpoint_id'],
        'selected_update':16,'cumulative_updates':cp['cumulative_updates'],
        'credential_status':{k:bool(os.environ.get(k)) for k in ['TINKER_API_KEY','MODAL_TOKEN_ID','MODAL_TOKEN_SECRET','EXA_API_KEY','PAST_API_KEY']}}
