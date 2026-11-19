"""Shared-spec Sand3D dressing for measured MuJoCo episodes."""
import math
import bpy
from mathutils import Vector


def add_desk_props(spec, asset, box, material, empty, cylinder, lettering, root):
    bindings={}
    paper=material('Warm, handled paper',(.78,.735,.64),0,.9)
    ink=material('Graphite pencil marks',(.065,.075,.068),0,.86)
    cream=material('Glazed ivory mug',(.72,.70,.62),0,.23)
    coffee=material('Coffee surface',(.025,.012,.006),0,.22)
    graphite=material('Printer output tray',(.025,.030,.033),.12,.43)

    def stroke(parent,name,points,r=.00009,mat=ink):
        c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=r;c.bevel_resolution=1
        p=c.splines.new('POLY');p.points.add(len(points)-1)
        for v,xyz in zip(p.points,points):v.co=(*xyz,1)
        o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);o.parent=parent;o.data.materials.append(mat)

    for p in spec['props']:
        g=empty(p['name'],p['pos']);g.rotation_euler.z=p['yaw'];bindings[p['name']]=g
        sx,sy,sz=p['size'];key=p['asset']
        if key not in ['paper','sticky','tray']:
            model=asset('richdesk/'+key+'.glb',p['name']+' visual');model.parent=g;model.location=(0,0,0);model.scale=(sx,sy,sz)
            for o in model.children_recursive:
                if o.type!='MESH':continue
                for slot in o.material_slots:
                    if not slot.material:continue
                    m=slot.material.copy();slot.material=m
                    if not m.use_nodes:continue
                    bs=m.node_tree.nodes.get('Principled BSDF')
                    if key=='book':
                        color=bs.inputs['Base Color'].default_value
                        if sum(color[:3])/3<.3:
                            h=p.get('color','#455563').lstrip('#');rgb=[int(h[i:i+2],16)/255 for i in (0,2,4)]
                            bs.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1)
                            bs.inputs['Roughness'].default_value=.78
                        else:bs.inputs['Roughness'].default_value=.94
                    if key=='mug':slot.material=cream
        else:
            mat=graphite if key=='tray' else material('Ochre sticky paper',(.62,.48,.19),0,.95) if key=='sticky' else paper
            o=box(p['name']+' sheet',p['size'],(0,0,0),mat,.0001);o.parent=g;o.location=(0,0,sz/2)

        if key=='book':
            title=lettering(g,p.get('title','NOTES'),(0,-sy/2-.00015,sz*.48),min(.0024,sz*.3),paper)
            for i in range(1,7):
                stroke(g,'Individual page edges',[(-sx*.47,-sy/2+.0004,sz*(.15+i*.105)),(sx*.47,-sy/2+.0004,sz*(.15+i*.105))],.000025,ink)
        if key=='paper':
            for i in range(9):
                y=sy*.31-i*sy*.066;length=sx*(.6 if i%3 else .40)
                stroke(g,'Printed line',[(-sx*.35,y,sz+.00006),(-sx*.35+length,y,sz+.00006)],.00007)
            stroke(g,'A small plotted trace',[(-sx*.32+i*sx*.035,-sy*.35+sy*.07*math.sin(i*.65)+i*sy*.005,sz+.00008) for i in range(18)],.00012)
        if key=='notebook':
            # A loose working page on the sourced spiral pad, with a diagram and notes.
            sheet=box('Working sheet',(.16,.11,.00015),(0,0,0),paper,.0002);sheet.parent=g;sheet.location=(.004,0,sz+.0001)
            for i in range(7):stroke(g,'Pencil notes',[(-.061,.036-i*.008,sz+.0003),(.018+(.014 if i%2 else 0),.036-i*.008,sz+.0003)],.00009)
            stroke(g,'Hand-drawn linkage',[(-.038,-.034,sz+.0004),(-.014,-.018,sz+.0004),(.018,-.032,sz+.0004),(.047,-.006,sz+.0004)],.00023)
        if key=='mug':
            cylinder(g,'Coffee',.028,.0004,(0,0,sz*.81),coffee)
    # Human-scale task lamp, already sourced and attributed by the V4 scene.
    lamp=asset('sand-desk-lamp.glb','Human desk lamp');lamp.location=(-.47,.29,.015);lamp.rotation_euler.z=.3
    # These are surface marks; they carry no task outcome or collision geometry.
    ringmat=material('Old coffee ring',(.22,.12,.055),0,1)
    mug=next(p for p in spec['props'] if p['asset']=='mug')
    center=(mug['pos'][0]-.015,mug['pos'][1]-.008,.00018)
    for phase in [0.,.16]:
        points=[(center[0]+.036*math.cos(a),center[1]+.036*math.sin(a),center[2]) for a in [phase+i*math.pi/90 for i in range(145)]]
        stroke(None,'Interrupted coffee stain',points,.00027,ringmat)
    return bindings
