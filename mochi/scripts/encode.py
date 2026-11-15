"""Encode Blender frames at their original simulation rate; no time warping."""
import argparse,json
from pathlib import Path
import imageio.v2 as imageio
from PIL import Image,ImageDraw,ImageFont
p=argparse.ArgumentParser();p.add_argument('--root',default='mochi/artifacts');p.add_argument('--stride',type=int,default=2);p.add_argument('--scope',default='local');a=p.parse_args();root=Path(a.root);dest=root/a.scope;dest.mkdir(exist_ok=True)
for label in ['baseline','selected','heldout']:
    files=sorted((root/f'film-{label}'/'frames').glob('*.png'))
    if not files:continue
    with imageio.get_writer(str(dest/f'{label}.mp4'),fps=25/a.stride,codec='libx264',quality=8,macro_block_size=1) as writer:
        for f in files:writer.append_data(imageio.imread(f))
    if label=='selected':Image.open(files[min(20,len(files)-1)]).save(dest/'hero.png')
    print(label,len(files),'frames',len(files)*a.stride/25,'seconds')
base=sorted((root/'film-baseline'/'frames').glob('*.png'));best=sorted((root/'film-selected'/'frames').glob('*.png'))
if base and best:
    font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
    try:font=ImageFont.truetype(font_path,24)
    except OSError:font=ImageFont.load_default()
    with imageio.get_writer(str(dest/'comparison.mp4'),fps=25/a.stride,codec='libx264',quality=8,macro_block_size=1) as writer:
        for f,g in zip(base,best):
            left=Image.open(f).convert('RGB');right=Image.open(g).convert('RGB');canvas=Image.new('RGB',(left.width*2,left.height+65),'#f6f4ed');canvas.paste(left,(0,65));canvas.paste(right,(left.width,65));d=ImageDraw.Draw(canvas);d.text((24,20),'STARTING POLICY',fill='#273d35',font=font);d.text((left.width+24,20),'SELECTED POLICY',fill='#273d35',font=font);writer.append_data(__import__('numpy').array(canvas))
    print('Wrote synchronized comparison.mp4')
