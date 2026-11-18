"""Isolated reach/contact feasibility before freezing manipulation approaches."""
import asyncio,json,os
from pathlib import Path
from .remote import app,contact
from ..curriculum.world import STATIONS
ROOT=Path(__file__).resolve().parents[3]
async def main():
 out=ROOT/'artifacts/planning';out.mkdir(parents=True,exist_ok=True)
 cfg=json.loads((ROOT/'configs/planning-calibration.json').read_text())
 jobs=[(seed,'laptop',code,list(pose) if len(pose)==3 else [*pose,STATIONS['laptop'][2]]) for seed in cfg['seeds'] for pose in cfg['laptop_poses'] for code in cfg['profiles']] if 'laptop_poses' in cfg else [(seed,t,code,(-.375,y,STATIONS[t][2]) if t=='alarm' else STATIONS[t]) for seed in [19000,19001] for t in ['alarm','laptop'] for y in ([.015,.025] if t=='alarm' else [0]) for code in 'ABCDEFGH']
 async with app.run():rows=[r async for r in contact.starmap.aio(jobs,order_outputs=True)]
 report={'phase':cfg['phase']+'; training-scenario isolated contact calibration, not held-out evaluation','source_sha':os.getenv('GITHUB_SHA'),'rollouts':len(rows),'optimizer_updates':0,'rows':rows};(out/'contact-calibration.json').write_text(json.dumps(report,indent=2))
 for t in sorted({r['task'] for r in rows}):
  for pose in sorted({tuple(r['pose']) for r in rows if r['task']==t}):
   print(t,pose,{code:sum(r['result']['success'] for r in rows if r['task']==t and tuple(r['pose'])==pose and r['result']['profile']['code']==code) for code in cfg.get('profiles','ABCDEFGH')},flush=True)
 print('ACTUAL_MODAL_ROLLOUTS',len(rows),'TINKER_UPDATES',0)
if __name__=='__main__':asyncio.run(main())
