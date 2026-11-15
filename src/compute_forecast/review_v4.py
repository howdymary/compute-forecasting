"""Reconstruct the frozen study from hash-verified public artifacts."""
from __future__ import annotations
import argparse,hashlib,io,json,math,os,statistics,zipfile
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
RUN="c24ee0b5943f48c2bfa17032598f42f4"
ARCHIVE_SHA="5ec7ef997571dd925ef521895f9b950373f87d85cf8111bfe52adf5937e8c3e5"
ARCHIVE_URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run/experimental/downloads/43677783872.zip"
FORECAST_SHA="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
TREE=["tree_56_3","tree_56_7","tree_28_3","tree_28_7"]
INITIAL=["last_value","last_value_empirical"]
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,allow_nan=False).encode()).hexdigest()
def encoded(v):return (json.dumps(v,indent=2,allow_nan=False)+"\n").encode()
def close(a,b):
    if not math.isclose(float(a),float(b),rel_tol=0,abs_tol=1e-12):raise ValueError("Source arithmetic mismatch")
def sources(root):
    root=Path(root);m=json.loads((root/"results/manifest.json").read_bytes());out={}
    for name,meta in m["files"].items():
        raw=(root/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=meta["sha256"]:raise ValueError("Changed source "+name)
        out[name]=json.loads(raw) if name.endswith(".json") else raw
    if hashlib.sha256(out["results/frozen-v1/forecasts.csv"]).hexdigest()!=FORECAST_SHA:raise ValueError("Official CSV changed")
    return out,m
def read_archive(raw):
    if hashlib.sha256(raw).hexdigest()!=ARCHIVE_SHA:raise ValueError("Archive checksum mismatch")
    z=zipfile.ZipFile(io.BytesIO(raw))
    if len(z.infolist())>500 or sum(x.file_size for x in z.infolist())>100_000_000:raise ValueError("Archive limit")
    manifest=json.loads(z.read("member-manifest.json"));out={}
    for name,meta in manifest["members"].items():
        if ".." in Path(name).parts or Path(name).is_absolute():raise ValueError("Archive path")
        value=z.read(name)
        if len(value)!=meta["bytes"] or hashlib.sha256(value).hexdigest()!=meta["sha256"]:raise ValueError("Archive member changed")
        if name.endswith(".json"):out[name]=json.loads(value)
    return out,manifest
def one(archive,suffix):
    matches=[(k,v) for k,v in archive.items() if k.endswith(suffix)]
    if len(matches)!=1:raise ValueError("Ambiguous artifact "+suffix)
    return matches[0]
def indexed(report):
    rows={}
    for trace in report["traces"]:
        if len(trace["cases"])!=trace["n_cells"]:raise ValueError("Cell denominator")
        for c in trace["cases"]:
            k=(trace["origin"],c["series_id"],int(c["horizon_days"]))
            if k in rows:raise ValueError("Duplicate cell")
            if any(not math.isfinite(float(c[x])) for x in ("loss","baseline_loss","width")):raise ValueError("Nonfinite metric")
            rows[k]={**c,"origin":trace["origin"]}
    if len(rows)!=report["n_cells"]:raise ValueError("Report denominator")
    close(statistics.mean(c["loss"] for c in rows.values()),report["pinball"])
    return rows
def attribution(candidate,reference,label):
    a,b=indexed(candidate),indexed(reference)
    if set(a)!=set(b):raise ValueError("Unmatched comparison cells")
    n=len(a);delta=candidate["pinball"]-reference["pinball"];groups={}
    for dimension,field in (("series","series_id"),("origin","origin"),("horizon","horizon_days")):
        grouped={}
        for k,c in a.items():grouped.setdefault(str(c[field]),[]).append(k)
        values=[]
        for name,keys in sorted(grouped.items()):
            ca=statistics.mean(a[k]["loss"] for k in keys);rb=statistics.mean(b[k]["loss"] for k in keys)
            base=statistics.mean(a[k]["baseline_loss"] for k in keys)
            values.append({"id":name,"candidate_pinball":ca,"reference_pinball":rb,"delta":ca-rb,"weighted_contribution":len(keys)/n*(ca-rb),"n_cells":len(keys),"candidate_coverage":sum(a[k]["covered"] for k in keys)/len(keys),"reference_coverage":sum(b[k]["covered"] for k in keys)/len(keys),"candidate_width":statistics.mean(a[k]["width"] for k in keys),"reference_width":statistics.mean(b[k]["width"] for k in keys),"baseline_pinball":base,"relative_skill":None if abs(base)<1e-12 else 1-ca/base})
        close(sum(v["weighted_contribution"] for v in values),delta);groups[dimension]=values
    cells=[{"origin":k[0],"series_id":k[1],"horizon_days":k[2],"candidate_loss":a[k]["loss"],"reference_loss":b[k]["loss"],"delta":a[k]["loss"]-b[k]["loss"],"weighted_contribution":(a[k]["loss"]-b[k]["loss"])/n,"candidate_covered":a[k]["covered"],"reference_covered":b[k]["covered"]} for k in sorted(a)]
    return {"id":label,"cohort_id":"v2_selector_12","classification":"retrospective_previously_inspected","candidate":candidate["policy"],"reference":reference["policy"],"candidate_pinball":candidate["pinball"],"reference_pinball":reference["pinball"],"delta":delta,"relative_change":None if reference["pinball"]==0 else delta/reference["pinball"],"n_cells":n,"n_origins":len({k[0] for k in a}),"groups":groups,"cells":cells}
def mechanism(tasks,trained,hidden):
    by_task={t["task_id"]:t for t in tasks};h={t["task_id"]:t for t in hidden["traces"]};rows=[]
    if set(h)!={t["task_id"] for t in trained["traces"]}:raise ValueError("Unmatched paired tasks")
    for trace in trained["traces"]:
        t=by_task[trace["task_id"]];other=h[trace["task_id"]];checks=[]
        for v in (trace,other):
            reveal=v["revealed"]
            if len(reveal)!=6 or len(set(reveal))!=6 or reveal[:2]!=INITIAL:raise ValueError("Reveal contract")
            chosen=min(reveal,key=lambda c:t["validation"][c]["loss"])
            if chosen!=v["selected_config_id"]:raise ValueError("Recorded chooser mismatch")
            close(t["future_evaluator_only"][chosen]["loss"],v["pinball"])
            if t["future_evaluator_only"][chosen]["cases"]!=v["cases"]:raise ValueError("Recorded scored cases changed")
            checks.append({"selected_config_id":chosen,"tied_minima":[c for c in reveal if t["validation"][c]["loss"]==t["validation"][chosen]["loss"]]})
        fixed=INITIAL+TREE;selected=min(fixed,key=lambda c:t["validation"][c]["loss"]);loss=t["future_evaluator_only"][selected]["loss"]
        raw_a=trace.get("forecast_rows");raw_b=other.get("forecast_rows")
        rows.append({"task_id":t["task_id"],"origin":t["origin"],"series_ids":t["series_ids"],"n_cells":trace["n_cells"],"feedback_order":trace["revealed"],"hidden_order":other["revealed"],"same_order":trace["revealed"]==other["revealed"],"same_reveal_set":set(trace["revealed"])==set(other["revealed"]),"matches_tree_portfolio":set(trace["revealed"])==set(fixed),"feedback_choice":checks[0]["selected_config_id"],"hidden_choice":checks[1]["selected_config_id"],"same_terminal_choice":checks[0]["selected_config_id"]==checks[1]["selected_config_id"],"ties":checks,"feedback_pinball":trace["pinball"],"hidden_pinball":other["pinball"],"same_forecast_loss":abs(trace["pinball"]-other["pinball"])<1e-12,"prediction_equivalence":raw_a==raw_b if raw_a is not None and raw_b is not None else None,"prediction_evidence":"Raw quantile rows not retained in these public evaluations; equal losses alone are insufficient","compressed_choice":selected,"compressed_pinball":loss,"compressed_choice_matches":selected==trace["selected_config_id"],"compressed_loss_matches":abs(loss-trace["pinball"])<1e-12,"revealed_validation":[{"config_id":c,**t["validation"][c]} for c in trace["revealed"]]})
    return {"classification":"posthoc_descriptive_portfolio_selected_after_evaluation","run_id":RUN,"tree_portfolio":TREE,"n_tasks":len(rows),"n_cells":sum(r["n_cells"] for r in rows),"same_reveal_sets":sum(r["same_reveal_set"] for r in rows),"same_terminal_choices":sum(r["same_terminal_choice"] for r in rows),"changed_orders":sum(not r["same_order"] for r in rows),"compressed_choice_matches":sum(r["compressed_choice_matches"] for r in rows),"compressed_loss_matches":sum(r["compressed_loss_matches"] for r in rows),"raw_prediction_equality":None,"tasks":rows,"claim":"The observed portfolio and recorded terminal choices can be compressed on these four tasks. This is not a preregistered baseline or proof of equivalence on unfamiliar tasks."}
def readiness(tasks):
    from .policy_v2 import reachable_training_rewards
    train=[t for t in tasks if t["phase"]=="training"];dev=[t for t in tasks if t["phase"]=="development"]
    audit=[reachable_training_rewards(t) for t in train];informative=sum(v["possible_terminal_reward_range"]>1e-8 for v in audit)
    fingerprints=[digest({"observation":t["observation"],"validation":{k:round(v["loss"],10) for k,v in t["validation"].items()}}) for t in train]
    criteria={"distinct_training_tasks":{"actual":len({t["task_id"] for t in train}),"minimum":24},"training_origins":{"actual":len({t["origin"] for t in train}),"minimum":8},"informative_training_tasks":{"actual":informative,"minimum":12},"development_origins":{"actual":len({t["origin"] for t in dev}),"minimum":4},"unique_contexts":{"actual":len(set(fingerprints)),"minimum":12}}
    passed=all(v["actual"]>=v["minimum"] for v in criteria.values())
    return {"status":"ready" if passed else "gated_pending_broader_training_data","criteria":criteria,"rationale":"Conservative engineering diversity gates, fixed before any new optimization; not a statistical power or generalization guarantee. Repeats and prompt augmentation do not increase independent task counts.","training_tasks":len(train),"training_origins":sorted({t["origin"] for t in train}),"development_origins":sorted({t["origin"] for t in dev}),"zero_reward_variation_tasks":len(train)-informative,"reward_audit":audit,"near_duplicate_definition":"Exact observation plus validation-loss fingerprint rounded to 10 decimals; this is a diagnostic, not an independence estimator","unique_context_fingerprints":len(set(fingerprints)),"optimizer_updates_launched":0}
def build(root,raw,source_sha):
    from .policy_v2 import make_tasks
    data,manifest=sources(root);archive,index=read_archive(raw)
    _,grid=one(archive,"campaign-v2-grid/v2-grid/grid.json") if any(k.endswith("campaign-v2-grid/v2-grid/grid.json") for k in archive) else one(archive,"/grid.json")
    tasks,_=make_tasks(grid)
    prefix="campaign-v2-policy-soft-17/v2-policy/"
    names={n:one(archive,prefix+n+".json") for n in ("trained-evaluation","starting-evaluation","no-observation","controls")}
    trained=names["trained-evaluation"][1];starting=names["starting-evaluation"][1];hidden=names["no-observation"][1]
    control=next(v for v in names["controls"][1] if v["policy"]=="training_selected_static")
    comparisons=[attribution(trained,starting,"starting"),attribution(trained,control,"static"),attribution(trained,hidden,"hidden")]
    for seed in (17,29,43):
        p="runs/rl/campaign-v2-rl-"+str(seed)+"/v2-policy/"
        a=one(archive,p+"trained-evaluation.json");b=one(archive,p+"sft-parent-evaluation.json")
        comparisons.append(attribution(a[1],b[1],"rl_parent_"+str(seed)))
    summary=data["results/expanded-v2/summary.json"]
    result={"schema_version":4,"study_id":"compute-forecast-review-v4","source_sha":source_sha,"generated_at":datetime.now(timezone.utc).isoformat(),"classification":"Post-hoc descriptive reconstruction; frozen studies unchanged","source_manifest_sha256":hashlib.sha256((Path(root)/"results/manifest.json").read_bytes()).hexdigest(),"archive_sha256":ARCHIVE_SHA,"source_artifacts":{n:index["members"][path] | {"path":path} for n,(path,_) in names.items()},"official_csv_sha256":FORECAST_SHA,"mechanism":mechanism(tasks,trained,hidden),"comparisons":comparisons,"readiness":readiness(tasks),"teacher_alignment":summary["analysis"]["teacher_alignment_training_only"],"experiment_status":{"prospective":"registered_pending_first_eligible_issuance","interval":"registered_pending_vintage_correct_residuals","learning":"gated_pending_broader_training_data","evidence":"registered_pending_matched_forward_tasks"},"existing_prospective":summary["prospective"],"accounting":{"new_optimizer_updates":0,"new_model_inferences":0,"new_numerical_trials":0,"analysis_compute":"Hosted CPU reconstruction of saved results","cost_usd":None},"limitations":["Three dependent reused evaluation dates; 12 cells are not independent cases","Compressed portfolio is identified post hoc","Raw quantile prediction equality is unavailable and not inferred from equal loss","Independent context is not joined to official forecasts"]}
    from .public_results import private_guard
    private_guard(result)
    return result
def validate(v):
    if v["schema_version"]!=4 or v["official_csv_sha256"]!=FORECAST_SHA:raise ValueError("V4 contract")
    m=v["mechanism"]
    if m["n_tasks"]!=4 or m["n_cells"]!=12:raise ValueError("Mechanism scope")
    for comparison in v["comparisons"]:
        if comparison["n_cells"]!=12 or comparison["cohort_id"]!="v2_selector_12":raise ValueError("Comparison scope")
        for values in comparison["groups"].values():
            if sum(g["n_cells"] for g in values)!=12:raise ValueError("Attribution count")
            close(sum(g["weighted_contribution"] for g in values),comparison["delta"])
    from .public_results import private_guard
    private_guard(v)
    return v
def publish_files(files):
    """GitHub-only nonforce publication from an exact source head."""
    import base64
    from .public_results import github
    if os.environ.get("GITHUB_REF")!="refs/heads/compute-observatory":raise ValueError("Publication branch")
    repo=os.environ["GITHUB_REPOSITORY"];b=github("GET","repos/"+repo+"/branches/compute-observatory");parent=b["commit"]["sha"]
    if parent!=os.environ["GITHUB_SHA"]:raise ValueError("Branch advanced before v4 publication")
    entries=[]
    for path,raw in files.items():
        if not path.startswith("results/review-v4/"):raise ValueError("Unapproved output path")
        blob=github("POST","repos/"+repo+"/git/blobs",{"encoding":"base64","content":base64.b64encode(raw).decode()})
        entries.append({"path":path,"mode":"100644","type":"blob","sha":blob["sha"]})
    tree=github("POST","repos/"+repo+"/git/trees",{"base_tree":b["commit"]["commit"]["tree"]["sha"],"tree":entries})
    commit=github("POST","repos/"+repo+"/git/commits",{"message":"Publish reconstructed policy mechanisms and research attribution","parents":[parent],"tree":tree["sha"]})
    if github("GET","repos/"+repo+"/branches/compute-observatory")["commit"]["sha"]!=parent:raise ValueError("Branch changed during publication")
    github("PATCH","repos/"+repo+"/git/refs/heads/compute-observatory",{"sha":commit["sha"],"force":False})
    return commit["sha"]

def publish_append_only(files):
    """Retain uniquely named reports while preserving independently advanced heads."""
    import base64,re
    from urllib.error import HTTPError
    from .public_results import github,private_guard
    if os.environ.get("GITHUB_REF")!="refs/heads/compute-observatory":raise ValueError("Publication branch")
    repo=os.environ["GITHUB_REPOSITORY"];blobs={}
    for path,raw in files.items():
        if not re.fullmatch(r"results/review-v4/(market|runtime|vintages|prospective)/[0-9]+(?:-[a-z]+)?\.json",path):raise ValueError("Only uniquely named operation reports may append")
        private_guard(json.loads(raw))
        blobs[path]=github("POST","repos/"+repo+"/git/blobs",{"encoding":"base64","content":base64.b64encode(raw).decode()})["sha"]
    for attempt in range(3):
        branch=github("GET","repos/"+repo+"/branches/compute-observatory");parent=branch["commit"]["sha"];entries=[]
        for path,sha in blobs.items():
            try:existing=github("GET","repos/"+repo+"/contents/"+path+"?ref="+parent)["sha"]
            except HTTPError as error:
                if error.code!=404:raise
                existing=None
            if existing and existing!=sha:raise ValueError("An immutable operation report already exists with different bytes")
            if not existing:entries.append({"path":path,"mode":"100644","type":"blob","sha":sha})
        if not entries:return parent
        tree=github("POST","repos/"+repo+"/git/trees",{"base_tree":branch["commit"]["commit"]["tree"]["sha"],"tree":entries})
        commit=github("POST","repos/"+repo+"/git/commits",{"message":"Publish versioned v4 operation receipts","parents":[parent],"tree":tree["sha"]})
        if github("GET","repos/"+repo+"/branches/compute-observatory")["commit"]["sha"]!=parent:continue
        try:
            github("PATCH","repos/"+repo+"/git/refs/heads/compute-observatory",{"sha":commit["sha"],"force":False})
            return commit["sha"]
        except HTTPError as error:
            if error.code not in (409,422):raise
    raise ValueError("Branch changed repeatedly during append-only publication")

def main():
    p=argparse.ArgumentParser();p.add_argument("--publish",action="store_true");p.add_argument("--archive");a=p.parse_args()
    raw=Path(a.archive).read_bytes() if a.archive else urlopen(ARCHIVE_URL,timeout=90).read()
    v=validate(build(".",raw,os.environ.get("GITHUB_SHA","uncommitted")))
    out=Path("artifacts/review-v4");out.mkdir(parents=True,exist_ok=True);(out/"findings.json").write_bytes(encoded(v))
    fixture={"status":"passed","kind":"synthetic_contract_fixture_not_market_data","weighted_delta":(2*(.3-.2)+(.1-.4))/3}
    files={"results/review-v4/findings.json":encoded(v),"results/review-v4/reproduction.json":encoded({"status":"verified","source_sha":v["source_sha"],"archive_sha256":ARCHIVE_SHA,"official_csv_sha256":FORECAST_SHA,"n_cells":12,"source_member_hashes_verified":True,"synthetic_fixture":fixture})}
    files["results/review-v4/manifest.json"]=encoded({"schema_version":4,"source_sha":v["source_sha"],"files":{k:{"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)} for k,b in files.items()}})
    for name,b in files.items():(out/Path(name).name).write_bytes(b)
    if a.publish:print("V4_PUBLISHED_COMMIT:"+publish_files(files),flush=True)
    print("V4_FINDINGS:"+json.dumps({"tasks":v["mechanism"]["n_tasks"],"same_sets":v["mechanism"]["same_reveal_sets"],"compressed_matches":v["mechanism"]["compressed_loss_matches"],"readiness":v["readiness"]["status"]}),flush=True)
if __name__=="__main__":main()
