"""Measured route and sole-reference tracks from one uninterrupted rollout."""
import json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np,mujoco
from scipy.spatial.transform import Rotation
from mochi.terrain_v12.world import TerrainWorld

def main():
    row=json.loads((ROOT/'artifacts/terrain-v12/continuous-four-task-reference-2.json').read_text());e=row['episode'];w=TerrainWorld(row['seed'],False)
    fig,(ax,side)=plt.subplots(1,2,figsize=(13,5.8),gridspec_kw={'width_ratios':[1.25,1]});fig.patch.set_facecolor('#f6f3ea')
    for a in [ax,side]:a.set_facecolor('#f6f3ea');a.spines[['top','right']].set_visible(False)
    for g in range(w.m.ngeom):
        if int(w.m.geom_bodyid[g]) in w.robot_bodies or w.m.geom_type[g]!=mujoco.mjtGeom.mjGEOM_BOX:continue
        if not w.m.geom_contype[g]:continue
        name=mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_GEOM,g) or ''
        if name=='desk':continue
        sx,sy=w.m.geom_size[g,:2];R=w.d.geom_xmat[g].reshape(3,3);pos=w.d.geom_xpos[g]
        points=np.array([pos+R@np.array([x,y,0]) for x,y in [(-sx,-sy),(sx,-sy),(sx,sy),(-sx,sy)]])[:,:2]
        ax.add_patch(Polygon(points,facecolor='#b5b69e' if 'book-step' in name else '#ddd7c8',edgecolor='#a09d8b',linewidth=.6))
    frames=e['trajectory']['frames'];positions=np.array([f['positions'][1] for f in frames]);ax.plot(positions[:,0],positions[:,1],c='#a65a3e',lw=1.8,label='Measured pelvis path')
    labels={'book-ascent':'1 · Clock','drawer-station':'2 · Drawer','laptop-station':'3 · Laptop','globe-station':'4 · Globe'}
    for a in row['arrivals']:
        if a['label'] not in labels:continue
        x,y=a['root'][:2];ax.scatter(x,y,s=30,c='#244b47',zorder=4);ax.annotate(labels[a['label']],(x,y),xytext=(8,7),textcoords='offset points',fontsize=9,color='#244b47')
    ax.scatter(*positions[0,:2],s=24,c='#244b47');ax.annotate('Start',positions[0,:2],xytext=(-34,-16),textcoords='offset points',fontsize=9)
    ax.set(xlim=(-.6,.6),ylim=(-.4,.4),xlabel='Desk x (m)',ylabel='Desk y (m)',title='One continuous four-task route');ax.set_aspect('equal');ax.legend(loc='lower right',frameon=False,fontsize=9)
    y=np.linspace(-.23,.06,600);side.step(y*1000,[w.terrain_height(-.375,v)*1000 for v in y],where='mid',c='#636b4b',lw=2,label='Book surfaces')
    names=e['trajectory']['body_names']
    for s,color in [('left','#b56d46'),('right','#417b80')]:
        idx=names.index(s+'_ankle_roll_link');points=[]
        for f in frames:
            if f['t']>135:break
            q=f['quaternions'][idx];p=np.array(f['positions'][idx])+Rotation.from_quat([q[1],q[2],q[3],q[0]]).apply([.005,0,-.00585]);points.append(p)
        p=np.array(points);side.plot(p[:,1]*1000,p[:,2]*1000,c=color,lw=.8,alpha=.85,label='Measured '+s+' sole centre')
    side.set(xlabel='Forward desk coordinate y (mm)',ylabel='Height above desk (mm)',title='Measured ascent and descent',ylim=(-2,43));side.legend(loc='upper left',frameon=False,fontsize=8)
    fig.suptitle('MOCHI · Verified engineering reference · seed 41001',x=.05,ha='left',fontsize=16,color='#244b47')
    fig.text(.05,.02,'251.46 simulated seconds · four tasks and recoveries passed · no fall or forbidden contact · zero applied base force\nInitial object collision envelopes and measured body trajectories. This is controller engineering, not a trained-checkpoint result.',fontsize=9,color='#4c594c')
    fig.tight_layout(rect=[0,.09,1,.93]);out=ROOT/'docs/terrain-v12-route.png';fig.savefig(out,dpi=160);print(out)

if __name__=='__main__':main()
