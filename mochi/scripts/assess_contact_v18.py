"""Independently check completed C18 records without running physics or training."""
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = 'bdba8600e9abb94c20aa1dc68ee617b51ee4999c'
WORKFLOW = 44800327838


def read(path):
    return json.loads(path.read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def same(a, b):
    if isinstance(a, float) or isinstance(b, float):
        assert a is not None and b is not None and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9), (a, b)
    else:
        assert a == b, (a, b)


def choices(row):
    return [(d['observation']['domain'], d['observation'].get('station', d['observation'].get('task')), d['action'])
            for d in row['model_decisions']]


def decision_audit(before, after):
    left, right = before['model_decisions'], after['model_decisions']
    first_difference = next((i for i, (a, b) in enumerate(zip(choices(before), choices(after))) if a != b), None)
    shared = len(left) if first_difference is None else first_difference
    prefix = []
    for i in range(min(shared + 1, len(left), len(right))):
        a, b = left[i], right[i]
        # State at the first different action must also be identical if the
        # shared prefix alone explains the physical state reached so far.
        prefix.append({'decision_index': i,
                       'same_physical_state': a['initial_physical_state_sha256'] == b['initial_physical_state_sha256'],
                       'same_physical_time': math.isclose(a['t'], b['t'], abs_tol=1e-8)})
    return {'seed': before['seed'], 'identical_complete_action_sequence': choices(before) == choices(after),
            'actions_match_until_shorter_attempt_stops': all(a == b for a, b in zip(choices(before), choices(after))),
            'first_action_difference': first_difference, 'shared_prefix_state_checks': prefix,
            'unexplained_prefix_variation': any(not x['same_physical_state'] or not x['same_physical_time'] for x in prefix),
            'parent_complete': before['complete_sequence_success'], 'selected_complete': after['complete_sequence_success']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--skip-public-recordings', action='store_true')
    args = parser.parse_args()
    folder = Path(args.source)
    from mochi.contact_v18.objective import summary, paired, valid_branch, branch_rank, select_checkpoint
    from mochi.control_v8.verification import full_success
    from mochi.smooth_v16.verification import forward_descent_check
    from assess_smooth_v17 import qualification_failures, failure_details
    from foot_clearance_evidence import after_descent_clearance

    report = read(folder / 'report.json')
    cfg = report['protocol']
    assert report['study'] == 'mochi-contact-v18' and report['status'] == 'completed'
    assert report['execution_source_sha'] == report['source_sha'] == EXECUTION
    assert report['optimizer_updates_completed'] == 16
    log = report['training_log']
    assert [entry['update'] for entry in log] == list(range(1, 17))
    domains = set(cfg['training']['domains'])
    assert len(domains) == 6
    for entry in log:
        assert entry['optimizer_completed'] and entry['forward_backward_completed']
        assert set(entry['domain_loss_metrics']) == set(entry['domain_counts']) == domains
        assert all(math.isfinite(metrics['loss:sum']) for metrics in entry['domain_loss_metrics'].values())
        assert all(n > 0 for n in entry['domain_counts'].values()) and entry['tokens'] > 0
        assert len(entry['batch_sha256']) == 64
    assert max(report['first_optimizer_probability_change'].values()) > 1e-7
    assert len(cfg['frozen_sha256']) == 212
    for name, expected in cfg['frozen_sha256'].items():
        assert sha((ROOT / name).read_bytes()) == expected, name
    assert sha((ROOT / cfg['implementation_prompt']).read_bytes()) == cfg['prompt_sha256']
    amendment = cfg['runtime_amendment']
    assert sha((ROOT / amendment['document']).read_bytes()) == amendment['document_sha256']
    prior = read(folder / 'prior-runtime-execution.json')
    assert prior['source_sha'] == '4d2be964a9be26f6697513a314a3b23a64d07b90'
    assert prior['optimizer_updates_completed'] == 0 and not prior['held_out_opened']
    assert sum(p != 'src/mochi/contact_v18/train.py' and cfg['frozen_sha256'][p] == h
               for p, h in prior['protocol']['frozen_sha256'].items()) == 210
    reconciliation = read(folder / 'runtime-reservation-reconciliation.json')
    assert reconciliation == report['runtime_reservation_reconciliation']
    assert sha((folder / 'checkpoint-0.json').read_bytes()) == reconciliation['baseline_artifact_sha256']
    assert report['carried_baseline']['sha256'] == reconciliation['baseline_artifact_sha256']
    assert reconciliation['interrupted_physical_attempts_upper_bound'] == 4
    assert report['runtime_wrapper_probe']['expected_error'] == 'Unavailable action'
    assert report['runtime_wrapper_probe']['receipt']['physical_rollouts'] == 1
    engineering = read(ROOT / cfg['engineering_evidence']['path'])
    assert sha((ROOT / cfg['engineering_evidence']['path']).read_bytes()) == cfg['engineering_evidence']['sha256']
    assert engineering['physical_attempts'] == cfg['engineering_usage']['physical_rollouts'] == 58

    checkpoints = {c['update']: c for c in report['checkpoints']}
    assert set(checkpoints) == {0, 1, 4, 8, 16}
    assert len({c['checkpoint_id'] for c in checkpoints.values()}) == 5
    assert all(c['cumulative_updates'] == 121 + c['update'] for c in checkpoints.values())
    selection = read(folder / 'selection-freeze.json')
    assert not selection['held_out_opened'] and not selection.get('held_out')
    assert selection['selected_checkpoint']['checkpoint_id'] == report['selected_checkpoint']['checkpoint_id']
    partitions = [set(cfg[key]) for key in ['training_seeds', 'development_seeds', 'held_out_seeds']]
    assert not any(a & b for i, a in enumerate(partitions) for b in partitions[i + 1:])
    evaluated = cfg['training']['evaluation_checkpoints']
    assert evaluated == [0, 1, 4, 16] and checkpoints[8]['development'] is None
    development = {u: read(folder / f'checkpoint-{u}.json') for u in evaluated}
    for update, rows in development.items():
        assert {row['seed'] for row in rows} == partitions[1]
        recomputed = summary(deepcopy(rows), cfg)
        for key, value in checkpoints[update]['development'].items():
            same(value, recomputed[key])
    assert select_checkpoint([checkpoints[u] for u in evaluated], development, cfg)['checkpoint_id'] == report['selected_checkpoint']['checkpoint_id']

    teachers = [read(folder / f'teacher-{seed}.json') for seed in cfg['training_seeds']]
    teacher_branches = 0
    for teacher in teachers:
        assert teacher['valid'] and teacher['row']['complete_sequence_success']
        assert len(teacher['examples']) == len(teacher['trials'])
        teacher_branches += sum(len(t['outcomes']) for t in teacher['trials'])
        for example, trial in zip(teacher['examples'], teacher['trials']):
            assert example['observation'] == trial['observation']
            valid = [row for row in trial['outcomes'] if valid_branch(row)]
            assert valid
            best = min(valid, key=lambda row: branch_rank(trial['domain'], row))
            assert best['action'] == example['action']
            assert len({row['initial_state_sha256'] for row in trial['outcomes']}) == 1
            assert example['initial_state_sha256'] == best['initial_state_sha256']
            assert sha(json.dumps(trial['outcomes'], sort_keys=True).encode()) == example['outcomes_sha256']
    assert teacher_branches + len(teachers) == sum(t['receipt']['physical_rollouts'] for t in teachers)
    walking_candidates = []
    for teacher in teachers:
        for trial in teacher['trials']:
            if trial['domain'] != 'walk':
                continue
            for candidate in trial['outcomes']:
                clearance = candidate.get('flat_foot_clearance') or {}
                if clearance.get('moving_swings_measured', 0) < 2:
                    continue
                walking_candidates.append({
                    'seed': teacher['seed'], 'destination': trial['task'],
                    'action': candidate['action'], 'valid': valid_branch(candidate),
                    'success': candidate['success'], 'failure': candidate['failure'],
                    'moving_sole_clearance_m': clearance['moving_median_peak_m'],
                    'steps': candidate['steps']['attempts'], 'duration_s': candidate['duration_s'],
                    'native_acceleration_rms_rad_s2': candidate['native_smoothness']['sampled_acceleration_rms_rad_s2'],
                    'selected_training_label': next(e['action'] for e in teacher['examples']
                        if e['domain'] == trial['domain'] and e['task'] == trial['task']) == candidate['action'],
                    'initial_state_sha256': candidate['initial_state_sha256'],
                })
    assert report['data_collection_provenance']['reused_regression_examples'] == 3
    for example in cfg['engineering_training_examples']:
        assert example['domain'] == 'laptop' and example['evidence_id'] in cfg['engineering_evidence']['production_validations']
        evidence = next(e for e in engineering['attempts'] if e['id'] == example['evidence_id'])
        assert example['evidence_sha256'] == evidence['sha256']
        assert example['initial_state_sha256'] == evidence['initial_state_sha256']
        assert evidence['success'] and evidence['recovery_success'] and not evidence['fall'] and not evidence['invalid_contact']
    observation_labels = {}
    for teacher in teachers:
        for example in teacher['examples']:
            key = json.dumps(example['observation'], sort_keys=True)
            observation_labels.setdefault(key, []).append({'seed': teacher['seed'], 'action': example['action']})
    label_conflicts = [{'observation': json.loads(key), 'labels': labels}
                      for key, labels in observation_labels.items()
                      if len({row['action'] for row in labels}) > 1]

    held = {label: read(folder / f'held-out-{label}.json') for label in ['parent', 'selected', 'fixed', 'static']}
    failures = {}
    for label, rows in held.items():
        expected_seeds = partitions[2] if label in ['parent', 'selected'] else set(cfg['control_seeds'])
        assert len(rows) == len(expected_seeds) and {row['seed'] for row in rows} == expected_seeds
        recomputed = summary(deepcopy(rows), cfg)
        for key, value in report['held_out'][label].items():
            same(value, recomputed[key])
        failures[label] = []
        for row in rows:
            episode = row['episode']
            qualification_failures(row, cfg)
            assert episode['maximum_applied_base_force'] == 0
            if row['complete_sequence_success']:
                assert full_success(episode) and not episode['fall'] and not episode['invalid_contact']
                assert episode['postit_crossings']
                assert forward_descent_check(episode['step_events'], episode['book_motion_samples'])['verified']
                assert len(episode['recoveries']) == 4 and all(r['success'] for r in episode['recoveries'])
                assert all(episode['results'][task]['contacts'] > 0 and episode['results'][task]['non_hand_contact_steps'] == 0
                           and episode['results'][task]['max_force_n'] < .8 for task in ['alarm', 'drawer', 'laptop', 'globe'])
            else:
                failures[label].append(failure_details(row))
            clearance = episode.get('flat_foot_clearance', {})
            moving = [e for e in clearance.get('swings', []) if e['category'] in ['flat_transit', 'turning', 'fixture_clearance']]
            assert len(moving) == clearance.get('moving_swings_measured', 0)
            if moving:
                import statistics
                same(statistics.median(e['peak_minimum_sole_clearance_m'] for e in moving), clearance['moving_median_peak_m'])
    pp = paired(held['parent'], held['selected'])
    assert pp == report['paired_held_out']
    selected = report['held_out']['selected']
    goal = bool(selected['qualified_complete_successes'] == 4 and selected['clear_stepping_successes'] == 4 and pp['n'] >= 2
                and pp['mean_step_reduction_fraction'] >= .10 and pp['mean_recovery_arm_travel_reduction_fraction'] >= .15
                and pp['mean_time_reduction_fraction'] >= 0)
    assert goal == report['improvement_goal_met']
    choice_audits = [decision_audit(a, next(b for b in held['selected'] if b['seed'] == a['seed'])) for a in held['parent']]
    development_choice_audits = [
        {'from_update': left, 'to_update': right,
         **decision_audit(a, next(b for b in development[right] if b['seed'] == a['seed']))}
        for left, right in zip(evaluated, evaluated[1:]) for a in development[left]]
    static_seeds = {row['seed'] for row in held['static']}
    static_comparisons = [{'seed': a['seed'], 'identical_action_sequence': choices(a) == choices(next(b for b in held['static'] if b['seed'] == a['seed']))}
                          for a in held['selected'] if a['seed'] in static_seeds]

    usage, eng = report['budget_usage_or_reserved'], cfg['engineering_usage']
    receipts = [entry['receipt'] for entry in report['physics_receipts']]
    assert all(r['cpu'] == 1 for r in receipts)
    interrupted = report['interrupted_physical_attempts_accounted']
    assert interrupted == reconciliation['interrupted_physical_attempts_upper_bound']
    assert usage['physical_rollouts'] == eng['physical_rollouts'] + sum(r['physical_rollouts'] for r in receipts) + interrupted
    assert usage['physical_rollouts'] == report['total_physical_attempts_accounted']
    assert usage['physical_rollouts'] - interrupted == report['total_physical_rollouts_completed']
    same(usage['simulation_cpu_hours'], eng['simulation_cpu_hours'] + sum(r['duration_seconds'] / 3600 for r in receipts) + report['interrupted_simulation_cpu_hours_bound'])
    assert usage['optimizer_updates'] == 16
    assert usage['training_token_presentations'] == sum(entry['tokens'] for entry in log)
    assert all(0 <= usage[key] <= limit for key, limit in cfg['bounds'].items() if key != 'modal_concurrency')
    eligibility = report['services']['eligibility']
    assert eligibility['writers'] > 1 and eligibility['readers'] > 1 and eligibility['cross_agent_reads'] > 0 and eligibility['isolation_passed']
    assert not report['services']['pending_ingestions']
    assert report['services']['sources'] and all(s['request_id'] and s['sources'] for s in report['services']['sources'])

    recordings = 0
    if not args.skip_public_recordings:
        public = ROOT / 'web/desk/contact-v18'
        manifest = read(public / 'manifest.json')
        assert manifest['source_sha'] == EXECUTION and manifest['selected_update'] == report['selected_checkpoint']['update']
        starts = {}
        for name, meta in manifest['recordings'].items():
            data = (public / name).read_bytes()
            assert sha(data) == meta['sha256']
            raw = gzip.decompress(data)
            assert sha(raw) == meta['uncompressed_sha256']
            episode = json.loads(raw)
            frames = episode['trajectory']['frames']
            assert frames[0]['t'] == 0 and 0 <= episode['duration'] - frames[-1]['t'] <= .05
            assert all(0 < b['t'] - a['t'] <= .05 for a, b in zip(frames, frames[1:]))
            assert episode['maximum_applied_base_force'] == 0
            assert len(episode['step_events']) == episode['steps']['attempts'] == meta['steps']['attempts']
            starts[name] = frames[0]
        for scenario in manifest['scenarios']:
            for version in scenario['versions']:
                assert starts[scenario['parent_file']] == starts[version['file']]
        recordings = len(starts)
        assert recordings == 20

    audit = {'study': report['study'], 'source_sha': EXECUTION, 'run_id': report['run_id'],
             'execution_workflow_run': WORKFLOW, 'optimizer_updates': 16, 'domain_gradient_calls': 96,
             'selected_is_parent': report['selected_checkpoint']['update'] == 0,
             'selected_update': report['selected_checkpoint']['update'], 'held_out': report['held_out'],
             'paired': pp, 'improvement_goal_met': goal, 'budget_usage': usage, 'teacher_branches_verified': teacher_branches,
             'public_recordings_verified': recordings, 'frozen_files_verified': 212, 'choice_audit': choice_audits,
             'development_choice_audit': development_choice_audits,
             'runtime_amendment': amendment, 'runtime_reconciliation': reconciliation,
             'static_choice_audit': static_comparisons, 'failures': failures, 'service_eligibility': eligibility,
             'after_descent_clearance':{label:[{'seed':row['seed'],**after_descent_clearance(row['episode'])} for row in rows] for label,rows in held.items()},
             'walking_training_candidates': walking_candidates,
             'identical_observation_label_conflicts': label_conflicts,
             'static_control_training_scope': 'Built from the two guarded teachers. The selector additionally receives three laptop regression examples; this static control does not receive those three labels.',
             'resource_receipt_caveat': 'The shared receipt helper reports 3072 MiB, inherited from an older function. C18 functions declare 4096 MiB. CPU and measured duration accounting use the actual one-CPU configuration.',
             'limits': ['Four final scenarios in one furnished layout. No hardware validation.',
                        'Tinker trains LoRA controller selection. Native gait weights stay fixed.',
                        'P5/P6 laptop repair and W8 foot lift are engineered and shared by every checkpoint.',
                        'A foot-clearance gain alone does not establish fewer steps, faster completion or smoother arms.',
                        'Identical action prefixes with different physical states cannot be attributed to a changed selector.',
                        'The static control omits the three additional regression labels used for selector training.',
                        'Parent proposals are evaluated on a guarded trajectory. Teacher overrides change subsequent states; these are not all states visited by the unmodified parent.',
                        'No causal search or memory ablation.']}
    output = ROOT / 'docs/contact-v18-assessment.json'
    output.write_text(json.dumps(audit, indent=2) + '\n')
    def number(value, places=2):
        return 'Unavailable' if value is None else f'{value:.{places}f}'
    lines = ['# Laptop contact and flat-ground stepping study', '',
             f"Tinker completed 16 additional optimizer updates on the six-domain Qwen3.5-4B LoRA controller selector. Development selection chose update {audit['selected_update']}. The declared joint improvement target was {'met' if goal else 'not met'}.", '',
             'The model chooses walking strategies, manipulation profiles and arm recovery from structured simulator state. The camera is a rendered replay. The native ONNX gait weights remain fixed. The bounded laptop force controls and foot-lift correction are controller engineering shared by the parent, intermediate checkpoints and fixed controls.', '',
             '[Continuous checkpoint replay](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/) · '
             f'[Execution and artifacts](https://github.com/howdymary/mochi-demo/actions/runs/{WORKFLOW}) · '
             '[Numerical audit](contact-v18-assessment.json)', '',
             '## Fresh final scenarios', '',
             '| Policy | Complete | Within quality limits | Clear stepping | Mean steps | Seconds | Recovery travel, rad | Intertask arm travel, rad | Moving sole clearance, mm |',
             '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    if audit['selected_is_parent']:
        lines.insert(4, 'No newly trained checkpoint was promoted. The parent and selected final cohorts use the same saved weights, so any difference between those repetitions cannot establish a training gain. The unpromoted development checkpoints retain their measured foot-lift changes and failures.')
        lines.insert(5, '')
    for label, stats in report['held_out'].items():
        clearance = stats['successful_mean_flat_sole_clearance_m']
        lines.append(f"| {label} | {stats['complete_successes']}/{stats['n']} | {stats['qualified_complete_successes']}/{stats['n']} | {stats['clear_stepping_successes']}/{stats['n']} | {number(stats['successful_mean_steps'], 1)} | {number(stats['successful_mean_seconds'], 1)} | {number(stats['successful_mean_recovery_arm_joint_travel_rad'])} | {number(stats['successful_mean_intertask_arm_joint_travel_rad'])} | {number(None if clearance is None else clearance * 1000)} |")
    lines += ['', 'Cost and clearance means use qualified completions only. Recovery travel is the mean joint travel per recovery. The replay counter totals all recoveries. An early failed attempt is not a cheap successful run.', '',
              f"Matched qualified pairs: {pp['n']}. Step reduction: {number(None if pp['mean_step_reduction_fraction'] is None else 100 * pp['mean_step_reduction_fraction'])}%. Recovery-travel reduction: {number(None if pp['mean_recovery_arm_travel_reduction_fraction'] is None else 100 * pp['mean_recovery_arm_travel_reduction_fraction'])}%. Time reduction: {number(None if pp['mean_time_reduction_fraction'] is None else 100 * pp['mean_time_reduction_fraction'])}%.", '',
              f"Intertask arm-travel reduction: {number(None if pp['mean_intertask_arm_travel_reduction_fraction'] is None else 100 * pp['mean_intertask_arm_travel_reduction_fraction'])}%. This includes walking, turning and recovery. Native walking arm swing remains fixed. A reduction in recovery travel alone does not establish less total arm movement between tasks.", '',
              'The frozen joint target requires all four fresh scenarios to complete within the quality limits and meet the 4.5 mm moving-sole-clearance target, at least two qualified pairs, at least 10% fewer steps and 15% less recovery joint travel, without longer successful time. Four scenarios in one layout do not establish reliability on other desks or hardware.', '',
              '## Why the old walking looked like a shuffle', '',
              'Book traversal uses planned contact footsteps. Flat-ground travel then switches to a fixed ONNX gait with much lower swing clearance. A 25 Hz replay could also hide short lift peaks. The new recorder targets 100 Hz during flat transit and renders the measured body transforms at their actual timestamps.', '',
              'W8 adds a contact-gated 6 mm lift and 2 mm forward reference to the original walking controller. The joint correction is capped at 0.10 rad and changes at no more than 2 rad/s. It requires the opposite foot to carry at least 0.65 N. It is disabled for tiny station-alignment commands. It changes actuator targets, with no physical root repositioning or render-only foot movement.', '',
              'Clearance is measured at the lowest physical collision-pad point on the sole relative to the local terrain, while the opposite foot is loaded. Moving and turning swings are reported separately from alignment. Every detected step still counts toward the efficiency objective.', '',
              'The accepted local matched corridor test increased median minimum-sole clearance from 2.55 mm to 4.78 mm, but increased measured steps from 44 to 56 and physical time from 6.26 to 7.74 seconds. This engineering result motivated the experiment. It was not a checkpoint improvement or an efficiency gain.', '',
              '## Laptop repair and learning data', '',
              'P5 regulates upper-edge contact using lid angle, closing speed and measured foot loads, with a bounded pulse finish. P6 uses bounded intermittent contact. These controls passed three opened regression states with withdrawal. The old opened 103xxx cases are regression and training evidence, not fresh tests.', '',
              f"Two guarded training sequences supplied {teacher_branches} measured candidate branches. Each label was checked against valid branches starting from the same physical state. Three validated regression examples were added for laptop selection. No successful trajectories were invented.", '',
              'The parent proposes actions, measured branches determine the accepted action, and the main trajectory executes that accepted action. Overrides therefore change subsequent states. The training states come from guarded trajectories, rather than exclusively from the unmodified parent policy.', '',
              'Training, development and final seeds are disjoint. The final seeds were unopened until the development-selected checkpoint was saved. Every optimizer update included walking, clock, drawer, laptop, globe and recovery examples. There were 96 completed domain-gradient calls. A change in selection probability verifies a changed decision policy; physical improvement requires the separate simulation results.', '',
              '## Checkpoint progression', '',
              '| Additional updates | Complete | Qualified | Clear stepping | Falls | Forbidden contacts |',
              '| --- | --- | --- | --- | --- | --- |']
    for update, cp in sorted(checkpoints.items()):
        stats = cp['development']
        if stats is None:
            lines.append(f'| {update} | Saved, not evaluated | Unavailable | Unavailable | Unavailable | Unavailable |')
            continue
        lines.append(f"| {update} | {stats['complete_successes']}/{stats['n']} | {stats['qualified_complete_successes']}/{stats['n']} | {stats['clear_stepping_successes']}/{stats['n']} | {stats['falls']} | {stats['invalid_contacts']} |")
    lines += ['', 'The parent has 121 cumulative updates. The counts above are additional updates in this campaign. Five states were saved; four checkpoints were physically evaluated. All physical comparisons use the same frozen scene, controller library, route, verifiers and quality limits.', '',
              'Before training and final tests, the paired runtime was extended to 3600 seconds after one parent input took nearly 24 minutes. The completed baselines were retained. Update 8 remained saved without physical evaluation, and fixed/static controls used the predeclared seeds 186000 and 186001. The four fresh parent/selected pairs and original improvement criteria remained unchanged. See the [runtime amendment](contact-v18-runtime-amendment.md).', '',
              '## Attribution and failures', '',
              f"Parent and selected final tests run sequentially in the same worker from reset. {sum(x['unexplained_prefix_variation'] for x in choice_audits)}/4 pairs had a different physical state or time during their shared action prefix. Such variation cannot be attributed to learned selection. The numerical audit retains every prefix check.", '',
              f"The audit also checked {len(development_choice_audits)} adjacent-checkpoint development pairs. In {sum(x['actions_match_until_shorter_attempt_stops'] and x['parent_complete'] != x['selected_complete'] for x in development_choice_audits)} pairs, actions agreed until the shorter attempt stopped, while completion differed. Those outcome differences do not demonstrate improved or degraded action selection. The state hashes are bitwise checks, not a measure of physical distance or tolerance.", '',
              f"The selected policy and training-derived static control chose identical complete action sequences in {sum(x['identical_action_sequence'] for x in static_comparisons)}/{len(static_comparisons)} matched control scenarios. This comparison limits claims that context-dependent selection was necessary.", '',
              'The static preference uses the two guarded teachers. The selector additionally receives three laptop regression labels. The fixed heuristic uses the regression-derived lid-angle rule. These information differences limit a claim of equal-data superiority over the static control.', '',
              'All failed attempts remain in the final table and replay. No checkpoint was selected using final-test outcomes. No service ablation establishes a causal improvement from Exa or past.dev.', '',
              '| Policy | Seed | Last decision | Failure |', '| --- | --- | --- | --- |']
    any_failure = False
    for label, rows in failures.items():
        for row in rows:
            any_failure = True
            lines.append(f"| {label} | {row['seed']} | {row['last_decision_domain']} | {row['failure']} |")
    if not any_failure:
        lines.append('| All | All final seeds | Complete | No failed final attempts |')
    lines += ['', '## Desk walking immediately after descent', '',
              'This diagnostic covers moving and turning swings between the verified descent-exit stance and drawer-station arrival. Book steps and station alignment are excluded. It was added for the post-descent walking question and was not a checkpoint-selection or joint-goal criterion. A partially completed leg stays labelled incomplete.', '',
              '| Policy | Seed | Leg completed | Measured moving swings | Median minimum sole clearance, mm |',
              '| --- | --- | --- | --- | --- |']
    for label in ['parent', 'selected']:
        for row in audit['after_descent_clearance'][label]:
            value = row['median_peak_m']
            lines.append(f"| {label} | {row['seed']} | {'Yes' if row['completed_leg'] else 'No'} | {row['moving_swings']} | {number(None if value is None else value * 1000)} |")
    lines += ['', '## Measured walking candidates used for training', '',
              'These are candidate controllers tested from matched training states, not checkpoint gains. Each row covers the complete leg to its destination, including any book or paper transitions. The clearance column covers moving flat-ground swings only. Invalid candidates remain visible and cannot supply a positive training label.', '',
              '| Seed | Destination | Controller | Valid | Teaching label | Sole clearance, mm | Steps | Physical seconds | Native acceleration RMS, rad/s² |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in walking_candidates:
        lines.append(f"| {row['seed']} | {row['destination']} | {row['action']} | {'Yes' if row['valid'] else 'No'} | {'Yes' if row['selected_training_label'] else 'No'} | {number(row['moving_sole_clearance_m'] * 1000)} | {row['steps']} | {number(row['duration_s'], 1)} | {number(row['native_acceleration_rms_rad_s2'])} |")
    lines += ['', 'The frozen native-acceleration limit is 161.4 rad/s². A completed route can still be invalid. More foot clearance can also require more steps; the final evaluation reports those costs separately.', '',
              f"The two guarded trajectories contain {len(label_conflicts)} identical-observation groups with different teaching labels. The audit retains their observations, seeds and labels. A deterministic selector cannot choose different actions from identical inputs. Additional updates alone cannot recover physical distinctions removed by observation rounding, and a near-threshold validity change also motivates improving the controller's safety margin.", '',
              '## Services and resource accounting', '',
              f"Accounted physical attempts: {usage['physical_rollouts']}, including 58 local engineering attempts. Confirmed completed attempts: {report['total_physical_rollouts_completed']}. Accounted simulation CPU-hours: {usage['simulation_cpu_hours']:.3f}. Limits were 160 attempts, 14 CPU-hours, 16 optimizer updates and four parallel workers. These are measured budget records, not a billing invoice.", '',
              'Four unfinished stages and eight CPU-minutes were conservatively charged for two interrupted teacher inputs. Their reserved inference tokens were retained. A separate cloud wrapper check intentionally reached the invalid-action validator after physical initialization; its failed attempt was charged and provided no training label.', '',
              'Each cloud function requests one CPU and 4096 MiB memory. The reused receipt helper carries a stale 3072 MiB memory label; that field is not an accurate allocation or billing receipt. The CPU-duration budget calculation is unaffected.', '',
              'Tinker performed the optimizer updates, checkpoint storage and decision inference. Modal ran measured MuJoCo branches and uninterrupted evaluation episodes. Exa searched for contact and support mechanisms in the main research loop. past.dev carried the sourced hypothesis, experiment plan, actual results and qualified verdict across distinct identities, with source-verified reads and a private-canary access check.', '',
              'An initial Modal image configuration failed before cloud physics or optimizer updates. The corrected execution preserved its research records, API usage and original campaign budget. No gradients were repeated by that setup recovery.', '',
              f"Frozen execution source: `{EXECUTION}`. Campaign: `{report['run_id']}`. Execution workflow: `{WORKFLOW}`. The audit verified all 212 frozen files and {recordings} public recordings. The carried baseline retains the original hashes for all 210 support files except the coordinator.", '',
              '## Reproduction', '', 'From the repository root:', '', '```bash',
              'PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/build_contact_v18_preview.py --source <downloaded-artifact-folder>',
              'PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/assess_contact_v18.py --source <downloaded-artifact-folder>',
              'node mochi/scripts/check_contact_v18_ui.mjs',
              'python3 -m http.server 4120 --directory mochi/web/desk', '```', '',
              'Open `http://127.0.0.1:4120/contact-v18.html`. Exporting retained recordings requires the authenticated Modal profile. The public replay uses no service credentials. Exact model re-execution requires access to retained backend checkpoints and provider credentials.']
    (ROOT / 'docs/contact-v18-assessment.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'audit': str(output), 'selected_update': audit['selected_update'],
                      'held_out_qualified': selected['qualified_complete_successes'],
                      'clear_stepping': selected['clear_stepping_successes'], 'goal_met': goal,
                      'verified_recordings': recordings, 'usage': usage}, indent=2))


if __name__ == '__main__':
    main()
