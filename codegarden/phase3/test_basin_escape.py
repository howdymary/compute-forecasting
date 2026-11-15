"""Independent literal-string check of distinct-pair objective and sampled all-word fields."""
import collections,functools,importlib.util,itertools,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity
check_integrity();spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
@functools.lru_cache(None)
def ds(w):return set(D.descendants(format(w,"016b")))
rows=json.loads(subprocess.run([str(ROOT/".build/pair_test")],text=True,capture_output=True,check=True).stdout)
for row in rows:
 C=row["words"];assert len(C)==len(set(C))==227
 pairs=sum(bool(ds(a)&ds(b)) for a,b in itertools.combinations(C,2));counts=collections.Counter(d for w in C for d in ds(w))
 assert pairs==row["pair_energy"]
 assert sum(v*(v-1)//2 for v in counts.values())==row["descendant_energy"]
 for w,value in row["sample_fields"]:assert sum(bool(ds(w)&ds(v)) for v in C if v!=w)==value
out=ROOT/"artifacts/phase3/basin_escape_001";out.mkdir(parents=True,exist_ok=True);(out/"tests.json").write_text(json.dumps({"states":len(rows),"pairs_per_state":25651,"sampled_candidate_fields":320,"independent_literal_string_checks":True},indent=2));print("PAIR_BREAKOUT_TESTS",len(rows),flush=True)

# Exercise the new target-cardinality and forbidden-word predicates through the real CLI.
base=next((ROOT/"artifacts/baselines").glob("arena_225_*.txt"));C=[int(w,2) for w in base.read_text().split()];banned=min(set(range(65536))-set(C));ban=out/"test_forbidden.txt";ban.write_text(str(banned));known=out/"test_known.txt";known.write_text("")
r=json.loads(subprocess.run([str(ROOT/".build/basin_escape"),".03","1310001","adaptive",str(out/"test_checkpoint.txt"),str(known),"226",str(ban)],input=base.read_text(),text=True,capture_output=True,check=True).stdout)
assert r["target"]==226 and len(r["best"])==len(set(r["best"]))==226 and banned not in r["best"]
assert all(len(A["words"])==226 and banned not in A["words"] for A in r["archive"])
assert sum(bool(ds(a)&ds(b)) for a,b in itertools.combinations(r["best"],2))==r["minimum_pair_conflicts"]
(out/"cli_tests.json").write_text(json.dumps({"target":226,"forbidden_word":banned,"passed":True,"minimum_pair_conflicts":r["minimum_pair_conflicts"]},indent=2));print("BASIN_ESCAPE_CLI_TESTS passed",flush=True)
