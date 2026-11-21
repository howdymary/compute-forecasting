"""Read compact campaign progress without exposing credentials or model paths."""
import argparse
import json
from pathlib import Path

import modal


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', default='mochi-p19-44839589468')
    p.add_argument('--progress-dict', default='mochi-paperfree-v19-progress')
    p.add_argument('--save', help='Backend/local report destination, not a frontend asset')
    a = p.parse_args()
    try:
        r = modal.Dict.from_name(a.progress_dict).get(a.run)
    except modal.exception.NotFoundError:
        print(json.dumps({'run_id': a.run, 'status': 'coordinator-not-started'}))
        return
    if r is None:
        print(json.dumps({'run_id': a.run, 'status': 'coordinator-not-started'}))
        return
    if a.save:
        target = Path(a.save)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(r, indent=2) + '\n')
    visible = {k: r.get(k) for k in ['run_id', 'status', 'phase', 'optimizer_updates_completed',
        'campaign_modal_rollouts_completed', 'held_out_opened', 'error_type', 'error', 'budget_usage_or_reserved']}
    visible['preflight_qualified'] = r.get('preflight', {}).get('qualified_complete')
    visible['checkpoints'] = [{'update': c['update'], 'development': c['development']} for c in r['checkpoints']]
    if r.get('held_out'):
        visible.update(held_out=r['held_out'], paired_held_out=r['paired_held_out'],
            selected_update=r['selected_checkpoint']['update'], goal_met=r['improvement_goal_met'])
    print(json.dumps(visible))


if __name__ == '__main__':
    main()
