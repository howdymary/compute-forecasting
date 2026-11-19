"""Detached counterfactual branches, never spliced into the continuous demo."""
import copy
import mujoco
import numpy as np
from .onnx_walk import HubWalker,HoldWalker

MODEL_FIELDS=['actuator_gainprm','actuator_biasprm','actuator_biastype',
              'actuator_ctrllimited','actuator_forcelimited','actuator_forcerange']

def branch(source):
    from .sequence import SequenceWorld
    w=SequenceWorld(source.s['seed'],False,scene=source.scene)
    for field in MODEL_FIELDS:getattr(w.m,field)[:]=getattr(source.m,field)
    # MjData's supported copy preserves solver warm starts and derived arrays.
    # Re-running mj_forward here refreshes pre-integration caches and can
    # change a feedback policy's next observation. Keep the exact data copy.
    w.d=copy.copy(source.d)
    skip={'m','d','viz','walker','frames','events','control_telemetry','measurements'}
    for name,value in source.__dict__.items():
        if name not in skip:setattr(w,name,copy.deepcopy(value))
    w.record=False;w.frames=[];w.events=[];w.control_telemetry=[]
    w.measurements=copy.deepcopy(source.measurements[-30:])
    old=source.walker
    if isinstance(old,HoldWalker):
        w.walker=HubWalker(w)
        w.walker=HoldWalker(w)
        fields=['target','initial_target','neutral','origin','final_target','standing_target','previous_description']
    elif isinstance(old,HubWalker):
        w.walker=HubWalker(w)
        fields=['action','target','filtered_command','velocity_integral','yaw_integral','last','origin','calls','feedback','mode','control_arms','stand_phase','stage']
    else:
        fields=[]
    for name in fields:setattr(w.walker,name,copy.deepcopy(getattr(old,name)))
    # Hold constructors park arm commands; restore those commands so even
    # controller initialization does not alter the detached starting state.
    w.d.ctrl[:]=source.d.ctrl
    return w
