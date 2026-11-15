from dataclasses import replace
import numpy as np
import pytest
from mochi.simulation import Policy,rollout,scenario,PROTOCOL,summarize

def test_reproducible_contact_and_trajectory():
    p=Policy(name='test-slow',speed=.05,stop_distance=.02)
    a=rollout(p,101,record=True);b=rollout(p,101,record=True)
    assert a==b
    assert a['contact_steps']>0 and a['success']
    assert a['final_distance_m']<=PROTOCOL['success_radius_m']
    t=a['trajectory'];i=t['body_names'].index('puck')
    assert np.linalg.norm(np.array(t['frames'][0]['positions'][i])-t['frames'][-1]['positions'][i])>.03
    assert all(np.isfinite(f['positions']).all() for f in t['frames'])

def test_initial_controller_can_fail_without_invalid_physics():
    r=rollout(Policy(),101)
    assert not r['success'] and not r['invalid'] and r['contact_steps']>0

def test_evaluation_splits_are_disjoint_and_shift_is_physical():
    a,b,c=(set(PROTOCOL[x]) for x in ['development_seeds','heldout_seeds','shift_seeds'])
    assert not a&b and not a&c and not b&c
    assert scenario(101,True)['friction']>scenario(101)['friction']
    assert scenario(101,True)['mass']>scenario(101)['mass']

def test_policy_bounds_and_small_sample_uncertainty():
    with pytest.raises(AssertionError):replace(Policy(),speed=20).validate()
    result=summarize([{'success':True,'final_distance_m':.01,'invalid':False}])
    assert result['wilson_95'][0]<.5 and result['wilson_95'][1]>.99
