"""Matched fixed-cardinality search followed by independent projection and exact polish."""
import argparse,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity,verify
from search import canonical
from phase3.project_tensor3 import project
from phase3.polish_tensor import run as polish
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case;check_integrity();out=ROOT/"artifacts/phase3/pair_events_001"/str(case);out.mkdir(parents=True,exist_ok=True)
 baseline=next((ROOT/"artifacts/baselines").glob("arena_"+str(226 if case<4 else 225)+"_*.txt"));accepted=verify(baseline);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=sorted(set.intersection(*(set(C) for C in info["codes"])));assert len(core)==216
 cp=out/"core.txt";cp.write_text("\n".join(map(str,core)));mode="fixed" if case%2==0 else "adaptive";seed=1301001+case//2;quota=227
 known=out/"known226.txt";rev=lambda w:int(format(w,"016b")[::-1],2);orbits=[sorted(O) for C in info["codes"] for O in [C,[65535^w for w in C],[rev(w) for w in C],[65535^rev(w) for w in C]]];known.write_text("".join("226 "+" ".join(map(str,C))+"\n" for C in orbits))
 r=json.loads(subprocess.run([str(ROOT/".build/pair_events"),"300",str(seed),mode,str(out/"raw_checkpoint.txt"),str(known)],input=baseline.read_text(),text=True,capture_output=True,check=True,timeout=400).stdout)
 raw=out/"search.json";raw.write_text(json.dumps(r,indent=2));report=project(raw,out/"projections");positive=None
 for i,C in enumerate(r["novel226_candidates"]):
  q=out/"projections"/("event226_"+str(i)+".txt");q.write_text(canonical(C));v=verify(q);assert v["cardinality"]==226
  item={"witness":q.name,"verification":v,"known226_orbit":False};report["rows"].append({"event_capture":True,"projections":[item]});report["novel226_orbits"].append(item)
 (out/"projections/report.json").write_text(json.dumps(report,indent=2))
 if r["minimum_pair_conflicts"]==0:
  p=out/"candidate.txt";p.write_text(canonical(r["best"]));positive=verify(p);assert positive["cardinality"]==227
 polished=polish(out) if report["novel226_orbits"] else None
 result={"source_sha":os.environ["GITHUB_SHA"],"case":case,"mode":mode,"quota":quota,"seed":seed,"starting_verification":accepted,"cpu_seconds":r["cpu_seconds"],"iterations":r["iterations"],"event_candidates":len(r["novel226_candidates"]),"raw_energy_at_best_pair_state":r["raw_energy_at_best_pair_state"],"minimum_pair_conflicts":r["minimum_pair_conflicts"],"verified_target":positive,"best_verified":max(report["best_independently_verified"],polished.get("best_verified",226) if polished else 226),"novel226":len(report["novel226_orbits"]),"scope":"Raw227-word states with positive energy are invalid. Only projected codes passing both protected verifiers count. Paired runs have equal native CPU budgets; quota restrictions are reported explicitly."}
 (out/"report.json").write_text(json.dumps(result,indent=2));print("PAIR_EVENTS",json.dumps(result),flush=True)
if __name__=="__main__":main()
