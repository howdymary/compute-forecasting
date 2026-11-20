"""Safety isolation and categorical-interface checks for the new study."""
import pytest
from mochi.contact_v18 import policy
from mochi.smooth_v17 import policy as parent

def test_legacy_choices_keep_their_order_and_decision_labels_match():
    for task in ['alarm','drawer','laptop','globe']:
        for domain in ['walk',task,'recovery']:
            before=parent.choices(domain,task);after=policy.choices(domain,task)
            assert after[:len(before)]==before
            observed={'domain':domain,'station':task,'available_actions':after}
            assert list(policy.decision(observed).labels)==after

def test_controller_failure_cannot_leave_the_force_schedule_enabled():
    class FailedWorld:
        def do_task(self,*args,**kwargs):raise RuntimeError('contact aborted')
    w=FailedWorld()
    with pytest.raises(RuntimeError,match='contact aborted'):policy.execute(w,'laptop','laptop','P5')
    assert not w.contact_force_schedule

def test_pulsed_controller_does_not_accidentally_use_the_scheduled_controller():
    class World:
        contact_force_schedule=True
        def do_task(self,*args,**kwargs):
            assert not self.contact_force_schedule
            return args,kwargs
    w=World();args,kwargs=policy.execute(w,'laptop','laptop','P6')
    assert args[1].pulse_on==.30 and args[1].pulse_off==.15
    assert args[1].force<.8 and kwargs['max_seconds']==24.
    assert not w.contact_force_schedule
