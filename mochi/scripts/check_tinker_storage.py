"""Read-only recovery inventory: never deletes checkpoints or changes billing."""
import asyncio,json,os
from pathlib import Path
async def main():
 import tinker
 rest=tinker.RestClient();run='47dd6051-72dc-5bec-8b50-f08e30be20f7:train:0';ours=await rest.list_checkpoints(run);recent=await rest.list_user_checkpoints(limit=100)
 report={'training_run_id':run,'owned_checkpoint_count':recent.cursor.total_count if recent.cursor else len(recent.checkpoints),'mochi_checkpoints':[c.model_dump(mode='json') for c in ours.checkpoints]}
 try:
  u=await tinker.AdminClient().get_current_checkpoint_storage_usage();report['organization_storage_snapshot']={'checkpoint_count':sum(i.checkpoint_count for i in u.data),'size_bytes':sum(i.size_bytes for i in u.data),'size_gigabytes':sum(i.size_gigabytes for i in u.data),'effective_rate_usd_per_gigabyte_month':u.effective_rate_usd_per_gigabyte_month,'snapshot_can_lag_hours':2}
 except Exception as e:report['storage_snapshot_error_type']=type(e).__name__
 out=Path(os.getenv('MOCHI_ROOT','mochi'))/'artifacts/curriculum';out.mkdir(exist_ok=True,parents=True);(out/'storage-report.json').write_text(json.dumps(report,indent=2));print(json.dumps({'owned_checkpoint_count':report['owned_checkpoint_count'],'organization_storage_snapshot':report.get('organization_storage_snapshot'),'mochi_checkpoints':[{'id':c.checkpoint_id,'type':c.checkpoint_type,'size_bytes':c.size_bytes} for c in ours.checkpoints]}),flush=True)
asyncio.run(main())
