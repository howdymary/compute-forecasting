"""Frozen success predicates matching the original curriculum, outside policy."""
import math
def laptop_good(angle,speed,progress):
 return angle<math.radians(5) and abs(speed)<.15 and progress>math.radians(4)
def task_valid(dwell,contacts,bad_contacts,fall,max_force):
 return bool(dwell>.35 and contacts>0 and bad_contacts==0 and not fall and max_force<.8)
def full_success(episode):
 values=episode.get('final_object_states',{});speeds=episode.get('final_object_speeds',{})
 return bool(all(episode['results'].get(t,{}).get('success',False) for t in ['alarm','drawer','laptop','globe']) and not episode['fall'] and values.get('drawer',1)<.002 and values.get('laptop',9)<math.radians(5) and abs(values.get('globe',9))<math.radians(3) and all(abs(speeds.get(t,9))<v for t,v in [('drawer',.01),('laptop',.15),('globe',.07)]))

def sequence_success(row):
 ep=row['episode'];return bool(full_success(ep) and row['mode']=='done' and row['failure'] is None and len(row['arrivals'])==4 and len(ep.get('recoveries',[]))==4 and all(r['success'] for r in ep['recoveries']))
