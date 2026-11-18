"""Convert verified Sand3D USD geometry into fitted, attributed GLB assets."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
root=Path(__file__).resolve().parents[1];source=root/'assets/realism/sand3d';dest=root/'web/desk/assets';records=json.loads((source/'selected.json').read_text());manifest=[]

def load(name):
    bpy.ops.wm.read_factory_settings(use_empty=True);path=source/(name+'.usda');record=next(r for r in records if r['entry']==name);assert hashlib.sha256(path.read_bytes()).hexdigest()==record['usda_sha256'];bpy.ops.wm.usd_import(filepath=str(path));return record
def ancestry(o):
    out=[]
    while o:out.append(o.name);o=o.parent
    return out
def clone(o,matrix,name=None):
    ob=bpy.data.objects.new(name or o.name,o.data.copy());bpy.context.collection.objects.link(ob);ob.data.transform(matrix@o.matrix_world);ob.matrix_world=Matrix.Identity(4)
    for face in ob.data.polygons:face.use_smooth=len(ob.data.vertices)>64
    if len(ob.data.vertices)<=32:
        bevel=ob.modifiers.new('Manufactured edge radius','BEVEL');bevel.width=.00018;bevel.segments=3;ob.modifiers.new('Corner normals','WEIGHTED_NORMAL')
    return ob
def export(objects,filename,record,modifications,extra=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(dest/filename),export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
    manifest.append({'file':filename,'dataset':'Sandflow/sand3d-articraft','record_id':record['id'],'source_usda_path':record['usda_path'],'source_usda_sha256':record['usda_sha256'],'license':record['license'],'source_license':record['source_license'],'attribution':record['attribution'],'additional_credit':'Sand3D, Thibault Neveu and Andréa Loy, Sandflow, 2026','modifications':modifications,'sha256':hashlib.sha256((dest/filename).read_bytes()).hexdigest(),**(extra or {})})

r=load('business_laptop');original=list(bpy.context.scene.objects);lid=bpy.data.objects['lid'];inv=lid.matrix_world.inverted();lid_meshes=[o for o in original if o.type=='MESH' and ('lid' in ancestry(o) or 'shutter' in ' '.join(ancestry(o)))]
verts=[inv@o.matrix_world@v.co for o in lid_meshes for v in o.data.vertices];lo=Vector(tuple(min(v[i] for v in verts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in verts) for i in range(3)))
scale=Vector((.29/(hi.x-lo.x),-.007/(hi.y-lo.y),.175/(hi.z-lo.z)));center=(lo+hi)/2;offset=Vector((0,0,.0925));fit=Matrix.Translation(offset)@Matrix.Diagonal((*scale,1))@Matrix.Translation(-center)@inv
objects=[clone(o,fit) for o in lid_meshes];export(objects,'sand-laptop-lid.glb',r,'Lid parts fitted to 290 × 7 × 175 mm, viewing face mirrored toward -Y, hinge retargeted to MuJoCo; small edge bevels.')
base_meshes=[o for o in original if o.type=='MESH' and o not in lid_meshes and not any('key' in n for n in ancestry(o))];verts=[o.matrix_world@v.co for o in base_meshes for v in o.data.vertices];lo=Vector(tuple(min(v[i] for v in verts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in verts) for i in range(3)));center=(lo+hi)/2;fit=Matrix.Diagonal((.29/(hi.x-lo.x),.195/(hi.y-lo.y),.014/(hi.z-lo.z),1))@Matrix.Translation(-center)
export([clone(o,fit) for o in base_meshes],'sand-laptop-base.glb',r,'Base shell fitted to 290 × 195 × 14 mm. Source keypad omitted; a full keyboard is added by Mochi.')

r=load('classroom_globe_on_meridian');parts=[]
for name,size,position in [('weighted_base',(.078,.078,.012),(0,0,.006)),('upright_post',(.008,.008,.052),(0,0,.038)),('side_knob_1',(.010,.013,.013),(.009,0,.038))]:
    original=bpy.data.objects[name];verts=[original.matrix_world@v.co for v in original.data.vertices];lo=Vector(tuple(min(v[i] for v in verts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in verts) for i in range(3)));fit=Matrix.Translation(Vector(position))@Matrix.Diagonal(tuple(size[i]/(hi[i]-lo[i]) for i in range(3))+(1,))@Matrix.Translation(-(lo+hi)/2);o=clone(original,fit)
    if len(o.data.vertices)>10000:dec=o.modifiers.new('Knurl display optimization','DECIMATE');dec.ratio=.18
    parts.append(o)
export(parts,'sand-globe-base.glb',r,'Pedestal, post and knurled adjustment knob fitted below the fixed 123 mm sphere center; meridian geometry is supplied separately to keep the push path clear.')
original=bpy.data.objects['ocean_sphere'];sphere=clone(original,Matrix.Identity(4),'sandflow_earth');sphere.modifiers.clear()
for v in sphere.data.vertices:v.co=v.co.normalized()*.058
uv=sphere.data.uv_layers.new(name='Globe atlas')
for face in sphere.data.polygons:
    coords=[]
    for loop in face.loop_indices:
        v=sphere.data.vertices[sphere.data.loops[loop].vertex_index].co.normalized();coords.append((loop,(math.atan2(v.y,v.x)+math.pi)/(2*math.pi),(math.asin(max(-1,min(1,v.z)))+math.pi/2)/math.pi))
    seam=max(c[1] for c in coords)-min(c[1] for c in coords)>.5
    for loop,u,v in coords:uv.data[loop].uv=(u+1 if seam and u<.5 else u,v)
sphere.data.materials.clear();mat=bpy.data.materials.new('Printed globe paper');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.53;tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(dest/'globe-map.jpg'));mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);sphere.data.materials.append(mat)
export([sphere],'sand-earth.glb',r,'Ocean sphere projected to exactly 58 mm radius; original stylized continents replaced by the credited Natural Earth print; regenerated spherical UVs.')

r=load('desk_task_lamp');objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];verts=[o.matrix_world@v.co for o in objects for v in o.data.vertices];minimum=min(v.z for v in verts);height=max(v.z for v in verts)-minimum;scale=.42/height;fit=Matrix.Diagonal((scale,scale,scale,1))@Matrix.Translation(Vector((0,0,-minimum)))
export([clone(o,fit) for o in objects],'sand-desk-lamp.glb',r,'Uniform scale to a 420 mm human-size desk lamp; static rest pose, only a background prop.')
(dest/'sand3d-attribution.json').write_text(json.dumps(manifest,indent=2));print('SAND_EXPORTS',[(x['file'],(dest/x['file']).stat().st_size) for x in manifest])
