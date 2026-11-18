"""Remote authenticated readiness; never logs credential values."""
import asyncio,json,os,time
from pathlib import Path
async def main():
 import tinker
 start=time.perf_counter();client=tinker.ServiceClient(display_name='mochi-curriculum-readiness')
 capabilities=await asyncio.wait_for(client.get_server_capabilities_async(),180)
 names=[m.model_name for m in capabilities.supported_models]
 result={'authenticated':True,'preferred_model':'Qwen/Qwen3.5-4B','preferred_model_available':'Qwen/Qwen3.5-4B' in names,'small_model_candidates':[n for n in names if any(x in n for x in ['4B','8B','Inkling'])],'duration_seconds':time.perf_counter()-start,'credential_names_available':[k for k in ['TINKER_API_KEY','MODAL_TOKEN_ID','MODAL_TOKEN_SECRET','EXA_API_KEY','PAST_API_KEY'] if os.environ.get(k)]}
 out=Path('mochi/artifacts/curriculum');out.mkdir(parents=True,exist_ok=True);(out/'readiness.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
asyncio.run(main())
