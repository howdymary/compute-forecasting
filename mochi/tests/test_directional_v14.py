import math
import pytest
from mochi.directional_v14.navigation import command, NavigationParameters


def test_sideways_target_first_requests_a_real_turn():
    velocity, phase, desired = command((0., 0.), math.pi/2, (.2, 0., 0.), 0., .055, NavigationParameters())
    assert phase == 'turn-to-path'
    assert velocity[0] == velocity[1] == 0.
    assert velocity[2] < 0 and desired == pytest.approx(0.)


def test_aligned_target_is_forward_travel():
    velocity, phase, _ = command((0., 0.), 0., (.2, 0., 0.), 0., .055, NavigationParameters())
    assert phase == 'walk-forward'
    assert velocity[0] > 0 and velocity[1] == pytest.approx(0.)


def test_small_final_trim_keeps_the_task_facing_direction():
    velocity, phase, desired = command((.29, .153), math.pi/2, (.30, .16, math.pi/2),
                                       0., .055, NavigationParameters(), aligning=True)
    assert desired == pytest.approx(math.pi/2)
    assert phase == 'task-alignment' and abs(velocity[1]) <= .012


def test_wrap_uses_the_short_rotation_across_pi():
    _, _, desired = command((0., 0.), math.radians(179), (-.2, -.0035, math.radians(-179)),
                             math.pi, .055, NavigationParameters(), aligning=True)
    velocity, phase, _ = command((0., 0.), math.radians(179), (-.2, -.0035, desired),
                                  math.pi, .055, NavigationParameters(), aligning=True)
    assert phase == 'task-alignment'
    assert 0 < velocity[2] < .1
