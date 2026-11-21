import copy
import json
from pathlib import Path

from mochi.paperfree_v19.objective import valid_branch as previous_branch
from mochi.paperfree_v19r1.objective import branch_reward, qualify, valid_branch

ROOT = Path(__file__).resolve().parents[1]


def probe():
    return json.loads((ROOT / 'evidence/paperfree-v19r1/branch-scope-probe.json').read_text())


def test_recorded_short_branch_does_not_receive_a_whole_route_rms_gate():
    row = probe()['branch']
    assert row['success'] and row['native_smoothness']['sampled_acceleration_rms_rad_s2'] > 161.4
    assert not previous_branch(row, 'walk')
    assert valid_branch(row, 'walk')
    assert branch_reward('walk', row) > 0


def test_local_safety_and_real_foot_clearance_remain_required():
    row = probe()['branch']
    for key in ['fall', 'invalid_contact']:
        bad = copy.deepcopy(row)
        bad[key] = True
        assert not valid_branch(bad, 'walk')
    row['flat_foot_clearance']['moving_median_peak_m'] = .0025
    assert not valid_branch(row, 'walk')


def test_complete_routes_keep_the_original_native_limit():
    row = probe()['full_row']
    cfg = json.loads((ROOT / 'configs/paperfree-v19-training.json').read_text())
    assert qualify(row, cfg)['qualified_complete']
    row['episode']['native_smoothness']['sampled_acceleration_rms_rad_s2'] = 165.
    assert not qualify(row, cfg)['qualified_complete']
