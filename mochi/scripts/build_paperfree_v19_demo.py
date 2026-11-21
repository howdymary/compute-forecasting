"""Publish actual paper-free trajectories, with engineering/training separated."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from build_contact_v18_preview import public_evidence
from build_terrain_training_preview import public_report
from foot_clearance_evidence import after_descent_clearance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'web/desk/paperfree-v19'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def metadata(row, episode, checkpoint, descriptor, label=None):
    assert not episode['paper_geometry_present']
    assert episode['maximum_applied_base_force'] == 0
    assert episode['steps']['attempts'] == len(episode['step_events'])
    return dict(checkpoint, seed=row['seed'], complete=row['complete_sequence_success'],
        qualified_complete=row['qualified_complete'], failure=row['failure'], label=label,
        sha256=descriptor['sha256'], uncompressed_sha256=descriptor['uncompressed_sha256'],
        archive=row.get('archive'), steps=episode['steps'], duration=episode['duration'],
        direction_metrics=row['direction_metrics'], native_smoothness=episode['native_smoothness'],
        flat_foot_clearance=episode['flat_foot_clearance'], flat_legs=episode['flat_legs'],
        after_descent_clearance=after_descent_clearance(episode),
        recovery_arm_joint_travel_rad=sum(r['arm_joint_travel_rad'] for r in episode['recoveries']),
        intertask_arm_joint_travel_rad=sum(episode['intertask_arm_joint_travel_rad'].values()),
        book_turnaround_verified=any(a['label'] == 'book-top-turnaround' and a['success']
            and a.get('book_top', {}).get('instant_valid') for a in row['arrivals']),
        forward_descent_verified=any(a['label'] == 'book-forward-descent' and a['success']
            and a.get('forward_verification', {}).get('verified') for a in row['arrivals']),
        task_outcomes={t: r['success'] for t, r in episode['results'].items()},
        action_summary=[{'domain': d['observation']['domain'],
            'station': d['observation'].get('station', d['observation'].get('task', d['observation']['domain'])),
            'action': d['action']} for d in row.get('model_decisions', [])])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--engineering', action='store_true')
    p.add_argument('--source')
    p.add_argument('--workflow-run', type=int)
    p.add_argument('--development-preview', action='store_true')
    p.add_argument('--preview-update', type=int)
    a = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    files, scenarios = {}, []
    scene = json.loads((ROOT / 'configs/richdesk-v19-paperfree.json').read_text())
    assert not any(prop['name'] == 'sticky-notes' for prop in scene['props'])
    note = ('Uninterrupted MuJoCo replay at actual recorded timestamps. Paper geometry and its forced crossing are absent. '
            'Every step attempt counts. Qualification requires all four tasks, balance, support and per-leg foot clearance. '
            'The native gait network and book controller remain fixed.')
    if a.engineering:
        if (OUT / 'manifest.json').exists():
            assert json.loads((OUT / 'manifest.json').read_text())['evaluation_status'] == 'engineering'
        from mochi.smooth_v16.public import rounded
        versions = []
        for code in ['W8', 'W9', 'W10']:
            name = 'paperfree-' + code.lower() + '-p5-full'
            data = (ROOT / 'artifacts/paperfree-v19-engineering' / (name + '.json.gz')).read_bytes()
            row = json.loads(gzip.decompress(data))
            episode = row['episode']
            clip = {k: v for k, v in episode.items() if k not in ['control_telemetry', 'book_motion_samples']}
            clip['balance_measurements'] = [{k: v for k, v in m.items() if k in
                ['t', 'phase', 'gait_phase', 'roll_rad', 'loads_n', 'step_category']} for m in episode['balance_measurements']]
            raw = json.dumps(rounded(clip), separators=(',', ':')).encode()
            packed = gzip.compress(raw, compresslevel=6, mtime=0)
            file = name + '.json.gz'
            (OUT / file).write_bytes(packed)
            cp = {'checkpoint_update': 0, 'checkpoint_id': 'engineering-' + code, 'cumulative_updates': 0}
            files[file] = metadata(row, episode, cp,
                {'sha256': sha(packed), 'uncompressed_sha256': sha(raw)}, 'FIXED ' + code + ' CONTROLLER')
            versions.append({'update': 0, 'file': file})
        scenarios = [{'id': 'engineering-185000', 'label': 'Paper-free engineering scenario 185000',
            'partition': 'engineering', 'parent_file': versions[0]['file'], 'versions': versions}]
        manifest = {'study': 'mochi-paperfree-v19', 'evaluation_status': 'engineering',
            'optimizer_updates_completed': 0, 'selected_update': 0, 'selection_finalized': False,
            'checkpoints': [], 'engineering_note': 'Paper-free physical engineering comparison. Zero new Tinker updates. All three fixed-controller attempts and their failures are preserved. Training and fresh-scenario tests are pending.',
            'improvement_goal_met': False, 'held_out': None, 'source_sha': 'local-engineering',
            'services': {}, 'display_note': note}
        report = {'study': manifest['study'], 'status': 'engineering',
            'scope': manifest['engineering_note'], 'recordings': files}
    else:
        import modal
        source = Path(a.source)
        report = json.loads((source / 'report.json').read_text())
        assert report['study'] in ['mochi-paperfree-v19', 'mochi-paperfree-v19r1']
        all_cps = {c['update']: c for c in report['checkpoints']}
        assert set(all_cps) == {0, 1, 4, 8}
        cps = {u: c for u, c in all_cps.items() if c['development'] is not None}
        if a.development_preview:
            assert report['status'] == 'running' and not report.get('held_out')
            if (OUT / 'manifest.json').exists():
                assert json.loads((OUT / 'manifest.json').read_text())['evaluation_status'] != 'completed'
            selected = a.preview_update
            assert selected in cps
        else:
            assert report['status'] == 'completed' and len(cps) == 4
            selected = report['selected_checkpoint']['update']
        volumes = {}

        def recording(row, update, kind):
            d = row['public_recording']
            volume = volumes.setdefault(d['volume'], modal.Volume.from_name(d['volume']))
            file = f'{kind}-{row["seed"]}-{update}.json.gz'
            target = OUT / file
            if target.exists():
                assert sha(target.read_bytes()) == d['sha256']
            else:
                temporary = target.with_suffix('.download')
                with temporary.open('wb') as stream:
                    for chunk in volume.read_file(d['path']):
                        stream.write(chunk)
                assert sha(temporary.read_bytes()) == d['sha256']
                temporary.replace(target)
            raw = gzip.decompress(target.read_bytes())
            assert sha(raw) == d['uncompressed_sha256']
            episode = json.loads(raw)
            c = cps[update]
            files[file] = metadata(row, episode, {'checkpoint_update': update,
                'checkpoint_id': c['checkpoint_id'], 'cumulative_updates': c['cumulative_updates']}, d)
            files[file]['execution_source_sha'] = report['carried_baseline']['source_sha'] if kind == 'development' and update == 0 and report.get('carried_baseline') else report['source_sha']
            files[file]['execution_workflow_run'] = report['carried_baseline']['workflow_run'] if kind == 'development' and update == 0 and report.get('carried_baseline') else a.workflow_run
            return file

        for seed in report['protocol']['development_seeds']:
            versions = []
            for update in sorted(cps):
                row = next(r for r in json.loads((source / f'checkpoint-{update}.json').read_text()) if r['seed'] == seed)
                versions.append({'update': update, 'file': recording(row, update, 'development')})
            scenarios.append({'id': 'development-' + str(seed), 'label': 'Development scenario ' + str(seed),
                'partition': 'development', 'parent_file': versions[0]['file'], 'versions': versions})
        parents = [] if a.development_preview else json.loads((source / 'held-out-parent.json').read_text())
        trained = {} if a.development_preview else {r['seed']: r for r in json.loads((source / 'held-out-selected.json').read_text())}
        if not a.development_preview:
            assert len(parents) == len(trained) == 4
        for before in parents:
            bf = recording(before, 0, 'held-out-parent')
            af = recording(trained[before['seed']], selected, 'held-out-selected')
            scenarios.append({'id': 'held-out-' + str(before['seed']), 'label': 'Fresh test scenario ' + str(before['seed']),
                'partition': 'held_out', 'parent_file': bf, 'versions': [{'update': selected, 'file': af}]})
        manifest = {k: report.get(k) for k in ['study', 'optimizer_updates_completed', 'scope',
            'checkpoints', 'held_out', 'paired_held_out', 'improvement_goal_met', 'source_sha']}
        manifest.update(evaluation_status='development_preview' if a.development_preview else 'completed',
            selection_finalized=bool(report.get('selected_checkpoint')), selected_update=selected,
            pending_evaluation_updates=sorted(set(all_cps) - set(cps)),
            services=report['services']['eligibility'], campaign_id=report['run_id'],
            execution_workflow_run=a.workflow_run, display_note=note,
            budget_usage_or_reserved=report['budget_usage_or_reserved'], carried_baseline=report.get('carried_baseline'), data_provenance=report.get('data_provenance'))
        report = public_evidence(public_report(report), report['run_id'])
    preferred = next((s['id'] for s in scenarios if s['partition'] == 'held_out' and files[s['parent_file']]['qualified_complete'] and files[s['versions'][0]['file']]['qualified_complete']), None)
    preferred = preferred or next((s['id'] for s in scenarios if s['partition'] == 'held_out' and files[s['versions'][0]['file']]['qualified_complete']), None)
    if a.development_preview:
        preferred = next((s['id'] for s in scenarios if files[s['parent_file']]['qualified_complete']
            and files[next(v['file'] for v in s['versions'] if v['update'] == a.preview_update)]['qualified_complete']), None)
    manifest.update(scene=scene, scenarios=scenarios, recordings=files,
        default_scenario=preferred or scenarios[0]['id'],
        default_selection_rule='First qualified matched development pair; otherwise first development scenario. All cases and failures remain available.' if a.development_preview else 'First qualified fresh parent/selected pair; otherwise first qualified selected fresh attempt; otherwise first development scenario. All cases and failures remain available.')
    for name, value in [('manifest', manifest), ('report', report)]:
        raw = json.dumps(value, indent=2) + '\n'
        assert 'tinker://' not in raw, 'Private optimizer references stay backend-only'
        (OUT / (name + '.json')).write_text(raw)
        if a.engineering:
            (OUT / ('engineering-' + name + '.json')).write_text(raw)
    print(json.dumps({'recordings': len(files), 'scenarios': len(scenarios), 'status': manifest['evaluation_status']}))


if __name__ == '__main__':
    main()
