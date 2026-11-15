"""Freeze lineages before counterfactual labels; all outcomes independently checked."""
import hashlib,json,pathlib,random,time,subprocess,sys,datetime as dt
from common import *
def build():
 parents=sorted(p for p in (ROOT/"artifacts/baselines").glob("arena_*.txt") if "226" not in p.name)
 assert len(parents)==4
 cases=[]
 for i in range(32):
  p=parents[i%4];words=p.read_text().splitlines();rng=random.Random(80000+i)
  remove=set(rng.sample(words,2+3*(i//4%5)));initial=[w for w in words if w not in remove]
  cases.append({"case_id":"train-"+str(i),"split":"train","family":p.stem,"seed":80000+i,"initial_words":initial,"parent_reference_size":len(words)})
 native=json.loads((ROOT/"artifacts/native/report.json").read_text());candidates={}
 for worker in native["workers"]:
  for code in worker["archive"]:
   words=[format(w,"016b") for w in code];candidates.setdefault(orbit(words),words)
 for i,(key,words) in enumerate(sorted(candidates.items())[:8]):
  rng=random.Random(90000+i);remove=set(rng.sample(words,4+4*(i%4)))
  cases.append({"case_id":"heldout-"+str(i),"split":"heldout","family":"kgrey-lineage","seed":90000+i,
   "initial_words":[w for w in words if w not in remove],"parent_orbit_sha256":key,"parent_reference_size":len(words)})
 assert len(cases)==40
 # Warmups create observed history and actual stagnation; never fabricated features.
 for i,c in enumerate(cases):
  warm=kernel(c["initial_words"],c["seed"],.08,i%6)
  c["starting_words"]=warm["words"];c["starting_sha256"]=sha(c["starting_words"]);c["orbit_sha256"]=orbit(c["starting_words"])
  c["warmup_verification"]=check_words(c["starting_words"],"episodes/"+c["case_id"]+"_start.txt")
  c["state"]=state(c["starting_words"],[{"action":ACTIONS[i%6],"gain":len(warm["words"])-len(c["initial_words"]),
   "cpu_seconds":warm["cpu_seconds"]}],warm["stagnation_cpu_seconds"],120)
 for c in cases:
  c["state"]["known_parent_reference_size"]=c["parent_reference_size"]
  c["state"]["episode_best_before_action"]=max(c["parent_reference_size"],len(c["starting_words"]))
 train_orbits={c["orbit_sha256"] for c in cases if c["split"]=="train"}
 assert not train_orbits&{c["orbit_sha256"] for c in cases if c["split"]=="heldout"}
 manifest={"cases":cases,"split":"Four non-kgrey arena lineages train; eight kgrey-lineage archived codes held out, disjoint starting-code symmetry orbits.",
  "operator_cpu_seconds":1.0,"search_cpu_seconds_per_evaluation_case":120,"evaluation_chunks":4,
  "monetary_cap_per_condition_usd":5,"wall_limit_per_case_seconds":2400,
  "frozen_before_counterfactual_labels":True,"frozen_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
 save("frozen_cases.json",manifest)
 print("FROZEN_MANIFEST "+hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),flush=True)
 subprocess.run([sys.executable,"-B",str(ROOT/"phase2/publish.py")],check=True)
 examples=[];strict_cases=0;strict_winners=set()
 for c in cases:
  if c["split"]!="train":continue
  scores=[]
  for arm in range(6):
   r=kernel(c["starting_words"],c["seed"]*10+arm,1.0,arm)
   r["verification"]=check_words(r["words"],"episodes/"+c["case_id"]+"_arm"+str(arm)+".txt")
   scores.append({"action":ACTIONS[arm],"size":len(r["words"]),"cpu_seconds":r["cpu_seconds"],
    "gain_beyond_known_best":max(0,len(r["words"])-c["state"]["episode_best_before_action"]),
    "progress":r["progress"],"verification":r["verification"],"witness":"episodes/"+c["case_id"]+"_arm"+str(arm)+".txt"})
  best=max(x["gain_beyond_known_best"] for x in scores);worst=min(x["gain_beyond_known_best"] for x in scores)
  winners=[i for i,s in enumerate(scores) if s["gain_beyond_known_best"]==best]
  if best>worst:
   strict_cases+=1
   if len(winners)==1:strict_winners.add(winners[0])
  chosen=winners[int(hashlib.sha256(c["case_id"].encode()).hexdigest(),16)%len(winners)]
  examples.append({"case_id":c["case_id"],"split":"train","verified":True,"state":c["state"],"action":ACTIONS[chosen],
   "scores":scores,"label_eligible":best>0,"parent_reference_size":c["parent_reference_size"],"starting_words":c["starting_words"],"family":c["family"],"ties":len(winners)})
  save("training_progress.json",{"completed":len(examples),"examples":examples})
 gate={"differential_cases":strict_cases,"distinct_unique_winning_actions":len(strict_winners),
  "meaningful":strict_cases>=8 and len(strict_winners)>=2,
  "rule":"At least eight verified differential gains beyond the known parent/episode best and two different uniquely winning actions; arbitrary ties do not satisfy the diversity gate."}
 save("training_cases.json",{"examples":examples,"gate":gate,"frozen_manifest":"frozen_cases.json"})
 return manifest,examples,gate
