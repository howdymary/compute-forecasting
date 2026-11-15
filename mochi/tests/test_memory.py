import asyncio
from mochi.integrations import Services

def test_memory_cannot_silently_fallback_or_leak_private_canary():
    async def exercise():
        s=Services()
        s.records['r1']={'author':s.actors['researcher'],'sha256':'abc','payload':{'content':{'gain':.5}}}
        async def allowed(method,path,payload):
            assert payload['identity']==s.actors['designer']
            return {'results':[{'sources':[{'sourceId':'r1'}]}]}
        s.request=allowed
        assert await s.read('designer','r1')=={'gain':.5}
        assert s.reads[-1]['cross_agent_use']
        async def denied(method,path,payload):return {'results':[]}
        s.request=denied
        assert await s.read('designer','r1',allowed=False)=={'access':'denied-as-expected'}
        async def leaked(method,path,payload):return {'results':[{'content':'MOCHI_PRIVATE_CANARY'}]}
        s.request=leaked
        try:await s.read('designer','r1',allowed=False)
        except RuntimeError:pass
        else:raise AssertionError('Private content leakage must fail')
        await s.http.aclose()
    asyncio.run(exercise())
