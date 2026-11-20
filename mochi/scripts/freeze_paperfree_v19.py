"""Freeze the new scene and objective after bounded physical engineering."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ledger = json.loads((ROOT / 'artifacts/paperfree-v19-engineering/ledger.json').read_text())
    attempts = list(ledger['attempts'].values())
    assert all(a['status'] in ['completed', 'error'] for a in attempts)
    assert len(attempts) <= 12
    reference = next(a for a in attempts if a['id'] == 'paperfree-w8-p5-full')
    assert reference['qualified'], 'The unchanged safety gates must pass before training'
    evidence = {'study': 'mochi-paperfree-v19-engineering', 'attempts': attempts,
        'physical_rollouts': len(attempts),
        'simulation_cpu_hours': sum(a['wall_seconds'] for a in attempts) / 3600.,
        'scope': 'One CPU per local process, elapsed process time. Includes failed diagnostic branches. No new optimizer updates.',
        'source_caveat': 'First seven preliminary attempts predate per-attempt source hashing. Later source hashes are launch-time measurements.',
        'reference': reference['id']}
    target = ROOT / 'evidence/paperfree-v19/engineering.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists(), 'Preserve a previous freeze'
    target.write_text(json.dumps(evidence, indent=2) + '\n')
    previous = json.loads((ROOT / 'configs/contact-v18-training.json').read_text())
    frozen = previous['frozen_sha256'].copy()
    for name, expected in frozen.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    additions = list((ROOT / 'src/mochi/paperfree_v19').glob('*.py'))
    additions += [ROOT / n for n in ['configs/richdesk-v19-paperfree.json',
        'configs/paperfree-v19-controls.json', 'docs/paperfree-v19-protocol.md',
        'tests/test_paperfree_v19.py', 'scripts/freeze_paperfree_v19.py', 'evidence/paperfree-v19/engineering.json']]
    for p in additions:
        frozen[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    cfg = {k: previous[k] for k in ['smoothness', 'walking_goal']}
    cfg.update(study='mochi-paperfree-v19', protocol='docs/paperfree-v19-protocol.md',
        preflight_seed=185000, training_seeds=[211000, 211001],
        development_seeds=[212000, 212001, 212002], held_out_seeds=[213000, 213001, 213002, 213003],
        control_seeds=[213000, 213001],
        bounds={'modal_concurrency': 4, 'physical_rollouts': 112, 'simulation_cpu_hours': 10,
            'optimizer_updates': 8, 'training_token_presentations': 600000, 'inference_tokens': 900000,
            'exa_searches': 2, 'past_writes': 10, 'past_recalls': 12},
        engineering_usage={k: evidence[k] for k in ['physical_rollouts', 'simulation_cpu_hours']},
        engineering_evidence={'path': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()},
        reward={'valid': '1000 - all measured step attempts - bounded arm/time tie-breakers',
            'invalid': -1000000, 'step_weight': 1, 'maximum_combined_tiebreaker': .0011,
            'optimization': 'Reward-derived matched-state supervised labels; not direct low-level gait RL'},
        objective={'step_reduction_target_fraction': .1, 'minimum_forward_facing_fraction': .9,
            'longest_unsupported_seconds_max': .06},
        scene_revision={'version': 'richdesk-v19-paperfree', 'paper_geometry_present': False,
            'forced_paper_route': False, 'laptop_hinge_friction_increment_nm': .015},
        training={'updates': 8, 'checkpoints': [0, 1, 4, 8], 'learning_rate': .0001, 'seed': 202619,
            'domains': ['walk', 'alarm', 'drawer', 'laptop', 'globe', 'recovery']},
        scope='Tinker post-trains Qwen3.5-4B LoRA walking/task/recovery selection. Native gait weights and book controller stay fixed. Paper removal and the same engineered control library are shared by all checkpoints and controls.',
        frozen_sha256=frozen)
    cfg['smoothness']['qualification'] = 'Existing C18 limits retained without relaxation. C19 adds per-flat-leg physical foot-clearance qualification and removes the paper requirement.'
    (ROOT / 'configs/paperfree-v19-training.json').write_text(json.dumps(cfg, indent=2) + '\n')
    print(json.dumps({'attempts': len(attempts), 'engineering_cpu_hours': evidence['simulation_cpu_hours'], 'frozen_files': len(frozen)}))


if __name__ == '__main__':
    main()
