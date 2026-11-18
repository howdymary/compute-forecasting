"""Read-only storage audit. Never deletes checkpoints or changes billing."""
import asyncio,json,os
from pathlib import Path
from datetime import datetime,timezone
async def main():
 import tinker
 rest=tinker.RestClient();all_rows=[];offset=0;total=None
 for _ in range(20):
  page=await rest.list_user_checkpoints(limit=100,offset=offset);all_rows.extend(page.checkpoints);total=page.cursor.total_count if page.cursor else len(all_rows)
  if not page.checkpoints or len(all_rows)>=total:break
  offset+=len(page.checkpoints)
 ours=[c.model_dump(mode='json') for c in all_rows if 'mochi' in c.checkpoint_id.lower()]
 report={'at':datetime.now(timezone.utc).isoformat(),'owner_checkpoint_count':total,'listed':len(all_rows),'mochi_checkpoints':ours,'mutations':0,'training_updates':0,'billing_changed':False}
 try:
  usage=await tinker.AdminClient().get_current_checkpoint_storage_usage();report['storage_snapshot']={'count':sum(x.checkpoint_count for x in usage.data),'bytes':sum(x.size_bytes for x in usage.data),'effective_rate_usd_per_gib_month':usage.effective_rate_usd_per_gigabyte_month,'can_lag_hours':2}
 except Exception as exc:report['storage_snapshot_error_type']=type(exc).__name__
 out=Path(os.environ.get('MOCHI_ROOT','mochi'))/'artifacts/planning';out.mkdir(parents=True,exist_ok=True);(out/'storage-private.json').write_text(json.dumps(report,indent=2))
 print(json.dumps({k:v for k,v in report.items() if k!='mochi_checkpoints'}),flush=True)
 print('Mochi checkpoint labels',[(x['checkpoint_id'],x['checkpoint_type']) for x in ours],flush=True)
if __name__=='__main__':asyncio.run(main())
