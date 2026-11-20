"""Add the existing measured-support press to the furnished-desk world.

The rejected lateral-force experiment is available only behind an explicit
engineering flag. Production candidates retain the original force controller.
Legacy actions, physical state, contacts, force limits and verifiers stay intact.
"""
from ..smooth_v16.world import EfficientWorld, restore as old_restore
from ..control_v8.support import SupportWorld
from ..control_v8.manipulation import ControlWorld


class ContactWorld(EfficientWorld, SupportWorld):
    def laptop(self, p, horizon):
        if getattr(self,'contact_force_schedule',False):
            from .contact import adaptive_laptop
            return adaptive_laptop(self,p,horizon)
        if getattr(self,'contact_rear_face',False):
            raise RuntimeError('Rear-face pilot rejected; archived source retained')
        if getattr(self, 'contact_inverse_dynamics', False):
            from .stance import ContactHold
            from ..balanced.onnx_walk import HoldWalker
            self.walker=ContactHold(self)
            self.contact_stance_active=True
            try:
                result=ControlWorld.laptop(self,p,horizon)
                result['stance_controller']=self.walker.description()
                return result
            finally:
                self.contact_stance_active=False
                self.walker=HoldWalker(self)
        if getattr(self, 'contact_lateral_support', False) and p.code in ['P5', 'P6']:
            return SupportWorld.laptop(self, p, horizon)
        return ControlWorld.laptop(self, p, horizon)

    def step(self,*args,**kwargs):
        if getattr(self,'parked_arm_transit',False):
            if hasattr(self.walker,'control_arms'):self.walker.control_arms=False
            for arm in self.arm.values():self.d.ctrl[arm['acts']]=arm['rest']
        if getattr(self,'contact_stance_active',False):kwargs['standing']=False
        super().step(*args,**kwargs)


def restore(saved, record=False):
    w=old_restore(saved, record)
    w.__class__=ContactWorld
    w.support_press=None
    w.support_push_start=None
    w.support_peak_x=0.
    return w
