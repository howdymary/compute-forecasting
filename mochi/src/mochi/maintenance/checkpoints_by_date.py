"""Inventory, then delete an exact user-authorized local creation date.

No training sessions, checkpoint writes, billing changes, or other-date deletes.
The inventory and mutation receipts retain hashes rather than private paths.
"""
import asyncio,hashlib,json,os
from collections import Counter
from datetime import datetime,timezone,date,time,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(os.environ.get('MOCHI_ROOT',Path(__file__).resolve().parents[3]))
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def checkpoint_time(checkpoint):
 raw=checkpoint.model_dump(mode='json').get('time')
 if raw is None:return None
 stamp=datetime.fromisoformat(str(raw).replace('Z','+00:00'))
 if stamp.tzinfo is None:raise ValueError('Checkpoint creation timestamp has no timezone')
 return stamp
def eligible(checkpoint,local_date,tz):
 stamp=checkpoint_time(checkpoint)
 return bool(stamp is not None and stamp.astimezone(tz).date()==local_date)
async def inventory(rest):
 rows=[];offset=0
 for _ in range(100):
  page=await rest.list_user_checkpoints(limit=100,offset=offset);rows.extend(page.checkpoints)
  total=page.cursor.total_count if page.cursor else None
  if not page.checkpoints or total is not None and len(rows)>=total or len(page.checkpoints)<100:break
  offset+=len(page.checkpoints)
 else:raise RuntimeError('Checkpoint inventory pagination limit; no deletion permitted')
 if len({c.tinker_path for c in rows})!=len(rows):raise RuntimeError('Duplicate inventory records; no deletion permitted')
 return rows
async def main():
 import tinker
 cfg=json.loads((ROOT/'configs/checkpoint-cleanup.json').read_text());day=date.fromisoformat(cfg['creation_date']);tz=ZoneInfo(cfg['timezone']);rest=tinker.RestClient();before=await inventory(rest);selected=[c for c in before if eligible(c,day,tz)];target_ids=sorted(digest(c.tinker_path) for c in selected);target_digest=digest({'date':day.isoformat(),'timezone':cfg['timezone'],'checkpoint_ids':target_ids});out=ROOT/'artifacts/maintenance';out.mkdir(parents=True,exist_ok=True)
 start=datetime.combine(day,time(),tzinfo=tz);end=datetime.combine(day+timedelta(days=1),time(),tzinfo=tz)
 report={'at':datetime.now(timezone.utc).isoformat(),'workflow_run':os.getenv('GITHUB_RUN_ID'),'source_sha':os.getenv('GITHUB_SHA'),'mode':cfg['mode'],'date':day.isoformat(),'timezone':cfg['timezone'],'utc_start_inclusive':start.astimezone(timezone.utc).isoformat(),'utc_end_exclusive':end.astimezone(timezone.utc).isoformat(),'before_count':len(before),'eligible_count':len(selected),'eligible_bytes':sum(c.size_bytes or 0 for c in selected),'target_digest':target_digest,'target_ids':target_ids,'counts_by_local_date':dict(Counter(checkpoint_time(c).astimezone(tz).date().isoformat() if checkpoint_time(c) else 'unknown' for c in before)),'eligible_types':dict(Counter(c.checkpoint_type for c in selected)),'records':[{'id_sha256':digest(c.tinker_path),'created_at':checkpoint_time(c).isoformat() if checkpoint_time(c) else None,'checkpoint_type':c.checkpoint_type,'size_bytes':c.size_bytes,'selected':eligible(c,day,tz),'mochi_named':'mochi' in c.checkpoint_id.lower()} for c in before],'deleted':[],'failures':[],'training_updates':0,'billing_changed':False,'private_paths_exposed':False}
 def save():
  (out/'checkpoint-date-cleanup.json').write_text(json.dumps(report,indent=2)+'\n')
 save();print('INVENTORY',json.dumps({k:report[k] for k in ['mode','date','timezone','before_count','eligible_count','eligible_bytes','target_digest','counts_by_local_date','eligible_types']}),flush=True)
 if cfg['mode']=='inventory':return
 if cfg['mode']!='delete':raise ValueError('Unsupported maintenance mode')
 if cfg.get('expected_target_digest')!=target_digest or cfg.get('expected_count')!=len(selected):raise RuntimeError('Date-scoped target set changed; zero deletions permitted')
 protected={digest(c.tinker_path) for c in before if not eligible(c,day,tz)}
 for c in selected:
  assert eligible(c,day,tz)
  try:
   await rest.delete_checkpoint_from_tinker_path(c.tinker_path);report['deleted'].append({'id_sha256':digest(c.tinker_path),'created_at':checkpoint_time(c).isoformat(),'checkpoint_type':c.checkpoint_type,'size_bytes':c.size_bytes})
  except Exception as exc:
   report['failures'].append({'id_sha256':digest(c.tinker_path),'error_type':type(exc).__name__,'status_code':getattr(exc,'status_code',None)});save();break
  save();print('DELETED',len(report['deleted']),digest(c.tinker_path)[:12],flush=True)
 after=await inventory(rest);remaining={digest(c.tinker_path) for c in after};missing_protected=sorted(protected-remaining);residual=[digest(c.tinker_path) for c in after if eligible(c,day,tz)];report.update(after_count=len(after),remaining_selected_count=len(residual),protected_count=len(protected),protected_preserved=not missing_protected,missing_protected=missing_protected,deleted_bytes=sum(c['size_bytes'] or 0 for c in report['deleted']),verified_at=datetime.now(timezone.utc).isoformat());save()
 if missing_protected:raise RuntimeError('Other-date checkpoints disappeared during cleanup')
 if residual or report['failures']:raise RuntimeError('Date-scoped cleanup incomplete; inspect hashed receipt')
 print('VERIFIED',json.dumps({k:report[k] for k in ['date','timezone','before_count','after_count','eligible_count','deleted_bytes','remaining_selected_count','protected_preserved','billing_changed']}),flush=True)
if __name__=='__main__':asyncio.run(main())
