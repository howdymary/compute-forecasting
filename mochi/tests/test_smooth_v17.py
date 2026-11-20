"""Extended-action safety and legacy-controller compatibility contracts."""
from mochi.smooth_v17 import policy
from mochi.smooth_v16.policy import choices as old_choices
from mochi.control_v8.manipulation import PRESSES


def test_extension_keeps_every_existing_action_in_order():
    for task in ['alarm','drawer','laptop','globe']:
        for domain in ['walk',task,'recovery']:
            old=old_choices(domain,task)
            assert policy.choices(domain,task)[:len(old)]==old
    assert policy.choices('alarm','alarm')[-1]=='H0'
    assert policy.choices('laptop','laptop')[-1]=='P4'
    assert next(p for p in PRESSES if p.code=='P2').force==.55


def test_only_the_new_laptop_choice_changes_its_force_and_horizon(monkeypatch):
    class World:
        def do_task(self,*args,**kwargs):return args,kwargs
    args,kwargs=policy.execute(World(),'laptop','laptop','P4')
    assert args[0]=='laptop' and args[1].force==.60 and args[1].release_degrees==42
    assert kwargs=={'max_seconds':16.}
    monkeypatch.setattr(policy,'old_execute',lambda *args:('legacy',args[-1]))
    assert policy.execute(World(),'laptop','laptop','P2')==('legacy','P2')
