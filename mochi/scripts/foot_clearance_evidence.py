"""Describe the first desk-walking leg using recorded contact measurements."""
from statistics import median


def after_descent_clearance(episode):
    events=episode.get('events',[])
    start=next((e for e in events if e.get('label')=='forward-descent-exit-stance' and e.get('success')),None)
    if start is None:
        return {'descent_exit_reached':False,'completed_leg':False,'moving_swings':0,'median_peak_m':None}
    end=next((e for e in events if e.get('label')=='drawer-station' and e.get('success') and e['t']>=start['t']),None)
    stop=end['t'] if end else episode['duration']
    swings=[s for s in episode.get('flat_foot_clearance',{}).get('swings',[])
            if s.get('category') in ['flat_transit','turning','fixture_clearance'] and start['t']<=s['start_t']<=stop]
    return {'descent_exit_reached':True,'completed_leg':end is not None,'moving_swings':len(swings),
            'median_peak_m':median(s['peak_minimum_sole_clearance_m'] for s in swings) if swings else None,
            'start_t':start['t'],'end_t':stop,
            'scope':'Descriptive first-leg diagnostic added for the post-descent walking question; not a checkpoint-selection or joint-goal criterion. Partial legs remain labelled incomplete.'}
