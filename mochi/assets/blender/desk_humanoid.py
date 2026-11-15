"""Original industrial desk-humanoid concept. Static design rig; not a policy rollout.
blender -b -t 4 --python mochi/assets/blender/desk_humanoid.py -- --out mochi/artifacts/design-v2
"""
import bpy,math,json,argparse,sys
from pathlib import Path
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--view',choices=['desk','character'],default='desk');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def material(name,c,metal=0,rough=.38,emit=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=(*c,1);s.inputs['Roughness'].default_value=rough;s.inputs['Metallic'].default_value=metal
 if emit:s.inputs['Emission Color'].default_value=(*c,1);s.inputs['Emission Strength'].default_value=emit
 return m
shell=material('Warm white engineering polymer',(.76,.79,.77),.20,.3);graphite=material('Graphite structural frame',(.035,.045,.048),.45,.32);rubber=material('Rubber contact pads',(.025,.031,.032),0,.8);metal=material('Brushed actuator alloy',(.30,.34,.35),.85,.27);orange=material('Safety orange trim',(.90,.29,.075),.12,.36);glass=material('Optical visor',(.012,.027,.035),.65,.2);light=material('Status light',(.68,.87,.82),0,.3,1.5);wood=material('Desk oak',(.39,.25,.13),0,.5);paper=material('Ivory paper',(.88,.86,.78),0,.8);screen=material('Laptop screen',(.025,.045,.047),.2,.35,.25);coffee=material('Coffee',(.04,.015,.008),0,.18);blue=material('Blue glass marble',(.045,.24,.38),.45,.16);pinmat=material('Pencil caps',(.84,.81,.68),.1,.4);wall=material('Warm studio wall',(.30,.34,.31),0,.9)
def finish(o,name,mat,parent=None):
 o.name=name;o.data.materials.append(mat)
 if parent:o.parent=parent
 if o.type=='MESH':
  for f in o.data.polygons:f.use_smooth=True
 return o
def box(name,pos,size,mat,parent=None,r=.002):
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.location=pos;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if r:mod=o.modifiers.new('Edge radii','BEVEL');mod.width=r;mod.segments=4;o.modifiers.new('Panel normals','WEIGHTED_NORMAL')
 return finish(o,name,mat,parent)
def sphere(name,pos,size,mat,parent=None):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12);o=bpy.context.object;o.location=pos;o.scale=size;return finish(o,name,mat,parent)
def cylinder(name,pos,rad,depth,mat,parent=None,axis='Z',vertices=32):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=rad,depth=depth);o=bpy.context.object;o.location=pos
 if axis=='X':o.rotation_euler[1]=math.pi/2
 if axis=='Y':o.rotation_euler[0]=math.pi/2
 finish(o,name,mat,parent);b=o.modifiers.new('Machined rim','BEVEL');b.width=min(.0007,rad*.15);b.segments=3;o.modifiers.new('Normals','WEIGHTED_NORMAL');return o
def link(name,start,end,rad,mat,parent):
 start=Vector(start);end=Vector(end);v=end-start;o=cylinder(name,(start+end)/2,rad,v.length,mat,parent);o.rotation_mode='QUATERNION';o.rotation_quaternion=v.to_track_quat('Z','Y');return o
def curve(name,points,r,mat,parent=None):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=16;c.bevel_depth=r;c.bevel_resolution=3;s=c.splines.new('BEZIER');s.bezier_points.add(len(points)-1)
 for b,co in zip(s.bezier_points,points):b.co=co;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
 o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);return finish(o,name,mat,parent)
def text(value,pos,size,mat,parent=None,rot=(math.pi/2,0,0),align='CENTER'):
 bpy.ops.object.text_add();o=bpy.context.object;o.location=pos;o.rotation_euler=rot;o.data.body=value;o.data.size=size;o.data.align_x=align;o.data.extrude=.00003;return finish(o,value,mat,parent)
joints=[]
def joint(name,parent,pos,rot=(0,0,0),axis=None):
 o=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(o);o.parent=parent;o.location=pos;o.rotation_euler=rot
 if axis:joints.append({'name':name,'axis':axis,'status':'visual design pivot; not an actuated MuJoCo joint'})
 return o
root=joint('Mochi_22cm',None,(-.135,-.035,0));pelvis=joint('pelvis',root,(0,0,.105));box('Pelvis housing',(0,0,0),(.043,.032,.022),graphite,pelvis,.004)
waist=joint('waist_pitch',pelvis,(0,0,.018),(.08,0,0),'X');cylinder('Waist yaw bearing',(0,0,0),.015,.014,metal,waist)
torso=joint('torso',waist,(0,0,.025));box('Torso frame',(0,0,0),(.050,.031,.056),graphite,torso,.006)
for sign in [-1,1]:
 plate=box('Split chest shell',(sign*.013,-.018,.007),(.024,.009,.040),shell,torso,.004);plate.rotation_euler[1]=sign*.06
 for z in [-.006,.024]:cylinder('Chest fastener',(sign*.020,-.023,z),.0012,.0008,metal,torso,'Y',12)
box('Orange identification stripe',(-.018,-.023,.012),(.003,.001,.020),orange,torso,.0006)
text('MOCHI',(0,-.024,-.006),.0045,graphite,torso);text('05',(0,-.024,-.014),.003,metal,torso)
for z in [-.029,-.035]:box('Abdomen segment',(0,-.007,z),(.030,.024,.004),shell,torso,.0015)
for x in [-.018,-.012,-.006,0,.006,.012,.018]:box('Back heat sink',(x,.017,.003),(.002,.004,.030),metal,torso,.0007)
neck=joint('neck_yaw',torso,(0,0,.037),(0,0,.28),'Z');cylinder('Neck actuator',(0,0,0),.008,.012,metal,neck)
head=joint('head_pitch',neck,(0,0,.020),(.12,0,0),'X');box('Compact helmet',(0,0,0),(.039,.033,.035),shell,head,.007)
box('Optical visor',(0,-.017,.001),(.034,.006,.019),glass,head,.004);box('Brow sensor strip',(0,-.020,.004),(.020,.0015,.0015),light,head,.0005)
for x in [-.010,.010]:cylinder('Optical aperture',(x,-.0208,-.003),.0022,.001,graphite,head,'Y');cylinder('Lens',(x,-.0214,-.003),.0011,.0005,metal,head,'Y')
for sign in [-1,1]:cylinder('Helmet side hinge',(sign*.020,0,-.002),.005,.002,graphite,head,'X');cylinder('Helmet screw',(sign*.0213,0,-.002),.0013,.0006,metal,head,'X',8)
box('Helmet crown seam',(0,.001,.0178),(.001,.022,.0006),graphite,head,.0002)
def bearing(parent,name,r=.009):
 cylinder(name+' motor',(0,0,0),r,.013,graphite,parent,'X')
 for sign in [-1,1]:
  cylinder(name+' cap',(sign*.007,0,0),r*.8,.0015,metal,parent,'X')
  cylinder(name+' axis bolt',(sign*.008,0,0),r*.22,.001,shell,parent,'X',8)
def hand(parent,side):
 palm=joint(side+'_wrist',parent,(0,0,-.043),(0,0,0),'Z');box(side+' palm',(0,0,-.004),(.016,.012,.015),graphite,palm,.002);box(side+' hand back',(0,.006,-.004),(.014,.003,.012),shell,palm,.002)
 for i,x in enumerate([-.004,.004]):
  digit=joint(f'{side}_finger_{i}',palm,(x,-.002,-.011),(.16 if side=='right' else .05,0,0),'X');box('Proximal finger',(0,0,-.005),(.0035,.004,.010),metal,digit,.001)
  tip=joint(f'{side}_finger_tip_{i}',digit,(0,0,-.010),(.25,0,0),'X');box('Grip pad',(0,0,-.0035),(.0035,.004,.007),rubber,tip,.001)
 thumb=joint(side+'_thumb',palm,(.009,-.002,-.003),(0,-.6,0),'Y');box('Opposing thumb',(0,0,-.005),(.004,.005,.012),metal,thumb,.001)
 return palm
for side,sign in [('left',-1),('right',1)]:
 shoulder=joint(side+'_shoulder_yaw',torso,(sign*.034,0,.012),(0,0,0),'Z');bearing(shoulder,side+' shoulder',.010)
 pitch=joint(side+'_shoulder_pitch',shoulder,(0,0,0),(.12 if side=='left' else .06,-.35 if side=='right' else .15,0),'Y')
 roll=joint(side+'_shoulder_roll',pitch,(0,0,0),(0,sign*.05,0),'X')
 link('Upper arm structural link',(0,0,-.007),(0,0,-.037),.006,graphite,roll);box('Upper arm armor',(0,-.002,-.022),(.016,.015,.029),shell,roll,.004)
 elbow=joint(side+'_elbow',roll,(0,0,-.040),(.20 if side=='left' else 0,-.35 if side=='right' else 0,0),'Y');bearing(elbow,side+' elbow',.0075)
 link('Forearm structure',(0,0,-.006),(0,0,-.040),.0055,graphite,elbow);box('Forearm shell',(0,-.001,-.022),(.014,.014,.030),shell,elbow,.003)
 for z in [-.012,-.030]:box('Forearm panel seam',(0,-.008,z),(.009,.0007,.001),graphite,elbow,.0002)
 palm=hand(elbow,side)
 if side=='right':
  sphere('Bowling marble held in gripper',(0,-.004,-.024),(.008,)*3,blue,palm)
 for i,x in enumerate([sign*.016]):
  hip=joint(side+'_hip_yaw',pelvis,(x,0,-.003),(0,0,0),'Z');bearing(hip,side+' hip',.008)
  hroll=joint(side+'_hip_roll',hip,(0,0,0),(0,sign*.08,0),'X');hpitch=joint(side+'_hip_pitch',hroll,(0,0,0),(-.1,0,0),'Y')
  link('Thigh core',(0,0,-.006),(0,0,-.039),.006,graphite,hpitch);box('Thigh shell',(0,-.002,-.022),(.018,.018,.029),shell,hpitch,.003)
  knee=joint(side+'_knee',hpitch,(0,0,-.041),(.15,0,0),'X');bearing(knee,side+' knee',.007)
  link('Shin core',(0,0,-.005),(0,0,-.039),.0055,graphite,knee);box('Shin shell',(0,-.003,-.023),(.016,.016,.031),shell,knee,.003)
  for z in [-.015,-.026]:cylinder('Shin screw',(0,-.012,z),.001,.001,metal,knee,'Y',8)
  ankle=joint(side+'_ankle_pitch',knee,(0,0,-.041),(-.05,0,0),'X');bearing(ankle,side+' ankle',.005)
  foot=joint(side+'_ankle_roll',ankle,(0,0,0),(0,-sign*.08,0),'Y');box('Rubber sole',(0,-.007,-.015),(.024,.039,.005),rubber,foot,.003);box('Foot upper',(0,-.006,-.010),(.024,.037,.009),shell,foot,.004);box('Toe plate',(0,-.019,-.0055),(.020,.011,.0025),metal,foot,.001)
# Full-size desk objects are the scale reference, not miniatures.
box('Full size oak desktop',(0,.05,-.022),(1.3,.75,.044),wood,None,.007)
# Subtle physical wood seams.
grain=material('Oak grain',(.24,.14,.065),0,.8)
for i in range(22):curve('Wood grain',[(-.65,-.27+i*.028,-.0001),(-.1,-.266+i*.028,.0001),(.65,-.272+i*.028,-.0001)],.00023,grain)
laptop=joint('Full size 13 inch laptop',None,(-.32,.18,.010),(0,0,.06));box('Laptop base',(0,0,0),(.30,.20,.014),metal,laptop,.005)
for row in range(4):
 for col in range(12):box('Key',(-.125+col*.022,.012+row*.022,.009),(.019,.018,.0025),graphite,laptop,.0015)
box('Trackpad',(0,-.060,.008),(.083,.040,.0015),graphite,laptop,.003)
hinge=joint('Screen hinge',laptop,(0,.095,.01),(-.16,0,0));box('Laptop display',(0,0,.10),(.30,.009,.20),graphite,hinge,.006);box('Display pixels',(0,-.005,.105),(.278,.001,.172),screen,hinge,.002)
text('MOCHI / CONTROL STUDIO',(0,-.006,.166),.009,light,hinge);text('DESK HUMANOID — DESIGN STUDY',(0,-.006,.148),.005,light,hinge);text('SCALE  0.22m   |   ARTICULATED RIG',(0,-.006,.035),.0045,light,hinge)
# Wireframe-looking robot schematic on laptop.
for x,y,z,w,h in [(0,0,.115,.025,.024),(0,0,.082,.035,.033),(-.025,0,.082,.007,.040),(.025,0,.082,.007,.040),(-.012,0,.048,.008,.028),(.012,0,.048,.008,.028)]:box('Blueprint geometry',(x,-.0068,z),(w,.0008,h),metal,hinge,.001)
# Coffee cup, 95mm tall, with an actual rim and handle.
mug=joint('Full size coffee mug',None,(.29,.14,0));cylinder('Mug body',(0,0,.047),.038,.092,shell,mug);cylinder('Coffee surface',(0,0,.094),.033,.0008,coffee,mug)
bpy.ops.mesh.primitive_torus_add(major_radius=.0355,minor_radius=.0028,location=(0,0,.094));finish(bpy.context.object,'Mug rim',shell,mug)
bpy.ops.mesh.primitive_torus_add(major_radius=.022,minor_radius=.0045,location=(.047,0,.052),rotation=(math.pi/2,0,0));finish(bpy.context.object,'Mug handle',shell,mug)
text('HUMAN',(0,-.0385,.047),.008,graphite,mug);text('FUEL',(0,-.0386,.035),.006,graphite,mug)
# Pencil-cap skittles, three across a tiny taped lane.
for i,(x,y) in enumerate([(.20,-.075),(.235,-.054),(.235,-.096)],1):
 pin=joint('Pin '+str(i),None,(x,y,0));cylinder('Pencil cap',(0,0,.019),.007,.038,pinmat,pin);cylinder('Pin orange band',(0,0,.028),.0072,.004,orange,pin);sphere('Pin rounded top',(0,0,.038),(.007,.007,.004),pinmat,pin)
 for j in range(6):ang=j*math.pi/3;box('Cap groove',(.0069*math.sin(ang),.0069*math.cos(ang),.011),(.0005,.0005,.014),graphite,pin,.0001)
tape=material('Paper masking tape',(.73,.75,.64),0,.8)
for y in [-.124,-.024]:box('Bowling lane tape',(.112,y,.0006),(.31,.005,.001),tape,None,.0003)
for x in [.005,.07,.135]:text('›',(x,-.073,.001),.012,graphite,rot=(0,0,-math.pi/2))
note=joint('Scorecard',None,(.18,-.235,.001),(0,0,.12));box('Scorecard paper',(0,0,0),(.17,.10,.001),paper,note,.001)
text('LUNCH BREAK LEAGUE',(0,.021,.0008),.007,graphite,note,(0,0,0));text('MOCHI    /    LANE 01',(0,.007,.0008),.005,graphite,note,(0,0,0));text('PINS  03    ·    COFFEE SPILLS  00',(0,-.012,.0008),.0038,graphite,note,(0,0,0))
pen=joint('Full size pencil',None,(-.26,-.22,.006),(0,math.pi/2,.2));cylinder('Pencil shaft',(0,0,0),.0035,.175,orange,pen,vertices=6);cylinder('Pencil eraser',(0,0,-.094),.0036,.012,pinmat,pen,vertices=12)
mouse=joint('Full size mouse',None,(.43,-.12,.013));sphere('Mouse',(0,0,0),(.03,.052,.017),graphite,mouse);box('Mouse center seam',(0,-.015,.017),(.001,.05,.001),metal,mouse,.0002)
curve('Mouse cable',[(.43,-.06,.008),(.42,.00,.004),(.44,.08,.004),(.40,.23,.004),(.14,.28,.004),(-.19,.24,.004)],.0017,rubber)
# A workshop context, kept out of focus.
box('Backdrop',(0,.7,.3),(3,.035,1.5),wall,None,.005)
for i in range(4):box('Workshop book',(-.43+i*.028,.40,.075),(.023,.13,.15),[graphite,metal,pinmat,shell][i],None,.002)
pot=joint('Desk plant',None,(.46,.34,0));cylinder('Plant pot',(0,0,.035),.035,.07,graphite,pot)
leaf=material('Plant green',(.11,.21,.14),0,.5)
for i in range(7):ang=i*2.4;end=(.04*math.cos(ang),.04*math.sin(ang),.13+i*.003);curve('Plant stem',[(0,0,.05),(.01*math.cos(ang),.01*math.sin(ang),.10),end],.0012,leaf,pot);o=sphere('Plant leaf',end,(.012,.026,.003),leaf,pot);o.rotation_euler=(.3,.4,ang)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.6,.65,.7,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.25
target=Vector((-.01,.015,.095))
bpy.ops.object.camera_add(location=(.46,-.68,.39));cam=bpy.context.object;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=48;scene.camera=cam
if a.view=='character':cam.location=(.12,-.40,.235);target=Vector((-.135,-.035,.12));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=60
cam.data.dof.use_dof=True;cam.data.dof.focus_distance=(target-cam.location).length;cam.data.dof.aperture_fstop=9
for loc,power,size in [((-.4,-.4,.8),35,.6),((.4,.3,.7),25,.5),((-.5,.5,.6),18,.4)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.size=size;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'desk-humanoid.blend'));scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out/(a.view+'.png'));bpy.ops.render.render(write_still=True)
(out/'design.json').write_text(json.dumps({'name':'Mochi desk humanoid','nominal_height_m':.22,'render_status':'Design concept only; static Blender pose, no task execution or new policy result','joint_pivots':joints,'pivot_count':len(joints),'task_proposal':'Desktop bowling with marble and pencil-cap pins; coffee exclusion zone','assets':'Original procedural geometry; no external robot meshes'},indent=2))
