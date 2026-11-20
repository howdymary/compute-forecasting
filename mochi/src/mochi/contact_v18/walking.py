"""Use the validated legacy route with a bounded swing-clearance correction."""
from ..smooth_v17.policy import execute

def lifted_leg(w,task):
    return execute(w,'walk',task,'W6' if task=='globe' else 'W5')
