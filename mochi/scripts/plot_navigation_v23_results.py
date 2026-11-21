"""Descriptive research figure from the completed paired cohort."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/navigation-v23/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p = json.loads((ROOT / 'evidence/navigation-v23/results.json').read_text())
assert p['status'] == 'completed'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.facecolor': '#f3f1e9', 'figure.facecolor': '#f3f1e9',
    'text.color': '#253b36', 'axes.labelcolor': '#253b36', 'xtick.color': '#253b36', 'ytick.color': '#253b36'})
fig, ax = plt.subplots(1, 3, figsize=(14, 4.6), constrained_layout=True)
names, keys = ['Parent', 'Selected', 'Planner', 'Tuner', 'Fixed'], ['parent', 'selected', 'planner', 'conventional', 'fixed']
values = [p['final_summaries'][k]['qualified'] for k in keys]
ax[0].bar(names, values, color=['#89958e', '#36746c', '#a2a88c', '#a2a88c', '#b26f47'])
ax[0].set(ylim=(0, 18), ylabel='Qualified attempts out of 16', title='First attempts: eight unseen layouts')
for i, value in enumerate(values):
    ax[0].text(i, value + .35, str(value), ha='center')
ax[0].tick_params(axis='x', rotation=25)
a, b = p['final']['parent'], p['final']['selected']
qualified = [(i+1, y['steps']['attempts'] - x['steps']['attempts']) for i, (x, y) in enumerate(zip(a, b)) if x['qualified'] and y['qualified']]
excluded = [i+1 for i, (x, y) in enumerate(zip(a, b)) if not (x['qualified'] and y['qualified'])]
ax[1].axhline(0, color='#89958e', linewidth=1)
ax[1].scatter([x for x, _ in qualified], [y for _, y in qualified], color='#36746c', zorder=3)
for i, index in enumerate(excluded):
    ax[1].axvspan(index-.3, index+.3, color='#b26f47', alpha=.18,
        label='Quality failure; excluded' if i == 0 else None)
ax[1].set(xlim=(0, 17), xlabel='Paired attempt (two seeds per layout)', ylabel='Selected minus parent steps', title='One changed choice drives the reduction')
ax[1].legend(loc='lower left', frameon=False, fontsize=8)
labels = ['Parent\nno retrieval', 'Parent\nretrieval', 'Selected\nno retrieval', 'Selected\nretrieval']
keys = ['parent_no_memory', 'parent_memory', 'selected_no_memory', 'selected_memory']
values = [p['adaptation_summary'][k]['success_within_three'] for k in keys]
ax[2].bar(labels, values, color=['#89958e', '#89958e', '#36746c', '#36746c'])
ax[2].set(ylim=(0, 9.5), ylabel='Successful layouts out of 8', title='Success within three attempts')
for i, value in enumerate(values):
    ax[2].text(i, value + .2, str(value), ha='center')
fig.suptitle('MOCHI: post-training a navigation selector, with a fixed native gait', fontsize=14, fontweight='bold')
fig.supxlabel('Descriptive counts. Layouts are the experimental units. Conditional efficiency excludes quality failures; paired uncertainty is in the numerical audit.', fontsize=9)
out = ROOT / 'evidence/navigation-v23'
fig.savefig(out / 'results-figure.png', dpi=180)
print('Wrote research figure from completed evidence.')
