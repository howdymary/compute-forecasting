"""Publish complete engineering recordings without calling them checkpoints."""
import argparse,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'web/desk/balanced-v11'
EVIDENCE=ROOT/'evidence/balance-v11'

def rounded(value):
    if isinstance(value,float):return round(value,6)
    if isinstance(value,list):return [rounded(x) for x in value]
    if isinstance(value,dict):return {k:rounded(v) for k,v in value.items()}
    return value

def main():
    p=argparse.ArgumentParser();p.add_argument('--latest');a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);EVIDENCE.mkdir(parents=True,exist_ok=True)
    chosen=[('baseline-sway-0','Original support transfers'),
            ('hub-brake-hold-1','Book-top pose; fixture clearance unaudited'),
            ('reference-stop-diagnostic-0','Alarm and descent; fixture clearance unaudited'),
            ('reference-native-stop-0','Supported stop; rejected task drift')]
    if a.latest:chosen.append((a.latest,'Latest engineering attempt'))
    for i in range(4):
        ident='modal-clearance-'+str(i)
        if (ROOT/'artifacts/balance-v11'/f'{ident}.json').exists():chosen.append((ident,'Strict clearance trial '+str(i+1)))
    manifest={'study':'mochi-balanced-v11','optimizer_updates_completed':0,
              'training_gate_open':False,'scope':'Engineering revisions; walking clock contacts invalidate the legacy full-task reference. Zero new optimizer updates.',
              'scene':json.loads((ROOT/'configs/richdesk-v9.json').read_text()),'attempts':[]}
    for ident,label in chosen:
        path=ROOT/'artifacts/balance-v11'/f'{ident}.json';raw=path.read_bytes();row=json.loads(raw)
        e=row['episode'];r=row.get('result',row)
        clip={k:e[k] for k in ['scenario','events','results','fall','invalid_contact','duration',
                              'maximum_applied_base_force','balance_metrics','trajectory','scene','final_object_states','final_object_speeds'] if k in e}
        clip['balance_measurements']=[{k:v for k,v in m.items() if k in ['t','phase','gait_phase','root','lateral_m','roll_rad','loads_n']} for m in e.get('balance_measurements',[])]
        clip['recoveries']=e.get('recoveries',[])
        clip['recording_note']='Complete 25 Hz body-transform recording; six-decimal display quantization, without a motion-stabilization filter. Full numerical original retained in artifacts.'
        (OUT/f'{ident}.json').write_text(json.dumps(rounded(clip),separators=(',',':')))
        arrivals=r.get('arrivals',[])
        entry={'id':ident,'label':label,'file':ident+'.json','duration':e['duration'],
               'failure':r.get('failure'),'fall':e['fall'],'invalid_contact':e.get('invalid_contact',False),
               'verified_ascent':r.get('book_ascent_verified',False) or any(x.get('book_top',{}).get('instant_valid',False) for x in arrivals if x.get('book_top')),
               'verified_descent':any(x['success'] and x['label']=='descend-supported-stop' for x in arrivals),
               'task_results':{t:v['success'] for t,v in e['results'].items()},
               'full_sequence_success':r.get('complete_sequence_success',False),
               'metrics':e['balance_metrics'],'arrivals':arrivals,'source_artifact_sha256':hashlib.sha256(raw).hexdigest(),
               'source_hashes':r.get('sources',{}),'contact_failures':e.get('contact_failures',[]),'optimizer_updates_completed':0}
        entry['fixture_audit_status']='enforced-at-runtime' if ident.startswith('modal-clearance-') else 'not-established'
        if entry['contact_failures']:
            entry['failure']='Rejected: '+str(entry['contact_failures'][0]['fixture'])+' contact'
        manifest['attempts'].append(entry)
    for entry in manifest['attempts']:
        if entry['id']=='frozen-interface-reference-0':
            entry['legacy_complete_sequence_success']=entry['full_sequence_success']
            entry['legacy_verified_ascent']=entry['verified_ascent']
            entry.update(label='Rejected reference: clock contacts',full_sequence_success=False,
                         verified_ascent=False,fixture_audit_status='rejected',
                         failure='Rejected: unintended clock support while walking',audit='reference-audit.json')
            entry['audit_contacts']=json.loads((EVIDENCE/'reference-audit.json').read_text())['contacts']
    manifest['default_attempt']=a.latest or chosen[-2][0]
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    ledger=json.loads((ROOT/'artifacts/balance-v11/ledger.json').read_text())
    (EVIDENCE/'calibration-index.json').write_text(json.dumps(ledger,indent=2)+'\n')
    print(json.dumps({'recordings':len(chosen),'largest_mb':max(p.stat().st_size for p in OUT.glob('*.json'))/1e6,'local_attempts':ledger['local_rollouts']}))

if __name__=='__main__':main()
