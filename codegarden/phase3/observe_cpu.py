"""Read-only inspection of the existing CPU tensor worker. No new Modal functions."""
import datetime as dt,hashlib,json,os,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
def main():
 import modal
 out=ROOT/"artifacts/phase3/cpu_snapshot_001";out.mkdir(parents=True,exist_ok=True);check_integrity();volume=modal.Volume.from_name("codegarden-phase3-cpu-tensor-checkpoints",create_if_missing=False);names={str(x.path).lstrip("/") for x in volume.listdir("/",recursive=True)};rows=[];best=226
 def read(path):return b"".join(volume.read_file(path))
 for name in sorted(p for p in names if p.endswith("/metadata.json")):
  meta=json.loads(read(name))
  if meta.get("source_sha")!="a92159037d77ead65dbf736ac3ed9467d168ab57":continue
  folder=name.rsplit("/",1)[0];row={"metadata":meta,"exports":[]}
  for base in ["tensor_checkpoint.json","result.json"]:
   p=folder+"/"+base
   if p not in names:continue
   raw=read(p);q=out/(folder.replace("/","_")+"_"+base);q.write_bytes(raw)
   try:
    data=json.loads(raw);row[base]={"sha256":hashlib.sha256(raw).hexdigest(),"steps":data.get("steps"),"minimum_raw_energy":data.get("minimum_raw_energy"),"archive_count":len(data.get("archive",[])),"progress":data.get("progress",[])[-2:],"scope":"Positive-energy227-word states are invalid diagnostics, not accepted codes."}
   except Exception as e:row[base]={"unreadable_snapshot":str(e)[:200]}
  if folder+"/candidate.txt" in names:
   q=out/"candidate.txt";q.write_bytes(read(folder+"/candidate.txt"));checked=verify(q);assert checked["cardinality"]==227;row["candidate_verification"]=checked;best=227
  rows.append(row)
 receipt={"observed_at":dt.datetime.now(dt.timezone.utc).isoformat(),"observer_source":os.environ["GITHUB_SHA"],"rows":rows,"best_independently_verified":best,"new_modal_workers":0,"new_paid_reservations":0,"scope":"Only committed snapshots of the one already-reserved CodeGarden CPU function. Missing data is not failure or stagnation; no billing settings or jobs are changed."}
 (out/"receipt.json").write_text(json.dumps(receipt,indent=2));print("CPU_SNAPSHOT",json.dumps(receipt),flush=True)
if __name__=="__main__":main()
