"""Fetch pinned, hash-checked source meshes; never execute dataset programs."""
import hashlib,json
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[1]

def fetch(client,url,path,digest):
 if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==digest:return
 data=client.get(url).raise_for_status().content
 if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Asset hash mismatch: '+path.name)
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);print('Verified',path.name)

if __name__=='__main__':
 with httpx.Client(follow_redirects=True,timeout=180,headers={'User-Agent':'Mochi-visual-assets/1.0'}) as client:
  source=root/'assets/robot/g1';m=json.loads((source/'source.json').read_text())
  for relative,digest in m['files'].items():fetch(client,f"https://raw.githubusercontent.com/{m['repository']}/{m['revision']}/{m['path']}/{relative}",source/relative,digest)
  source=root/'assets/realism/sand3d';m=json.loads((source/'downloads.json').read_text())
  for r in m['records']:fetch(client,f"https://huggingface.co/datasets/{m['dataset']}/resolve/{m['revision']}/{r['usda_path']}",source/(r['entry']+'.usda'),r['usda_sha256'])

  clock=json.loads((root/'assets/realism/sand3d/clock-source.json').read_text())
  fetch(client,f"https://huggingface.co/datasets/{clock['dataset']}/resolve/{clock['revision']}/{clock['usda_path']}",root/'assets/realism/sand3d/traditional_alarm_clock.usda',clock['usda_sha256'])

  source=root/'assets/robot/locomotion';m=json.loads((source/'source.json').read_text())
  for item in m['files']:fetch(client,f"https://raw.githubusercontent.com/{m['repository']}/{m['revision']}/{item['path']}",source/item['path'],item['sha256'])
