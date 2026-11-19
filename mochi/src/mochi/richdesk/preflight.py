"""Fail closed before any furnished-desk optimizer campaign."""
import json
from .world import ROOT


def training_readiness():
    cfg=json.loads((ROOT/'configs/richdesk-campaign.json').read_text())
    proof=ROOT/'artifacts/richdesk-v10/reference-sequence.json'
    result={'study':cfg['study'],'optimizer_updates_authorized_now':False,
        'configured_gate_open':cfg['training_gate']['open'],'physical_sequence_record_present':proof.exists(),
        'required':cfg['training_gate']['requires_all'],'reasons':[]}
    if not proof.exists():result['reasons'].append('No verified continuous physical ascent/descent and four-task reference sequence')
    else:
        row=json.loads(proof.read_text())
        required=['geometry_route_valid','book_ascent_verified','book_descent_verified',
                  'four_tasks_verified','all_recoveries_verified','reward_diversity_verified','frozen_hashes_verified']
        for name in required:
            if row.get(name) is not True:result['reasons'].append('Unverified: '+name)
        if row.get('maximum_applied_base_force')!=0:result['reasons'].append('Nonzero or unrecorded applied base force')
        if not row.get('source_physics_trajectory'):result['reasons'].append('No exact physical trajectory provenance')
    if not result['configured_gate_open']:result['reasons'].append('Configured training gate is closed')
    result['optimizer_updates_authorized_now']=not result['reasons']
    return result


if __name__=='__main__':
    r=training_readiness();print(json.dumps(r,indent=2))
    raise SystemExit(0 if r['optimizer_updates_authorized_now'] else 2)
