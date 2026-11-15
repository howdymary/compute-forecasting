"""Credential-free numerical/provenance audit of the published live demo pack."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('pack');a=p.parse_args();root=Path(a.pack);r=json.loads((root/'report.json').read_text())
assert r['mode']=='live-sponsored-research'
memory=r['memory'];records={x['id']:x for x in memory['records']};used={x for d in memory['decisions'] for x in d['input_record_ids']}
cross=[x for x in memory['reads'] if x['cross_agent_use']]
for read in cross:
    record=records[read['record_id']]
    assert read['source_id_verified'] and read['record_id'] in used
    assert record['author']!=read['reader']
    digest=hashlib.sha256(json.dumps(record['payload'],sort_keys=True).encode()).hexdigest()
    assert digest==read['sha256']==record['sha256']
assert len(cross)==11 and memory['eligibility']['isolation_passed']
assert {d['role'] for d in memory['decisions']}=={'researcher','designer','experimenter','critic'}
assert len(r['sources'])==2 and all(x['request_id'] for x in r['sources'])
assert r['research_budget_rollouts']==r['random_control']['budget_rollouts']==48
for condition in r['evaluation'].values():
    for role in ['baseline','selected','random']:
        trials=condition['paired_results'][role];s=condition[role]
        assert sum(x['success'] for x in trials)==s['successes'] and len(trials)==s['n']
        assert abs(sum(x['final_distance_m'] for x in trials)/len(trials)-s['mean_final_distance_m'])<1e-12
        assert all(x['remote_receipt']['provider']=='Modal' for x in trials)
assert r['evaluation']['heldout']['selected']['successes']==8
assert r['evaluation']['changed_conditions']['selected']['successes']==1
manifest=json.loads((root/'manifest.json').read_text())
for name,entry in manifest['files'].items():
    assert Path(name).name==name
    raw=(root/name).read_bytes();assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
print(json.dumps({'status':'passed','cross_agent_reads':len(cross),'roles':4,'rollouts':r['remote_rollouts'],'manifest_files':len(manifest['files']),'robustness_failure_preserved':True}))
