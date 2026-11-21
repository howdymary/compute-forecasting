"""Blender material authoring; keep G1 dimensions, body nodes and pivots."""
import hashlib
import json
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
TEXTURES = ROOT / 'web/desk/assets/visual-motion-v22'
OUT = ROOT / 'artifacts/visual-motion-v22'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
source = ROOT / 'web/desk/assets/g1-mini.glb'
bpy.ops.import_scene.gltf(filepath=str(source))


def texture(name):
    image = bpy.data.images.load(str(TEXTURES / name), check_existing=True)
    image.colorspace_settings.name = 'Non-Color'
    return image


mat_count = 0
for material in bpy.data.materials:
    if not material.use_nodes:
        continue
    shader = material.node_tree.nodes.get('Principled BSDF')
    if shader is None:
        continue
    dark = 'graphite' in material.name.lower()
    shader.inputs['Base Color'].default_value = (.022, .029, .034, 1) if dark else (.61, .64, .63, 1)
    shader.inputs['Metallic'].default_value = .07 if dark else .78
    shader.inputs['Roughness'].default_value = .42 if dark else .30
    shader.inputs['Coat Weight'].default_value = .12 if dark else .16
    shader.inputs['Coat Roughness'].default_value = .35
    nodes, links = material.node_tree.nodes, material.node_tree.links
    rough = nodes.new('ShaderNodeTexImage')
    rough.image = texture('polymer-roughness.png' if dark else 'brushed-roughness.png')
    links.new(rough.outputs['Color'], shader.inputs['Roughness'])
    if not dark:
        normal = nodes.new('ShaderNodeTexImage')
        normal.image = texture('brushed-normal.png')
        mapping = nodes.new('ShaderNodeNormalMap')
        mapping.inputs['Strength'].default_value = .18
        links.new(normal.outputs['Color'], mapping.inputs['Color'])
        links.new(mapping.outputs['Normal'], shader.inputs['Normal'])
    mat_count += 1

meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
coated = {}
for obj in meshes:
    body = obj.parent.name if obj.parent else ''
    if any(part in body for part in ['torso_link', 'hip_yaw_link', 'knee_link', 'shoulder_yaw_link', 'elbow_link']):
        for slot in obj.material_slots:
            original = slot.material
            if original is None or 'graphite' in original.name.lower():
                continue
            if original.name not in coated:
                finish = original.copy()
                finish.name = 'Warm enamel over machined shell'
                shader = finish.node_tree.nodes.get('Principled BSDF')
                shader.inputs['Base Color'].default_value = (.73, .75, .70, 1)
                shader.inputs['Metallic'].default_value = .06
                shader.inputs['Roughness'].default_value = .72
                shader.inputs['Coat Weight'].default_value = .24
                coated[original.name] = finish
            slot.material = coated[original.name]
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if not obj.data.uv_layers:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.008)
        bpy.ops.object.mode_set(mode='OBJECT')

target = OUT / 'g1-studio-unpacked.glb'
bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB', export_extras=True,
    export_apply=False, export_materials='EXPORT', export_animations=False)
receipt = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'blender_version': bpy.app.version_string, 'materials_authored': mat_count,
    'meshes': len(meshes), 'geometry_edited': False,
    'scope': 'Appearance only. UVs and PBR materials added; no collision, joint, controller or trajectory edits.'}
(OUT / 'robot-materials.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('V22_ROBOT_MATERIALS', json.dumps(receipt))
