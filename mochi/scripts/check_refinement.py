"""Verify published claims against actual gradient and physical decision records."""
import argparse,json,math
from pathlib import Path
from mochi.curriculum.features import encode
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--development-only',action='store_true');a=p.parse_args();root=a.source
report=json.loads((root/('incomplete.json' if a.development_only else 'report.json')).read_text());log=report['training_log'];n=report['optimizer_updates_completed'];domains={'walk','alarm','drawer','laptop','globe'}
assert a.development_only or report['status']=='completed'
assert len(log)==n and [r['update'] for r in log]==list(range(1,n+1))
assert all(r['forward_backward_completed'] and r['optimizer_completed'] and set(r['domain_counts'])==domains and set(r['domain_loss_metrics'])==domains for r in log)
assert report['selected_checkpoint']['update']==n
checks={'completed_optimizer_updates':n,'completed_domain_gradient_calls':len(domains)*n,'domain_examples_including_repeats':{d:sum(r['domain_counts'][d] for r in log) for d in sorted(domains)},'checkpoint_ids':[r['checkpoint_id'] for r in report['checkpoints']],'decision_distributions_checked':0,'paired_initial_states_checked':0}
def verify(row):
 decisions=row['model_decisions']
 assert row['actions']==[d['action'] for d in decisions]
 assert row['actions']==[d['action'] for d in row['episode']['decisions']]
 for d in decisions:
  if d['distribution'] is None:continue
  assert encode(d['observation'])==d['model_observation']
  assert d['action']==max(d['distribution'],key=d['distribution'].get)
  assert all(math.isfinite(v) and v>=0 for v in d['distribution'].values())
  checks['decision_distributions_checked']+=1
 assert row['episode']['maximum_applied_base_force']==0
for cp in report['checkpoints']:
 for bundle in json.loads((root/f"checkpoint-receipts-{cp['update']}.json").read_text()):verify(bundle['results']['policy'])
for filename in ([] if a.development_only else ['paired-held-out-routes.json','paired-held-out-navigation.json']):
 for bundle in json.loads((root/filename).read_text()):
  assert bundle['receipt']['provider']=='Modal' and bundle['receipt']['paired_on_one_worker']
  results=bundle['results'];before=results['starting_model'];after=results['post_trained_model'];verify(before);verify(after)
  assert before['episode']['scenario']==after['episode']['scenario']
  frames=[r['episode']['trajectory']['frames'] for r in [before,after]]
  if all(frames):
   assert frames[0][0]==frames[1][0];checks['paired_initial_states_checked']+=1
reads=report['services']['reads'];assert sum(r['cross_agent_use'] and r['source_id_verified'] for r in reads)>0
assert report['services']['eligibility']['isolation_passed']
checks['verified_cross_role_recalls']=sum(r['cross_agent_use'] and r['source_id_verified'] for r in reads)
checks['held_out_scenarios']=report['protocol']['held_out_seeds'];checks['physics_hashes']=report['protocol']['frozen_physics_sha256'];checks['status']='passed';checks['scope']='Development evidence only' if a.development_only else 'Completed training and final held-out evaluation'
(root/('development-provenance-checks.json' if a.development_only else 'provenance-checks.json')).write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
