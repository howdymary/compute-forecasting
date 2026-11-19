"""Journal pending memory writes; dependent reads still require ready sources."""
import asyncio,json,time
from ..desk.services import DeskServices
from ..integrations import now,digest
from ..curriculum.world import ROOT

class TerrainServices(DeskServices):
    def __init__(self):
        super().__init__();self.pending={}

    def journal(self):
        path=ROOT/'artifacts/terrain-v12-training'/f'{self.run_id}-memory-journal.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'pending':self.pending,'ready':self.records},indent=2)+'\n')

    async def write(self,role,content,private=False):
        rid=self.run_id+'-r'+str(len(self.records)+len(self.pending));at=now();started=time.perf_counter()
        value={'record_id':rid,'author':self.actors[role],'occurred_at':at,'content':content}
        text=f'Mochi desk {role} record {rid}. Canonical SHA256 {digest(value)}. '+json.dumps(content,sort_keys=True)
        reply=await self.request('POST','/ingest',{'id':rid,'identity':self.actors[role],
            'audience':self.private if private else self.audience,'timestamp':at,
            'label':f'Mochi desk {content.get("kind","finding")}','content':text})
        record={'id':rid,'role':role,'author':self.actors[role],'audience':self.private if private else self.audience,
            'at':at,'sha256':digest(value),'ingestion_id':reply['ingestionId'],'payload':value,'status':'pending'}
        self.pending[rid]=record;self.journal();last_report=started
        while time.perf_counter()-started<900:
            status=await self.request('GET','/ingest/'+record['ingestion_id']);record['status']=status.get('status','unknown')
            if record['status']=='completed':
                record['write_to_ready_seconds']=time.perf_counter()-started
                self.records[rid]=self.pending.pop(rid);self.journal();return rid
            if record['status']=='failed':self.journal();raise RuntimeError('Memory ingestion failed; journal preserved')
            if time.perf_counter()-last_report>=45:
                print('MEMORY_PENDING',rid,round(time.perf_counter()-started),flush=True);last_report=time.perf_counter();self.journal()
            await asyncio.sleep(5)
        self.journal();raise TimeoutError('Memory ingestion remains pending; ingestion ID preserved for retry')

    def report(self):
        return {**super().report(),'pending_ingestions':[
            {k:v for k,v in r.items() if k not in ['payload']} for r in self.pending.values()]}
