"""The original-controller ablation must preserve actual physical dynamics."""
import numpy as np
from mochi.curriculum.world import World
from mochi.curriculum.gait_control import install,slew

def test_native_modulation_is_the_original_physics():
 a,b=World(18000),World(18000);install(b,'native')
 for _ in range(600):
  a.step((.025,0,.45));b.step((.025,0,.45))
 assert np.array_equal(a.d.qpos,b.d.qpos)
 assert a.base_force==b.base_force==0

def test_velocity_slew_bounds_vector_acceleration():
 old=np.array([0.,0.]);new=slew(old,[1.,1.],.14,.01)
 assert np.linalg.norm(new-old)<=.14*.01+1e-12
 assert np.all(new>=0)
