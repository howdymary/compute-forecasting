"""Build evidence tables and score-versus-resource figures from immutable run receipts."""
import collections,csv,hashlib,json,os,pathlib,statistics,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase2"
sys.path.insert(0,str(ROOT))
def read(path,default=None):
 p=ROOT/path
 return json.loads(p.read_text()) if p.exists() else default
def mean(xs):return statistics.mean(xs) if xs else None
def main():
 training=read("artifacts/phase2/training_cases.json");main_eval=read("artifacts/phase2/evaluation.json",{})
 supplement=read("artifacts/phase2/supplement/evaluation.json",{});memory=read("artifacts/phase2/supplement/memory_recovery/memory_benchmark.json",read("artifacts/phase2/supplement/memory_benchmark.json",{}))
 rewards=[]
 for e in training["examples"]:
  reference=int(e["family"].split("_")[1])
  rewards.append({"case_id":e["case_id"],"family_reference_size":reference,"starting_size":len(e["starting_words"]),
   "best_counterfactual_size":max(s["size"] for s in e["scores"]),
   "gains_beyond_reference":[max(0,s["size"]-reference) for s in e["scores"]]})
 reward_audit={"cases":rewards,"recovery_only_differential_cases":training["gate"]["differential_cases"],
  "differential_cases_beyond_known_parent":sum(max(r["gains_beyond_reference"])>min(r["gains_beyond_reference"]) for r in rewards),
  "cases_exceeding_parent":sum(max(r["gains_beyond_reference"])>0 for r in rewards),
  "new_training":False,"corrected_future_gate":"dataset.py now labels gains beyond max(known parent size, episode best); raw executed receipts remain unchanged."}
 (OUT/"reward_audit.json").write_text(json.dumps(reward_audit,indent=2))
 curves=[];main_rows=[];configurations=[]
 for t in main_eval.get("trials",[]):
  cpu=0;episode_best=t["initial_size"];curves.append({"study":"fallback120","condition":t["condition"],"case":t["case_id"],"search_cpu_seconds":0,"best_verified_size":t["initial_size"]})
  for r in t["chunks"]:
   cpu+=r["cpu_seconds"]
   verified=max(episode_best,r["host_verification"]["cardinality"]);episode_best=verified
   curves.append({"study":"fallback120","condition":t["condition"],"case":t["case_id"],"search_cpu_seconds":cpu,"best_verified_size":verified})
   configurations.append({"study":"fallback120","condition":t["condition"],"case":t["case_id"],"starting_sha256":r["starting_witness_sha256"],"seed":r["seed"],
    "arm":r["preferred_arm"],"cpu_cap":30,"program_sha256":r["source_sha256"]})
 for r in supplement.get("rows",[]):
  for x,y in [(0,r["starting_size"]),(r["result"]["cpu_seconds"],r["host_verification"]["cardinality"])]:
   curves.append({"study":"supplement20","condition":r["condition"],"case":r["case_id"],"search_cpu_seconds":x,"best_verified_size":y})
  configurations.append({"study":"supplement20","condition":r["condition"],"case":r["case_id"],"starting_sha256":r["starting_sha256"],"seed":r["seed"],"arm":r["arm"],
   "cpu_cap":20,"program_sha256":"same pinned kernel_v2 in supplemental source"})
 byconfig=collections.defaultdict(list)
 for c in configurations:
  key=hashlib.sha256(json.dumps({k:v for k,v in c.items() if k not in ["study","condition","case"]},sort_keys=True).encode()).hexdigest()
  byconfig[key].append({k:c[k] for k in ["study","condition","case"]})
 duplicates=[{"configuration_sha256":k,"executions":v} for k,v in byconfig.items() if len(v)>1]
 (OUT/"configuration_audit.json").write_text(json.dumps({"executions":len(configurations),"distinct_configurations":len(byconfig),
  "duplicate_configuration_groups":duplicates,"repeated_executions":sum(len(x["executions"])-1 for x in duplicates),
  "equivalent_program_note":"Supplement legacy action identifiers explicitly alias six compiled backends. Equality of program configuration is not assumed from action spelling.",
  "duplicate_warning":"The original no-research and with-research arms were identical empirical fallback sweeps after the gate failed; they are not independent LLM evidence."},indent=2))
 with (OUT/"score_resource.csv").open("w",newline="") as stream:
  writer=csv.DictWriter(stream,fieldnames=list(curves[0]));writer.writeheader();writer.writerows(curves)
 import matplotlib;matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(1,2,figsize=(13,4.8));labels={"fixed":"Fixed ruin32","adaptive_no_external":"Fallback sweep, no external","adaptive_with_research":"Same fallback + supplied context",
  "strong_fixed":"Train-selected fixed exchange23","untrained_no_external":"Untrained, no external","untrained_with_memory":"Untrained + recalled finding","historical_trained_with_memory":"Historical trained + recalled finding"}
 for ax,study,title in zip(axes,["fallback120","supplement20"],["Original fallback study (not an LLM ablation)","Supplemental frozen proposer control"]):
  selected=[r for r in curves if r["study"]==study]
  for condition in dict.fromkeys(r["condition"] for r in selected):
   rr=[r for r in selected if r["condition"]==condition];points=collections.defaultdict(list)
   for r in rr:points[round(r["search_cpu_seconds"]/30)*30 if study=="fallback120" else round(r["search_cpu_seconds"]/20)*20].append(r["best_verified_size"])
   xx=sorted(points);ax.plot(xx,[mean(points[x]) for x in xx],marker="o",label=labels.get(condition,condition))
  ax.set(title=title,xlabel="Search CPU seconds per case",ylabel="Mean independently verified episode best")
  ax.grid(alpha=.25);ax.legend(fontsize=7);ax.text(.01,-.25,"Recovery from perturbed 226-family codes; no new length-16 record.",transform=ax.transAxes,fontsize=8)
 fig.tight_layout();fig.savefig(OUT/"score_resource.svg",bbox_inches="tight");fig.savefig(ROOT/"demo/phase2_curve.svg",bbox_inches="tight");plt.close(fig)
 longs=[]
 for period in [1,2]:
  for r in read("artifacts/phase2/long_period"+str(period)+".json",[]):
   longs.append({"period":period,"seed":r["seed"],"policy":r["policy"],"best":r["host_verification"]["cardinality"],"iterations":r["iterations"],
    "cpu_seconds":r["cpu_seconds"],"cache_hits":r["cache_hits"],"exact_augmentations":r["exact_augmentations"],"archive":r["archive"]})
 from phase2.common import orbit
 orbits={orbit([format(w,"016b") for w in c]) for r in longs for c in r["archive"]}
 base=set((ROOT/"artifacts/best_code.txt").read_text().splitlines());lineage=[]
 for p in sorted((ROOT/"artifacts/baselines").glob("arena_*.txt")):
  words=p.read_text().splitlines();transforms=[set(words),{w[::-1] for w in words},{"".join("1" if b=="0" else "0" for b in w) for w in words},{"".join("1" if b=="0" else "0" for b in w[::-1]) for w in words}]
  lineage.append({"family":p.stem,"maximum_jaccard_against_226_modulo_symmetries":max(len(base&t)/len(base|t) for t in transforms)})
 (OUT/"lineage_audit.json").write_text(json.dumps(lineage,indent=2))
 analysis={"lineage_audit":lineage,"main_summary":main_eval.get("summary"),"supplement_summary":supplement.get("summary"),"memory_summary":memory.get("summary"),
  "long_search":{"workers":len(longs),"iterations":sum(r["iterations"] for r in longs),"search_cpu_seconds":sum(r["cpu_seconds"] for r in longs),
   "distinct_archived_symmetry_orbits":len(orbits),"best":max(r["best"] for r in longs),
   "exact_augmentations_are_not_global_improvements":True},"reward_audit":reward_audit,"configuration_duplicates":len(duplicates)}
 (OUT/"analysis.json").write_text(json.dumps(analysis,indent=2))
 data=read("demo/data.json")
 data["run_state"]="Recorded phase-two campaign, November 14–15, 2026. Paid search stopped at the published cutoff; this page replays evidence."
 data["hypothesis"]="After exact small exchanges were exhausted, test larger compatible repair pools and symmetry-orbit constructions. No strict improvement beyond 226 was found."
 data["training"]["summary"]="Phase-two fine-tuning skipped: zero counterfactual gains exceeded the known parent constructions."
 data["training"]["scope"]="The previous trained checkpoint is tested separately. Earlier matched-CPU losses remain in the phase-one report."
 data["memory"]["status"]="Distinct analyst, researcher and strategist OS processes read and wrote past.dev. Recalled root exhaustion informed an Exa-backed larger-repair plan. Model and memory controls are reported separately."
 data["phase2"]={"analysis":analysis,"cycle":[
  {"step":"Stagnation","evidence":"Root 1→2 and 2→3 exchanges exhausted around the pinned 226-word witness."},
  {"step":"Recall","evidence":"Researcher PID 2975 retrieved analyst PID 2972's exact scoped result from past.dev."},
  {"step":"Research and selection","evidence":"Actual Exa query returned Sviridenko–Ward large-neighborhood set packing; strategist PID 2980 retrieved the proposed larger-repair method."},
  {"step":"Execution","evidence":"Six sparse CP repairs; outer-controller extension to exact radii 3–4 and 512 conflict-driven repairs."},
  {"step":"Independent checks","evidence":"175 matching certificates checked; 337 other pools re-solved with an independent exact clique routine. All 512 full pools reconstructed with protected string descendants."}],
  "scope":"Recorded causal trace. The radius extension was proposed by the outer research assistant, outside the frozen policy comparison. It is not evidence that the trained model chose the extension."}
 data["causal_references"].append({"phase2":"artifacts/phase2/roles/; source hashes and provider request IDs retained"})
 (ROOT/"demo/data.json").write_text(json.dumps(data,indent=2))
 print("ANALYSIS "+json.dumps({k:v for k,v in analysis.items() if k not in ["reward_audit","lineage_audit"]}))
if __name__=="__main__":main()
