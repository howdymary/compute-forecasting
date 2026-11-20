"""Selection and provenance checks for the interrupted-collector repair."""
import copy
import numpy as np
from mochi.smooth_v16_resume.objective import select_checkpoint
from mochi.smooth_v16_resume.remote import cached_outcome_eligible,physical_hash_from_saved
from mochi.smooth_v16.remote import physical_hash
from mochi.smooth_v16.world import EfficientWorld,state,restore
from mochi.balanced.onnx_walk import HubWalker,HoldWalker


def test_cache_requires_exact_initial_state():
    assert cached_outcome_eligible({'initial_state_sha256':'same'},{'physical_state_sha256':'same'})
    assert not cached_outcome_eligible({'initial_state_sha256':'old'},{'physical_state_sha256':'new'})
    assert not cached_outcome_eligible(None,{'physical_state_sha256':'same'})


def test_full_snapshot_preserves_physical_and_controller_state_without_advancing():
    w=EfficientWorld(41001,True);w.walker=HubWalker(w);w.walker=HoldWalker(w)
    saved=state(w,include_history=True);x=restore(saved,True)
    assert physical_hash_from_saved(saved)==physical_hash(w)==physical_hash(x)
    for field in ['qpos','qvel','ctrl','qacc_warmstart']:
        np.testing.assert_array_equal(getattr(w.d,field),getattr(x.d,field))
    np.testing.assert_array_equal(w.m.dof_frictionloss,x.m.dof_frictionloss)
    np.testing.assert_array_equal(w.walker.target,x.walker.target)
    assert w.d.time==x.d.time==0


def test_unqualified_parent_does_not_make_every_candidate_cost_equal():
    base={'qualified_complete_successes':0,'falls':0,'invalid_contacts':0}
    early={**base,'qualified_complete_successes':3,'successful_mean_steps':500,
        'successful_mean_recovery_arm_joint_travel_rad':5,'successful_mean_seconds':350}
    later={**early,'successful_mean_steps':400,'successful_mean_recovery_arm_joint_travel_rad':4.5}
    cps=[{'update':0,'development':base},{'update':1,'development':early},{'update':4,'development':later}]
    cfg={'selection_without_qualified_parent':{'steps':500,'recovery_rad':5,'seconds':420}}
    assert select_checkpoint(cps,{},cfg)['update']==4
    regressed=copy.deepcopy(cps);regressed[2]['development']['qualified_complete_successes']=2
    assert select_checkpoint(regressed,{},cfg)['update']==1
