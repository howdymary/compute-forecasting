"""Blender: convert licensed G1 visual meshes into body-bound GLB geometry."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Quaternion
root=Path(__file__).resolve().parents[1];bundle=json.loads((root/'artifacts/realism-v4/g1-geometry.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True);bodies={};mats={}
for row in bundle['meshes']:
    name=row['body']
    if name not in bodies:
        body=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(body);body['mujoco_body']=name;bodies[name]=body
    if row['type']=='mesh':
        mesh=bpy.data.meshes.new(row['name']);mesh.from_pydata(row['vertices'],[],row['faces']);mesh.update();ob=bpy.data.objects.new(row['name'],mesh);bpy.context.collection.objects.link(ob)
        for face in mesh.polygons:face.use_smooth=True
        if hasattr(mesh,'set_sharp_from_angle'):mesh.set_sharp_from_angle(angle=.52)
        # Display LOD only. Authoritative collision meshes are unchanged.
        if len(mesh.polygons)>6000:
            dec=ob.modifiers.new('Display mesh LOD','DECIMATE');dec.ratio=.55
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=row['radius']);ob=bpy.context.object;ob.name=row['name']
        for face in ob.data.polygons:face.use_smooth=True
    ob.parent=bodies[name];ob.location=row['position'];ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Quaternion(row['quaternion'])
    rgba=tuple(round(v,3) for v in row['rgba']);dark=sum(rgba[:3])<.9
    if rgba not in mats:
        mat=bpy.data.materials.new('G1 '+('graphite' if dark else 'satin shell')+' '+str(len(mats)));mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.014,.018,.021,1) if dark else (.44,.46,.47,1);bs.inputs['Metallic'].default_value=.12 if dark else .52;bs.inputs['Roughness'].default_value=.48 if dark else .33;mats[rgba]=mat
    ob.data.materials.append(mats[rgba])
    if 'push-pad' in row['name']:ob.data.materials[0]=mats[rgba];ob['retrofit']='Fixed miniature rubber pushing pad beyond fingertips'
out=root/'web/desk/assets/g1-mini.glb';bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',export_apply=True,export_extras=True);meta={**bundle['metadata'],'appearance':'Graphite polymer for native black material; satin aluminum shell; visual material treatment only','display_mesh_lod':'55% triangles for visual meshes above 6000 faces; native collision meshes retained','glb_sha256':hashlib.sha256(out.read_bytes()).hexdigest()};(out.parent/'g1-source.json').write_text(json.dumps(meta,indent=2));(out.parent/'G1-LICENSE.txt').write_text((root/'assets/robot/g1/LICENSE').read_text());print('G1_GLB',out.stat().st_size,len(bodies))
