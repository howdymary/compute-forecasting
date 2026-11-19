"""Safety/utility and exact-state contracts for the next training campaign."""
import hashlib
import numpy as np

from mochi.terrain_v13.objective import branch_rank, checkpoint_rank, static_from_training, meaningful_corrections


def result(duration, roll=.2, lateral=.01, complete=True):
    return {'complete_sequence_success': complete, 'episode': {'duration': duration,
        'balance_metrics': {'roll_rms_deg': roll, 'lateral_rms_m': lateral},
        'recoveries': [{'arm_joint_travel_rad': 5.}]}}


def totals(complete=2):
    return {'complete_successes': complete, 'falls': 0, 'invalid_contacts': 0,
        'task_successes': {t: complete for t in ['alarm', 'drawer', 'laptop', 'globe']},
        'smooth_complete_successes': complete}


def test_small_balance_difference_does_not_hide_large_time_improvement():
    slow = checkpoint_rank(totals(), [result(260, .21), result(260, .21)])
    fast = checkpoint_rank(totals(), [result(250, .22), result(250, .22)])
    assert fast > slow
    # The same practical tolerance governs teacher walking labels.
    rows = [{'metrics': {'roll_rms_deg': r, 'lateral_rms_m': .01}, 'duration_s': t}
            for r, t in [(.21, 100), (.22, 90)]]
    assert branch_rank('walk', rows[1]) < branch_rank('walk', rows[0])


def test_failed_short_episode_cannot_win_checkpoint_selection():
    assert checkpoint_rank(totals(2), [result(260), result(260)]) > checkpoint_rank(
        totals(1), [result(260), result(10, complete=False)])


def test_task_label_charges_for_withdrawal_instead_of_only_press_force():
    slow = {'duration_s': 5., 'coupled_recovery': {'arm_joint_travel_rad': 12.},
            'result': {'max_force_n': .3}}
    clean = {'duration_s': 5., 'coupled_recovery': {'arm_joint_travel_rad': 5.},
             'result': {'max_force_n': .4}}
    assert branch_rank('laptop', clean) < branch_rank('laptop', slow)


def test_recovery_cost_can_reject_a_faster_but_needlessly_long_arm_path():
    short = {'duration_s': 2., 'result': {'arm_joint_travel_rad': 2.}}
    excessive = {'duration_s': 1.9, 'result': {'arm_joint_travel_rad': 8.}}
    assert branch_rank('recovery', short) < branch_rank('recovery', excessive)


def test_static_control_uses_only_station_votes_with_deterministic_ties():
    teachers = [{'examples': [{'domain': 'walk', 'task': 'alarm', 'action': a}
                              for a in ['W2', 'W0', 'W2']]}]
    assert static_from_training(teachers) == {'walk:alarm': 'W2'}


def test_arbitrary_walking_label_tie_is_not_a_training_opportunity():
    make = lambda action, duration: {'action': action, 'success': True, 'fall': False,
        'invalid_contact': False, 'duration_s': duration,
        'metrics': {'roll_rms_deg': .2, 'lateral_rms_m': .01}}
    teacher = {'examples': [{'domain': 'walk', 'task': 'alarm', 'action': 'W0'}],
        'trials': [{'domain': 'walk', 'task': 'alarm', 'student_preference': 'W1',
                    'outcomes': [make('W0', 10.), make('W1', 10.00001)]}]}
    assert meaningful_corrections([teacher]) == {}
    teacher['trials'][0]['outcomes'][1]['duration_s'] = 11.
    assert meaningful_corrections([teacher]) == {'walk': 1}


def test_diagnostic_clone_preserves_the_physical_state_and_next_step():
    from mochi.terrain_v12.world import TerrainWorld
    from mochi.balanced.onnx_walk import HubWalker, HoldWalker
    from mochi.terrain_v12.snapshot import branch
    w = TerrainWorld(71099, False)
    while w.d.time < .4:
        w.step(standing=True)
    w.walker = HubWalker(w)
    w.walker = HoldWalker(w)
    a, b = branch(w), branch(w)
    values = lambda x: np.r_[x.d.qpos, x.d.qvel, x.d.ctrl, x.d.time]
    assert hashlib.sha256(values(a).tobytes()).digest() == hashlib.sha256(values(w).tobytes()).digest()
    a.step()
    b.step()
    assert np.array_equal(a.d.qpos, b.d.qpos) and np.array_equal(a.d.qvel, b.d.qvel)
    assert a.base_force == b.base_force == 0
