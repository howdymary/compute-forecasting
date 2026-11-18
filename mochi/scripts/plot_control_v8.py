"""Plot measured development outcomes, including regressions."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);a=p.parse_args();r=json.load(open(a.source/'report.json'));cps=r['checkpoints'];x=[c['update'] for c in cps];fig,ax=plt.subplots(figsize=(10,3.5));fig.patch.set_facecolor('#f6f3ed');ax.set_facecolor('#f6f3ed')
for label,color,fn in [('Walking arrivals','#367a7d',lambda s:s['stations_reached']/s['station_opportunities']),('Task checks','#b57555',lambda s:sum(s['task_successes'].values())/(s['n']*4)),('Safe arm recoveries','#76788a',lambda s:s['recovery_successes']/(s['n']*4)),('Complete sequences','#303e35',lambda s:s['full_successes']/s['n'])]:ax.plot(x,[100*fn(c['continuous_development']) for c in cps],label=label,color=color,marker='o',markersize=4,linewidth=1.8)
ax.axvline(r['selected_checkpoint']['update'],color='#b57555',linestyle=':',linewidth=1,label='Development-selected checkpoint');ax.set(xticks=x,ylim=(-4,104),yticks=[0,25,50,75,100],xlabel='Additional Tinker optimizer updates after parent 96',ylabel='Opportunities passed (%)');ax.spines[['top','right']].set_visible(False);ax.spines[['bottom','left']].set_color('#bbb5aa');ax.tick_params(colors='#4a514c');ax.grid(axis='y',color='#ded9cf',linewidth=.6);ax.legend(loc='upper center',bbox_to_anchor=(.5,1.25),ncol=3,frameon=False,fontsize=8);fig.tight_layout();out=Path('mochi/web/desk/curriculum/v8-checkpoint-results.svg');fig.savefig(out,format='svg',metadata={'Date':None});out.write_text('\n'.join(line.rstrip() for line in out.read_text().splitlines())+'\n')
