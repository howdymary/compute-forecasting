"""Freeze a physically demonstrated V16 campaign while preserving V15."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    prior=json.loads((ROOT/'configs/efficient-v15-training.json').read_text())
    frozen=dict(prior['frozen_sha256'])
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    evidence=ROOT/'evidence/smooth-v16/engineering.json'
    engineering=json.loads(evidence.read_text())
    assert engineering['validated_route']['complete_sequence_success']
    ledger=json.loads((ROOT/'artifacts/smooth-v16-engineering/ledger.json').read_text())
    assert all(r['status'] in ['completed','failed'] for r in ledger.values())
    assert len(ledger)<=32 and sum(r['wall_seconds'] for r in ledger.values())<7200
    for p in [*sorted((ROOT/'src/mochi/smooth_v16').glob('*.py')),ROOT/'docs/smooth-v16-plan.md',evidence]:
        frozen[str(p.relative_to(ROOT))]=sha(p)
    train=list(range(101000,101003));dev=list(range(102000,102003));held=list(range(103000,103004))
    new=set(train+dev+held)
    for p in (ROOT/'configs').glob('*.json'):
        if p.name.startswith('smooth-v16'):continue
        v=json.loads(p.read_text())
        if isinstance(v,dict):
            for k in ['training_seeds','development_seeds','held_out_seeds']:
                assert not new.intersection(v.get(k,[]))
    cfg={'study':'mochi-smooth-v16','implementation_prompt':'docs/smooth-v16-plan.md',
        'prompt_sha256':sha(ROOT/'docs/smooth-v16-plan.md'),'engineering_evidence_sha256':sha(evidence),
        'preflight_seed':41001,'training_seeds':train,'development_seeds':dev,'held_out_seeds':held,
        'bounds':{'modal_concurrency':4,'physical_rollouts':224,'simulation_cpu_hours':18,'optimizer_updates':16,
            'training_token_presentations':1000000,'inference_tokens':900000,'exa_searches':3,'past_writes':12,'past_recalls':16},
        'engineering_usage':{'physical_rollouts':len(ledger),'simulation_cpu_hours':sum(r['wall_seconds'] for r in ledger.values())/3600},
        'training':{'updates':16,'checkpoints':[0,1,4,8,16],'learning_rate':.0001,'seed':161119,
            'base_model':'Qwen/Qwen3.5-4B','domains':['walk','alarm','drawer','laptop','globe','recovery']},
        'frozen_sha256':frozen,
        'smoothness':{**prior['smoothness'],'sequence_time_seconds_max':420},
        'objective':{'step_reduction_target_fraction':.10,'recovery_arm_travel_reduction_target_fraction':.15,
            'minimum_forward_facing_fraction':.90,'longest_unsupported_seconds_max':.06,
            'selection':'Qualified completion and safety first, then meeting both development cost targets without longer time, then lowest normalized steps plus recovery arm travel plus0.1time. Prefer earlier update on ties.',
            'time_scope':'New420-second feasibility horizon declared for new book-turn and paper route before training; all weights and baselines use it.'},
        'data_collection':{'type':'Guarded fixed-parent visitation, exact-state counterfactuals',
            'max_rollouts_per_seed':40,'training_scenarios':3,'incremental_branch_archives':True},
        'execution':{'teacher_timeout_s':5400,'evaluation_timeout_s':2400,'component_timeout_s':3600,
            'job_minutes':360,'main_step_minutes':335,'cpu_per_worker':1,'max_workers':4,'numerical_threads':1},
        'scene_revision':{'version':'richdesk-v16-open-hinge','laptop_hinge_friction_increment_nm':.015},
        'scope':'Tinker post-trains shared Qwen3.5-4B LoRA controller-selection weights for walking, four tasks and arm recovery. Physical turnaround, forward descent, paper-top support rule and action library are engineered before baseline and frozen. Native gait weights stay fixed. Actual checkpoint comparison on structured-state simulation, not hardware or camera policy.'}
    path=ROOT/'configs/smooth-v16-training.json';path.write_text(json.dumps(cfg,indent=2)+'\n')
    print('Frozen',len(frozen),'files; engineering',cfg['engineering_usage'],'planned remote rollouts176')
if __name__=='__main__':main()
