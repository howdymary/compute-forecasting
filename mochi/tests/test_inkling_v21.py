import pytest
from mochi.inkling_v21.controls import validate


@pytest.mark.parametrize('changes', [
    {'root_position': [0, 0, 1]}, {'force_n': .81}, {'force_n': float('nan')},
    {'force_n': True}, {'station_x_m': .1}, {'success_threshold': 1},
])
def test_external_proposals_cannot_change_physics_or_escape_bounds(changes):
    with pytest.raises(ValueError):
        validate({'id': 'proposal', 'domain': 'laptop', 'changes': changes})


def test_boolean_controller_flag_is_not_coerced_from_text():
    with pytest.raises(ValueError):
        validate({'id': 'proposal', 'domain': 'navigation', 'changes': {'terminal_translation_deadband': 'false'}})


def test_valid_proposal_is_copied_without_executing_explanation():
    candidate = {'id': 'proposal', 'domain': 'navigation', 'changes': {'terminal_translation_deadband': True},
        'mechanism': 'This text is never evaluated as Python.'}
    copy = validate(candidate)
    copy['changes']['terminal_translation_deadband'] = False
    assert candidate['changes']['terminal_translation_deadband'] is True


@pytest.mark.parametrize('changes', [{'station_position_tolerance_m': .0121}, {'globe_clearance_y_m': .04}])
def test_new_fields_cannot_loosen_arrival_or_exceed_route_bounds(changes):
    domain = 'laptop' if 'station_position_tolerance_m' in changes else 'navigation'
    with pytest.raises(ValueError):
        validate({'id': 'proposal', 'domain': domain, 'changes': changes})


def test_profile_choice_is_limited_to_existing_force_limited_controllers():
    validate({'id': 'pulse', 'domain': 'laptop', 'changes': {'profile': 'P6'}})
    with pytest.raises(ValueError):
        validate({'id': 'pulse', 'domain': 'laptop', 'changes': {'profile': '__import__("os")'}})
