"""Draw the first measured engineering route from authoritative collision data."""
import gzip
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
row = json.loads(gzip.decompress((root / 'artifacts/navigation-v23/engineering/engineering-r0-planner-0.json.gz').read_bytes()))
out = root / 'evidence/navigation-v23'
out.mkdir(parents=True, exist_ok=True)
im = Image.new('RGB', (1500, 1130), '#f1eee6')
d = ImageDraw.Draw(im)
font = '/System/Library/Fonts/Supplemental/Arial.ttf'
f = lambda size: ImageFont.truetype(font, size)
xy = lambda p: (int(90 + (p[0] + .6) * 1100), int(145 + (.4 - p[1]) * 1050))
d.text((85, 35), 'MOCHI  /  PHYSICAL NAVIGATION PLAN', font=f(30), fill='#293b36')
d.text((85, 85), 'Engineering layout 0. Exact MuJoCo collision geometry. Not a held-out result.', font=f(21), fill='#65735d')
d.rounded_rectangle((90, 145, 1410, 985), 9, fill='#c5af8e', outline='#a28b69', width=2)
for o in row['obstacles']:
 a,b=xy(o['minimum']),xy(o['maximum'])
 d.rectangle((min(a[0],b[0]), min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])),fill='#84867b',outline='#666c61',width=1)
plan=row['plans']['planner']
points=[xy(p) for p in plan['points']]
d.line(points, fill='#245f65',width=7)
r=int(row['envelope']['planning_radius_m']*1100)
for p in points[1:-1]:
 d.ellipse((p[0]-r,p[1]-r,p[0]+r,p[1]+r),outline='#b48a40',width=3)
path=[xy(p['root']) for p in row['tracking']]
d.line(path,fill='#b46843',width=3)
start,goal=points[0],points[-1]
for point,name in [(start,'START'),(goal,'TARGET + HEADING')]:
 d.ellipse((point[0]-8,point[1]-8,point[0]+8,point[1]+8),fill='#293b36')
 d.text((point[0]-12,point[1]+18),name,font=f(17),fill='#293b36')
d.text((90,1010),'Teal: planned route     Copper: physically executed pelvis path     Gold: nominal turn envelope',font=f(21),fill='#4b5c4c')
d.text((90,1050),f"Qualified arrival. {row['steps']['attempts']} measured steps. {row['physical_seconds']:.2f} seconds. No falls or invalid contacts.",font=f(21),fill='#293b36')
im.save(out/'first-physical-route.png')
print(str(out/'first-physical-route.png'))
