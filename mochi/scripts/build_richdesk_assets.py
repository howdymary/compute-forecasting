"""Normalize verified Sand3D GLBs for one shared simulation/render scene spec."""
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/richdesk'
OUT=ROOT/'web/desk/assets/richdesk'
OUT.mkdir(parents=True,exist_ok=True)
records=json.loads((SOURCE/'selected.json').read_text())['records']
result=[]
for record in records:
    key=record['key'];path=SOURCE/'source'/(key+'.glb')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==record['source_sha256']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    dimensions=hi-lo;axes=[0,1,2]
    if key in ['book','notebook']:
        thin=min(range(3),key=lambda i:dimensions[i]);long=max(range(3),key=lambda i:dimensions[i])
        axes=[next(i for i in range(3) if i not in [thin,long]),long,thin]
    elif key=='glasses':
        thin=min(range(3),key=lambda i:dimensions[i]);long=max(range(3),key=lambda i:dimensions[i]);axes=[long,next(i for i in range(3) if i not in [thin,long]),thin]
    elif key in ['pencil','pen']:
        long=max(range(3),key=lambda i:dimensions[i]);rest=[i for i in range(3) if i!=long];axes=[long,*rest]
    rotation=Matrix(tuple(tuple(float(axes[i]==j) for j in range(3)) for i in range(3)))
    if rotation.determinant()<0:
        for j in range(3):rotation[0][j]*=-1
    rotated=[rotation@p for p in points]
    lo2=Vector(tuple(min(p[i] for p in rotated) for i in range(3)))
    hi2=Vector(tuple(max(p[i] for p in rotated) for i in range(3)))
    size=hi2-lo2;center=(lo2+hi2)/2;center.z=lo2.z
    fit=Matrix.Diagonal((1/size.x,1/size.y,1/size.z,1))@Matrix.Translation(-center)@rotation.to_4x4()
    originals=list(bpy.context.scene.objects);clones=[]
    for o in objects:
        n=bpy.data.objects.new(o.name+'_fitted',o.data.copy());bpy.context.collection.objects.link(n)
        n.data.transform(fit@o.matrix_world);clones.append(n)
    for o in originals:bpy.data.objects.remove(o,do_unlink=True)
    bpy.ops.object.select_all(action='SELECT')
    out=OUT/(key+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',export_apply=True,export_extras=True)
    result.append({**record,'file':'richdesk/'+key+'.glb','normalized_axes':axes,
        'source_bounds':{'lo':list(lo),'hi':list(hi)},'normalized_bounds':{'lo':[-.5,-.5,0],'hi':[.5,.5,1]},
        'modifications':'Rigid mesh transforms baked, thin book dimension mapped to Z and pencil/pen length mapped to X; unit bounding box, then explicit metre dimensions supplied by the shared scene config. Original materials retained.',
        'sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
    print('DESK_ASSET',key,'parts',len(objects),'source_dimensions',list(dimensions),'axes',axes,flush=True)
(OUT/'attribution.json').write_text(json.dumps({'credit':'Sand3D, Thibault Neveu and Andréa Loy, Sandflow, 2026; per-object original credits below.','assets':result},indent=2)+'\n')
