"""Carry the stopped zero-update campaign without resetting its resource use."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from mochi.integrations import digest
from build_contact_v18_preview import public_evidence
from build_terrain_training_preview import public_report

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True)
    a = p.parse_args()
    prior = json.loads((Path(a.source) / 'incomplete.json').read_text())
    assert prior['status'] == 'incomplete' and prior['optimizer_updates_completed'] == 0
    assert not prior['held_out_opened'] and prior['run_id'] == 'mochi-p19-44839589468'
    old = json.loads((ROOT / 'configs/paperfree-v19-training.json').read_text())
    receipts = [r['receipt'] for r in prior['physics_receipts']]
    usage = prior['budget_usage_or_reserved']
    assert usage['physical_rollouts'] == old['engineering_usage']['physical_rollouts'] + sum(r['physical_rollouts'] for r in receipts)
    assert abs(usage['simulation_cpu_hours'] - old['engineering_usage']['simulation_cpu_hours'] - sum(r['duration_seconds'] for r in receipts) / 3600.) < 1e-8
    assert usage['physical_rollouts'] + 22 + 9 + 8 + 4 <= old['bounds']['physical_rollouts']
    evidence = ROOT / 'evidence/paperfree-v19r1/stopped-campaign.json'
    encoded = json.dumps(public_evidence(public_report(prior), prior['run_id']), indent=2) + '\n'
    assert 'tinker://' not in encoded
    evidence.write_text(encoded)
    retained = [json.loads((Path(a.source) / f'teacher-{seed}.json').read_text()) for seed in [211000, 211001]]
    new_seeds = [] if any(t['valid'] for t in retained) else [185000]
    cfg = copy.deepcopy(old)
    cfg.update(study='mochi-paperfree-v19r1', protocol='docs/paperfree-v19r1-amendment.md',
        training_seeds=new_seeds + [211000, 211001], new_training_seeds=new_seeds, retained_training_seeds=[211000, 211001],
        carried_usage=usage, carry={'run_id': prior['run_id'], 'workflow_run': 44839589468,
            'source_sha': prior['source_sha'], 'report_digest': digest(prior), 'evidence': str(evidence.relative_to(ROOT)),
            'teacher_file_sha256': {str(seed): hashlib.sha256((Path(a.source) / f'teacher-{seed}.json').read_bytes()).hexdigest() for seed in [211000, 211001]}},
        scope='Tinker post-trains Qwen3.5-4B LoRA walking/task/recovery selection on real branches. Full-route physics and qualification are unchanged. Branch eligibility uses local constraints; full-route native RMS limits apply to complete references and evaluations. Native gait and book-controller weights stay fixed. Prior zero-update usage, reference and parent measurements are explicitly carried.')
    frozen = cfg['frozen_sha256']
    for name, expected in frozen.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    extras = list((ROOT / 'src/mochi/paperfree_v19r1').glob('*.py')) + [ROOT / n for n in [
        'configs/paperfree-v19-training.json', 'docs/paperfree-v19r1-amendment.md',
        'tests/test_paperfree_v19r1.py', 'scripts/freeze_paperfree_v19r1.py',
        'evidence/paperfree-v19r1/stopped-campaign.json', 'evidence/paperfree-v19r1/branch-scope-probe.json']]
    for path in extras:
        frozen[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    target = ROOT / 'configs/paperfree-v19r1-training.json'
    assert not target.exists(), 'Preserve an existing frozen campaign'
    target.write_text(json.dumps(cfg, indent=2) + '\n')
    print(json.dumps({'frozen_files': len(frozen), 'carried_attempts': usage['physical_rollouts'],
        'carried_cpu_hours': usage['simulation_cpu_hours'], 'maximum_new_attempts': 43,
        'new_training_references': new_seeds, 'old_optimizer_updates': 0}))


if __name__ == '__main__':
    main()
