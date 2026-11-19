"""Candidate desk routes checked against a detached MuJoCo geometry copy."""
import json, math
from pathlib import Path
import mujoco
import numpy as np
from .world import DeskWorld, ROOT

OUT = ROOT/'artifacts/richdesk-v10'
STATIONS = {'alarm':[-.375,.025,math.pi/2], 'drawer':[-.13,.02,math.pi/2],
            'laptop':[.30,.16,math.pi/2], 'globe':[.35,-.145,0.]}


class DeskSpace:
    def __init__(self):
        self.w = DeskWorld(31000); self.m = self.w.m; self.d = self.w.d
        self.initial = self.d.qpos.copy(); self.calls = 0; self.cache = {}
        self.robot = {i for i,b in enumerate(self.m.geom_bodyid) if int(b) in self.w.robot_bodies}
        self.feet = {i for i in self.robot if 'ankle_roll_link' in (mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,int(self.m.geom_bodyid[i])) or '')}
        # Enable all robot shells only in this planning copy; live physics is
        # unchanged. Broadphase contacts test full height-aware geometry.
        self.m.geom_contype[list(self.robot)] = 1; self.m.geom_conaffinity[list(self.robot)] = 1
        self.m.geom_margin[:] = .003
        self.desk = self.w.id('geom','desk')

    def bounds(self,g):
        a=self.m.geom_aabb[g]; R=self.d.geom_xmat[g].reshape(3,3)
        c=self.d.geom_xpos[g]+R@a[:3]; e=abs(R)@a[3:]
        return c-e,c+e

    def check(self,xy,yaw):
        key=tuple(np.round([*xy,yaw],5))
        if key in self.cache:return self.cache[key]
        self.calls+=1; self.d.qpos[:]=self.initial; self.d.qpos[:2]=xy
        self.d.qpos[2]=self.w.meta['pelvis_height_m']+self.w.terrain_height(*xy)
        self.d.qpos[3:7]=[math.cos(yaw/2),0,0,math.sin(yaw/2)]
        mujoco.mj_forward(self.m,self.d); collisions=[]
        for g in self.feet:
            lo,hi=self.bounds(g)
            if min(lo[0]+.6,.6-hi[0],lo[1]+.4,.4-hi[1])<.005:collisions.append('desk-edge')
        for c in self.d.contact:
            a,b=int(c.geom1),int(c.geom2)
            if self.desk in [a,b] or (a in self.robot)==(b in self.robot):continue
            robot=a if a in self.robot else b; other=b if a in self.robot else a
            # Terrain transitions need unequal foot heights; a rigid rest-pose
            # body sweep cannot certify them. Separate foot and dynamics gates
            # explicitly retain that obligation.
            if other in self.w.book_geoms:continue
            if c.dist<.002:
                collisions.append(mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_GEOM,other))
        result={'free':not collisions,'collisions':sorted(set(collisions))}
        self.cache[key]=result;return result

    def inspect(self,points):
        collisions=[]; length=0.; turning=0.; heading=points[0][2]
        for a,b in zip(points,points[1:]):
            delta=np.array(b[:2])-a[:2]; distance=float(np.linalg.norm(delta));length+=distance
            desired=b[4] if len(b)>4 else math.atan2(delta[1],delta[0]) if distance>1e-8 else b[2]
            turn=(desired-heading+math.pi)%(2*math.pi)-math.pi;turning+=abs(turn)
            for u in np.linspace(0,1,max(2,math.ceil(abs(turn)/.12)+1)):
                r=self.check(a[:2],heading+u*turn)
                if not r['free']:collisions.append({'at':a[:2],'kind':'turn',**r})
            for u in np.linspace(0,1,max(2,math.ceil(distance/.005)+1)):
                xy=(1-u)*np.array(a[:2])+u*np.array(b[:2]);r=self.check(xy,desired)
                if not r['free']:collisions.append({'at':xy.tolist(),'kind':'translation',**r})
            heading=desired
            if len(b)>3 and b[3]:
                turn=(b[2]-heading+math.pi)%(2*math.pi)-math.pi;turning+=abs(turn)
                for u in np.linspace(0,1,max(2,math.ceil(abs(turn)/.12)+1)):
                    r=self.check(b[:2],heading+u*turn)
                    if not r['free']:collisions.append({'at':b[:2],'kind':'station-turn',**r})
                heading=b[2]
        return {'sampled_collision_free':not collisions,'distance_m':length,'turning_rad':turning,
                'nominal_walking_seconds':length/.025+turning/.45,
                'collisions':collisions[:30],'collision_samples':len(collisions)}


def stair_feet(spec,reverse=False):
    """Conservative flat-foot landing suggestions; not a walking certificate."""
    w=DeskWorld(31000); centers=[-.19,-.155,-.108,-.09,-.048,.0,.025]
    if reverse:centers=list(reversed(centers))
    steps=[]
    for y in centers:
        for side,x in [('left',-.395),('right',-.355)]:
            z=w.terrain_height(x,y)
            corners=[w.terrain_height(x+dx,y+dy) for dx in [-.007,.007] for dy in [-.018,.018]]
            steps.append({'side':side,'position':[x,y,z],'flat_support':all(abs(h-z)<1e-6 for h in corners),
                          'orientation_rad':math.pi/2,'status':'planned-not-executed'})
    return steps


def main():
    OUT.mkdir(parents=True,exist_ok=True); space=DeskSpace(); spec=space.w.scene
    start=spec['initial_pose']; alarm=[*STATIONS['alarm'],True]; drawer=[*STATIONS['drawer'],True]
    laptop=[*STATIONS['laptop'],True]; globe=[*STATIONS['globe'],True]
    common=[start,alarm,[-.375,-.18,math.pi/2],[-.19,-.18,0],[-.19,-.03,math.pi/2],drawer]
    candidates={
      'short-direct':common+[laptop,globe],
      'front-corridor':common+[[.08,.02,0],[.08,-.055,math.pi/2],[.30,-.055,0],[.30,.02,math.pi/2],laptop,[.30,.02,math.pi/2,False,math.pi/2],[.35,-.145,0],globe],
      'wide-corridor':common+[[.08,.02,0],[.08,-.085,math.pi/2],[.325,-.085,0],[.325,.10,math.pi/2],laptop,[.30,.02,math.pi/2,False,math.pi/2],[.325,-.085,math.pi/2],globe]}
    evaluated=[]
    for name,points in candidates.items():
        measured=space.inspect(points);evaluated.append({'id':name,'points':points,**measured,
             'estimated_motion_cost':measured['nominal_walking_seconds']+12.,
             'time_caveat':'Command-speed estimate plus declared 12-second terrain overhead, excludes tasks and recovery; not measured.'})
    valid=[r for r in evaluated if r['sampled_collision_free']]
    selected=min(valid,key=lambda r:r['estimated_motion_cost']) if valid else None
    report={'study':'mochi-richdesk-v10','status':'geometric-plan-only','scene':spec,'stations':STATIONS,
      'selected_candidate':selected['id'] if selected else None,'candidates':evaluated,
      'footsteps':{'ascent':stair_feet(spec),'descent':stair_feet(spec,True)},
      'geometry_queries':space.calls,'clearance_m':.002,'global_optimality_claim':False,
      'scope':'Detached rest-pose collision sampling. Swing envelopes, dynamic balance, approach and recovery must still pass real physics.',
      'training_gate':'No Tinker campaign before complete physical route feasibility.'}
    mujoco.mj_forward(space.m,space.d);obstacles=[]
    space.d.qpos[:]=space.initial;mujoco.mj_forward(space.m,space.d)
    for g in range(space.m.ngeom):
        if g in space.robot or g==space.desk:continue
        lo,hi=space.bounds(g);obstacles.append({'name':mujoco.mj_id2name(space.m,mujoco.mjtObj.mjOBJ_GEOM,g),'lo':lo.tolist(),'hi':hi.tolist()})
    report['obstacles']=obstacles
    (OUT/'route-plan.json').write_text(json.dumps(report,indent=2)+'\n')
    plot(report)
    print(json.dumps({'selected':report['selected_candidate'],'candidates':[{k:r[k] for k in ['id','sampled_collision_free','distance_m','turning_rad','collision_samples']} for r in evaluated]}))


def plot(r):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(13,9));fig.patch.set_facecolor('#f4f1e9');ax.set_facecolor('#dfc7a3')
    for p in r['obstacles']:
        lo,hi=np.array(p['lo']),np.array(p['hi']);name=p['name'] or ''
        color='#7f9b9b' if 'book-step' in name else '#606d72'
        ax.add_patch(Rectangle(lo[:2],*(hi-lo)[:2],fc=color,ec='#f4f1e9',alpha=.65,lw=.6))
    colors=['#ba7368','#246e79','#9a8a52']
    for c,color in zip(r['candidates'],colors):
        xy=np.array([p[:2] for p in c['points']]);ax.plot(*xy.T,'o-',ms=3,c=color,lw=2,label=f"{c['id']}: {c['distance_m']:.2f} m; {c['collision_samples']} flagged samples")
    for name,p in r['stations'].items():
        ax.annotate(name.replace('laptop','laptop close'),p[:2],xytext=(9,9),textcoords='offset points',weight='bold',fontsize=10)
        ax.arrow(*p[:2],.04*math.cos(p[2]),.04*math.sin(p[2]),width=.0015,color='#20343c')
    for p in r['footsteps']['ascent']:
        x,y,z=p['position'];ax.add_patch(Rectangle((x-.007,y-.018),.014,.036,fill=False,ec='#fff8db',lw=.9))
    for p in r['scene']['props']:
        if p['asset'] in ['printer','mug','notebook']:
            ax.text(*p['pos'][:2],p['asset'],ha='center',fontsize=9,color='#fff8ec')
    start=r['scene']['initial_pose'];ax.scatter(*start[:2],s=100,c='#20343c',marker='*');ax.annotate('START',start[:2],xytext=(-45,-20),textcoords='offset points')
    ax.text(-.58,.37,'CLOCK ON BOOKS: 3 × 8 mm\nOutlined feet are landing proposals, not a recorded gait.',fontsize=9,va='top')
    ax.set(xlim=(-.6,.6),ylim=(-.4,.4),aspect='equal',xlabel='Desk x (m)',ylabel='Desk y (m)')
    ax.set_title('MOCHI / furnished desk route study\nCollision sampling first. Physical execution still required.',loc='left',pad=16)
    ax.legend(loc='lower left',fontsize=9,facecolor='#f4f1e9');fig.tight_layout()
    fig.savefig(OUT/'route-plan.png',dpi=170);fig.savefig(OUT/'route-plan.svg');plt.close(fig)


if __name__=='__main__':main()
