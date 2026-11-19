"""Strict full-sole support check, in addition to the V11 fixture audit."""
import copy,math
import mujoco,numpy as np
from scipy.spatial import ConvexHull,QhullError
from ..balanced.sequence import SequenceWorld


class TerrainWorld(SequenceWorld):
    def __init__(self,seed=41000,record=False,scene=None):
        from ..richdesk.world import scene_spec
        scene=copy.deepcopy(scene or scene_spec())
        if 'terrain_conditions' not in scene:
            rng=np.random.default_rng(seed+11203)
            conditions={'initial_xy_offset_m':[0.,0.],'initial_yaw_offset_rad':0.,'terrain_friction_multiplier':1.}
            if seed>=42000:
                conditions={'initial_xy_offset_m':rng.uniform(-.002,.002,2).tolist(),
                    'initial_yaw_offset_rad':float(rng.uniform(-.015,.015)),
                    'terrain_friction_multiplier':float(rng.uniform(.95,1.05))}
                scene['initial_pose'][:2]=(np.array(scene['initial_pose'][:2])+conditions['initial_xy_offset_m']).tolist()
                scene['initial_pose'][2]+=conditions['initial_yaw_offset_rad']
            scene['terrain_conditions']=conditions
        super().__init__(seed,record,scene=scene)
        for g in {self.id('geom','desk')}|self.book_geoms:
            self.m.geom_friction[g,0]*=scene['terrain_conditions']['terrain_friction_multiplier']
        self.terrain_conditions=scene['terrain_conditions']

    def sole_patch(self,side):
        body=self.id('body',side+'_ankle_roll_link');R=self.d.xmat[body].reshape(3,3);points=[];load=0.
        for i,c in enumerate(self.d.contact):
            a,b=int(c.geom1),int(c.geom2);other=b if a in self.support_geoms else a if b in self.support_geoms else -1
            if other<0 or int(self.m.geom_bodyid[other])!=body or abs(float(c.frame[2]))<.7:continue
            force=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,force)
            if force[0]>.0005:points.append(c.pos[:2].copy());load+=float(force[0])
        area=0.;capture_margin=None
        if len(points)>=3:
            try:
                hull=ConvexHull(np.unique(points,axis=0));area=float(hull.volume)
                J=np.zeros((3,self.m.nv));mujoco.mj_jacSubtreeCom(self.m,self.d,J,1)
                com=self.d.subtree_com[1];height=max(.02,float(com[2]-(self.d.xpos[body]+R@np.array([.005,0,-.00585]))[2]))
                capture=com[:2]+(J@self.d.qvel)[:2]/math.sqrt(9.81/height)
                capture_margin=float(np.min(-(hull.equations[:,:2]@capture+hull.equations[:,2])))
            except QhullError:pass
        return {'loaded':load>.05,'load_n':load,'contact_points':len(points),'area_m2':area,
                'capture_margin_m':capture_margin,
                'tilt_degrees':math.degrees(math.acos(float(np.clip(R[2,2],-1,1))))}

    def foot_touching(self,side):
        if not super().foot_touching(side):return False
        p=self.sole_patch(side)
        return p['loaded'] and p['contact_points']>=3 and p['area_m2']>.00010 and p['tilt_degrees']<1.5
