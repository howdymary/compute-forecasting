"""Independent graph-generator fixtures and baseline native executable smoke tests."""
import hashlib,json,os,pathlib,random,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];TMP=ROOT/".tmp/global_smoke";TMP.mkdir(parents=True,exist_ok=True);OUT=ROOT/"artifacts/side_research/archive_001";OUT.mkdir(parents=True,exist_ok=True)
rng=random.Random(2271136);counts=[]
def ds(x,n):
 s=format(x,"0"+str(n)+"b");return {s[:i]+s[i+1:j]+s[j+1:] for i in range(n) for j in range(i+1,n)}
for n,P in [(6,list(range(64))),(7,sorted(rng.sample(range(128),80))),(8,sorted(rng.sample(range(256),96)))]:
 pool=TMP/("pool"+str(n)+".txt");graph=TMP/("g"+str(n)+".graph");pool.write_text("\n".join(map(str,P))+"\n")
 z=subprocess.run([str(ROOT/".build/global_graph"),str(n),str(pool),str(graph)],capture_output=True,text=True,check=True)
 lines=graph.read_text().splitlines();N,E=map(int,lines[0].split());assert N==len(P);D=[ds(w,n) for w in P];edges=0
 for i,line in enumerate(lines[1:]):
  actual=[int(v)-1 for v in line.split()];expected=[j for j in range(N) if i!=j and D[i]&D[j]]
  assert actual==expected;edges+=len(actual)
 assert edges==2*E
 counts.append({"n":n,"vertices":N,"independently_checked_pairs":N*(N-1)//2,"edges":E})
toy=TMP/"toy.graph";toy.write_text("4 4\n2 4\n1 3\n2 4\n1 3\n")
pool=TMP/"toy_pool.txt";pool.write_text("0\n1\n2\n3\n");seed=TMP/"toy_seed.txt";seed.write_text("0000000000000000\n")
defaults=None;rows=[]
for name in ["redumis","codegarden_pool_warm"]:
 target=TMP/(name+".txt");env=dict(os.environ,CODEGARDEN_POOL_WORDS=str(pool),CODEGARDEN_START_CODES=str(seed),OMP_NUM_THREADS="2")
 r=subprocess.run([str(ROOT/".build/global-KaMIS"/name),str(toy),"--seed","2271136","--time_limit","1","--output",str(target),"--console_log"],text=True,capture_output=True,env=env,cwd=TMP,timeout=30)
 (OUT/(name+"_smoke.txt")).write_text(r.stdout+r.stderr);assert r.returncode==0,(name,r.returncode,r.stderr[-300:])
 tokens=target.read_text().split();assert len(tokens)==4 and set(tokens)<={"0","1"};selected=[i for i,x in enumerate(tokens) if x=="1"];assert len(selected)==2 and all((i+1)%4 not in selected for i in selected)
 if name=="codegarden_pool_warm":
  config=next(json.loads(l.split("CODEGARDEN_WARM_CONFIG ",1)[1]) for l in r.stdout.splitlines() if l.startswith("CODEGARDEN_WARM_CONFIG "))
  defaults=config["baseline_force_cand"]
 rows.append({"binary":name,"returncode":r.returncode,"independent_set_size":2})
(OUT/"smoke.json").write_text(json.dumps({"graph_fixtures":counts,"native_smoke":rows,"default_force_cand":defaults,"scope":"Arbitrary small graph fixtures, not length16 codeword submissions."},indent=2));print("GLOBAL_KAMIS_SMOKE",json.dumps(rows),flush=True)
