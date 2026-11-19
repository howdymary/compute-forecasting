"""Freeze the new bounded protocol without modifying the preceding study."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prior=json.loads((ROOT/'configs/terrain-v13-training.json').read_text())
    frozen=dict(prior['frozen_sha256'])
    for name,expected in frozen.items():
        assert sha(ROOT/name)==expected, 'Preserve previous frozen source: '+name
    for path in [*sorted((ROOT/'src/mochi/efficient_v15').glob('*.py')),
                 ROOT/'docs/efficient-v15.md',ROOT/'evidence/efficient-v15/engineering.json']:
        frozen[str(path.relative_to(ROOT))]=sha(path)
    evidence=json.loads((ROOT/'evidence/efficient-v15/engineering.json').read_text())
    assert all(r['complete'] for r in evidence['matched_full_routes'].values())
    train=list(range(91000,91004));dev=list(range(92000,92003));held=list(range(93000,93004))
    proposed=set(train+dev+held)
    for path in (ROOT/'configs').glob('*.json'):
        if path.name.startswith('efficient-v15'):
            continue
        old=json.loads(path.read_text())
        if isinstance(old,dict):
            for key in ['training_seeds','development_seeds','held_out_seeds']:
                assert not proposed.intersection(old.get(key,[])), 'Previously used scenario partition'
    cfg={'study':'mochi-efficient-v15','predecessor_run':44600829444,
        'implementation_prompt':'docs/efficient-v15.md','prompt_sha256':sha(ROOT/'docs/efficient-v15.md'),
        'fallback_report_sha256':sha(ROOT/'web/desk/terrain-training/report.json'),
        'engineering_evidence_sha256':sha(ROOT/'evidence/efficient-v15/engineering.json'),
        'preflight_seed':41001,'training_seeds':train,'development_seeds':dev,'held_out_seeds':held,
        'bounds':{'modal_concurrency':4,'modal_rollouts':224,'modal_cpu_hours':18,'optimizer_updates':16,
            'training_token_presentations':1000000,'inference_tokens':800000,'exa_searches':3,'past_writes':12,'past_recalls':16},
        'training':{'updates':16,'checkpoints':[0,1,4,8,16],'learning_rate':.0001,'seed':151119,
            'base_model':'Qwen/Qwen3.5-4B','domains':['walk','alarm','drawer','laptop','globe','recovery']},
        'frozen_sha256':frozen,
        'smoothness':{**prior['smoothness'],'native_acceleration_rms_max':161.4,'native_torque_change_rms_max':.00371},
        'objective':{'step_reduction_target_fraction':.20,'time_reduction_stretch_fraction':.10,
            'minimum_forward_facing_fraction':.90,'longest_unsupported_seconds_max':.06,
            'priority':'Valid complete sequence and safe smooth motion, then fewer physical step attempts, then time. Early failure has no efficiency advantage.',
            'native_smoothness_caps':'Approximately 20% above measured W0 native-walking proxies; frozen pilot tolerances, not hardware safety certificates.'},
        'data_collection':{'type':'Guarded frozen-parent visitation with exact-state counterfactual branches',
            'max_rollouts_per_seed':37,'task_labels_include_measured_withdrawal':True,
            'first_update_after':'At least two valid complete collectors, all six domains and substantial walking/task corrections; remaining pinned-parent collectors may still run.',
            'global_worker_limit':4,'incremental_branch_archives':True},
        'execution':{'teacher_timeout_s':5400,'evaluation_timeout_s':1800,'component_timeout_s':3600,
            'job_minutes':360,'main_step_minutes':335,'cpu_per_worker':1,'max_workers':4,'numerical_threads':1},
        'scope':'Tinker post-trains shared Qwen3.5-4B LoRA decision weights for directional walking strategies, four contact tasks and arm recovery. Both parent and every checkpoint use the same new navigator and bounded action library. Native ONNX gait weights, MuJoCo physics, scene, route, verifiers and step detector stay fixed. Engineering gains are separate from measured weight-training gains.'}
    target=ROOT/'configs/efficient-v15-training.json'
    target.write_text(json.dumps(cfg,indent=2)+'\n')
    print('Frozen',len(frozen),'source and evidence files; planned physical rollouts204; hard cap224')


if __name__=='__main__':
    main()
