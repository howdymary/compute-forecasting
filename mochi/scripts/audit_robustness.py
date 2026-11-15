"""Check the expanded study's frozen splits, numerical rows, and service provenance."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('report')
a = p.parse_args()
r = json.loads(Path(a.report).read_text())
assert r['status'] == 'completed' and r['study'] == 'robustness-v2'
config = r['config']
digest = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()
assert digest(config) == r['config_sha256']
assert digest(r['selected']) == r['selected_sha256']
dev = set(config['development_seeds'])
held = set(range(config['heldout_start'], config['heldout_start'] + config['heldout_count']))
stress = set(range(config['stress_start'], config['stress_start'] + config['stress_count']))
assert not dev & held and not dev & stress and not held & stress

def check(rows, summary, seeds, stress_only=False):
    assert {x['scenario']['seed'] for x in rows} == seeds
    assert len(rows) == len(seeds) == summary['n']
    assert sum(x['success'] for x in rows) == summary['successes']
    assert summary['success_rate'] == summary['successes'] / summary['n']
    assert abs(sum(x['final_distance_m'] for x in rows) / len(rows) - summary['mean_final_distance_m']) < 1e-12
    for x in rows:
        assert x['remote_receipt']['provider'] == 'Modal'
        assert x['remote_receipt']['duration_seconds'] > 0
        assert x['scenario']['shift'] == (stress_only or x['scenario']['seed'] % 2 == 1)
    return len(rows)

archived = 0
assert len(r['rounds']) == config['rounds'] == 8
for iteration in r['rounds']:
    assert len(iteration['candidates']) == config['candidates_per_round']
    for candidate in iteration['candidates']:
        archived += check(candidate['results'], candidate['summary'], dev)
assert len(r['control_candidates']) == 32
assert set(x['family'] for x in r['control_candidates']) <= {'open_loop', 'object_feedback', 'slow_open_loop', 'earlier_stop'}
for candidate in r['control_candidates']:
    archived += check(candidate['results'], candidate['summary'], dev)
for label, seeds in [('development', dev), ('heldout', held), ('stress', stress)]:
    scope = r['evaluation'][label]
    for name in ['baseline', 'research', 'family_matched_random']:
        archived += check(scope['paired_results'][name], scope[name], seeds, label == 'stress')
        if name == 'research':
            assert all(x['policy'] == r['selected'] for x in scope['paired_results'][name])
initial = r['initial_results']
initial_summary = {'n':len(initial),'successes':sum(x['success'] for x in initial),'success_rate':sum(x['success'] for x in initial)/len(initial),'mean_final_distance_m':sum(x['final_distance_m'] for x in initial)/len(initial)}
archived += check(initial, initial_summary, dev)
assert archived == r['remote_rollouts'] == config['maximum_total_simulations'] == 2016

service = r['services']
assert len(service['sources']) == 8 and all(x['request_id'] for x in service['sources'])
assert len(service['decisions']) == 33
assert {x['role'] for x in service['decisions']} == {'researcher', 'designer', 'experimenter', 'critic'}
records = {x['id']: x for x in service['records']}
used = {x for decision in service['decisions'] for x in decision['input_record_ids']}
cross = [x for x in service['reads'] if x['cross_agent_use']]
for read in cross:
    record = records[read['record_id']]
    assert read['source_id_verified'] and read['record_id'] in used
    assert read['author'] == record['author'] != read['reader']
    assert digest(record['payload']) == record['sha256'] == read['sha256']
assert len(cross) == 41
assert service['eligibility']['writers'] == service['eligibility']['readers'] == 4
assert all(x['status'] in range(200, 300) for x in service['calls'])
print(json.dumps({'status': 'passed', 'run_id': r['run_id'], 'rollouts_counted': r['remote_rollouts'], 'archived_per_rollout_receipts': archived, 'exa_searches': len(service['sources']), 'tinker_decisions': len(service['decisions']), 'model': r['model'], 'memory_records': len(records), 'verified_cross_agent_reads': len(cross)}))
