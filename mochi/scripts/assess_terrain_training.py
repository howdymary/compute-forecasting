"""Assess a completed physical campaign without training or changing any result."""
import argparse,json,math
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1]

def initial_frame_delta(a,b):
    if isinstance(a,dict):
        assert a.keys()==b.keys()
        return max((initial_frame_delta(a[k],b[k]) for k in a),default=0.)
    if isinstance(a,list):
        assert len(a)==len(b)
        return max((initial_frame_delta(x,y) for x,y in zip(a,b)),default=0.)
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        assert math.isfinite(a) and math.isfinite(b)
        return abs(a-b)
    assert a==b
    return 0.

def paired_complete(before,after):
    left={r['seed']:r for r in before};right={r['seed']:r for r in after}
    assert left.keys()==right.keys(),'Pair the same physical scenarios'
    result=[]
    for seed,a in sorted(left.items()):
        b=right[seed]
        assert a['episode']['scenario']==b['episode']['scenario'] and a['episode']['scene']==b['episode']['scene']
        assert a['terrain_conditions']==b['terrain_conditions']
        delta=initial_frame_delta(a['episode']['trajectory']['frames'][0],b['episode']['trajectory']['frames'][0])
        assert delta<=1e-12,'Initial physical states differ beyond floating-point tolerance'
        if not(a['complete_sequence_success'] and b['complete_sequence_success']):continue
        x,y=a['episode'],b['episode']
        result.append({'seed':seed,'initial_frame_max_abs_difference':delta,'time_change_s':y['duration']-x['duration'],
            'distance_change_m':y['executed_root_distance_m']-x['executed_root_distance_m'],
            'roll_rms_change_deg':y['balance_metrics']['roll_rms_deg']-x['balance_metrics']['roll_rms_deg'],
            'contact_travel_proxy_change_m':sum(y['foot_slip_estimate_m'].values())-sum(x['foot_slip_estimate_m'].values()),
            'recovery_joint_travel_change_rad':sum(r['arm_joint_travel_rad'] for r in y['recoveries'])-sum(r['arm_joint_travel_rad'] for r in x['recoveries'])})
    return result

def evidence(rows):
    failures=Counter();contacts=Counter();choices=Counter();complete=[];ascent=descent=0
    for row in rows:
        e=row['episode']
        if row['failure']:failures[row['failure']]+=1
        if row['complete_sequence_success']:complete.append(e['duration'])
        for c in e.get('contact_failures',[]):contacts[(c['body'],c['fixture'],c.get('phase','unspecified'))]+=1
        for d in row.get('model_decisions',[]):choices[(d['observation']['domain'],d['action'])]+=1
        ascent+=any(a['label']=='book-ascent' and a['success'] for a in row['arrivals'])
        descent+=any(a['label']=='book-descent' and a['success'] for a in row['arrivals'])
    return {'n':len(rows),'verified_book_ascents':ascent,'verified_book_descents':descent,
        'successful_completion_mean_s':mean(complete) if complete else None,'failures':dict(failures),
        'forbidden_contacts':[{'body':a,'fixture':b,'phase':c,'count':n} for (a,b,c),n in contacts.items()],
        'chosen_controls':[{'domain':d,'action':a,'count':n} for (d,a),n in sorted(choices.items())]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',default=str(ROOT/'docs/terrain-v12-assessment.md'));a=p.parse_args()
    source=Path(a.source);report=json.loads((source/'report.json').read_text())
    assert report['status']=='completed' and report['held_out_opened'],'Wait for completed physical evaluation'
    dev={c['update']:json.loads((source/f"checkpoint-{c['update']}.json").read_text()) for c in report['checkpoints']}
    held={label:json.loads((source/f'held-out-{label}.json').read_text()) for label in ['parent','selected','fixed']}
    paired=paired_complete(held['parent'],held['selected'])
    audit={'study':report['study'],'training_run':report['run_id'],'source_sha':report['source_sha'],
        'evaluation_recovery':report.get('recovery'),'optimizer_updates_completed':report['optimizer_updates_completed'],
        'selected_checkpoint':report['selected_checkpoint'],'development':{k:evidence(v) for k,v in dev.items()},
        'held_out':{k:evidence(v) for k,v in held.items()},'paired_successful_completions':paired,
        'domain_interventions':report.get('isolated'),'scope':report['scope'],
        'initial_state_float_tolerance':1e-12,
        'limits':['Small simulated cohorts; keep development separate from final tests.',
                  'Paired timing and movement changes exclude cases where either run fails.',
                  'Domain interventions are whole routes, not exact matched-pose manipulation tests.',
                  'Tinker updates decision weights; native gait and physical controllers stay fixed.']}
    data=ROOT/'artifacts/terrain-v12-assessment/final.json';data.parent.mkdir(parents=True,exist_ok=True)
    data.write_text(json.dumps(audit,indent=2)+'\n')
    lines=['# V12 completed-training assessment','',f"Tinker completed {report['optimizer_updates_completed']} new optimizer updates. Development selection chose update {report['selected_checkpoint']['update']}. Native gait weights stayed fixed.",'',
           '| Development checkpoint | Complete | Within smoothness limits | Successful completion time |',
           '|---|---:|---:|---:|']
    for c in report['checkpoints']:
        e=audit['development'][c['update']];t=e['successful_completion_mean_s'];s=c['development']
        lines.append(f"| {c['update']} | {s['complete_successes']}/{s['n']} | {s['smooth_complete_successes']}/{s['n']} | {t:.2f} s |" if t is not None else f"| {c['update']} | 0/{s['n']} | 0/{s['n']} | No complete sequence |")
    lines+=['','| Final test policy | Complete | Within smoothness limits | Verified book ascent / descent |','|---|---:|---:|---:|']
    for name,s in report['held_out'].items():
        e=audit['held_out'][name]
        lines.append(f"| {name} | {s['complete_successes']}/{s['n']} | {s['smooth_complete_successes']}/{s['n']} | {e['verified_book_ascents']}/{e['n']} · {e['verified_book_descents']}/{e['n']} |")
    lines+=['',f'Paired timing and movement comparisons use {len(paired)} final scenarios where both policies complete. Earlier failures are not counted as faster completions.']
    if paired:
        lines.append(f"Mean selected-minus-parent differences: {mean(x['time_change_s'] for x in paired):+.2f} s completion time; {mean(x['roll_rms_change_deg'] for x in paired):+.3f}° torso-roll RMS; {mean(x['recovery_joint_travel_change_rad'] for x in paired):+.3f} rad recovery joint travel.")
    lines+=['','Remaining observed failures:']
    for name,e in audit['held_out'].items():
        lines.append(f"- {name}: "+(', '.join(f'{k} × {n}' for k,n in e['failures'].items()) or 'none in this cohort')+'.')
        for c in e['forbidden_contacts']:lines.append(f"  Contact: {c['body']} with {c['fixture']} during {c['phase']} ({c['count']}).")
    lines+=['','The full-route domain interventions help identify which decision domain changes an outcome. They do not establish a matched-pose recovery or manipulation effect.','',*audit['limits'],'',f"[Training receipts](https://github.com/howdymary/mochi-demo/actions/runs/{report['run_id'].split('-')[-1]}) · [Evaluation receipts](https://github.com/howdymary/mochi-demo/actions/runs/{report.get('recovery',{}).get('evaluation_run','')})"]
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(lines)+'\n')
    out.with_suffix('.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({'assessment':str(out),'numerical_audit':str(data),'paired_successes':len(paired),'selected_update':report['selected_checkpoint']['update']}))

if __name__=='__main__':main()
