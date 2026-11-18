"""Render actual development traces into the laptop's diagnostic display."""
from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parents[1];im=Image.new('RGB',(1440,900),'#132025');d=ImageDraw.Draw(im)
font='/System/Library/Fonts/Menlo.ttc'
def text(p,s,size=25,color='#99afa9'):d.text(p,s,font=ImageFont.truetype(font,size),fill=color)
text((70,48),'MOCHI / CONTACT CONTROL',33,'#d4ddd4');text((70,104),'RECORDED DEVELOPMENT RUN 9000 / NO TRAINED WEIGHTS',20)
d.line((65,150,1375,150),fill='#344548',width=2)
for i,(task,label) in enumerate([('laptop','LAPTOP SCREEN'),('globe','GLOBE MARKER')]):
 r=json.loads((root/'web/desk/tasks'/f'{task}.json').read_text());top=220+i*305;target=math.degrees(r['scenario']['target_angle']);frames=r['trajectory']['frames'];initial=math.degrees(frames[0]['angle']);low=min(initial,target)-4;high=max(initial,target)+4
 text((80,top-35),f'{label}   FINAL ERROR {r["error_degrees"]:.2f} DEG',25,'#c6ceb8')
 for a in range(4):y=top+a*57;d.line((80,y,1340,y),fill='#2f4346',width=2)
 def yy(angle):return top+190-(angle-low)/(high-low)*190
 y=yy(target)
 for x in range(80,1340,25):d.line((x,y,x+11,y),fill='#c49e79',width=2)
 points=[(80+f['t']/7*1260,yy(math.degrees(f['angle']))) for f in frames];d.line(points,fill='#adc2b0',width=5);text((80,top+208),'0 SEC',18);text((1235,top+208),'7 SEC',18)
text((80,845),'PASS: +/- 3 DEG, SETTLED 0.4 SEC | PHYSICS 500 HZ / CONTROL 50 HZ',20)
im.save(root/'web/desk/assets/laptop-display.png',optimize=True)
