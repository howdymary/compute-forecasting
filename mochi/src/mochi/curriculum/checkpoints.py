"""Keep canonical training states; rebuild duplicate inference caches on demand."""
import json
from pathlib import Path

async def retire_reconstructible_mochi_samplers(rest,training_run_id,archive):
    response=await rest.list_checkpoints(training_run_id);by_id={c.checkpoint_id:c for c in response.checkpoints}
    expected=[0,8,16,32]
    for update in expected:
        state=by_id.get(f'weights/mochi_walk_tasks_{update}')
        if state is None or state.checkpoint_type!='training':raise RuntimeError('Missing canonical optimizer state; no cache cleanup permitted')
    plan=[]
    for update in [0,8,16]:
        sampler=by_id.get(f'sampler_weights/mochi_walk_tasks_{update}');state=by_id[f'weights/mochi_walk_tasks_{update}']
        if sampler:
            if sampler.checkpoint_type!='sampler' or not sampler.tinker_path.startswith('tinker://'+training_run_id+'/sampler_weights/mochi_walk_tasks_'):raise RuntimeError('Unexpected cache ownership')
            plan.append({'sampler_cache':sampler.model_dump(mode='json'),'canonical_state':state.model_dump(mode='json'),'reason':'Both were saved consecutively with no intervening optimizer update. Full state retains identical policy weights plus Adam state.'})
    archive=Path(archive);archive.parent.mkdir(exist_ok=True,parents=True);archive.write_text(json.dumps({'training_run_id':training_run_id,'preserved_states':expected,'cache_retirement_plan':plan},indent=2))
    for item in plan:await rest.delete_checkpoint_from_tinker_path(item['sampler_cache']['tinker_path'])
    remaining=await rest.list_checkpoints(training_run_id);after={c.checkpoint_id:c for c in remaining.checkpoints}
    if any(f'weights/mochi_walk_tasks_{u}' not in after for u in expected):raise RuntimeError('Canonical state verification failed')
    return {'retired_reconstructible_sampler_copies':len(plan),'preserved_optimizer_updates':expected,'billing_changed':False},after

class StateSampler:
    """Read-only inference after training, one fixed snapshot per evaluation.

    Each state uses a fresh client: Tinker permits load_state only as the first call.
    The canonical saved states stay immutable. This object never takes gradients.
    """
    def __init__(self,service,client=None):self.service=service;self.client=client
    async def load(self,path):
        self.client=await self.service.create_training_client_from_state(path)
        return await self.client.save_weights_and_get_sampling_client(kind='snapshot')
