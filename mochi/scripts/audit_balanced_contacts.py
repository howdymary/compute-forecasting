"""Read-only contact observer on the frozen continuous engineering reference."""
import hashlib,json
from pathlib import Path
import mujoco,numpy as np
from mochi.balanced.sequence import SequenceWorld,run
from mochi.balanced.policy import fixed
from mochi.balanced.budget import reserve,finish,OUT

ident='independent-contact-audit-0'
reserve(ident,{'scope':'Additional contact observations only; no changed controls, state or physics'})
original=SequenceWorld.step;contacts={}

def observed(self,*args,**kwargs):
    original(self,*args,**kwargs)
    if self.phase!='walk':return
    allowed={self.id('geom','desk')}|self.book_geoms
    for i,c in enumerate(self.d.contact):
        a,b=int(c.geom1),int(c.geom2);ra=int(self.m.geom_bodyid[a]) in self.robot_bodies;rb=int(self.m.geom_bodyid[b]) in self.robot_bodies
        if ra==rb:continue
        robot,fixture=(a,b) if ra else (b,a)
        body=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,int(self.m.geom_bodyid[robot]))
        if fixture in allowed and body in ['left_ankle_roll_link','right_ankle_roll_link']:continue
        f=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,f)
        if f[0]<=.01:continue
        name=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_GEOM,fixture) or str(fixture);key=body+' / '+name
        row=contacts.setdefault(key,{'count':0,'peak_n':0.,'first_t':float(self.d.time),'last_t':0.})
        row['count']+=1;row['peak_n']=max(row['peak_n'],float(f[0]));row['last_t']=float(self.d.time)

try:
    SequenceWorld.step=observed
    result=run(31000,True,native_stand=True,choose=fixed)
    result['independent_walking_contact_audit']=contacts
    result['observer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (OUT/(ident+'.json')).write_text(json.dumps(result,separators=(',',':')))
    finish(ident,{'status':'completed','complete':result['complete_sequence_success'],'unintended_contact_pairs':len(contacts)})
    print(json.dumps({'complete':result['complete_sequence_success'],'walking_contact_audit':contacts}),flush=True)
finally:
    SequenceWorld.step=original
