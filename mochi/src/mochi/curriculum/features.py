"""Visible-state discretization and exact, checkpoint-specific inference caching.

No teacher action, seed, latent dynamics or test outcome enters these features.
The learned model must combine independent geometry bins to choose an action.
"""
import asyncio,json
from .decisions import choose

def signed_band(value,low,high):
 a=abs(value)
 return 'within_'+str(low) if a<=low else ('positive_' if value>0 else 'negative_')+('small' if a<high else 'large')

def encode(obs):
 if obs['domain']!='walk':return obs
 d=obs['distance_mm'];f=obs['target_forward_mm'];l=obs['target_left_mm'];h=obs['heading_error_degrees'];a=abs(h)
 return {'domain':'walk','range_mm':'below_18' if d<18 else '18_to_below_70' if d<70 else '70_through_100' if d<=100 else 'above_100','bearing_band_degrees':signed_band(obs['bearing_degrees'],10,25),'heading_band_degrees':'within_7' if a<=7 else ('positive_' if h>0 else 'negative_')+('7_to_below_9' if a<9 else '9_to_below_25' if a<25 else 'at_least_25'),'forward_offset_mm':'within_9' if abs(f)<=9 else 'positive' if f>0 else 'negative','lateral_offset_mm':'within_9' if abs(l)<=9 else 'positive' if l>0 else 'negative','larger_absolute_offset_axis':'forward' if abs(f)>=abs(l) else 'lateral'}

class CachedSelector:
 """Every unique encoded observation is actually scored by the saved model.

 Identical observations at the same checkpoint reuse that exact distribution.
 There is no heuristic controller, teacher call or default-action fallback here.
 """
 def __init__(self):self.cache={};self.pending={};self.hits=0;self.calls=0
 async def __call__(self,sampler,renderer,obs):
  observed=encode(obs);key=json.dumps(observed,sort_keys=True)
  if key in self.cache:self.hits+=1;return self.cache[key]
  if key not in self.pending:self.calls+=1;self.pending[key]=asyncio.create_task(choose(sampler,renderer,observed))
  else:self.hits+=1
  answer=await self.pending[key];self.cache[key]=answer;return answer
 def receipt(self):return {'actual_tinker_inference_calls':self.calls,'identical_observation_cache_hits':self.hits,'distributions':[{'encoded_observation':json.loads(k),'action':v[0],'distribution':v[1]} for k,v in self.cache.items()]}
