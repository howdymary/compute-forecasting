"""Independent string check of the FULL compatible universe for the216 shared words."""
import hashlib,importlib.util,itertools,json,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,pool_hash
from supervisor import verify,check_integrity
check_integrity();out=ROOT/"artifacts/phase3/core_repair_001";out.mkdir(parents=True,exist_ok=True);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=sorted(set.intersection(*(set(C) for C in info["codes"])));root=sorted(info["codes"][0]);raw="226 "+" ".join(map(str,root))+"\n216 "+" ".join(map(str,core))+"\n";(out/"root_core.txt").write_text(raw)
native=json.loads(subprocess.run([str(ROOT/".build/core_repair"),"--pool"],input=raw,text=True,capture_output=True,check=True).stdout);occupied=set();start=time.monotonic()
spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
for w in core:occupied.update(D.descendants(format(w,"016b")))
pool=[];core_set=set(core);pairs=list(itertools.combinations(range(16),2))
for w in range(65536):
 if w in core_set:continue
 s=format(w,"016b");compatible=True
 for i,j in pairs:
  child=s[:i]+s[i+1:j]+s[j+1:]
  if child in occupied:compatible=False;break
 if compatible:pool.append(w)
assert pool==native["pool"] and core==native["core"]
palette=set.union(*(set(C) for C in info["codes"]));report={"source_sha":__import__("os").environ["GITHUB_SHA"],"fixed_core":core,"fixed_core_hash":hashlib.sha256(canonical(core).encode()).hexdigest(),"full_universe_compatible_pool":pool,"pool_sha256":pool_hash(pool),"known_palette_extra_words":sorted(set(pool)-palette),"pool_equals_known_palette_variables":set(pool)==palette-set(core),"independent_string_check":True,"seconds":time.monotonic()-start,"scope":"All65536 words tested for compatibility with the specified216 fixed words, using direct string deletion independent of the packed kernel. Does not assert validity of arbitrary subsets of this pool."}
(out/"core_pool_check.json").write_text(json.dumps(report,indent=2));print("CORE_FULL_POOL_CHECK",json.dumps({"pool_size":len(pool),"equals_known_palette":report["pool_equals_known_palette_variables"],"seconds":report["seconds"]}),flush=True)
