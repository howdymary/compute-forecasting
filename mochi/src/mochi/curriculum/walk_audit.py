"""Direct, matched locomotion evaluation of existing Tinker checkpoints. No training."""
import asyncio,json,os,time
from pathlib import Path
import numpy as np
import modal
from .remote import image as physics_image,Runner
from .world import ROOT,World
from .decisions import choose
from ..integrations import digest,now
image=physics_image.add_local_file(ROOT/'configs/walking-audit-protocol.json',remote_path='/app/configs/walking-audit-protocol.json')
app=modal.App('mochi-curriculum-v6-walking-audit')
PROTOCOL=json.loads((ROOT/'configs/walking-audit-protocol.json').read_text())
OUT=ROOT/'artifacts/walking-audit'
def save(name,value):
 OUT.mkdir(exist_ok=True,parents=True);(OUT/(name+'.json')).write_text(json.dumps(value,indent=2))
def wilson(k,n):
 z=1.95996398454;p=k/n;den=1+z*z/n;c=(p+z*z/(2*n))/den;h=z*((p*(1-p)/n+z*z/(4*n*n))**.5)/den;return [max(0.,c-h),min(1.,c+h)]
def summary(rows):
 successes=sum(x['success'] for x in rows)
 return {'n':len(rows),'successes':successes,'wilson_95_success_rate':wilson(successes,len(rows)),'falls':sum(x['episode']['fall'] for x in rows),'mean_position_error_mm':float(np.mean([x['end_observation']['distance_mm'] for x in rows])),'mean_heading_error_degrees':float(np.mean([abs(x['end_observation']['heading_error_degrees']) for x in rows])),'mean_duration_s':float(np.mean([x['episode']['duration'] for x in rows]))}
async def run_one(sampler,renderer,seed,offset,expert=False):
 r=Runner();s=r.reset(seed,False);goal=(float(r.w.d.qpos[0])+offset[0],float(r.w.d.qpos[1])+offset[1],offset[2]);r.goal=goal;s=r.status();actions=[]
 for _ in range(100):
  if s['mode']!='walk':break
  action=World.teacher_move(s['observation']) if expert else (await choose(sampler,renderer,s['observation']))[0];actions.append(action);s=r.advance(action)
 return {'seed':seed,'goal':goal,'actions':actions,'success':bool(s['mode']=='task' and not r.w.fall),'end_observation':r.w.walk_observation(goal),'episode':r.w.episode()}
@app.function(image=image,cpu=1,memory=2048,max_containers=8,timeout=600)
def verify(seed,goal,actions):
 r=Runner();r.reset(seed,False);r.goal=goal;s=r.status();start=time.perf_counter()
 for action in actions:
  if s['mode']!='walk':break
  s=r.advance(action)
 return {'seed':seed,'success':bool(s['mode']=='task' and not r.w.fall),'duration_s':float(r.w.d.time),'provider':'Modal','worker_wall_seconds':time.perf_counter()-start,'cpu':1,'memory_mib':2048}
async def main():
 import tinker
 from tinker_cookbook import model_info,renderers
 from tinker_cookbook.recipes.decisions import DecisionRenderer
 source=ROOT/'.cache/training-source';report=json.loads(next(source.rglob('report.json')).read_text());paths=json.loads(next(source.rglob('checkpoint-paths.json')).read_text());service=tinker.ServiceClient(display_name='mochi-v6-walking-audit');all_rows={};result={'created_at':now(),'source_sha':os.getenv('GITHUB_SHA'),'protocol':PROTOCOL,'protocol_sha256':digest(PROTOCOL),'training_source_sha':report['source_sha'],'selected_update':report['selected_checkpoint']['update'],'extra_optimizer_updates':0,'checkpoints':[]}
 async with app.run():
  for update in PROTOCOL['checkpoints']:
   sampler=await service.create_sampling_client(model_path=paths[str(update)]['weights']);renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),sampler.get_tokenizer()));rows=await asyncio.gather(*(run_one(sampler,renderer,seed,offset) for seed,offset in zip(PROTOCOL['seeds'],PROTOCOL['goal_offsets'])));all_rows[str(update)]=rows;cp={'update':update,'checkpoint_id':next(c['checkpoint_id'] for c in report['checkpoints'] if c['update']==update),**summary(rows)};result['checkpoints'].append(cp);save('progress',result);save('checkpoint-'+str(update),rows);print('WALKING_CHECKPOINT',json.dumps(cp),flush=True)
  baseline=await asyncio.gather(*(run_one(None,None,seed,offset,True) for seed,offset in zip(PROTOCOL['seeds'],PROTOCOL['goal_offsets'])));result['classical_waypoint']=summary(baseline);all_rows['classical']=baseline
  jobs=[(row['seed'],row['goal'],row['actions']) for rows in all_rows.values() for row in rows];remote=[x async for x in verify.starmap.aio(jobs,order_outputs=True)];local=[row for rows in all_rows.values() for row in rows]
  checks=[{'seed':a['seed'],'same_success':a['success']==b['success'],'duration_delta_s':abs(a['episode']['duration']-b['duration_s']),'receipt':b} for a,b in zip(local,remote)];result['remote_replay_checks']=checks;result['modal_rollouts']=len(remote)
  if not all(x['same_success'] and x['duration_delta_s']<.01 for x in checks):raise RuntimeError('Isolated walking replay disagreement')
  save('classical',baseline);result.update(status='completed',completed_at=now());save('report',result)
if __name__=='__main__':
 with modal.enable_output():asyncio.run(main())
