"""Reuse verified Mochi clients with longer, source-verified memory handoffs."""
import asyncio,json,time,uuid
from ..integrations import Services,now,digest

class DeskServices(Services):
    def __init__(self):
        super().__init__();self.run_id='mochi-desk-'+uuid.uuid4().hex[:8]
        self.actors={r:self.run_id+'-'+r for r in ['researcher','designer','experimenter','critic']}
        self.audience=self.run_id+'-shared';self.private=self.run_id+'-critic'

    async def setup(self):
        for role,actor in self.actors.items():
            await self.request('PUT','/identities/'+actor,{'traits':{'project':'mochi-desk-v3','role':role}})
        for slug,actors in [(self.audience,list(self.actors.values())),(self.private,[self.actors['critic']])]:
            assert len(slug)<=40
            await self.request('PUT','/audiences/'+slug,{'kind':'fixed','name':'Mochi desk research','identities':actors})
        import tinker
        from tinker_cookbook import model_info,renderers
        from tinker_cookbook.recipes.decisions import DecisionRenderer
        self.service=tinker.ServiceClient(display_name=self.run_id)
        self.sampler=await self.service.create_sampling_client_async(base_model='Qwen/Qwen3.5-4B')
        self.renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),self.sampler.get_tokenizer()))

    async def write(self,role,content,private=False):
        rid=self.run_id+'-r'+str(len(self.records));at=now();started=time.perf_counter()
        value={'record_id':rid,'author':self.actors[role],'occurred_at':at,'content':content}
        text=f'Mochi desk {role} record {rid}. Canonical SHA256 {digest(value)}. '+json.dumps(content,sort_keys=True)
        x=await self.request('POST','/ingest',{'id':rid,'identity':self.actors[role],'audience':self.private if private else self.audience,'timestamp':at,'label':f'Mochi desk {content.get("kind","finding")}','content':text})
        for attempt in range(150):
            status=await self.request('GET','/ingest/'+x['ingestionId'])
            if status.get('status')=='completed':break
            if status.get('status')=='failed':raise RuntimeError('Memory ingestion failed')
            if attempt%20==19:print('MEMORY_WAIT',rid,round(time.perf_counter()-started),flush=True)
            await asyncio.sleep(2)
        else:raise TimeoutError('Memory ingestion exceeded five minutes')
        self.records[rid]={'id':rid,'role':role,'author':self.actors[role],'audience':self.private if private else self.audience,'at':at,'sha256':digest(value),'ingestion_id':x['ingestionId'],'write_to_ready_seconds':time.perf_counter()-started,'payload':value}
        return rid

    async def read(self,role,rid,allowed=True):
        wanted=self.records[rid];found=False;reply={}
        for attempt in range(8 if allowed else 1):
            reply=await self.request('POST','/recall',{'identity':self.actors[role],'query':f'Mochi desk {wanted["payload"]["content"].get("kind","")} evidence from {wanted["role"]}, exact record {rid}.','level':'medium','limit':200,'occurredFrom':wanted['at'],'occurredTo':wanted['at']})
            ids={s.get('sourceId') for result in reply.get('results',[]) for s in result.get('sources',[])};found=rid in ids
            if found or not allowed:break
            await asyncio.sleep(2+attempt)
        if not allowed and (found or 'MOCHI_PRIVATE_CANARY' in json.dumps(reply)):raise RuntimeError('Memory ACL failed')
        self.reads.append({'reader':self.actors[role],'reader_role':role,'author':wanted['author'],'record_id':rid,'source_id_verified':found,'expected_access':allowed,'cross_agent_use':found and self.actors[role]!=wanted['author'],'sha256':wanted['sha256'] if found else None,'at':now()})
        if allowed and not found:raise RuntimeError('Required memory source absent; no silent fallback')
        return wanted['payload']['content'] if found else {'access':'denied-as-expected'}
