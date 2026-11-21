"""Recompute completion, step selection and accounting from retained records."""
import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path

from mochi.paperfree_v19.objective import paired, select_checkpoint, summary

ROOT = Path(__file__).resolve().parents[1]


def choice_comparison(before, after):
    """Describe executed choices separately from numerical differences."""
    def choices(row):
        result = {}
        for item in row['model_decisions']:
            o = item['observation']
            station = o.get('station') or o.get('task') or o['domain']
            key = o['domain'] + ':' + station
            assert key not in result
            result[key] = item['action']
        return result

    a, b = choices(before), choices(after)
    categories = []
    for row in [before, after]:
        counts = {}
        for event in row['episode']['step_events']:
            name = event['category']
            counts[name] = counts.get(name, 0) + 1
        assert sum(counts.values()) == row['episode']['steps']['attempts']
        categories.append(counts)
    return {
        'seed': before['seed'],
        'both_qualified': bool(before['qualified_complete'] and after['qualified_complete']),
        'changed_choices': [{'decision': key, 'before': a[key], 'after': b[key]}
            for key in sorted(a.keys() & b.keys()) if a[key] != b[key]],
        'unmatched_choices': {'before_only': sorted(a.keys() - b.keys()),
            'after_only': sorted(b.keys() - a.keys())},
        'step_categories': {'before': categories[0], 'after': categories[1]},
        'interpretation': 'Observed action and step differences do not isolate causality. Native gait weights stayed fixed. Shorter failed attempts are not efficiency gains.',
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True)
    a = p.parse_args()
    source = Path(a.source)
    report = json.loads((source / 'report.json').read_text())
    cfg = report['protocol']
    assert report['status'] == 'completed' and report['held_out_opened']
    assert report['study'] == cfg['study'] and cfg['study'] in ['mochi-paperfree-v19', 'mochi-paperfree-v19r1']
    for name, expected in cfg['frozen_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    partitions = [set(cfg[k]) for k in ['training_seeds', 'development_seeds', 'held_out_seeds']]
    assert all(not a & b for i, a in enumerate(partitions) for b in partitions[i + 1:])
    assert len(report['training_log']) == report['optimizer_updates_completed'] == 8
    losses = 0
    for record in report['training_log']:
        assert record['optimizer_completed'] and record['forward_backward_completed']
        assert set(record['domain_loss_metrics']) == set(cfg['training']['domains'])
        for domain_metrics in record['domain_loss_metrics'].values():
            assert all(math.isfinite(v) for v in domain_metrics.values() if isinstance(v, (float, int)))
            losses += 1
    assert losses == 48
    assert max(report['first_optimizer_probability_change'].values()) > 1e-7
    assert sum(r['tokens'] for r in report['training_log']) == report['budget_usage_or_reserved']['training_token_presentations']
    checkpoints = copy.deepcopy(report['checkpoints'])
    for cp in checkpoints:
        rows = json.loads((source / f'checkpoint-{cp["update"]}.json').read_text())
        assert {r['seed'] for r in rows} == set(cfg['development_seeds'])
        assert summary(rows, cfg) == cp['development'], cp['update']
    assert select_checkpoint(checkpoints)['update'] == report['selected_checkpoint']['update']
    cohorts = {}
    for label in ['parent', 'selected', 'fixed', 'static']:
        cohorts[label] = json.loads((source / ('held-out-' + label + '.json')).read_text())
        assert summary(cohorts[label], cfg) == report['held_out'][label], label
    assert paired(cohorts['parent'], cohorts['selected']) == report['paired_held_out']
    selected = report['selected_checkpoint']['update']
    parent_dev = json.loads((source / 'checkpoint-0.json').read_text())
    selected_dev = json.loads((source / f'checkpoint-{selected}.json').read_text())
    action_audit = {}
    for name, before, after in [('development', parent_dev, selected_dev),
            ('held_out', cohorts['parent'], cohorts['selected'])]:
        by_seed = {row['seed']: row for row in after}
        action_audit[name] = [choice_comparison(row, by_seed[row['seed']]) for row in before]
    (ROOT / 'evidence/paperfree-v19r1/choice-audit.json').write_text(json.dumps(action_audit, indent=2) + '\n')
    receipts = [r['receipt'] for r in report['physics_receipts']]
    carried = cfg.get('carried_usage', cfg['engineering_usage'])
    attempts = carried['physical_rollouts'] + sum(r['physical_rollouts'] for r in receipts)
    hours = carried['simulation_cpu_hours'] + sum(r['duration_seconds'] for r in receipts) / 3600.
    assert attempts == report['budget_usage_or_reserved']['physical_rollouts']
    assert abs(hours - report['budget_usage_or_reserved']['simulation_cpu_hours']) < 1e-8
    for key, used in report['budget_usage_or_reserved'].items():
        assert used <= cfg['bounds'][key], key
    manifest = json.loads((ROOT / 'web/desk/paperfree-v19/manifest.json').read_text())
    assert manifest['evaluation_status'] == 'completed'
    assert len(manifest['recordings']) == 20
    assert not any(p['name'] == 'sticky-notes' for p in manifest['scene']['props'])
    for file, meta in manifest['recordings'].items():
        data = (ROOT / 'web/desk/paperfree-v19' / file).read_bytes()
        assert hashlib.sha256(data).hexdigest() == meta['sha256']
        raw = gzip.decompress(data)
        assert hashlib.sha256(raw).hexdigest() == meta['uncompressed_sha256']
        episode = json.loads(raw)
        assert not episode['paper_geometry_present']
        assert not episode['postit_crossings']
        assert all(e.get('step_category') != 'postit_crossing' for e in episode['balance_measurements'])
        assert episode['maximum_applied_base_force'] == 0
        assert episode['steps']['attempts'] == meta['steps']['attempts'] == len(episode['step_events'])
        frames = episode['trajectory']['frames']
        assert frames[0]['t'] < .1
        assert all(b['t'] > a['t'] for a, b in zip(frames, frames[1:]))
    result = {'study': report['study'], 'run_id': report['run_id'], 'source_sha': report['source_sha'],
        'frozen_files_verified': len(cfg['frozen_sha256']), 'optimizer_updates_verified': 8,
        'domain_backwards_verified': losses, 'physical_attempts_accounted': attempts,
        'simulation_cpu_hours_accounted': hours, 'recordings_verified': len(manifest['recordings']),
        'selected_update': report['selected_checkpoint']['update'],
        'held_out': report['held_out'], 'paired_held_out': report['paired_held_out'],
        'improvement_goal_met': report['improvement_goal_met'],
        'services': report['services']['eligibility']}
    (ROOT / 'docs/paperfree-v19-assessment.json').write_text(json.dumps(result, indent=2) + '\n')
    out = ROOT / 'evidence/paperfree-v19'
    out.mkdir(parents=True, exist_ok=True)
    public = json.loads((ROOT / 'web/desk/paperfree-v19/report.json').read_text())
    (out / 'results.json.gz').write_bytes(gzip.compress(json.dumps(public, separators=(',', ':')).encode(), mtime=0))
    (out / 'service-receipts.json').write_text(json.dumps(public['services'], indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
