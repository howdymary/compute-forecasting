"""Thin HTTP/Tinker adapters following the parent repo's verified v5 patterns.

No import-time network calls; all actors, audiences and receipts belong to Mochi.
"""
import asyncio,hashlib,json,os,time,uuid
from datetime import datetime,timezone
import httpx

def now():return datetime.now(timezone.utc).isoformat()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

class Services:
    def __init__(self):
        self.run_id='mochi-'+uuid.uuid4().hex[:12]
        self.actors={role:self.run_id+'-'+role for role in ['researcher','designer','experimenter','critic']}
        self.audience=self.run_id+'-shared';self.private=self.run_id+'-private'
        self.calls=[];self.records={};self.reads=[];self.decisions=[];self.sources=[]
        self.http=httpx.AsyncClient(timeout=90)

    async def request(self,method,path,payload=None):
        response=await self.http.request(method,'https://api.past.dev/api/v1'+path,headers={'Authorization':'Bearer '+os.environ['PAST_API_KEY']},json=payload)
        self.calls.append({'provider':'past.dev','method':method,'kind':path.split('/')[1],'status':response.status_code,'at':now()})
        # Do not include response bodies or request headers in exceptions/logs.
        if response.is_error:raise RuntimeError(f'past.dev {path.split("/")[1]} HTTP {response.status_code}')
        return response.json()

    async def setup(self):
        for role,actor in self.actors.items():
            await self.request('PUT','/identities/'+actor,{'traits':{'project':'mochi','role':role}})
        for slug,actors in [(self.audience,list(self.actors.values())),(self.private,[self.actors['critic']])]:
            assert len(slug)<=40
            await self.request('PUT','/audiences/'+slug,{'kind':'fixed','name':'Mochi research','identities':actors})
        import tinker
        from tinker_cookbook import model_info,renderers
        from tinker_cookbook.recipes.decisions import DecisionRenderer
        self.service=tinker.ServiceClient(display_name=self.run_id)
        model='Qwen/Qwen3.5-4B'
        self.sampler=await self.service.create_sampling_client(base_model=model)
        self.renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(model),self.sampler.get_tokenizer()))

    async def write(self,role,content,private=False):
        rid=self.run_id+'-record-'+str(len(self.records));at=now();started=time.perf_counter()
        value={'record_id':rid,'author':self.actors[role],'occurred_at':at,'content':content}
        x=await self.request('POST','/ingest',{'id':rid,'identity':self.actors[role],'audience':self.private if private else self.audience,'timestamp':at,'content':json.dumps(value)})
        for _ in range(50):
            status=await self.request('GET','/ingest/'+x['ingestionId'])
            if status.get('status')=='completed':break
            if status.get('status')=='failed':raise RuntimeError('past.dev ingestion failed')
            await asyncio.sleep(1)
        else:raise TimeoutError('past.dev ingestion did not complete within bounded poll')
        self.records[rid]={'id':rid,'role':role,'author':self.actors[role],'audience':self.private if private else self.audience,'at':at,'sha256':digest(value),'ingestion_id':x['ingestionId'],'write_to_ready_seconds':time.perf_counter()-started,'payload':value}
        return rid

    async def read(self,role,rid,allowed=True):
        wanted=self.records[rid];found=False;reply={}
        for attempt in range(5 if allowed else 1):
            reply=await self.request('POST','/recall',{'identity':self.actors[role],'query':rid+' Return the evidence for this exact Mochi experiment record.','level':'medium'})
            ids={s.get('sourceId') for result in reply.get('results',[]) for s in result.get('sources',[])}
            found=rid in ids
            if found or not allowed:break
            await asyncio.sleep(1)
        # Check the canary contents as well as source identity in a denied read.
        if not allowed and (found or 'MOCHI_PRIVATE_CANARY' in json.dumps(reply)):raise RuntimeError('Memory isolation test failed')
        self.reads.append({'reader':self.actors[role],'reader_role':role,'author':wanted['author'],'record_id':rid,'source_id_verified':found,'expected_access':allowed,'cross_agent_use':found and self.actors[role]!=wanted['author'],'sha256':wanted['sha256'] if found else None,'at':now()})
        if allowed and not found:raise RuntimeError('Required source ID was absent from past.dev recall; no silent canonical fallback')
        # Resolve numerical payload by verified source ID, as in parent v5.
        return wanted['payload']['content'] if found else {'access':'denied-as-expected'}

    async def decide(self,role,question,context,choices,input_ids):
        from tinker_cookbook.recipes.decisions import Decision,sample_decision
        prompt=f'You are Mochi\'s {role}. Use supplied evidence and measured limits. Choose one bounded action. Do not invent experiments or claim new trained weights.\n{question}\n'+json.dumps(context,sort_keys=True)
        distribution=await sample_decision(self.sampler,self.renderer.render(Decision(prompt,[(x,x.replace('_',' ')) for x in choices])))
        selected=max(distribution,key=distribution.get)
        self.decisions.append({'role':role,'question':question,'selected':selected,'distribution':distribution,'input_record_ids':input_ids,'context_sha256':digest(context),'at':now()})
        return selected

    async def search(self,query):
        response=await self.http.post('https://api.exa.ai/search',headers={'x-api-key':os.environ['EXA_API_KEY']},json={'query':query,'type':'auto','numResults':3,'contents':{'highlights':True}})
        if response.is_error:raise RuntimeError(f'Exa HTTP {response.status_code}')
        raw=response.json();sources=[{'url':x.get('url'),'title':x.get('title'),'excerpt':' '.join(' '.join(x.get('highlights',[])).split()[:24]),'retrieved_at':now()} for x in raw.get('results',[])]
        if not sources:raise RuntimeError('Exa returned no usable source evidence')
        receipt={'query':query,'request_id':raw.get('requestId'),'cost_dollars':raw.get('costDollars'),'sources':sources,'response_sha256':digest(raw),'at':now()};self.sources.append(receipt);return receipt

    def report(self):
        writers={x['author'] for x in self.records.values()};readers={x['reader'] for x in self.reads if x['source_id_verified']}
        return {'actors':self.actors,'audiences':{'shared':self.audience,'critic_private':self.private},'records':[x for x in self.records.values() if x['audience']!=self.private],'reads':self.reads,'decisions':self.decisions,'calls':self.calls,'sources':self.sources,'eligibility':{'writers':len(writers),'readers':len(readers),'cross_agent_reads':sum(x['cross_agent_use'] for x in self.reads),'isolation_passed':any(not x['expected_access'] and not x['source_id_verified'] for x in self.reads)}}
