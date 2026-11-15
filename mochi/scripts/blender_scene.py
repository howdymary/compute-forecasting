"""Run with Blender --background --python this_file -- --trajectory FILE --out DIR."""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--trajectory',required=True);p.add_argument('--out',required=True);p.add_argument('--still',action='store_true');p.add_argument('--stride',type=int,default=3);p.add_argument('--width',type=int,default=960);args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
r=json.loads(Path(args.trajectory).read_text());out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mat(name,color,metal=0,rough=.4,emission=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=(*color,1);s.inputs['Metallic'].default_value=metal;s.inputs['Roughness'].default_value=rough
    if emission:s.inputs['Emission Color'].default_value=(*color,1);s.inputs['Emission Strength'].default_value=emission
    return m
ivory=mat('Porcelain / warm ivory',(.87,.85,.75),.12,.28);coral=mat('Apricot enamel',(.85,.29,.16),.15,.3);dark=mat('Graphite',(.025,.045,.043),.3,.3);mint=mat('Mint phosphor',(.40,.90,.64),0,.3,2);gold=mat('Honey puck',(.95,.55,.12),.2,.26);wood=mat('Ash table',(.56,.38,.23),0,.55);floor=mat('Warm paper',(.80,.78,.70),0,.8);white=mat('Lettering',(.99,.95,.8))
def finish(obj,name,material,parent=None):
    obj.name=name;obj.data.materials.append(material)
    if parent:obj.parent=parent
    if obj.type=='MESH':
        for poly in obj.data.polygons:poly.use_smooth=True
    return obj
def box(name,loc,scale,material,parent=None,bevel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.location=loc;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:b=o.modifiers.new('Soft manufactured edges','BEVEL');b.width=bevel;b.segments=5;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return finish(o,name,material,parent)
def sphere(name,loc,scale,material,parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12);o=bpy.context.object;o.location=loc;o.scale=scale;return finish(o,name,material,parent)
def capsule(name,a,b,rad,material,parent):
    a=Vector(a);b=Vector(b);v=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=rad,depth=v.length);o=bpy.context.object;o.location=(a+b)/2;o.rotation_mode='QUATERNION';o.rotation_quaternion=v.to_track_quat('Z','Y');finish(o,name,material,parent)
    sphere(name+' end A',a,(rad,)*3,material,parent);sphere(name+' end B',b,(rad,)*3,material,parent)
def label(text,loc,size,material,parent=None,rotation=(math.pi/2,0,0)):
    bpy.ops.object.text_add();o=bpy.context.object;o.data.body=text;o.data.align_x='CENTER';o.data.size=size;o.data.extrude=.0005;o.location=loc;o.rotation_euler=rotation;finish(o,text,material,parent);return o
bodies={}
for name in r['trajectory']['body_names']:
    o=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(o);o.rotation_mode='QUATERNION';bodies[name]=o
box('Laboratory plinth',(0,.07,-.028),(1.25,1.1,.06),floor,bevel=.05)
box('Tabletop',(0,0,.435),(.72,.58,.05),wood,bevel=.012)
for x in [-.29,.29]:
    for y in [-.22,.22]:box('Table leg',(x,y,.21),(.034,.034,.42),wood,bevel=.008)
sphere('Torso',(0,0,0),(.12,.075,.15),ivory,bodies['torso'])
box('Chest badge',(0,-.071,.02),(.09,.012,.052),coral,bodies['torso'],.012);label('M',(0,-.079,.001),.038,white,bodies['torso'])
box('Head shell',(0,0,0),(.29,.18,.23),ivory,bodies['head'],.055)
box('Face glass',(0,-.091,.002),(.238,.015,.151),dark,bodies['head'],.035)
for x in [-.052,.052]:box('Mochi eye',(x,-.102,.014),(.028,.008,.042),mint,bodies['head'],.01)
label('⌣',(0,-.104,-.043),.033,mint,bodies['head'])
for x in [-.157,.157]:sphere('Ear',(x,0,0),(.018,.04,.05),coral,bodies['head'])
capsule('Left upper',(0,0,0),(-.045,-.035,-.16),.035,ivory,bodies['left-upper'])
capsule('Left fore',(0,0,0),(.02,-.11,-.04),.03,ivory,bodies['left-fore']);sphere('Left mitten',(.02,-.11,-.04),(.033,.03,.028),coral,bodies['left-fore'])
sphere('Shoulder joint',(0,0,0),(.04,)*3,coral,bodies['right-yaw'])
capsule('Right upper',(0,0,0),(0,-.22,0),.029,ivory,bodies['right-upper'])
capsule('Right fore',(0,0,0),(0,-.20,0),.024,ivory,bodies['right-fore']);sphere('Elbow bearing',(0,0,0),(.032,)*3,coral,bodies['right-fore'])
sphere('Contact mitten',(0,0,0),(.018,)*3,coral,bodies['hand'])
for side in ['left','right']:
    capsule('Leg',(0,0,-.12),(0,0,.18),.04,ivory,bodies[side+'-leg'])
    box('Broad foot',(0,0,0),(.11,.17,.07),coral,bodies[side+'-foot'],.025)
bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.025,depth=.024);o=bpy.context.object;finish(o,'Physics puck',gold,bodies['puck']);b=o.modifiers.new('Puck rim','BEVEL');b.width=.002;b.segments=3
# Star stamp stays inside the physical puck surface.
vertices=[((.014 if i%2==0 else .006)*math.sin(i*math.pi/5),(.014 if i%2==0 else .006)*math.cos(i*math.pi/5),.0123) for i in range(10)]
mesh=bpy.data.meshes.new('Star stamp');mesh.from_pydata(vertices,[],[list(range(10))]);o=bpy.data.objects.new('Star stamp',mesh);bpy.context.collection.objects.link(o);finish(o,'Star stamp',white,bodies['puck'])
tx,ty,tz=r['scenario']['target'];bpy.ops.mesh.primitive_torus_add(major_radius=.028,minor_radius=.0025,location=(tx,ty,.463));finish(bpy.context.object,'Target ring',mint)
label('MOCHI',(0,.58,.002),.06,dark,rotation=(0,0,0));label('ROBOT RESEARCH LAB',(0,.51,.002),.013,dark,rotation=(0,0,0))
for x in [-.28,.28]:
    for y in [-.20,.20]:sphere('Table screw',(x,y,.461),(.004,.004,.001),dark)
frames=r['trajectory']['frames'][::args.stride]
for frame,f in enumerate(frames,1):
    for i,name in enumerate(r['trajectory']['body_names']):
        o=bodies[name];o.location=f['positions'][i];o.rotation_quaternion=f['quaternions'][i];o.keyframe_insert('location',frame=frame);o.keyframe_insert('rotation_quaternion',frame=frame)
scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=len(frames);scene.render.fps=25;scene.render.fps_base=args.stride
bpy.ops.object.camera_add(location=(.92,-1.2,1.03));camera=bpy.context.object;camera.rotation_euler=(Vector((0,.10,.47))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=1.48;scene.camera=camera
for loc,power,size in [((-.7,-.6,1.8),110,1.4),((.9,.3,1.6),85,1.0),((-.3,1.1,1.3),95,.8)]:
    bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=power;l.data.shape='DISK';l.data.size=size;l.rotation_euler=(Vector((0,.1,.4))-l.location).to_track_quat('-Z','Y').to_euler()
box('Ground',(0,0,-.075),(200,200,.025),floor,bevel=0)
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.70,.72,.66,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=args.width;scene.render.resolution_y=int(args.width*.8);scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
scene.frame_set(min(25,len(frames)));bpy.ops.wm.save_as_mainfile(filepath=str(out/'mochi.blend'))
if args.still:
    scene.render.filepath=str(out/'hero.png');bpy.ops.render.render(write_still=True)
else:
    scene.render.filepath=str(out/'frames'/'frame_');(out/'frames').mkdir(exist_ok=True);bpy.ops.render.render(animation=True)
