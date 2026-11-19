"""Counterfactual training branches; never spliced into a demonstration."""
from .development import state,restore

def branch(source):
    return restore(state(source,include_history=False),record=False)
