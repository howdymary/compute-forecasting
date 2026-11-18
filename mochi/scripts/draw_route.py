"""Draw the route consumed by control, its swept-envelope assumptions and data."""
import argparse,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Polygon,Circle
import numpy as np

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--route',default=str(root/'configs/desk-route-v1.json'));p.add_argument('--executed');p.add_argument('--output',default=str(root/'web/desk/planning/desk-route'));args=p.parse_args();route=json.loads(Path(args.route).read_text())
plt.rcParams.update({'font.family':'sans-serif','font.size':10,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(14,8));fig.patch.set_facecolor('#f5f3ed');ax.set_facecolor('#eee7da')
ax.set_aspect('equal');ax.set_xlim(-.65,.65);ax.set_ylim(-.45,.45);ax.add_patch(Rectangle((-.6,-.4),1.2,.8,fill=False,color='#3f4846',lw=2));ax.add_patch(Rectangle((-.59,-.39),1.18,.78,fill=False,edgecolor='#bf9655',ls=':',lw=1))
colors=['#708b79','#a68e72','#8a98a1','#8a9277']
for (name,box),color in zip(route['obstacles'].items(),colors):
 lo,hi=map(np.array,[box['lo'],box['hi']]);pad=route['clearance']['total_m'];ax.add_patch(Rectangle(lo[:2]-pad,hi[0]-lo[0]+2*pad,hi[1]-lo[1]+2*pad,facecolor=color,alpha=.14,hatch='///',edgecolor=color));ax.add_patch(Rectangle(lo[:2],hi[0]-lo[0],hi[1]-lo[1],facecolor=color,edgecolor='#52625b',alpha=.6));ax.text((lo[0]+hi[0])/2,hi[1]+.024,name.upper(),ha='center',fontsize=9,color='#45514c')
old=np.array([route['initial_pose'][:2]]+[x['pose'][:2] for x in route['old_route']]);ax.plot(old[:,0],old[:,1],'--',c='#92928d',lw=1.7,label='Existing waypoint line')
for i,leg in enumerate(route['legs']):
 for s in leg['segments']:
  a,b=np.array(s['from']),np.array(s['to']);ax.plot([a[0],b[0]],[a[1],b[1]],c='#2c777a',lw=2.4,label='New executable reference' if i==0 and s is leg['segments'][0] else None)
 x,y,h=leg['goal'];ax.add_patch(Circle((x,y),.012,fill=False,color='#2c777a',lw=1.2));ax.arrow(x,y,.037*math.cos(h),.037*math.sin(h),head_width=.009,color='#2c777a',length_includes_head=True);ax.text(x-.012,y-.012,str(i+1),ha='right',fontsize=9,color='#294c4c')
 # Actual rest-pose projected visual/physical geom bounds, not a guessed robot
 # rectangle. The planner itself checks 3D geometry at sampled gait poses.
 footprint=next((p for p in route.get('robot_projections',[]) if p['task']==leg['task']),None)
 if footprint:
  ax.add_patch(Polygon(footprint['body_xy'],fill=False,edgecolor='#447d80',alpha=.45,lw=.8))
  for xy in footprint['feet_xy']:ax.add_patch(Rectangle(np.min(xy,axis=0),np.ptp(xy,axis=0)[0],np.ptp(xy,axis=0)[1],fill=False,edgecolor='#447d80',alpha=.45,lw=.6))
 cx=-.49+i*.28;ax.text(cx,-.19,f"{i+1} / {leg['task'].upper()}\n\n{leg['length_m']:.3f} m · ~{leg['nominal_motion_s']:.1f} s*\n{x:.3f}, {y:.3f} m\nFacing {math.degrees(h):.0f}°",ha='left',va='top',fontsize=9,color='#294c4c')
start=route['initial_pose'];ax.scatter(*start[:2],s=45,c='#303e39',zorder=8);ax.arrow(*start[:2],.04*math.cos(start[2]),.04*math.sin(start[2]),head_width=.008,color='#303e39');ax.text(start[0]-.015,start[1]-.05,'START',ha='center',fontsize=9)
if args.executed:
 row=json.loads(Path(args.executed).read_text());episode=row.get('episode',row);frames=episode['trajectory']['frames'];xy=np.array([f['positions'][1][:2] for f in frames]);ax.plot(xy[:,0],xy[:,1],c='#b66046',lw=1,alpha=.8,label='Recorded pelvis motion (25 Hz)')
ax.legend(loc='upper left',bbox_to_anchor=(.04,.92),ncol=3,frameon=False,fontsize=9);ax.set_xlabel('Desk x (m)');ax.set_ylabel('Desk y (m)');ax.grid(alpha=.12);ax.set_title('MOCHI / Route planning before further training',loc='left',fontsize=18,pad=20)
fig.text(.125,.03,f"Reference {route['version']} · {route['length_m']:.3f} m · *{route['nominal_motion_s']:.1f} s command-speed estimate, excluding acceleration, tasks and settling.\nHatching: 10 mm fixture envelope. 7 sampled gait poses + 7.5 mm / 7.5° sweep checks; no continuous-motion or global-optimality certificate.",fontsize=9,color='#55615c')
fig.subplots_adjust(bottom=.16,top=.89);out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
for ext in ['svg','png']:fig.savefig(out.with_suffix('.'+ext),dpi=160)
svg=out.with_suffix('.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
print(out.with_suffix('.png'))
