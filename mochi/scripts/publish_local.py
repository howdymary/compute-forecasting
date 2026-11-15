"""Copy measured public artifacts to the isolated web app; no provider secrets."""
import argparse,shutil,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source');a=p.parse_args()
root=Path(__file__).resolve().parents[1];source=Path(a.source);dest=root/'web/data';dest.mkdir(parents=True,exist_ok=True)
for name in ['report.json','baseline.json','selected.json','heldout.json']:
    if (source/name).exists():shutil.copy2(source/name,dest/name)
for name in ['hero.png','baseline.mp4','selected.mp4','heldout.mp4','comparison.mp4','demo.mp4','manifest.json']:
    if (source/name).exists():shutil.copy2(source/name,dest/name)
print('Published only Mochi demo artifacts into mochi/web/data')
