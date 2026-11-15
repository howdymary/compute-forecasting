"""Stop only CodeGarden's retried long app after its logical CPU budget is spent.
No new Modal workers, no new spend reservations, no changes to other apps.
"""
import collections,datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity,verify
from providers import cli
OUT=ROOT/"artifacts/phase3/long_control_001";OUT.mkdir(parents=True,exist_ok=True)
SOURCE="9e02d5fbec4b5bef09c05f3182dc6f7109ea1090";APP="codegarden-phase3-long-diversification"
def publish():subprocess.run([sys.executable,"-B",str(ROOT/"phase3/publish_long_control.py")],check=True)
def audit():
 import modal
 volume=modal.Volume.from_name("codegarden-phase3-long-checkpoints",create_if_missing=False);names={str(e.path).lstrip("/") for e in volume.listdir("/",recursive=True)}
 def read(p):return b"".join(volume.read_file(p))
 rows=[]
 for path in sorted(p for p in names if p.endswith("/metadata.json")):
  meta=json.loads(read(path))
  if meta.get("source_sha")!=SOURCE:continue
  folder=path.rsplit("/",1)[0];row={"case":meta["case_index"],"directory":folder,"metadata_sha256":hashlib.sha256(read(path)).hexdigest(),"source_sha":SOURCE,"completed":False,"native_cpu_seconds":0,"exports":[]}
  for name in ["progress.json","result.json"]:
   p=folder+"/"+name
   if p not in names:continue
   raw=read(p);data=json.loads(raw);row[name]={"sha256":hashlib.sha256(raw).hexdigest(),"native_cpu_seconds":data.get("native_cpu_seconds",0),"segments":len(data.get("segments",[])),"status":data.get("status"),"allowance_reached":data.get("allowance_reached")}
   row["native_cpu_seconds"]=max(row["native_cpu_seconds"],data.get("native_cpu_seconds",0));row["completed"]=row["completed"] or (name=="result.json" and data.get("status")=="completed" and data.get("native_cpu_seconds",0)>=5999)
  for name in ["best.txt","unverified_live_checkpoint.txt"]:
   p=folder+"/"+name
   if p not in names:continue
   dest=OUT/(folder.replace("/","_")+"_"+name);dest.write_bytes(read(p))
   try:row["exports"].append({"file":dest.name,"verification":verify(dest)})
   except Exception as e:row["exports"].append({"file":dest.name,"not_accepted":str(e)[:300]})
  rows.append(row)
 completed={r["case"] for r in rows if r["completed"]};cpu=collections.Counter()
 for r in rows:cpu[r["case"]]+=r["native_cpu_seconds"]
 best=max([226]+[e.get("verification",{}).get("cardinality",0) for r in rows for e in r["exports"]])
 exhausted=all(cpu[i]>=5999 for i in range(8));other_done=all(i in completed for i in range(8) if i!=2);duplicate=sum(r["case"]==2 for r in rows)>1
 receipt={"observed_at":dt.datetime.now(dt.timezone.utc).isoformat(),"controller_source":os.environ["GITHUB_SHA"],"worker_source":SOURCE,"rows":rows,"logical_native_cpu_seconds":dict(cpu),"completed_cases":sorted(completed),"all_logical_budgets_spent":exhausted,"other_seven_completed":other_done,"duplicate_case2":duplicate,"best_independently_verified":best,"new_modal_workers":0,"new_provider_reservations":0,
  "censoring":"Case2 attempts are not independent samples. No claim of identical total compute; no exhaustion claim beyond the encoded randomized budget.",
  "action":"none","documentation":"https://modal.com/docs/cli/latest/app#modal-app-stop","budget":"Full7.22USD reservation and all earlier holds retained; no reconciliation or release."}
 if best>=227 or (duplicate and exhausted and other_done):
  apps=json.loads(cli("modal","app","list","--limit","100","--json"));apps=apps if isinstance(apps,list) else apps.get("apps",[])
  candidates=[a for a in apps if a.get("description")==APP and a.get("state")!="stopped" and "2026-11-15 09:17"<=str(a.get("created_at",""))<="2026-11-15 09:25:59"]
  assert len(candidates)<=1,"Ambiguous app ownership; refuse stop"
  if candidates:
   app=candidates[0];assert app["app_id"].startswith("ap-")
   receipt["guarded_app"]=app;receipt["action"]="guarded_stop_requested";(OUT/"receipt.json").write_text(json.dumps(receipt,indent=2));publish()
   cli("modal","app","stop",app["app_id"],"--yes");receipt["action"]="stopped_only_owned_long_app";receipt["reason"]="Verified227 target" if best>=227 else "All logical6000native-CPU allowances reached across recorded attempts; other seven completed; switch hypothesis"
  else:receipt["action"]="already_stopped"
 (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2));publish();print("LONG_CONTROL",json.dumps({k:receipt[k] for k in ["observed_at","logical_native_cpu_seconds","completed_cases","best_independently_verified","action"]}),flush=True);return receipt
def main():
 check_integrity()
 for step in range(75):
  r=audit()
  if r["action"]!="none" or dt.datetime.now(dt.timezone.utc)>=dt.datetime(2026,11,15,11,30,tzinfo=dt.timezone.utc):break
  time.sleep(30)
if __name__=="__main__":main()
