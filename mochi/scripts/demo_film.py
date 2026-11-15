"""Two-minute, captioned demo assembled from real Blender frames and run receipts."""
import argparse,json,textwrap
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import imageio.v2 as imageio
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--frames',default='mochi/artifacts');a=p.parse_args();run=Path(a.run);root=Path(a.frames);r=json.loads((run/'report.json').read_text());fps=12.5
fonts='/System/Library/Fonts/Supplemental/'
def font(size,serif=False):
    try:return ImageFont.truetype(fonts+('Georgia.ttf' if serif else 'Arial.ttf'),size)
    except OSError:return ImageFont.load_default(size=size)
F=font(25);S=font(18);H=font(54,True);T=font(88,True)
def text(d,xy,value,fill='#273d35',f=F,width=54):
    y=xy[1]
    for paragraph in str(value).split('\n'):
        for line in textwrap.wrap(paragraph,width=width) or ['']:
            d.text((xy[0],y),line,fill=fill,font=f);y+=f.size*1.35
    return y
base=[Image.open(f).convert('RGB').resize((720,576)) for f in sorted((root/'film-baseline/frames').glob('*.png'))]
best=[Image.open(f).convert('RGB').resize((720,576)) for f in sorted((root/'film-selected/frames').glob('*.png'))]
assert len(base)==75 and len(best)==75,'Complete 6-second / stride-2 Blender clips required'
ev=r['evaluation']['heldout'];sources=(r.get('sources') or []);live=r['mode']=='live-sponsored-research'
chapters=[(0,8,'Meet Mochi','A tiny robot with a scientific method.'),(8,20,'The physical question','Can a supported humanoid push a puck into a target, across varied friction and mass?'),(20,32,'First, a failure','The starting controller makes contact, but often misses the target.'),(32,44,'Then, a measured change','A selected parameterized controller runs on exactly the same development scenario.'),(44,56,'Same seed. Same physics.','A synchronized replay. This illustration is selected on development; final evaluation is separate.'),(56,70,'Research leaves a trail','Failure → Exa evidence → bounded policy-family choice → Modal experiment.'),(70,84,'A shared scientific memory','Researchers, designers, experimenters and critics exchange source-backed records.'),(84,100,'Test beyond the showcase','The policy is frozen before held-out and changed-condition evaluation.'),(100,112,'Show what still breaks','Supported base. State observations. Small samples. Simplified collisions. No walking or sim-to-real claim.'),(112,120,'Small robot. Open notebook.','Read the methods, inspect the receipts, reproduce the experiment.')]
if live:
    shifted=r['evaluation']['changed_conditions']
    chapters[8]=(100,112,'The important failure',f"Higher friction + mass: research-selected {shifted['selected']['successes']}/{shifted['selected']['n']}, conventional control {shifted['random']['successes']}/{shifted['random']['n']}. The gain does not establish robustness.")
with imageio.get_writer(str(run/'demo.mp4'),fps=fps,codec='libx264',quality=8,macro_block_size=1) as writer:
    for i in range(int(120*fps)):
        t=i/fps;start,end,title,caption=next(c for c in chapters if c[0]<=t<c[1]);im=Image.new('RGB',(1280,720),'#f6f4ed');d=ImageDraw.Draw(im)
        d.text((48,30),'MOCHI / ROBOT RESEARCH LAB',font=S,fill='#6f806c');d.text((48,642),f'TRACK 05  /  {int(t):03d}s',font=S,fill='#6f806c');d.line((48,625,1232,625),fill='#d3d9c9',width=1)
        if t<56 or t>=112:
            frame=int(((t-start)%6)*fps)%75
            if 44<=t<56:
                im.paste(base[frame].resize((600,480)),(30,110));im.paste(best[frame].resize((600,480)),(650,110));d.text((60,88),'STARTING POLICY',font=S,fill='#965e4b');d.text((680,88),'SELECTED POLICY',font=S,fill='#66825a');d.text((48,62),title,font=F,fill='#273d35')
            else:
                im.paste((base if 20<=t<32 else best)[frame],(555,48));text(d,(48,140),title,f=H,width=17);text(d,(50,325),caption,f=F,width=29)
            if t>=112:text(d,(50,450),'github.com/howdymary/\ncompute-forecasting/tree/\nmochi-hackathon/mochi',f=S,width=42)
        elif t<70:
            text(d,(48,90),title,f=H);text(d,(50,174),caption,f=F,width=85)
            if live:
                for j,item in enumerate(sources[:2]):
                    y=260+j*140;text(d,(55,y),'SEARCH: '+item['query'],f=S,width=100)
                    source=item['sources'][0];text(d,(55,y+52),source['title'],f=F,width=78);text(d,(55,y+90),source['url'],f=S,width=105)
            else:text(d,(55,280),'Local preview: conventional parameter search. Sponsor calls were not executed in this run.',f=F,width=75)
        elif t<84:
            text(d,(48,90),title,f=H);text(d,(50,174),caption,f=F,width=85)
            reads=r.get('memory',{}).get('reads',[]) if isinstance(r.get('memory'),dict) else []
            for j,item in enumerate([x for x in reads if x['cross_agent_use']][:4]):
                text(d,(60,260+j*65),item['author'].split('-')[-1]+' → '+item['reader_role']+' / '+item['record_id'],f=S,width=100)
            if not reads:text(d,(60,280),'No external memory claims for the local preview. Live reports require verified cross-agent recalls.',f=F,width=75)
        elif t<100:
            text(d,(48,90),title,f=H);text(d,(50,174),caption,f=F,width=85)
            for j,(name,v) in enumerate([(k,ev[k]) for k in ['baseline','selected','random'] if k in ev]):
                y=270+j*95;d.text((60,y),name.upper(),font=S,fill='#6f806c');d.rounded_rectangle((270,y,270+int(760*v['success_rate']),y+37),radius=8,fill='#aac29a' if name=='selected' else '#d3d8c9');d.text((1050,y),f"{v['successes']}/{v['n']}",font=F,fill='#273d35')
            text(d,(60,570),'Small-sample success counts; inspect all trials and uncertainty intervals.',f=S,width=100)
        else:
            text(d,(48,90),title,f=H);text(d,(55,210),caption,f=font(34),width=58);text(d,(55,450),'Controller search, not newly trained neural weights. Search and memory benefit require separate ablations.',f=F,width=76)
        d.text((1180,30),f'{int(t/120*100):02d}%',font=S,fill='#6f806c');writer.append_data(np.asarray(im))
(run/'demo-captions.json').write_text(json.dumps([{'start':x[0],'end':x[1],'title':x[2],'caption':x[3]} for x in chapters],indent=2));print('Wrote 120-second demo.mp4 from recorded Blender frames and actual report')
