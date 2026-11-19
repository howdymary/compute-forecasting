"""Render a continuous measured curriculum trajectory in Blender/Cycles."""
import bpy,json,math,sys,argparse
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1];assets=root/'web/desk/assets'
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);p.add_argument('--time',type=float,default=9);p.add_argument('--animate',action='store_true');p.add_argument('--samples',type=int,default=48);p.add_argument('--camera',choices=['follow','side','feet','wide','topdown'],default='follow');p.add_argument('--route');args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(args.out);out.mkdir(parents=True,exist_ok=True);r=json.loads(Path(args.input).read_text());frames=r['trajectory']['frames'];bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=args.samples;scene.cycles.use_denoising=True
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
 for d in prefs.devices:d.use=d.type=='METAL'
 scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.fps=25
world=bpy.data.worlds.new('Studio');world.use_nodes=True;scene.world=world;nodes=world.node_tree.nodes;env=nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(assets/'studio.hdr'));world.node_tree.links.new(env.outputs['Color'],nodes['Background'].inputs['Color']);nodes['Background'].inputs['Strength'].default_value=.45
def material(name,color,metal=0,rough=.5):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;return m
wood=material('Oak veneer',(1,1,1),0,.75);n=wood.node_tree.nodes;links=wood.node_tree.links;bs=n.get('Principled BSDF')
for name,socket in [('oak-color.jpg','Base Color'),('oak-roughness.jpg','Roughness')]:
 tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(assets/name));
 if socket=='Base Color':
  hue=n.new('ShaderNodeHueSaturation');hue.inputs['Saturation'].default_value=.48;links.new(tex.outputs['Color'],hue.inputs['Color']);links.new(hue.outputs['Color'],bs.inputs[socket])
 else:links.new(tex.outputs['Color'],bs.inputs[socket])
 if 'roughness' in name:tex.image.colorspace_settings.name='Non-Color'
tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(assets/'oak-normal.jpg'));tex.image.colorspace_settings.name='Non-Color';normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.08;links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])

def box(name,size,pos,mat,bevel=.001):
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos);o=bpy.context.object;o.name=name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
 if bevel:mod=o.modifiers.new('Manufactured edge','BEVEL');mod.width=bevel;mod.segments=3;o.modifiers.new('Normals','WEIGHTED_NORMAL')
 return o

def asset(file,name):
 old=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(assets/file));new=[o for o in bpy.data.objects if o not in old];par=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(par)
 for o in new:
  if not o.parent:o.parent=par
 return par

box('One human-size desk',(1.2,.8,.04),(0,0,-.02),wood,.003)
black=material('Graphite polymer',(.023,.029,.03),.15,.35);coral=material('Button cap',(.62,.30,.13),0,.4);walnut=material('Walnut organizer',(.15,.095,.055),0,.62);metal=material('Brushed steel',(.38,.42,.42),.85,.3)
def empty(name,pos):
 o=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(o);o.location=pos;return o
def part(parent,name,size,pos,mat,bevel=.001):
 o=box(name,size,pos,mat,bevel);o.parent=parent;o.location=pos;return o
# Traditional mechanical clock; passive chassis and active cap use the same pivots.
def cylinder(parent,name,radius,depth,pos,mat,axis='z'):
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=depth);o=bpy.context.object;o.name=name;o.parent=parent;o.location=pos
 if axis=='y':o.rotation_euler.x=math.pi/2
 o.data.materials.append(mat);bevel=o.modifiers.new('Machined edge','BEVEL');bevel.width=.0004;bevel.segments=3;o.modifiers.new('Normals','WEIGHTED_NORMAL');return o
def sphere(parent,name,radius,pos,mat,scale=(1,1,1)):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,radius=radius);o=bpy.context.object;o.name=name;o.parent=parent;o.location=pos;o.scale=scale;o.data.materials.append(mat)
 for poly in o.data.polygons:poly.use_smooth=True
 return o
def rod(parent,name,start,end,radius,mat):
 delta=Vector(end)-Vector(start);o=cylinder(parent,name,radius,delta.length,(Vector(start)+Vector(end))/2,mat);o.rotation_euler=delta.to_track_quat('Z','Y').to_euler();return o
def lettering(parent,label,pos,size,mat):
 bpy.ops.object.text_add();o=bpy.context.object;o.parent=parent;o.location=pos;o.rotation_euler=(math.pi/2,0,0);o.data.body=label;o.data.size=size;o.data.align_x='CENTER';o.data.align_y='CENTER';o.data.extrude=.00002;o.data.materials.append(mat);return o
clock=asset('sand-clock-case.glb','Alarm clock');clock.location=(-.36,.11,.06);cap=asset('sand-clock-stop.glb','Alarm silencer');cap.location=(-.335,.1,.124)
brass=material('Aged brass',(.47,.36,.21),.86,.3);dial=material('Warm paper dial',(.84,.79,.67),0,.78);ink=material('Dial ink',(.028,.044,.033),.1,.5);cx=.025;cy=-.0434;cz=-.001679;rad=.0495
cylinder(clock,'Printed cream dial',rad,.0004,(cx,cy+.0002,cz),dial,'y')
for i in range(60):
 angle=i*math.pi/30;length=.003 if i%5 else .0055;o=part(clock,'Dial index',(.00023 if i%5 else .0005,.00022,length),(cx+.0445*math.sin(angle),cy-.0002,cz+.0445*math.cos(angle)),ink,.00003);o.rotation_euler.y=angle
for i in range(1,13):
 angle=i*math.pi/6;lettering(clock,str(i),(cx+.033*math.sin(angle),cy-.0004,cz+.033*math.cos(angle)),.0113,ink)
lettering(clock,'M O C H I',(cx,cy-.0004,cz-.015),.0028,ink);lettering(clock,'MECHANICAL ALARM',(cx,cy-.0004,cz-.0195),.00205,ink)
rod(clock,'Hour hand',(cx,cy-.0007,cz),(cx-.015,cy-.0007,cz-.026),.0014,ink);rod(clock,'Minute hand',(cx,cy-.0013,cz),(cx,cy-.0013,cz+.039),.00095,ink);rod(clock,'Second hand',(cx-.006,cy-.0019,cz+.003),(cx+.032,cy-.0019,cz-.018),.00028,coral);cylinder(clock,'Hand pin',.0026,.0012,(cx,cy-.0025,cz),brass,'y')
cabinet=empty('Drawer cabinet',(-.1,.15,0))
for x in [-.052,.052]:part(cabinet,'Side',(.004,.09,.145),(x,0,.0725),walnut)
for size,pos in [((.108,.09,.004),(0,0,.147)),((.108,.004,.145),(0,.046,.0725)),((.108,.09,.004),(0,0,.002))]:part(cabinet,'Cabinet panel',size,pos,walnut)
drawer=empty('Drawer',(-.1,.075,.12));part(drawer,'Drawer front',(.095,.005,.043),(0,0,0),walnut);part(drawer,'Drawer tray',(.091,.065,.002),(0,.033,-.021),walnut);part(drawer,'Pull',(.03,.003,.003),(0,-.005,.003),metal)
base=asset('sand-laptop-base.glb','Laptop base');base.location=(.14,.17,.007);base.scale=(.25/.29,.17/.195,1)
for row in range(4):
 for col in range(12):part(base,'Keyboard key',(.015,.012,.0015),(-.104+col*.0188,.044-row*.017,.0077),black,.0005)
lid=empty('Laptop screen',(.14,.249,.0185));shell=asset('sand-laptop-lid.glb','Lid visual shell');shell.parent=lid;shell.location=(0,0,-.004286);shell.scale=(.25/.29,1,.15/.175)
screen_glass=material('Laptop dark display',(.005,.012,.018),.15,.23)
part(lid,'Display surface',(.227,.0004,.126),(0,-.0042,.077),screen_glass,.0004)
globe=asset('sand-earth.glb','Globe');stand=asset('sand-globe-base.glb','Globe base');stand.location=(.47,.22,0)
bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.0035);marker=bpy.context.object;marker.parent=globe;marker.location=(-.0583,0,0);marker.data.materials.append(coral)
part(stand,'Fixed zero index',(.015,.001,.0003),(-.027,0,.0128),coral,.00005);rod(stand,'Index arrow left',(-.035,0,.0128),(-.030,-.002,.0128),.00035,coral);rod(stand,'Index arrow right',(-.035,0,.0128),(-.030,.002,.0128),.00035,coral)
old=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(assets/'g1-mini.glb'));robot={o.name:o for o in bpy.data.objects if o not in old and o.type=='EMPTY'};bindings={**robot,'alarm-clock':clock,'alarm-button':cap,'drawer-cabinet':cabinet,'drawer':drawer,'laptop-base':base,'laptop-screen':lid,'globe':globe,'globe-base':stand}
part(robot['torso_link'],'Display-only face panel',(.002,.020,.019),(.012,0,.063),material('Black visor glass',(.004,.009,.012),.2,.15),.0015)
if r.get('scene',{}).get('version')=='richdesk-v9':
 sys.path.insert(0,str(root/'scripts'))
 from richdesk_blender import add_desk_props
 bindings.update(add_desk_props(r['scene'],asset,box,material,empty,cylinder,lettering,root))
for name,pos,energy,size in [('Window',(-.4,-.3,1),75,.7),('Fill',(.5,.3,.7),20,.6)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,.1,.1))-o.location).to_track_quat('-Z','Y').to_euler()
room=material('Room plaster',(.32,.35,.33),0,.95);box('Room floor',(5,5,.02),(0,0,-.76),room);box('Wall',(3,.05,2),(0,1.1,.24),room)
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.lens=45;camera.data.clip_start=.002;scene.camera=camera
bpy.context.preferences.edit.keyframe_new_interpolation_type='LINEAR'
if args.route:
 route=json.loads(Path(args.route).read_text());planned=material('Reference teal',(.035,.32,.33),0,.7);executed=material('Measured rust',(.65,.17,.075),0,.7)
 def overlay_line(name,points,mat):
  curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.bevel_depth=.0008;curve.bevel_resolution=2;spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
  for p,xy in zip(spline.points,points):p.co=(xy[0],xy[1],xy[2] if len(xy)>2 else .0017,1)
  obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj);obj.data.materials.append(mat)
 if 'candidates' in route:
  def height(x,y):return max([0.]+[p['pos'][2]+p['size'][2] for p in route['scene']['props'] if p.get('climb') and abs(x-p['pos'][0])<=p['size'][0]/2 and abs(y-p['pos'][1])<=p['size'][1]/2])
  candidate=next(c for c in route['candidates'] if c['id']==route['selected_candidate']);points=[]
  for a,b in zip(candidate['points'],candidate['points'][1:]):
   count=max(2,math.ceil(math.dist(a[:2],b[:2])/.004))
   for i in range(count+1):
    u=i/count;x=(1-u)*a[0]+u*b[0];y=(1-u)*a[1]+u*b[1];points.append([x,y,height(x,y)+.0025])
  overlay_line('Planned elevated route; not robot motion',points,planned)
  for foot in route['footsteps']['ascent']:
   x,y,z=foot['position'];overlay_line('Proposed foot landing; not an executed contact',[[x+dx,y+dy,z+.0027] for dx,dy in [(-.007,-.018),(.007,-.018),(.007,.018),(-.007,.018),(-.007,-.018)]],planned)
 else:
  for leg in route['legs']:
   for s in leg['segments']:overlay_line('Planned reference (annotation)',[s['from'],s['to']],planned)
   x,y,h=leg['goal'];overlay_line('Task-facing direction (annotation)',[[x,y],[x+.027*math.cos(h),y+.027*math.sin(h)]],planned)
   circle=[[x+.011*math.cos(a),y+.011*math.sin(a)] for a in [i*2*math.pi/48 for i in range(49)]];overlay_line('Stopping zone (annotation)',circle,planned)
 points=[f['positions'][1] for f in frames if f['phase']=='walk' and f['t']<=args.time]
 if len(points)>1:overlay_line('Recorded pelvis path (annotation)',points,executed)
selected=frames if args.animate else [min(frames,key=lambda f:abs(f['t']-args.time))]
for f in selected:
 frame=round(f['t']*25)+1
 for name,pos,q in zip(r['trajectory']['body_names'],f['positions'],f['quaternions']):
  o=bindings.get(name)
  if o:
   o.location=pos;o.rotation_mode='QUATERNION';o.rotation_quaternion=q
   if args.animate:o.keyframe_insert('location',frame=frame);o.keyframe_insert('rotation_quaternion',frame=frame)
 q=f['quaternions'][1];yaw=math.atan2(2*(q[0]*q[3]+q[1]*q[2]),1-2*(q[2]**2+q[3]**2));pos=f['positions'][1];target=Vector((pos[0]+.015,pos[1]+.025,.112));camera.location=target+Vector((.28,-.39,.24));
 if f.get('task')=='alarm':
  target=Vector(((pos[0]-.36)/2,(pos[1]+.11)/2,.107));camera.location=target+Vector((.24,-.38,.23))
 if f.get('task')=='drawer':target=Vector(((pos[0]-.10)/2,(pos[1]+.12)/2,.105));camera.location=target+Vector((.24,-.38,.23))
 if f.get('task')=='laptop':target=Vector(((pos[0]+.23)/2,(pos[1]+.20)/2,.105));camera.location=target+Vector((.26,-.32,.27))
 if f.get('task')=='globe':target=Vector(((pos[0]+.47)/2,(pos[1]+.22)/2,.115));camera.location=target+Vector((-.31,-.39,.28))
 if args.camera in ['side','feet']:
  target=Vector((pos[0],pos[1],.032 if args.camera=='feet' else .112));camera.location=target+Vector((.10,-.27,.055) if args.camera=='feet' else (0,-.52,.035))
 elif args.camera=='wide':target=Vector((0,.1,.08));camera.location=Vector((1.05,-1.35,.95))
 elif args.camera=='topdown':target=Vector((0,0,0));camera.location=Vector((0,-.0001,1.75));camera.data.type='ORTHO';camera.data.ortho_scale=1.35
 camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
 if args.animate:camera.keyframe_insert('location',frame=frame);camera.keyframe_insert('rotation_euler',frame=frame)
scene.frame_end=round(r['duration']*25)+1;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out/'measured-trajectory.png');bpy.ops.wm.save_as_mainfile(filepath=str(out/'measured-trajectory.blend'))
if not args.animate:bpy.ops.render.render(write_still=True)
print('MOCHI_CYCLES',json.dumps({'source':args.input,'source_time':selected[0]['t'] if not args.animate else None,'animation_frames':len(selected),'path':str(out)}))
