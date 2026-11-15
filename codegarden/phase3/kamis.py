"""Pinned external solver adaptation; no mathematical validity claims from solver logs."""
import argparse,hashlib,importlib.util,json,os,pathlib,resource,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
REV="2e4b3861b8063f05e8520434b97ce59e21ca49e7"
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as stream:
  while block:=stream.read(1<<20):h.update(block)
 return h.hexdigest()
def limit():
 resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",choices=["warm","scratch"],required=True);a=ap.parse_args()
 out=ROOT/"artifacts/phase3/kamis_001"/a.mode;out.mkdir(parents=True,exist_ok=True);build=ROOT/".build/kamis";build.mkdir(parents=True,exist_ok=True)
 check_integrity();exe=ROOT/".build/graph";small=build/"small.graph"
 p=subprocess.run([str(exe),"6",str(small)],text=True,capture_output=True,check=True)
 spec=importlib.util.spec_from_file_location("protected_d2",ROOT/"protected/verify_descendants.py");vd=importlib.util.module_from_spec(spec);spec.loader.exec_module(vd)
 lines=small.read_text().splitlines();assert lines[0].split()[0]=="64"
 ds=[set(vd.descendants(format(w,"06b"))) for w in range(64)]
 for w,line in enumerate(lines[1:]):assert set(int(v)-1 for v in line.split())=={v for v in range(64) if v!=w and ds[w]&ds[v]}
 graph=build/"full.graph";start=time.monotonic()
 p=subprocess.run([str(exe),"16",str(graph)],text=True,capture_output=True,timeout=300)
 profile=next((json.loads(l.split("GRAPH_PROFILE ",1)[1]) for l in p.stderr.splitlines() if "GRAPH_PROFILE " in l),{})
 report={"source_sha":os.environ["GITHUB_SHA"],"upstream_repository":"https://github.com/KarlsruheMIS/KaMIS","upstream_revision":REV,"mode":a.mode,
  "small_graph_all_edges_independently_checked":True,"profile":profile,"graph_build_seconds":time.monotonic()-start,"experiments":[],"best_verified":226,
  "scope":"Heuristic independent-set solver, not an optimality certificate. Graph is ephemeral and not committed.","provider_calls":0}
 if p.returncode:
  report["status"]="graph_memory_gate_or_error";(out/"report.json").write_text(json.dumps(report,indent=2));return
 report["graph_sha256"]=sha(graph);baseline=ROOT/"artifacts/phase3/kamis_001/preflight/baseline.txt";verify(baseline)
 for seed in [970001,970002]:
  selected=out/("selected_"+str(seed)+".txt");log=out/("solver_"+str(seed)+".log")
  binary=ROOT/".build/kamis-upstream"/("codegarden_warm" if a.mode=="warm" else "redumis")
  command=[str(binary),str(graph),"--seed",str(seed),"--time_limit","240","--output",str(selected),"--console_log"]
  env=dict(os.environ,OMP_NUM_THREADS="1",CODEGARDEN_START_CODES=str(baseline));start=time.monotonic()
  with log.open("w") as sink:
   try:run=subprocess.run(command,stdout=sink,stderr=subprocess.STDOUT,env=env,timeout=330,preexec_fn=limit);status="returned";returncode=run.returncode
   except subprocess.TimeoutExpired:status="timeout";returncode=None
  row={"seed":seed,"method":a.mode,"solver_time_limit_seconds":240,"wall_seconds":time.monotonic()-start,"status":status,"returncode":returncode,"log":log.name,"start_witness_sha256":sha(baseline) if a.mode=="warm" else None}
  if selected.exists() and returncode==0:
   bits=selected.read_text().split();assert len(bits)==65536 and set(bits)<={"0","1"},bits[:10]
   words=[format(w,"016b") for w,b in enumerate(bits) if b=="1"];witness=out/("witness_"+str(seed)+".txt");witness.write_text("\n".join(words)+"\n")
   row["verification"]=verify(witness);report["best_verified"]=max(report["best_verified"],len(words))
  report["experiments"].append(row);report["status"]="completed" if len(report["experiments"])==2 else "running"
  (out/"report.json").write_text(json.dumps(report,indent=2));print("KAMIS_PROGRESS",json.dumps(row),flush=True)
  if report["best_verified"]>226:break
if __name__=="__main__":main()
