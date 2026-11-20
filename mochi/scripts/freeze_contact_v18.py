"""Account for completed engineering and freeze the next bounded campaign."""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

old=json.loads((ROOT/'configs/smooth-v17-training.json').read_text())
unchanged={**old['frozen_sha256'],**old['continuation_frozen_sha256']}
for path,h in unchanged.items():assert sha(ROOT/path)==h,'Archived physics changed: '+path
attempts=[];examples=[]
for path in sorted((ROOT/'artifacts/contact-v18-engineering').glob('*.json')):
    data=json.loads(path.read_text());assert data['status']=='completed','Unfinished attempt: '+path.name
    result=data.get('result') or {};recovery=data.get('recovery') or data.get('coupled_recovery') or {}
    attempts.append({'id':path.stem,'physical_attempts':data['physical_attempts'],
       'wall_seconds':data['wall_seconds'],'sha256':sha(path),'parameters':data.get('parameters'),
       'failure':data.get('failure'),'fall':data.get('fall'),'invalid_contact':data.get('invalid_contact'),
       'success':data.get('success',result.get('success')),'recovery_success':recovery.get('success'),
       'initial_state_sha256':data.get('initial_state_sha256',(data.get('initial') or {}).get('physical_hash')),
       'max_force_n':result.get('max_force_n'),'steps':data.get('steps'),
       'duration_s':data.get('duration_s'),'clearance':data.get('clearance')})
    if path.stem in ['production-103000','production-103001','production-old-training']:
        assert data['valid_branch'] and data['maximum_applied_base_force']==0
        examples.append({'domain':'laptop','task':'laptop','observation':data['observation'],
            'action':data['action'],'initial_state_sha256':data['initial_state_sha256'],
            'evidence_id':path.stem,'evidence_sha256':sha(path)})
assert len(examples)==3
count=sum(r['physical_attempts'] for r in attempts)
seconds=sum(r['wall_seconds'] for r in attempts)
evidence={'study':'mochi-contact-v18-engineering','attempts':attempts,'physical_attempts':count,
    'completed_attempts':count,'measured_wall_seconds':seconds,'local_import_bound_seconds':15*count,
    'accounted_cpu_hours':(seconds+15*count)/3600,
    'scope':'Engineering and regression diagnostics, not neural training. Every attempted call retained. CPU accounting includes a conservative local Python import bound; not an invoice.',
    'accepted':'P5 force scheduling on high-angle regression; P6 pulsed contact on lower-angle regressions; W8 smoothed contact-gated lift using the W5/W6 path.',
    'walking_caveat':'Higher clearance increased steps and time in the isolated matched corridor. The joint target remains unestablished. Faster approach variant exceeded the acceleration limit and was rejected.'}
out=ROOT/'evidence/contact-v18';out.mkdir(parents=True,exist_ok=True)
(out/'engineering.json').write_text(json.dumps(evidence,indent=2)+'\n')
frozen=dict(unchanged)
for path in sorted((ROOT/'src/mochi/contact_v18').glob('*.py')):frozen[str(path.relative_to(ROOT))]=sha(path)
cfg={k:old[k] for k in ['smoothness','objective','selection_without_qualified_parent','scene_revision']}
cfg.update({'study':'mochi-contact-v18','implementation_prompt':'docs/contact-v18-prompt.md',
 'prompt_sha256':sha(ROOT/'docs/contact-v18-prompt.md'),'preflight_seed':184002,
 'training_seeds':[184000,184001],'development_seeds':[185000,185001,185002],
 'held_out_seeds':[186000,186001,186002,186003],
 'bounds':{'modal_concurrency':4,'physical_rollouts':160,'simulation_cpu_hours':14,'optimizer_updates':16,
    'training_token_presentations':1000000,'inference_tokens':900000,'exa_searches':2,'past_writes':10,'past_recalls':12},
 'engineering_usage':{'physical_rollouts':count,'simulation_cpu_hours':evidence['accounted_cpu_hours']},
 'engineering_evidence':{'path':'evidence/contact-v18/engineering.json','sha256':sha(out/'engineering.json'),
    'production_validations':[e['evidence_id'] for e in examples]},
 'engineering_training_examples':examples,'training':{'updates':16,'checkpoints':[0,1,4,8,16],
    'learning_rate':.0001,'seed':201118,'domains':['walk','alarm','drawer','laptop','globe','recovery']},
 'frozen_sha256':frozen,
 'scope':'Tinker updates six-domain Qwen3.5-4B LoRA controller-selection weights. Native ONNX weights remain fixed. All checkpoints and controls share the frozen laptop force/pulse library and measured swing-clearance option. Root/feet move only through forces and contacts. Fresh tests are uninterrupted from reset; previous 103xxx cases are training/regression evidence.',
 'walking_goal':{'moving_median_minimum_sole_clearance_m':.0045,
    'measurement':'Minimum physical collision-pad height above local terrain while opposite foot carries load. Moving/turning swings and station alignment reported separately; all steps counted.',
    'trajectory_sampling':'Target 100 Hz on flat transit / 25 Hz elsewhere; variable actual timestamps.'}})
assert count+2*35+15+16+1<=160,'Insufficient full campaign headroom'
(ROOT/'configs/contact-v18-training.json').write_text(json.dumps(cfg,indent=2)+'\n')
print(json.dumps({'engineering_attempts':count,'accounted_cpu_hours':evidence['accounted_cpu_hours'],'frozen_files':len(frozen),
    'maximum_planned_physical_attempts':count+2*35+15+16+1,'training_examples':len(examples)}))
