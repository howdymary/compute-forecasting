import pytest
from mochi.efficient_v15.steps import StepCounter


def sample(counter, t, load, position, yaw=0.):
    counter.update(t, {'left': {'position': position, 'yaw': yaw}}, {'left': load}, 'turning')


def test_counts_a_real_step_and_verified_touchdown():
    c = StepCounter()
    for t, load, x, z in [(0,.8,0,0),(.01,0,0,0),(.05,0,.003,.004),
                          (.10,.8,.02,0),(.15,.8,.02,0)]:
        sample(c,t,load,[x,0,z])
    assert c.summary()['attempts'] == c.summary()['completed'] == 1
    assert c.events[0]['touchdown_t'] == pytest.approx(.10)


def test_rejects_contact_chatter_without_foot_motion():
    c = StepCounter()
    for t, load in [(0,.8),(.01,0),(.05,.8),(.10,.8),(.15,.8)]:
        sample(c,t,load,[0,0,0])
    assert c.summary()['attempts'] == 0


def test_unfinished_and_turning_attempts_are_not_hidden():
    c = StepCounter()
    sample(c,0,.8,[0,0,0])
    sample(c,.01,0,[0,0,0])
    sample(c,.06,0,[0,0,0],.2)
    assert c.summary()['attempts'] == c.summary()['unfinished'] == 1
    assert c.summary()['by_category'] == {'turning':1}


def test_legacy_directional_command_is_preserved_for_w0():
    import math
    from mochi.directional_v14.navigation import command as previous, NavigationParameters as Prior
    from mochi.efficient_v15.navigation import command, NavigationParameters
    for position,yaw,goal,aligning in [((0,0),0,(.2,0,0),False),((0,0),math.pi/2,(.2,0,0),False),
                                      ((.29,.15),1.5,(.30,.16,math.pi/2),True)]:
        assert command(position,yaw,goal,0.,.055,NavigationParameters(),aligning)==previous(position,yaw,goal,0.,.055,Prior(),aligning)


def test_new_actions_expose_distinct_commands_without_redefining_legacy_walks():
    from mochi.efficient_v15.policy import WALKS,NAVIGATION,choices
    from mochi.terrain_v12.legs import WALKS as original
    from mochi.efficient_v15.navigation import command
    for code,p in original.items():
        assert WALKS[code]==p
    assert choices('walk','alarm')==['W0','W1','W2']
    assert choices('walk','laptop')==['W0','W3','W4']
    velocities=[command((0,0),0,(.06,0,0),0.,WALKS[c]['flat_speed'],NAVIGATION[c])[0][0] for c in ['W0','W3','W4']]
    assert velocities[0]<velocities[1]<velocities[2]


def test_counterfactual_restores_counter_and_next_physical_step_exactly():
    import numpy as np
    from mochi.efficient_v15.world import EfficientWorld,state,restore
    from mochi.balanced.onnx_walk import HubWalker,HoldWalker
    w=EfficientWorld(41001,False)
    w.use_native_stand=True
    while w.d.time<.4:
        w.step(standing=True)
    w.walker=HubWalker(w)
    w.walker=HoldWalker(w)
    saved=state(w)
    a,b=restore(saved),restore(saved)
    a.step()
    b.step()
    assert isinstance(a,EfficientWorld)
    assert np.array_equal(a.d.qpos,b.d.qpos)
    assert np.array_equal(a.d.qvel,b.d.qvel)
    assert a.step_counter.summary()==b.step_counter.summary()
