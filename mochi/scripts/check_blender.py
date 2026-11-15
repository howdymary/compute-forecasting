"""Verify three recorded body-pose keyframes against the actual saved Blender scene."""
import bpy,json,sys
from pathlib import Path
trajectory=Path(sys.argv[sys.argv.index('--')+1]);r=json.loads(trajectory.read_text());frames=r['trajectory']['frames'][::2];worst=0.
for i in [0,len(frames)//2,len(frames)-1]:
    bpy.context.scene.frame_set(i+1)
    for j,name in enumerate(r['trajectory']['body_names']):
        o=bpy.data.objects[name];p=frames[i]['positions'][j];q=frames[i]['quaternions'][j]
        err=max(abs(o.location[k]-p[k]) for k in range(3));qerr=min(max(abs(o.rotation_quaternion[k]-q[k]) for k in range(4)),max(abs(o.rotation_quaternion[k]+q[k]) for k in range(4)))
        worst=max(worst,err,qerr)
assert worst<1e-5, f'Blender transform mismatch: {worst}'
print('MOCHI_TRANSFORM_AUDIT:'+json.dumps({'max_pose_component_error':worst,'keyframes_checked':3,'bodies':len(r['trajectory']['body_names']),'source':str(trajectory),'status':'passed'}))
