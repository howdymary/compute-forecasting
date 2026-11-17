"""Post-hoc exposure audit of completed runs; reads only hash-bound frozen inputs."""
import collections,hashlib,json,math,os,pathlib
from compute_forecast.probability_v18 import digest,bin_index,support
from compute_forecast.continuation_v21 import batches,batch_identity
def read(path):return json.loads(pathlib.Path(path).read_bytes())
cfg=read("configs/ce-continuation-v21.json");binding=read("configs/ce-continuation-v21-inputs.json")
data=read("inputs/ce-continuation-v21/dataset.json");assert digest(data)==binding["dataset_sha256"]
pointer=read("results/ce-continuation-v21/latest.json");raw=pathlib.Path(pointer["report_path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"]
report=json.loads(raw);assert report["protocol_sha256"]==digest(cfg)==data["protocol_sha256"]
levels=data["log_levels"];zero=levels.index(0)
def audit(records,include_horizons=True):
    bins=collections.Counter();providers=collections.Counter();families=collections.Counter();months=collections.Counter();instruments=collections.Counter();unique=set();flat=small=outside=0;errors=[]
    for task,h in records:
        y=task["outcomes"][(1,3,7).index(h)];z=support(task["anchor"],levels);label=bin_index(z,y)
        bins[label]+=1;flat+=y==task["anchor"];small+=y!=task["anchor"] and label==zero
        outside+=y<z[0] or y>z[-1];errors.append(abs(z[label]-y)/task["anchor"])
        unique.add((task["task_id"],h));providers[task["metadata"]["provider"]]+=1;families[task["metadata"]["family"]]+=1;months[task["origin"][:7]]+=1;instruments[task["metadata"]["instrument_class"]]+=1
    n=sum(bins.values());assert n==len(records)
    result={"presentations":n,"unique_horizon_examples":len(unique),"repeated_presentations":n-len(unique),"actual_unchanged":flat,"actual_unchanged_fraction":flat/n if n else None,"quantized_unchanged":bins[zero],"quantized_unchanged_fraction":bins[zero]/n if n else None,"changed_but_quantized_unchanged":small,"out_of_support":outside,"mean_relative_quantization_error":sum(errors)/n if n else None,"classes":[{"level_index":i,"log_return":v,"presentations":bins[i]} for i,v in enumerate(levels)],"providers":dict(providers),"families":dict(families),"origin_months":dict(months),"instruments":dict(instruments),"independence":"Presentations and overlapping windows are not independent market experiments"}
    if include_horizons:result["by_horizon"]={str(h):audit([(t,j) for t,j in records if j==h],False) for h in (1,3,7)}
    return result
evaluation_series={v["series_id"] for v in report["baseline"]["retrospective"]["cells"] if v["horizon_days"]==7}
corpora={}
for arm in ("same","expanded"):
    assert digest(data["training"][arm])==binding["training_corpus_sha256"][arm]
    corpora[arm]=audit([(t,h) for t in data["training"][arm] for h in (1,3,7)])
    corpora[arm]["same_evaluation_series_7d"]=audit([(t,7) for t in data["training"][arm] if t["series_id"] in evaluation_series],False)
runs=[]
for run in report["runs"]:
    s=run["state"];plan=batches(data["training"][s["arm"]],s["seed"],cfg["model"]["max_updates"],cfg["model"]["batch_size"],cfg["parent"]["examples_seen_at_parent"])
    assert batch_identity(plan)==s["batch_order_sha256"]
    full=audit([record for group in plan for record in group]);selected=audit([record for group in plan[:s["selected"]["update"]] for record in group])
    assert full["presentations"]==s["example_presentations"] and full["unique_horizon_examples"]==s["unique_horizon_examples_presented"] and full["repeated_presentations"]==s["repeated_horizon_presentations"]
    assert selected["presentations"]==s["selected"]["update"]*cfg["model"]["batch_size"]
    full["same_evaluation_series_7d"]=audit([(t,h) for group in plan for t,h in group if h==7 and t["series_id"] in evaluation_series],False)
    selected["same_evaluation_series_7d"]=audit([(t,h) for group in plan[:s["selected"]["update"]] for t,h in group if h==7 and t["series_id"] in evaluation_series],False)
    runs.append({"arm":s["arm"],"ordering_seed":s["seed"],"selected_additional_update":s["selected"]["update"],"batch_order_sha256":s["batch_order_sha256"],"full_run":full,"selected_checkpoint_prefix":selected})
value={"study_id":"ce-continuation-v21-exposure-audit","source_report_path":pointer["report_path"],"source_report_sha256":pointer["report_sha256"],"dataset_sha256":digest(data),"protocol_sha256":digest(cfg),"corpora":corpora,"runs":runs,"source_attribution":report["source_attribution"],"new_optimizer_updates":0,"new_inference_calls":0,"raw_inputs_published":False,"limitations":["Post-hoc descriptive audit, not a causal test","The model conditions on history and metadata; unconditional class frequencies do not determine conditional forecast quality","No retrospective outcomes are used for configuration or checkpoint selection","No future or protected outcomes retrieved"]}
out=pathlib.Path("artifacts/ce-continuation-v21-exposure");out.mkdir(parents=True,exist_ok=True)
(out/"exposure.json").write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
lines=["# What the continuation actually trained on","","This audit reconstructs each completed run's exact recorded batch hash from the unchanged private input snapshot. It performs no model inference or optimization. Counts are presentations, not independent market evidence.","","| Arm / ordering | Selected update | Examples to selected checkpoint | Zero-price-change labels | Small changes mapped to zero | Unique examples in full100updates | Repeated presentations in full100updates |","|---|---:|---:|---:|---:|---:|---:|"]
for r in runs:
    a=r["selected_checkpoint_prefix"];b=r["full_run"]
    lines.append("| "+r["arm"]+" /"+str(r["ordering_seed"])+" | "+str(r["selected_additional_update"])+" | "+str(a["presentations"])+" | "+str(a["quantized_unchanged"])+" | "+str(a["changed_but_quantized_unchanged"])+" | "+str(b["unique_horizon_examples"])+" | "+str(b["repeated_presentations"])+" |")
lines+=["","Zero-price-change labels describe the registered nearest-level supervision. They are not forecast probabilities. Small nonzero observed movements that map to the zero class are counted separately. The same output support and quantization are preserved in both arms.","","Source report SHA-256: "+pointer["report_sha256"],"Dataset SHA-256: "+digest(data),"","Raw histories, private paths and model resources are excluded. Source permissions and attribution remain those recorded in the original data audit.","","Prospective improvement is not yet established."]
(out/"findings.md").write_text("\n".join(lines)+"\n");print(json.dumps({"status":"passed","completed_runs":len(runs),"dataset_sha256":digest(data),"new_optimizer_updates":0,"new_inference_calls":0}))
