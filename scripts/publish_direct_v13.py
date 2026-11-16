"""Publish versioned corrected-sampling controls; never replace v12 outputs."""
import hashlib,json,os,pathlib,subprocess,time
from compute_forecast.direct_forecast_v12 import cell_loss,price_quantiles,summarize,matched
repo=os.environ["GITHUB_REPOSITORY"];run=os.environ["GITHUB_RUN_ID"];root=pathlib.Path("inputs/v13");prefix="results/direct-v13/runs/"+run+"/"
def api(path,body=None,method=None):
    c=["gh","api","repos/"+repo+"/"+path]
    if method:c+=["-X",method]
    if body is not None:c+=["--input","-"]
    return json.loads(subprocess.check_output(c,input=json.dumps(body) if body is not None else None,text=True))
payload={};results=[]
for seed in (17,29,43):
    directory=root/("seed-"+str(seed))
    if not directory.exists():continue
    path=directory/"result.json"
    if path.exists():
        result=json.loads(path.read_text())
        assert result["new_optimizer_updates"]==result["new_persistent_checkpoints"]==0
        predictions=[]
        for name in ("evaluation-selected.json","evaluation-base.json"):
            value=json.loads((directory/name).read_text());assert value["summary"]==summarize(value["cells"])
            for task in value["tasks"]:
                qs=price_quantiles(task["sample_returns"],task["anchor"]) if not task["fallback"] else [[task["anchor"]]*3 for _ in (1,3,7)]
                assert task["sampling_seed"] is None and len(qs)==3
                assert task["distinct_vectors"]==len({tuple(v) for v in task["sample_returns"]})
                for index,row in enumerate(task["cells"]):
                    assert [row[k] for k in ("q10","q50","q90")]==qs[index]
                    assert abs(cell_loss(row["outcome"],qs[index])-row["loss"])<1e-12
            predictions.append(value)
        assert matched(predictions[0]["cells"],predictions[1]["cells"])==result["comparison_to_base"]
        results.append(result)
    for f in directory.glob("*.json"):
        raw=f.read_text();assert "tinker://" not in raw
        payload[prefix+"seed-"+str(seed)+"/"+f.name]=raw
assert payload,"No retained control artifacts"
summary={"study_id":"direct-sampling-v13","created_at":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),"status":"completed" if len(results)==3 else "partial","runs":results,"new_optimizer_updates":0,"original_v12_outputs_preserved":True,"prospective_accuracy":"not_established"}
payload[prefix+"report.json"]=json.dumps(summary,indent=2,allow_nan=False)+"\n"
manifest={"files":[{"path":p[len(prefix):],"sha256":hashlib.sha256(v.encode()).hexdigest(),"bytes":len(v.encode())} for p,v in sorted(payload.items())]}
payload[prefix+"manifest.json"]=json.dumps(manifest,indent=2)+"\n"
payload["results/direct-v13/latest.json"]=json.dumps({"study_id":summary["study_id"],"report_path":prefix+"report.json","report_sha256":hashlib.sha256(payload[prefix+"report.json"].encode()).hexdigest(),"status":summary["status"]},indent=2)+"\n"
lines=["# Frozen-weight sampling control v13","","Additional retrospective implementation control. No new optimizer updates and no checkpoint reselection. Original v12 forecasts remain unchanged.","","| Seed | Frozen update | Base7-day loss | Trained7-day loss | Trained coverage | Mean width |","| --- | ---: | ---: | ---: | ---: | ---: |"]
for r in results:
    h=r["selected"]["by_horizon"]["7"]
    lines.append(f"| {r['seed']} | {r['frozen_selection']['update']} | {r['base']['primary_pinball']:.8f} | {r['selected']['primary_pinball']:.8f} | {h['coverage']:.1%} | {h['width']:.6f} |")
lines+=["","22 tasks,66 horizon cells,three reused dependent origins. The same fixed inference budget yields stochastic samples; arithmetic is reproducible from the retained vectors. This does not establish prospective accuracy or supplementary-signal value.","","[Registered control](../configs/direct-sampling-v13.json) · [Sampling diagnosis](direct-v13-sampling-correction.md) · [Versioned results](../"+prefix+"report.json)"]
payload["docs/direct-v13-findings.md"]="\n".join(lines)+"\n"
for attempt in range(4):
    head=api("git/ref/heads/compute-observatory")["object"]["sha"];commit=api("git/commits/"+head)
    tree=api("git/trees",{"base_tree":commit["tree"]["sha"],"tree":[{"path":p,"mode":"100644","type":"blob","content":v} for p,v in payload.items()]},"POST")
    made=api("git/commits",{"parents":[head],"tree":tree["sha"],"message":"Publish frozen-weight direct forecasting sampling control"},"POST")
    if api("git/ref/heads/compute-observatory")["object"]["sha"]!=head:continue
    try:api("git/refs/heads/compute-observatory",{"sha":made["sha"],"force":False},"PATCH")
    except subprocess.CalledProcessError:time.sleep(1);continue
    print("SAMPLING_CONTROL_PUBLICATION "+made["sha"]);break
else:raise RuntimeError("Shared head advanced; publication refused")
