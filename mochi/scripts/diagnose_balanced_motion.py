"""Analyze retained measurements without executing or modifying a rollout."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    audit = json.loads((ROOT/'evidence/balance-v11/reference-audit.json').read_text())
    first_contact = min(v['first_t'] for v in audit['contacts'].values())
    cases = [('frozen-interface-reference-0', .055, first_contact),
             ('modal-clearance-0', .045, None),
             ('modal-clearance-2', .05, None)]
    report = {'study': 'mochi-balanced-v11', 'mode': 'recorded-measurement analysis',
              'new_rollouts': 0, 'optimizer_updates': 0, 'cases': [],
              'interpretation': 'Forward COM speed rises sharply at the book approach before clock contact. Lower nominal speed and removing velocity feedback did not establish a valid climb. This identifies a control failure, not its complete causal mechanism.',
              'next_gate': 'A terrain-capable actuator controller must demonstrate repeated unassisted ascent, descent, supported station stops and fixture-safe recovery before controller-selector training.'}
    traces = []
    for ident, speed, contact in cases:
        path = ROOT/'artifacts/balance-v11'/f'{ident}.json'
        raw = path.read_bytes(); run = json.loads(raw); episode = run['episode']
        contacts = episode.get('contact_failures', [])
        contact = contact or (contacts[0]['t'] if contacts else episode['duration'])
        rows = [r for r in episode['balance_measurements'] if .4 <= r['t'] <= min(contact, 5.)]
        t = np.array([r['t'] for r in rows])
        forward = np.array([np.dot(r['support']['com_velocity_m_s'][:2],
                                  [np.cos(r['path_heading']), np.sin(r['path_heading'])]) for r in rows])
        load = np.array([sum(r['loads_n'].values()) for r in rows])
        peak = int(np.argmax(forward))
        airborne = [r['t'] for r in rows if max(r['loads_n'].values()) <= .05]
        report['cases'].append({'id': ident, 'source_sha256': hashlib.sha256(raw).hexdigest(),
                                'nominal_route_speed_m_s': speed,
                                'peak_recorded_path_forward_com_speed_m_s': float(forward[peak]),
                                'peak_time_s': float(t[peak]),
                                'clock_contact_or_end_s': contact,
                                'samples_without_loaded_foot_support': len(airborne),
                                'first_sample_without_loaded_foot_support_s': airborne[0] if airborne else None,
                                'recorded_duration_s': episode['duration'],
                                'failure': run.get('failure'),
                                'scope': 'Samples after initial 0.4-second settling through first clock contact or episode end, capped at five seconds; nominal route speed differs from the feedback-filtered command. Samples are not continuous support-duration measurements.'})
        traces.append((ident, t, forward, load, contact, speed))
    evidence = ROOT/'evidence/balance-v11'; public = ROOT/'web/desk/balanced-v11'
    for folder in [evidence, public]:
        (folder/'dynamics-diagnosis.json').write_text(json.dumps(report, indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams['svg.hashsalt'] = 'mochi-balanced-v11'
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for ax in axes:
        ax.grid(alpha=.2); ax.spines[['top', 'right']].set_visible(False)
    colors = ['#ab503f', '#287b85', '#6b6584']
    labels = ['Rejected reference', 'Lower nominal speed', 'Velocity feedback removed']
    for (_, t, velocity, load, contact, speed), color, label in zip(traces, colors, labels):
        axes[0].plot(t, velocity, color=color, label=label)
        axes[0].axhline(speed, color=color, ls=':', alpha=.35)
        axes[1].plot(t, load, color=color)
    axes[0].axvline(first_contact, color='#ab503f', ls='--', alpha=.6)
    axes[0].annotate('First clock contact in rejected reference', xy=(first_contact, .03),
                     xycoords=('data', 'axes fraction'), xytext=(8, 20), textcoords='offset points', fontsize=9)
    axes[0].set_ylabel('Forward COM velocity (m/s)')
    axes[0].legend(loc='upper left', fontsize=9)
    axes[1].set_ylabel('Total loaded-foot force (N)'); axes[1].set_xlabel('Physical time (s)')
    fig.suptitle('The book approach loses control before the clock catches the robot', x=.09, ha='left')
    fig.text(.09, .01, 'Recorded simulation measurements. Dotted lines: nominal route speeds. Failed runs end at their actual stopping time.', fontsize=8)
    fig.tight_layout(rect=[0, .04, 1, .95])
    svg = public/'dynamics-diagnosis.svg'
    fig.savefig(svg, metadata={'Date': None})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    fig.savefig(ROOT/'artifacts/balance-v11/dynamics-diagnosis.png', dpi=130)
    plt.close(fig)
    print(json.dumps({'new_rollouts': 0, 'cases': report['cases']}))


if __name__ == '__main__':
    main()
