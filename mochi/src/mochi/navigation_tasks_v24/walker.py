"""Keep recovered arms under position actuators during crowded navigation."""
from mochi.balanced.onnx_walk import HubWalker


class NavigationWalker(HubWalker):
    """Fixed gait inference for legs; retain the validated arm command targets.

    Arms are neither welded nor animated. Existing position actuators and
    gravity compensation hold their last recovered targets under the same
    force limits. Native neural weights remain unchanged.
    """
    def __init__(self, world):
        super().__init__(world)
        self.control_arms = False

    def resume(self):
        super().resume()
        self.control_arms = False

    def command(self, velocity):
        self.control_arms = False
        super().command(velocity)

    def description(self):
        return {**super().description(), 'navigation_arm_mode': 'retain recovered actuator targets',
            'scope': 'Shared controller engineering; native gait weights fixed.'}
