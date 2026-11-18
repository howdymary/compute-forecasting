"""Read downloaded geometry as USD; never execute dataset Python programs."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1];result={}
for name in ['business_laptop','classroom_globe_on_meridian','desk_task_lamp']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.usd_import(filepath=str(root/'assets/realism/sand3d'/(name+'.usda')))
    objects=[]
    for o in bpy.context.scene.objects:
        bounds=[o.matrix_world@Vector(corner) for corner in o.bound_box] if o.type=='MESH' else []
        objects.append({'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'vertices':len(o.data.vertices) if o.type=='MESH' else 0,'dimensions':list(o.dimensions),'bounds_min':[min(p[i] for p in bounds) for i in range(3)] if bounds else None,'bounds_max':[max(p[i] for p in bounds) for i in range(3)] if bounds else None})
    result[name]=objects;print('SAND_ASSET',name,'objects',len(objects),'vertices',sum(x['vertices'] for x in objects),flush=True)
    print('SAND_PARTS',[(x['name'],x['parent'],x['vertices']) for x in objects[:35]],flush=True)
(root/'artifacts/realism-v4/sand-inspection.json').write_text(json.dumps(result,indent=2))
