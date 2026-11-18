"""Cycles render of recorded G1 body poses. Native metres and Z-up throughout."""
import bpy,json,math,sys,argparse
from pathlib import Path
from mathutils import Vector,Quaternion
root=Path(__file__).resolve().parents[1];assets=root/'web/desk/assets';out=root/'artifacts/realism-v4'
p=argparse.ArgumentParser();p.add_argument('--task',default='laptop');p.add_argument('--frame',type=int,default=0);p.add_argument('--samples',type=int,default=40);p.add_argument('--width',type=int,default=1200);p.add_argument('--height',type=int,default=800);args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=args.samples;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
 prefs.compute_device_type='METAL';prefs.get_devices()
 for d in prefs.devices:d.use=d.type=='METAL'
 scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=args.width;scene.render.resolution_y=args.height;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
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

box('One human desk',(1.2,.8,.04),(0,0,-.020),wood,.003)
base=asset('sand-laptop-base.glb','Laptop base');base.location=(-.12,-.024,.007)
keys=material('Key caps',(.025,.033,.037),.1,.5)
for row in range(4):
 for col in range(12):box('Keyboard key',(.0177,.016,.0017),(-.12-.119+col*.0215,-.024+.053-row*.022,.0149),keys,.0006)
box('Space bar',(.09,.011,.0014),(-.12,-.065,.0148),keys,.0006)
screen=asset('sand-laptop-lid.glb','Laptop screen');screen.location=(-.12,.07,.014)
display=material('Recorded controller traces',(1,1,1),0,.27);tex=display.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(assets/'laptop-display.png'));bs=display.node_tree.nodes.get('Principled BSDF');display.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);display.node_tree.links.new(tex.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=.17
bpy.ops.mesh.primitive_plane_add(size=1);panel=bpy.context.object;panel.name='Display diagnostic overlay';panel.parent=screen;panel.location=(0,-.0037,.094);panel.rotation_euler.x=math.pi/2;panel.scale=(.265,.149,1);panel.data.materials.append(display)
globe=asset('sand-earth.glb','Globe');globe.location=(.2,.04,.123)
stand=asset('sand-globe-base.glb','Globe stand');stand.location=(.2,.04,0)
brass=material('Brushed brass',(.32,.24,.10),.8,.33)
def rod(name,a,b,r,mat):
 a=Vector(a);b=Vector(b);bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=(b-a).length,location=(a+b)/2);ob=bpy.context.object;ob.name=name;ob.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();ob.data.materials.append(mat);return ob
curve=bpy.data.curves.new('Meridian arc','CURVE');curve.dimensions='3D';curve.bevel_depth=.0015;curve.bevel_resolution=3;spline=curve.splines.new('POLY');spline.points.add(60)
for i,point in enumerate(spline.points):a=i/60*math.pi;point.co=(.2,.04+.064*math.sin(a),.123+.064*math.cos(a),1)
ob=bpy.data.objects.new('Fixed meridian',curve);bpy.context.collection.objects.link(ob);ob.data.materials.append(brass)
rod('Globe top spindle',(.2,.04,.18),(.2,.04,.19),.003,brass);rod('Lower spindle',(.2,.04,.057),(.2,.04,.069),.003,brass);rod('Alignment pointer',(.2,-.038,.012),(.2,-.038,.123),.0016,brass);rod('Pointer tip',(.2,-.038,.123),(.2,-.022,.123),.0013,brass)
bpy.ops.mesh.primitive_circle_add(vertices=32,radius=.0037,fill_type='NGON');marker=bpy.context.object;marker.name='Coral alignment marker';marker.parent=globe;marker.location=(0,-.0583,0);marker.rotation_euler.x=math.pi/2;marker.data.materials.append(material('Coral paint',(.52,.13,.06),0,.6))
lamp=asset('sand-desk-lamp.glb','Task lamp');lamp.location=(-.37,.25,0);lamp.rotation_euler.z=.45
old=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(assets/'g1-mini.glb'));robot={o.name:o for o in bpy.data.objects if o not in old and o.type=='EMPTY'}
r=json.loads((out/(args.task+'.json')).read_text());frame=r['trajectory']['frames'][args.frame]
for name,pos,quat in zip(r['trajectory']['body_names'],frame['positions'],frame['quaternions']):
 ob=robot.get(name) or {'laptop-screen':screen,'globe':globe}.get(name)
 if ob:ob.location=pos;ob.rotation_mode='QUATERNION';ob.rotation_quaternion=quat
# The stand makes the fixed-pelvis simplification visible.
basepos=Vector(r['scenario']['robot_position']);yaw=r['scenario']['robot_yaw'];back=Vector((-math.cos(yaw)*.027,-math.sin(yaw)*.027,0));pole=basepos+back;steel=material('Support stand',(.02,.025,.028),.7,.4);rod('Supported pelvis column',(pole.x,pole.y,.002),(pole.x,pole.y,basepos.z),.0018,steel);rod('Pelvis clamp',pole,basepos,.0018,steel)
# Both fixtures are present, but only one is dynamic in each episode.
if args.task=='globe':screen.rotation_mode='XYZ';screen.rotation_euler.x=math.radians(20)

for name,position,energy,size in [('Window',(-.35,-.20,.8),65,.65),('Soft fill',(.45,.10,.6),18,.5)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size;ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.location=position;ob.rotation_euler=(Vector((.03,.015,.1))-ob.location).to_track_quat('-Z','Y').to_euler()
mat=material('Room plaster',(.34,.37,.35),0,.95);box('Room floor',(5,5,.02),(0,0,-.76),mat);box('Wall',(3,.05,2),(0,1.1,.24),mat)
bpy.ops.object.camera_add(location=(.31,-.46,.30));camera=bpy.context.object;camera.rotation_euler=(Vector((.035,.020,.105))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=48;camera.data.clip_start=.002;scene.camera=camera;camera.data.dof.use_dof=True;camera.data.dof.focus_distance=(camera.location-Vector((.035,.02,.105))).length;camera.data.dof.aperture_fstop=9
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out/f'{args.task}-frame-{args.frame:03d}.png');bpy.ops.render.render(write_still=True);print('FRAME',scene.render.filepath)
