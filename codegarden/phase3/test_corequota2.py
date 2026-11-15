"""Check real quota moves against independent string conflicts and all four core counts."""
import importlib.util,itertools,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical
from supervisor import check_integrity,verify
check_integrity();out=ROOT/"artifacts/phase3/corequota_002/tests";out.mkdir(parents=True,exist_ok=True);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));rev=lambda w:int(format(w,"016b")[::-1],2);images=[core,{65535^w for w in core},{rev(w) for w in core},{65535^rev(w) for w in core}];cp=out/"cores.txt";cp.write_text("".join("216 "+" ".join(map(str,sorted(C)))+"\n" for C in images));known=out/"known.txt";known.write_text("226 "+" ".join(map(str,info["codes"][0]))+"\n")
spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);rows=[]
for i,(target,quota,seconds) in enumerate([(226,210,0),(227,210,1),(226,206,1),(227,206,1)]):
 r=json.loads(subprocess.run([str(ROOT/".build/corequota2"),str(seconds),str(1420001+i),"adaptive",str(out/("checkpoint_"+str(i)+".txt")),str(cp),str(quota),str(target),str(known)],input=canonical(info["codes"][0]),text=True,capture_output=True,check=True).stdout);C=r["best"];assert len(C)==len(set(C))==target
 counts=[len(set(C)&F) for F in images];assert counts==r["best_core_counts"] and max(counts)<=quota
 ds=[set(D.descendants(format(w,"016b"))) for w in C];pairs=sum(bool(ds[a]&ds[b]) for a in range(len(C)) for b in range(a));assert pairs==r["minimum_pair_conflicts"]
 row={"target":target,"quota":quota,"seconds":seconds,"native_pair_conflicts":pairs,"literal_counts":counts,"passed":True}
 if not pairs:
  p=out/("valid_"+str(i)+".txt");p.write_text(canonical(C));row["verification"]=verify(p);print("COREQUOTA_TEST_VALID",len(C),flush=True)
 rows.append(row)
(out/"report.json").write_text(json.dumps(rows,indent=2));print("COREQUOTA_TESTS",len(rows),flush=True)
