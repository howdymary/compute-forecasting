"""Independent string checks of native pair energy, penalties and incremental updates."""
import collections,importlib.util,json,os,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("protected_energy_oracle",ROOT/"protected/verify_descendants.py")
D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
def energy(words,weights=None):
 c=collections.Counter(d for w in words for d in D.descendants(w))
 return sum(v*(v-1)//2*(weights[int(d,2)] if weights is not None else 1) for d,v in c.items())
def main():
 reports=[];binary=ROOT/".build/infeasible"
 for case in range(28):
  n=6 if case<24 else 16;rng=random.Random(910000+case)
  code=rng.sample(range(1<<n),rng.randrange(2,23) if n==6 else 227);words=[format(w,"0%db"%n) for w in code]
  p=subprocess.run([str(binary),"--inspect",str(n),str(910000+case),"32"],input="\n".join(words)+"\n",text=True,capture_output=True,check=True)
  result=json.loads(p.stdout);final=[format(w,"0%db"%n) for w in result["state"]]
  assert result["initial_pair_energy"]==energy(words)
  assert result["final_pair_energy"]==energy(final)
  assert result["weighted_energy"]==energy(final,result["weights"])
  assert len(set(final))==len(words) and result["incremental_check"]
  reports.append({"case":case,"n":n,"cardinality":len(words),"initial_pair_energy":result["initial_pair_energy"],"final_pair_energy":result["final_pair_energy"],"agrees":True})
 out=ROOT/"artifacts/phase3"/os.environ.get("CODEGARDEN_BATCH","infeasible_probe_001")/"preflight";out.mkdir(parents=True,exist_ok=True)
 (out/"energy_tests.json").write_text(json.dumps({"cases":28,"mutations_per_case":32,"all_agree":True,"oracle":"Protected independent string descendants; no native descendant/energy code imported","reports":reports},indent=2))
 print("ENERGY_TESTS "+json.dumps({"cases":28,"all_agree":True}),flush=True)
if __name__=="__main__":main()
