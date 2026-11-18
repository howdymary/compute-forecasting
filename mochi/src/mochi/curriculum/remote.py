"""Stateful Modal physics: model decisions advance one uninterrupted world."""
import time
from pathlib import Path
import modal
ROOT=Path(__file__).resolve().parents[3]
image=(modal.Image.debian_slim(python_version='3.11')
 .apt_install('libgl1','libglib2.0-0')
 .run_commands('pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu')
 .pip_install('mujoco==3.3.7','numpy==2.3.4','scipy==1.16.3','pyyaml==6.0.2')
 .env({'MOCHI_ROOT':'/app','PYTHONPATH':'/app/src','MUJOCO_GL':'disable','PYTHONWARNINGS':'ignore'})
 .add_local_dir(ROOT/'src',remote_path='/app/src')
 .add_local_dir(ROOT/'assets/robot/g1',remote_path='/app/assets/robot/g1')
 .add_local_dir(ROOT/'assets/robot/locomotion',remote_path='/app/assets/robot/locomotion'))
app=modal.App('mochi-curriculum-v6')

def receipt(start):
    return {'provider':'Modal','cpu':1,'memory_mib':2048,'duration_seconds':time.perf_counter()-start}

@app.function(image=image,cpu=1,memory=2048,max_containers=8,timeout=600)
def contact_trial(seed,task,code,record=False):
    from .world import World,PROFILES
    start=time.perf_counter();w=World(seed,record,start_task=task);obs=w.task_observation(task)
    result=w.do_task(task,next(p for p in PROFILES if p.code==code))
    return {'seed':seed,'observation':obs,'result':result,'receipt':receipt(start),'episode':w.episode() if record else None}

@app.function(image=image,cpu=1,memory=2048,max_containers=8,timeout=900)
def expert_sequence(seed,record=False):
    from .world import World,ROUTE
    start=time.perf_counter();w=World(seed,record);arrivals=[]
    for task,goal in ROUTE:
        arrived=w.walk_to(goal);arrivals.append({'station':task,'arrived':arrived})
        if not arrived:break
        if task!='transit':w.do_task(task);w.rest_arms()
    return {'seed':seed,'arrivals':arrivals,'episode':w.episode(),'receipt':receipt(start)}

class Runner:
    def reset(self,seed,record=True):
        from .world import World,ROUTE
        self.start=time.perf_counter();self.w=World(seed,record);self.index=0;self.arrivals=[];self.leg_start=0.;self.settle=0.;self.mode='walk';self.goal=ROUTE[0][1];self.calls=0
        return self.status()

    def status(self):
        from .world import ROUTE
        if self.w.fall or self.index>=len(ROUTE) or self.w.d.time-self.leg_start>24:
            self.mode='done';return {'mode':'done','episode':self.w.episode(),'arrivals':self.arrivals,'receipt':receipt(self.start),'physics_calls':self.calls}
        return {'mode':self.mode,'station':ROUTE[self.index][0],'observation':self.w.walk_observation(self.goal) if self.mode=='walk' else self.w.task_observation(ROUTE[self.index][0])}

    def next_station(self):
        from .world import ROUTE
        self.index+=1;self.mode='walk';self.leg_start=float(self.w.d.time);self.settle=0.;self.w.walker.last=-1.;self.w.walker.action[:]=0;self.w.walker.velocity_integral[:]=0;self.w.walker.yaw_integral=0
        if self.index<len(ROUTE):self.goal=ROUTE[self.index][1]

    def advance(self,action):
        from .world import ROUTE,MOVES,DT,PROFILES
        self.calls+=1;w=self.w
        if self.mode=='walk':
            w.task=None;w.phase='walk';obs=w.walk_observation(self.goal);w.decisions.append({'t':float(w.d.time),'observation':obs,'action':action});end=float(w.d.time)+(.45 if action=='stop' else .64 if obs['distance_mm']>100 else .32)
            while w.d.time<end and not w.fall:
                obs=w.walk_observation(self.goal);arrived=(self.settle>0 or obs['distance_mm']<22) and abs(obs['heading_error_degrees'])<12
                if action=='stop' and arrived:
                    w.step(standing=True);self.settle+=DT
                    if self.settle>.4:
                        self.arrivals.append({'station':ROUTE[self.index][0],'arrived':True,'t':float(w.d.time)})
                        if ROUTE[self.index][0]=='transit':self.next_station()
                        else:self.mode='task'
                        break
                else:self.settle=0.;w.step(MOVES[action])
        elif self.mode=='task':
            task=ROUTE[self.index][0];w.decisions.append({'t':float(w.d.time),'observation':w.task_observation(task),'action':action});w.do_task(task,next(p for p in PROFILES if p.code==action));w.rest_arms();self.next_station()
        return self.status()

@app.function(image=image,cpu=1,memory=2048,max_containers=8,timeout=900)
def replay(seed,actions,record=True):
    runner=Runner();status=runner.reset(seed,record)
    for action in actions:
        if status['mode']=='done':break
        status=runner.advance(action)
    if status['mode']!='done':
        status={'mode':'incomplete','episode':runner.w.episode(),'arrivals':runner.arrivals,'receipt':receipt(runner.start)}
    return status

@app.function(image=modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1'),cpu=.25,memory=256,max_containers=1,serialized=True)
@modal.fastapi_endpoint(method='GET')
def progress():
    """Public numerical status only: no credentials or model checkpoint paths."""
    return modal.Dict.from_name('mochi-curriculum-v6-progress',create_if_missing=True).get('latest',{'status':'waiting'})
