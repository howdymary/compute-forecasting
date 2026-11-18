"""Fetch licensed source assets once, verify downloads, build the globe print."""
import hashlib,json,subprocess,urllib.request
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'web/desk/assets';SOURCE=ROOT/'assets/realism'
WEB.mkdir(parents=True,exist_ok=True);SOURCE.mkdir(parents=True,exist_ok=True)
UA={'User-Agent':'Mochi-visual-study/1.0 (https://github.com/howdymary/mochi-demo)'}
def get(url):return urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read()
manifest={'retrieved_at':datetime.now(timezone.utc).isoformat(),'assets':[]}
for asset,maps in [('studio_small_09',[('hdri','1k','hdr','studio.hdr')]),('wood_table_001',[('Diffuse','2k','jpg','oak-color.jpg'),('nor_gl','2k','jpg','oak-normal.jpg'),('Rough','2k','jpg','oak-roughness.jpg')])]:
    info=json.loads(get('https://api.polyhaven.com/info/'+asset));files=json.loads(get('https://api.polyhaven.com/files/'+asset))
    for key,res,fmt,name in maps:
        item=files[key][res][fmt];path=WEB/name
        if not path.exists() or hashlib.md5(path.read_bytes()).hexdigest()!=item['md5']:path.write_bytes(get(item['url']))
        assert hashlib.md5(path.read_bytes()).hexdigest()==item['md5']
        manifest['assets'].append({'file':name,'source':item['url'],'asset_page':'https://polyhaven.com/a/'+asset,'authors':info['authors'],'license':'CC0-1.0','license_url':'https://polyhaven.com/license','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
        print('Verified',name,path.stat().st_size,flush=True)
revision=subprocess.check_output(['gh','api','repos/nvkelso/natural-earth-vector/commits/master','--jq','.sha'],text=True).strip()
url=f'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{revision}/geojson/ne_110m_admin_0_countries.geojson'
geo=SOURCE/'natural-earth-countries.geojson'
if not geo.exists():geo.write_bytes(get(url))
features=json.loads(geo.read_text())['features'];w,h=2048,1024;ocean=(121,151,158);image=Image.new('RGB',(w,h),ocean);draw=ImageDraw.Draw(image)
def xy(p):return((p[0]+180)/360*w,(90-p[1])/180*h)
for i,f in enumerate(features):
    polygons=f['geometry']['coordinates'] if f['geometry']['type']=='MultiPolygon' else [f['geometry']['coordinates']]
    value=(i*17)%13-6;color=(211+value,201+value,171+value)
    for poly in polygons:
        draw.polygon([xy(p) for p in poly[0]],fill=color,outline=(153,151,125))
        for hole in poly[1:]:draw.polygon([xy(p) for p in hole],fill=ocean)
for lon in range(-180,181,15):
    x=xy((lon,0))[0];draw.line((x,0,x,h),fill=(161,178,171),width=1)
for lat in range(-75,76,15):
    y=xy((0,lat))[1];draw.line((0,y,w,y),fill=(161,178,171),width=1)
draw.line((0,h/2,w,h/2),fill=(117,143,139),width=2)
font_path=Path('/System/Library/Fonts/Supplemental/Times New Roman.ttf');font=ImageFont.truetype(str(font_path),16) if font_path.exists() else ImageFont.load_default()
for label,lon,lat in [('PACIFIC OCEAN',-145,-8),('ATLANTIC OCEAN',-34,0),('INDIAN OCEAN',75,-23),('NORTH AMERICA',-110,46),('SOUTH AMERICA',-60,-14),('AFRICA',20,6),('ASIA',85,48),('AUSTRALIA',134,-25)]:
    draw.text(xy((lon,lat)),label,font=font,fill=(89,112,108),anchor='mm',stroke_width=0)
arr=np.asarray(image).astype(float);rng=np.random.default_rng(713);arr=np.uint8(np.clip(arr+rng.normal(0,.7,(h,w,1)),0,255));Image.fromarray(arr).save(WEB/'globe-map.jpg',quality=94)
manifest['assets'].append({'file':'globe-map.jpg','source':url,'source_revision':revision,'source_sha256':hashlib.sha256(geo.read_bytes()).hexdigest(),'license':'Public domain','license_url':'https://www.naturalearthdata.com/about/terms-of-use/','processing':'110m country polygons, original typesetting, print grain and graticule','sha256':hashlib.sha256((WEB/'globe-map.jpg').read_bytes()).hexdigest()})
(WEB/'sources.json').write_text(json.dumps(manifest,indent=2));(SOURCE/'sources.json').write_text(json.dumps(manifest,indent=2));print('Built globe map with source provenance.')
