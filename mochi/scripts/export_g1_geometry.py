"""Export native compiled visual geometry for Blender and the web viewer."""
from pathlib import Path
import json,hashlib
import mujoco,numpy as np
from mochi.desk.g1_model import TEMPLATE,METADATA,ROOT
m=mujoco.MjModel.from_xml_string(TEMPLATE);out=ROOT/'artifacts/realism-v4';out.mkdir(parents=True,exist_ok=True);meshes=[]
for g in range(m.ngeom):
    if m.geom_group[g]!=2:continue
    b=int(m.geom_bodyid[g]);name=mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,b)
    row={'body':name,'name':mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_GEOM,g),'position':m.geom_pos[g].tolist(),'quaternion':m.geom_quat[g].tolist(),'rgba':(m.mat_rgba[m.geom_matid[g]] if m.geom_matid[g]>=0 else m.geom_rgba[g]).tolist()}
    if m.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH:
        mi=int(m.geom_dataid[g]);row.update(type='mesh',vertices=m.mesh_vert[m.mesh_vertadr[mi]:m.mesh_vertadr[mi]+m.mesh_vertnum[mi]].tolist(),faces=m.mesh_face[m.mesh_faceadr[mi]:m.mesh_faceadr[mi]+m.mesh_facenum[mi]].tolist())
    elif m.geom_type[g]==mujoco.mjtGeom.mjGEOM_SPHERE:row.update(type='sphere',radius=float(m.geom_size[g,0]))
    else:raise ValueError('Unexpected visual primitive')
    meshes.append(row)
p=out/'g1-geometry.json';p.write_text(json.dumps({'metadata':METADATA,'meshes':meshes},separators=(',',':')));(out/'g1-mini-metadata.json').write_text(json.dumps(METADATA,indent=2));print(p,len(meshes),p.stat().st_size)
