"""One declared safety-first utility for labels and checkpoint selection."""
from collections import Counter, defaultdict


def branch_rank(domain, row):
    if domain == 'walk':
        return (round(row['metrics']['roll_rms_deg'] / .5),
                round(row['metrics']['lateral_rms_m'] / .002), row['duration_s'])
    if domain == 'recovery':
        return (row['duration_s'] + .25 * row['result']['arm_joint_travel_rad'],
                row['result']['arm_joint_travel_rad'])
    # Task candidates include a measured R0 withdrawal, rather than scoring
    # the press alone and ignoring the state in which it leaves the arm.
    return (row['duration_s'] + .25 * row['coupled_recovery']['arm_joint_travel_rad'],
            row['result']['max_force_n'])


def checkpoint_rank(summary, rows):
    complete = [r['episode'] for r in rows if r['complete_sequence_success']]
    # Never reward an early failed episode for its short duration.
    if complete:
        roll = sum(e['balance_metrics']['roll_rms_deg'] for e in complete) / len(complete)
        lateral = sum(e['balance_metrics']['lateral_rms_m'] for e in complete) / len(complete)
        cost = sum(e['duration'] + .25 * sum(x['arm_joint_travel_rad'] for x in e['recoveries'])
                   for e in complete) / len(complete)
    else:
        roll = lateral = cost = float('inf')
    return (summary['complete_successes'], -summary['falls'], -summary['invalid_contacts'],
            sum(summary['task_successes'].values()), summary['smooth_complete_successes'],
            -round(roll / .5) if complete else -10**9,
            -round(lateral / .002) if complete else -10**9, -cost)


def static_from_training(teachers):
    """State-independent station preferences, chosen only from training labels."""
    votes = defaultdict(Counter)
    for teacher in teachers:
        for e in teacher['examples']:
            votes[e['domain'] + ':' + e['task']][e['action']] += 1
    return {key: sorted(count, key=lambda a: (-count[a], a))[0] for key, count in votes.items()}


def meaningful_corrections(teachers):
    """Count corrections beyond roundoff or an arbitrary tie-break."""
    counts = Counter()
    for teacher in teachers:
        examples = {(e['domain'], e['task']): e for e in teacher['examples']}
        for trial in teacher['trials']:
            example = examples.get((trial['domain'], trial['task']))
            if not example or example['action'] == trial['student_preference']:
                continue
            by_action = {r['action']: r for r in trial['outcomes']}
            old, best = by_action[trial['student_preference']], by_action[example['action']]
            if not old['success'] or old['fall'] or old['invalid_contact']:
                counts[trial['domain']] += 1
                continue
            a, b = branch_rank(trial['domain'], old), branch_rank(trial['domain'], best)
            if trial['domain'] == 'walk':
                substantial = a[:2] > b[:2] or a[2] - b[2] >= .1
            else:
                substantial = a[0] - b[0] >= .1
            if substantial:
                counts[trial['domain']] += 1
    return dict(counts)
