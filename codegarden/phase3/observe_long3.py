"""Read committed CodeGarden snapshots without starting or altering Modal workers."""
import datetime as dt,json,os,pathlib,sys,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from providers import cli
def main():
 import modal
 out=ROOT/"artifacts/phase3/long_snapshot_003";out.mkdir(parents=True,exist_ok=True);check_integrity()
 volume=modal.Volume.from_name("codegarden-phase3-long-checkpoints",create_if_missing=False);entries=volume.listdir("/",recursive=True)
 names={str(e.path).lstrip("/") for e in entries};rows=[]
 def read(p):return b"".join(volume.read_file(p)).decode()
 for name in sorted(p for p in names if p.endswith("/metadata.json")):
  meta=json.loads(read(name))
  if meta.get("source_sha")!="9e02d5fbec4b5bef09c05f3182dc6f7109ea1090":continue
  prefix=name.rsplit("/",1)[0];case=meta["case_index"];row={"case":case,"pair":meta["pair"],"policy":meta["policy"],"family":meta["family"],"source_sha":meta["source_sha"],"volume_directory":prefix}
  for basename in ["progress.json","result.json"]:
   rel=prefix+"/"+basename
   if rel in names:
    p=json.loads(read(rel));row[basename]={"native_cpu_seconds":p.get("native_cpu_seconds"),"polish_cpu_seconds":p.get("polish_cpu_seconds"),"segments":len(p.get("segments",[])),"best_verified":p.get("best_verified",p.get("verification",{}).get("cardinality")),"status":p.get("status")}
  row["exports"]=[]
  for basename in ["best.txt","unverified_live_checkpoint.txt"]:
   rel=prefix+"/"+basename
   if rel not in names:continue
   path=out/("case_"+str(case)+"_"+basename);path.write_text(read(rel))
   try:
    v=verify(path);row["exports"].append({"file":path.name,"verification":v,"scope":"Independent snapshot acceptance; this does not imply the worker has completed"})
   except Exception as e:row["exports"].append({"file":path.name,"snapshot_not_accepted":str(e)[:300]})
  rows.append(row)
 receipt={"observed_at":dt.datetime.now(dt.timezone.utc).isoformat(),"source_sha":os.environ["GITHUB_SHA"],"rows":rows,"new_modal_workers":0,"modal_mutations":0,"api_access":"Read-only Volume list/read; no App run, spawn, cancellation, upload or billing setting change",
  "best_independently_verified":max([226]+[e.get("verification",{}).get("cardinality",0) for r in rows for e in r["exports"]]),"scope":"Committed snapshots only. Missing progress is not stagnation, failure or a completed experiment."}
 try:
  receipt["account_summary"]=json.loads(cli("modal","billing","summary","--json"))
  receipt["current_rates"]=json.loads(cli("modal","billing","rates","--json"))
  apps=json.loads(cli("modal","app","list","--limit","100","--json"));items=apps if isinstance(apps,list) else apps.get("apps",[])
  receipt["completed_codegarden_shard_apps"]=[r for r in items if any(n in json.dumps(r) for n in ["codegarden-phase3-sharded-nine","codegarden-phase3-sharded-ten"])]
 except Exception as e:receipt["account_audit_unavailable"]=str(e)[:300]
 (out/"receipt.json").write_text(json.dumps(receipt,indent=2));print("LONG_SNAPSHOT",json.dumps(receipt),flush=True)
if __name__=="__main__":main()
