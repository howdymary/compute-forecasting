"""Run on the remote CPU host, never creates workstation files."""
import hashlib,importlib.util,json,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
D=load("kernel_desc",ROOT/"protected/verify_descendants.py")
L=load("kernel_lcs",ROOT/"protected/verify_lcs.py")
binary=ROOT/".build/kernel"
samples=random.Random(7401).sample(range(65536),512)
words=[format(w,"016b") for w in samples]
p=subprocess.run([str(binary),"--descendants"],input="\n".join(words),text=True,capture_output=True,check=True)
actual=json.loads(p.stdout)
for w,word in zip(samples,words):
    assert set(actual[str(w)])=={int(d,2) for d in D.descendants(word)}
baseline=(ROOT/"artifacts/best_code.txt").read_text()
p=subprocess.run([str(binary),"0","17","adaptive"],input=baseline,text=True,capture_output=True,check=True)
r=json.loads(p.stdout);out=[format(w,"016b") for w in r["best"]]
assert D.verify(out)["valid"] and L.verify(out)["valid"]
bad=subprocess.run([str(binary),"0","17","adaptive"],input="0"*16+"\n"+"0"*16+"\n",text=True,capture_output=True)
assert bad.returncode!=0
p=subprocess.run([str(binary),"1","31","adaptive"],input=baseline,text=True,capture_output=True,check=True)
r=json.loads(p.stdout);out=[format(w,"016b") for w in r["best"]]
assert D.verify(out)["valid"] and L.verify(out)["valid"]
report={"sampled_descendant_sets":512,"invalid_duplicate_rejected":True,"dynamic_state_self_check":True,
 "one_second_iterations":r["iterations"],"one_second_best":len(out),
 "kernel_sha256":hashlib.sha256((ROOT/"kernel.cpp").read_bytes()).hexdigest()}
(ROOT/"artifacts/kernel_test.json").write_text(json.dumps(report,indent=2));print(json.dumps(report))
