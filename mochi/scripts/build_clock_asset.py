"""Fit a pinned Sand3D/NVIDIA clock; do not execute dataset programs."""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
root=Path(__file__).resolve().parents[1];source=root/'assets/realism/sand3d';out=root/'web/desk/assets';record=json.loads((source/'clock-source.json').read_text());path=source/'traditional_alarm_clock.usda';assert hashlib.sha256(path.read_bytes()).hexdigest()==record['usda_sha256']
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.wm.usd_import(filepath=str(path));original=[o for o in bpy.context.scene.objects if o.type=='MESH'];s=record['fit']['uniform_scale'];fit=Matrix.Translation(Vector((.025-s*.004,-.010-s*.004,-.06)))@Matrix.Scale(s,4)
def clone(ob,matrix):
 o=bpy.data.objects.new(ob.name+' fitted',ob.data.copy());bpy.context.collection.objects.link(o);o.data.transform(matrix@ob.matrix_world);o.matrix_world=Matrix.Identity(4)
 for poly in o.data.polygons:poly.use_smooth=True
 return o
body=[clone(o,fit) for o in original if o.name not in ['hammer','hammer_stem','arch']];control=[]
for original_part in [o for o in original if o.name in ['hammer','hammer_stem']]:
 o=clone(original_part,Matrix.Translation(Vector((-.025,.010,-.064)))@fit)
 if original_part.name=='hammer':
  lo=Vector(tuple(min(v.co[i] for v in o.data.vertices) for i in range(3)));hi=Vector(tuple(max(v.co[i] for v in o.data.vertices) for i in range(3)));center=(lo+hi)/2;scale=Vector((.025/(hi.x-lo.x),.018/(hi.y-lo.y),.004/(hi.z-lo.z)))
  for v in o.data.vertices:v.co=Vector(tuple((v.co[i]-center[i])*scale[i] for i in range(3)))
 m=bpy.data.materials.get('Silencer dark steel')
 if m is None:
  m=bpy.data.materials.new('Silencer dark steel');m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.018,.022,.025,1);bs.inputs['Metallic'].default_value=.7;bs.inputs['Roughness'].default_value=.42
 o.data.materials.clear();o.data.materials.append(m)
 if original_part.name=='hammer':
  b=o.modifiers.new('Control edge bevel','BEVEL');b.width=.0007;b.segments=3;o.modifiers.new('Control normals','WEIGHTED_NORMAL')
 control.append(o)
manifest=[]
for objects,name,changes in [(body,'sand-clock-case.glb','Uniform similarity fit; native case, bells, feet and winders retained; carrying arch omitted to keep the contact approach clear. Original dial print supplied separately.'),(control,'sand-clock-stop.glb','Native hammer and stem retargeted to the existing physical slider as a benchmark alarm silencer. Control pad matches its 25 x 18 x 4 mm contact envelope; no floating housing. This adds articulation absent from the upstream rigid asset.')]:
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.export_scene.gltf(filepath=str(out/name),export_format='GLB',use_selection=True,export_apply=True)
 manifest.append({'file':name,'dataset':record['dataset'],'revision':record['revision'],'record_id':record['id'],'source_usda_path':record['usda_path'],'source_usda_sha256':record['usda_sha256'],'license':record['license'],'source_license':record['source_license'],'attribution':record['attribution'],'additional_credit':'Sand3D, Thibault Neveu and Andréa Loy, Sandflow, 2026','modifications':changes,'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()})
p=out/'sand3d-attribution.json';old=json.loads(p.read_text());p.write_text(json.dumps([r for r in old if not r['file'].startswith('sand-clock-')]+manifest,indent=2));(out/'clock-attribution.json').write_text(json.dumps(manifest,indent=2));print('CLOCK_EXPORT',[(r['file'],(out/r['file']).stat().st_size) for r in manifest])
