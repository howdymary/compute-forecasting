"""Publish measured final findings from verified public artifacts, on the authorized branch only."""
from __future__ import annotations
import base64,hashlib,json,os,subprocess
from pathlib import Path
from urllib.request import urlopen
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
FILES={"README.md","docs/campaign-v2-findings.md","docs/campaign-v2-checkpoints.json","docs/campaign-v2-final-status.json","docs/campaign-v2-performance.json"}
CSV_SHA="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
def score(p,label):
    return next(c for c in p["comparisons"] if c["policy"]==label)
def selected(p):
    return score(p,"selected_"+p["mode"]+"_"+p["objective"])
def validate(data):
    reports=data["policy_reports"]
    sft=[p for p in reports if p["mode"]=="sft"];rl=[p for p in reports if p["mode"]=="rl"]
    if len(sft)!=6 or len(rl)!=3:raise ValueError("Complete six-SFT/three-RL reports required")
    if {(p["seed"],p["objective"]) for p in sft}!={(s,o) for s in (17,29,43) for o in ("hard","soft")}:raise ValueError("Wrong SFT identities")
    if sum(p["actual_optimizer_updates"] for p in sft)!=600:raise ValueError("Wrong actual SFT count")
    if any(p["future_competition_truth_loaded"] or p["v1_final_used"] for p in reports):raise ValueError("Protected outcomes were used")
    if "complete_encoding_gp_control" not in data["analysis"] or not data.get("artifact_archive"):raise ValueError("Final controls/archive not ready")
    if "tinker://" in json.dumps(data):raise ValueError("Private model path in public data")
    for p in reports:
        if selected(p)["n_cells"]!=12:raise ValueError("Selector scope changed")
        if p["mode"]=="rl":score(p,"sft_parent")
    return sorted(sft,key=lambda p:(p["seed"],p["objective"])),sorted(rl,key=lambda p:p["seed"])
def money(value):
    return "unknown" if value is None else "USD "+format(value,".8f").rstrip("0").rstrip(".")
def render(data,performance):
    sft,rl=validate(data);a=data["analysis"];first=sft[0];base=score(first,"starting_policy");archive=data["artifact_archive"]
    def dev(p):return next(c["development_pinball"] for c in p["checkpoints"] if c["update"]==p["selected_update"])
    deployed=min(sft,key=lambda p:(dev(p),p["selected_update"],p["seed"],p["objective"]))
    trained=selected(deployed);improved=sum(selected(p)["pinball"]<score(p,"sft_parent")["pinball"]-1e-12 for p in rl)
    tied=sum(abs(selected(p)["pinball"]-score(p,"sft_parent")["pinball"])<1e-12 for p in rl);worse=3-improved-tied
    blind=sum(abs(selected(p)["pinball"]-score(p,"selected_no_observation")["pinball"])<1e-12 for p in sft)
    total_rl=sum(p["actual_optimizer_updates"] for p in rl)
    cycles=[r for r in data.get("autonomy_runs",[]) if r.get("status")=="completed"];fresh=sum(r.get("new_executions",0) for r in cycles);reads=sum(r.get("actual_cross_role_reads",0) for r in cycles)
    lines=["# Compute Forecast v2: measured findings","",
      "All six selected SFT checkpoints lower pooled loss versus starting weights on three reused, dependent A100 dates. This is a retrospective result; it does not replace the original frozen submission.",
      "",
      f"The development-selected operational checkpoint is soft/seed {deployed['seed']}, update {deployed['selected_update']}: {trained['pinball']:.8f} pinball versus {base['pinball']:.8f} for starting weights ({(1-trained['pinball']/base['pinball'])*100:.2f}% lower). Agent-feedback-hidden controls tie in {blind}/6 SFT runs.",
      f"Three RL reports cover {total_rl} actual optimizer updates: {improved} lower loss versus their SFT parent, {tied} tie and {worse} increase loss. Completing updates is separate from demonstrating improvement.",
      "",
      "The original frozen v1 SFT result remains 0.01781945 versus 0.01735406 starting (2.68% worse). Its 111-row, 37-series November6 export remains byte-identical.",
      "",
      "## What the experiment measures","",
      "The pack measures advertised GPU rental offers, not transactions, available capacity or hardware resale values. Original targets and the Pacific scorer are retained.",
      "V2 training has nine eligible tasks across six dates (June20/27, July4/11/18/24), with every reward label ending by July31. Development has six tasks over August8/15/22. Selector evaluation has four tasks over August29, September5/12: 12 series-horizon cells, three dependent dates, A100 40GB and A100 SXM 80GB only.",
      "These evaluation dates were previously inspected during v1 development. They are excluded from new weight updates/checkpoint selection, but are not an untouched test. The original September27–October25 final and restricted November7–13 outcomes are excluded.",
      "The full numerical-grid evaluation has 15 cells. Its scores must not be mixed with the 12-cell selector scores. A100 40GB contributes three selector cells and SXM80GB nine; pooled SFT improvement is concentrated in SXM80GB. SFT loss on A100 40GB is 0.00290788 versus 0.00254829 starting, about14.1% worse.",
      "",
      "## Matched selector comparison","",
      "All search procedures use the same 42 candidates, two common persistence starts and four additional choices. The final deterministic chooser minimizes revealed matured validation loss. The six-trial budget counts cached result reveals, not equal wall time, dollars or offline training expenditure.",
      "",
      "| Procedure | Pinball | Skill vs last value |","| --- | ---: | ---: |"]
    refs=[("Official last value",{"pinball":base["baseline_pinball"]}),("Starting policy",base),("Development-selected SFT",trained),
      ("Static, training-validation ranked",score(first,"training_selected_static")),("Static, exhaustive training-outcome selected",a["stronger_static_control"]),
      ("Random search, 100-seed mean",score(first,"random_100_seed_distribution")),("GP, original encoding",score(first,"gp_expected_improvement")),
      ("GP, complete metadata",a["complete_encoding_gp_control"]),("Single forecaster selected on training: "+a["training_selected_fixed_forecaster"]["config_id"],a["training_selected_fixed_forecaster"])]
    for label,r in refs:lines.append(f"| {label} | {r['pinball']:.8f} | {(1-r['pinball']/base['baseline_pinball'])*100:.2f}% |")
    lines+=["","The exhaustive static portfolio is selected among91,390 possibilities using training outcomes only. Its worse evaluation result is retained. The additional complete-metadata GP preserves the original kernel, acquisition, starts and budget; it is an added retrospective control, not a replacement preregistered result.","",
      "## Every training seed","",
      "| Mode / objective / seed | Actual updates | Selected update | Development loss | Evaluation loss | Reference loss |","| --- | ---: | ---: | ---: | ---: | ---: |"]
    for p in sft+rl:
        reference=score(p,"sft_parent" if p["mode"]=="rl" else "starting_policy")
        lines.append(f"| {p['mode']} / {p['objective']} / {p['seed']} | {p['actual_optimizer_updates']} | {p['selected_update']} | {dev(p):.8f} | {selected(p)['pinball']:.8f} | {reference['pinball']:.8f} |")
    lines+=["","Checkpoints are selected by development loss with earlier-update ties, including update zero. The global operational SFT choice additionally breaks ties by seed/objective. Evaluation-best seeds are not substituted.",
      "[All evaluated checkpoint IDs, seeds, source revisions and recovery metadata](campaign-v2-checkpoints.json) are retained. IDs hash private sampler resource paths; they are not weight-content hashes. The model resources stay in the owner's account.",
      "",
      "## RL execution and storage recovery","",
      "RL uses genuinely sampled bounded actions and logged conditional propensities. Four trajectories share a task; reward is negative subsequent training-period loss divided by a training-only scale and clipped to[-5,5]. A categorical policy-gradient objective uses their mean reward as baseline. Constant groups do not update weights; five consecutive constant groups stop training. The60-group ceiling counts sampling iterations, separately from optimizer updates.",
      "A training-only curriculum selects registered cases with reachable clipped-reward variation; evaluation still covers all original eligible cases. The RL amendment was fixed before its first updates, after two seed17 SFT evaluations had been seen; it remains exploratory.",
      "The initial clients hit Tinker's free checkpoint-storage cap after exactly ten updates/thirteen groups each for seeds17/29; seed43 could not start. Cleanup removed26 temporary rollout samplers. Continuations restore the exact Adam/RNG prefixes, discard no optimizer updates and include those13 groups in the same60-group limit. Consumed samplers and superseded unevaluated recovery states are removed after successful use/replacement; original and evaluated models are preserved. No billing settings changed.",
      ""]
    for p in rl:
        if p.get("rl_gate"):lines.append(f"- Seed {p['seed']} gate: {p['rl_gate']}")
    lines+=["","RL's incremental reference is its own frozen SFT parent. A zero-update selected checkpoint means no demonstrated benefit from RL selection, even if other updates were performed.",
      "",
      "## Feedback, evidence and criticism","",
      "The no-observation arm hides history summaries and validation scores from the agent, while retaining tested-arm IDs/budget. The final deterministic chooser continues using matured validation in every arm. A forecast-loss tie therefore concerns feedback to experiment selection, not removal of all validation.",
      "",
      "| SFT objective / seed | Primary | Feedback hidden | Fixed critic added | Source metadata added |","| --- | ---: | ---: | ---: | ---: |"]
    for p in sft:
        vals=[selected(p)["pinball"],score(p,"selected_no_observation")["pinball"],score(p,"selected_with_criticism")["pinball"],score(p,"selected_with_method_evidence")["pinball"]]
        lines.append(f"| {p['objective']} / {p['seed']} | "+" | ".join(f"{v:.8f}" for v in vals)+" |")
    lines+=["","Action sequences can change while the selected forecaster/loss stays the same. Added evidence is a fixed source-metadata packet; its negative effects also involve inference-time prompt shift and do not establish that research evidence or criticism is universally harmful.",
      "Training-only teacher alignment is mixed: its validation-oracle choice beats persistence on one task, ties five and worsens three; rank correlations range approximately−0.291 to0.748. Paired-origin and leave-one-origin-out analyses are in the archive/API. These are descriptive checks across the same three dependent dates, not population confidence intervals.",
      "Hindsight regret compares the selected loss with the best future-scoring arm among42 after evaluation. That oracle may not be reachable under the fixed validation chooser.",
      "",
      "## Numerical models and measurement controls","",
      "The registry has42 configurations: official references, Ridge representations, direct autoregression, EWMA, quantile gradient boosting, convex mixtures and auxiliary-price controls. Chronos was not added. Numerical preprocessing/calibration uses permitted past data, preserves missingness and reports fallbacks.",
      "On the separate15-cell evaluation, tree_28_3/tree_28_7 score0.01335719 with five fallback cases; tree_56_3 scores0.01353057 without fallback; empirical persistence/drift score0.01412099. These are retrospective rows, not competition leaderboard results or replacement submissions.",
      "Matched price-value removal keeps absolute-level/log targets, 56-day windows, alpha100, train-only imputation and original missingness flags fixed. Removing nine price predictors increases level loss from0.02037651 to0.02903200 and log loss from0.02138023 to0.03128927, roughly42.5%/46.3%. It is a15-cell conditional diagnostic, not an economic mechanism claim. The earlier unmatched diagnostic also changed target/anchor formulation and remains labeled separately.",
      "Actual fit-mask auditing at18 origins finds evaluation auxiliary imputation about0.018% for raw composition and3.03% for fixed basket. Repeated masks are not independent data. The original v1 finding remains mixed: best individual fixed-basket configuration, lower matched-configuration mean for target-only features.",
      "",
      "## Operational autonomy and sources","",
      f"{len(cycles)} completed research cycles made {sum(r.get('actual_trials',0) for r in cycles)} numerical trials through {fresh} fresh Modal calls, with {reads} verified cross-role memory reads. Repeated training-origin observations are not independent new market evidence.",
      "Criticism of zero-loss July24 tasks led the starting scientist to choose a non-flat July18 task. The restored development-selected SFT policy also executed five fresh calls on July18, made context-sensitive choices and ultimately selected empirical persistence; its alternatives did not improve the task. Different operational contexts prevent a causal trained-versus-starting comparison.",
      "Exa supplied40 distinct methodological searches plus one Snapshot capability probe and76 unique URLs. Current evidence stays outside historical market inputs. Accepted Snapshot parameters do not verify historical entitlement, page/ranking vintage or numerical-data vintage. Raw bodies remain private; an initial retention failure and subsequent re-retrieval are disclosed.",
      "past.dev records preserve authorship, IDs and required-source recall checks. Canonical authored text is used after verification or a disclosed fallback. This establishes cross-role use, not a measured memory-system accuracy gain. The skeptic is bounded deterministic code, not an independently trained researcher.",
      "",
      "## Prospective commitment and publication","",
      "The corrected prospective manifest was issued November15 at02:55:42 UTC for November16/18/22, using a nine-day-old November6 snapshot. There are42 predictions across14 H100/A100 series; outcomes are pending and do not mature before the event. Numerical rows remain private pending publication review. The earlier UTC-misaligned manifest is retained as superseded.",
      "Commitment428296e044ca0a5c362ee5b96d9488c6fe47cd59be6a3d70000ac2c51cbf29d2 hashes the private record's sorted-key Python JSON serialization, with default separators and ensure_ascii=True, not its pretty-file bytes. See the public manifest for exact hash semantics.",
      "The pack compilation license is described as CC BY4.0, owner's default pending confirmation, with upstream terms unresolved. Aggregation does not establish redistribution permission. Raw offers, restricted excerpts, private resources and credentials stay private.",
      "Provider/configuration normalization is established practice: [Silicon Data](https://www.silicondata.com/products/silicon-index) and [SemiAnalysis](https://semianalysis.com/gpu-pricing-index/). Our contribution is an inspectable empirical study, not an invention/first-benchmark claim. A frozen data vintage and pretrained-model contamination remain limitations.",
      "",
      "## Runtime, cost and verification","",
      f"The numerical stage ran {performance['origins']} origins and {performance['method_origin_results']} method-origin results in {performance['stage_wall_seconds']:.3f} wall seconds, about {performance['origins_per_minute']:.3f} origins/minute. Function durations sum to {performance['sum_function_elapsed_seconds']/60:.2f} minutes. This includes stage cold-start/client overhead and does not establish serial speedup or GPU utilization.",
      "Costs below are provider-reported estimates before credits where available. They can lag and do not establish remaining balances; unknown is not zero.",""]
    usage=data.get("provider_usage") or data.get("usage") or {}
    for provider in ("tinker","modal","exa"):
        record=usage.get(provider,{})
        lines.append(f"- {provider}: {money(record.get('gross_reported_cost_usd'))}; status {record.get('status','unavailable')}.")
    lines+=["","See [the complete usage/provenance JSON](campaign-v2-final-status.json) for attribution scope, timestamps and receipt counts. SDK retry/failure totals are not completely instrumented; memory HTTP statuses and engineering failures remain in traces/Actions.",
      "The measured finalizer verified protected source blobs, all nine reports, the unchanged official CSV, real API values, desktop/mobile layouts, keyboard focus, reduced motion and outage/retry recovery. PNGs only; no recording job was run.",
      "",
      f"[Download the immutable derived archive]({archive['url']}). ZIP SHA-256: {archive['sha256']}. It includes member hashes, all permitted reports/traces, failed prefixes, cleanup receipts, client versions and the archived CSV; raw inputs/private resources are excluded.",
      "Failed prefixes also appear at the beginning of their resumed records. Do not count those updates twice. Independent numerical reproduction requires authorized pack access; model resources remain in the owner's account.",
      "",
      "## Defensible public claim","",
      f"Compute Forecast is an auditable GPU rental forecasting study with42 numerical configurations,600 SFT updates and {total_rl} cumulative RL updates. It runs real, evidence-guided numerical research and measures trained selection against fixed/random/adaptive controls. SFT lowers loss on three reused A100 dates, while feedback value and generalization remain limited; incremental RL has {improved} improving, {tied} tied and {worse} worsening seed results versus its SFT parents.",
      "Automation, state-sensitive adaptation, weight learning and forecast value are separate claims. No H100 policy result, broad research-intelligence gain, calibrated long-term confidence interval or competition win is established. Long-term rental/resale curves remain explicit assumption-based scenarios.",
      "",
      "[Remote runbook and canonical execution links](campaign-v2-reproduction.md) · [Live research view]("+URL+"/experimental)"]
    text="\n".join(lines)+"\n"
    for old,new in (("November6","November 6"),("June20","June 20"),("July4","July 4"),("July31","July 31"),("August8","August 8"),("August29","August 29"),("September5","September 5"),("September27","September 27"),("October25","October 25"),("November7","November 7"),("November15","November 15"),("November16","November 16"),("July24","July 24"),("July18","July 18"),("seed17","seed 17"),("seeds17","seeds 17"),("seed43","seed 43"),("update100","update 100"),("among91","among 91"),("thirteen","thirteen"),("removed26","removed 26"),("those13","those 13"),("same60","same 60"),("The60","The 60"),("SXM80","SXM 80"),("about14","about 14"),("from0","from 0"),("to0","to 0"),("about0","about 0"),("and3","and 3"),("roughly42","roughly 42"),("a15","a 15"),("separate15","separate 15"),("at18","at 18"),("has42","has 42"),("supplied40","supplied 40"),("and76","and 76"),("are42","are 42"),("across14","across 14"),("at02","at 02"),("Commitment428","Commitment 428"),("BY4","BY 4"),("among42","among 42"),("approximately−","approximately −"),("with42","with 42"),("configurations,600","configurations, 600")):text=text.replace(old,new)
    registry={"schema_version":2,"status":"measured campaign complete","id_basis":"Checkpoint IDs hash private sampler resource paths, not weight contents","private_paths_included":False,"runs":[{k:p.get(k) for k in ("mode","objective","seed","model","code_sha","grid_source_sha","actual_optimizer_updates","optimizer_updates_this_process","selected_update","checkpoints","recovery_checkpoints","resumption","parent_checkpoint_id","rl_gate")} for p in sft+rl]}
    summary={"schema_version":2,"status":"complete","report_generator_source_sha":os.environ.get("GITHUB_SHA"),"sft_updates":600,"rl_updates":total_rl,"rl_improving_seeds":improved,"rl_tied_seeds":tied,"rl_worsening_seeds":worse,"sft_feedback_ties":blind,"evaluation_dates":a["evaluation_temporal_origins"],"selector_cells":12,"operational_cycles":len(cycles),"fresh_modal_executions":fresh,"verified_memory_reads":reads,"provider_usage":usage,"archive":archive,"official_csv_sha256":CSV_SHA,"canonical_runs":{"sft":43665821333,"failed_rl_prefix":43671941385,"cleanup":43677120366,"rl_continuation":43677499284,"analysis":43677650007,"finalizer":43677709126,"archive":43677783872}}
    intro=f"[Experimental Research v2]({URL}/experimental) compares42 forecasters and six completed Tinker SFT runs (600 optimizer updates), plus three RL reports ({total_rl} cumulative updates). The development-selected SFT lowers loss by {(1-trained['pinball']/base['pinball'])*100:.2f}% on three reused A100 dates; {blind}/6 feedback-hidden controls tie. RL versus its SFT parents: {improved} improve, {tied} tie, {worse} worsen. [Measured findings](docs/campaign-v2-findings.md) · [All checkpoints](docs/campaign-v2-checkpoints.json) · [Verified archive]({archive['url']}). The frozen submission and negative v1 result remain unchanged; no H100 policy performance is claimed."
    intro=intro.replace("compares42","compares 42").replace("by"+format((1-trained["pinball"]/base["pinball"])*100,".2f"),"by "+format((1-trained["pinball"]/base["pinball"])*100,".2f"))
    return text,registry,summary,intro
def gh(path,method="GET",body=None):
    args=["gh","api","--method",method,path]
    if body is not None:args+=["--input","-"]
    return json.loads(subprocess.check_output(args,input=json.dumps(body) if body is not None else None,text=True))
def publish(files,intro):
    if os.environ.get("GITHUB_REF")!="refs/heads/compute-observatory":raise ValueError("Wrong publication branch")
    repo=os.environ["GITHUB_REPOSITORY"]
    for _ in range(3):
        head=gh("repos/"+repo+"/git/ref/heads/compute-observatory")["object"]["sha"]
        commit=gh("repos/"+repo+"/git/commits/"+head)
        readme=base64.b64decode(gh("repos/"+repo+"/contents/README.md?ref="+head)["content"]).decode()
        old=next(l for l in readme.splitlines() if l.startswith("[Experimental Research v2]"))
        payload={**files,"README.md":readme.replace(old,intro,1)}
        if set(payload)!=FILES:raise ValueError("Unexpected publication path")
        if "tinker://" in json.dumps(payload) or "TINKER_API_KEY=" in json.dumps(payload):raise ValueError("Private content")
        entries=[]
        for path,content in payload.items():
            blob=gh("repos/"+repo+"/git/blobs","POST",{"content":content,"encoding":"utf-8"})
            entries.append({"path":path,"mode":"100644","type":"blob","sha":blob["sha"]})
        tree=gh("repos/"+repo+"/git/trees","POST",{"base_tree":commit["tree"]["sha"],"tree":entries})
        new=gh("repos/"+repo+"/git/commits","POST",{"message":"Publish measured nine-policy findings and verified derived archive","tree":tree["sha"],"parents":[head]})
        try:gh("repos/"+repo+"/git/refs/heads/compute-observatory","PATCH",{"sha":new["sha"],"force":False})
        except subprocess.CalledProcessError:continue
        return new["sha"]
    raise RuntimeError("Concurrent branch writes prevented publication; no force update attempted")
def main():
    if os.environ.get("GITHUB_REF")!="refs/heads/compute-observatory":raise ValueError("Wrong report branch")
    raw=urlopen(URL+"/api/experimental",timeout=90).read();data=json.loads(raw);validate(data)
    archive=data["artifact_archive"]
    if hashlib.sha256(urlopen(archive["url"],timeout=90).read()).hexdigest()!=archive["sha256"]:raise ValueError("Archive bytes mismatch")
    if hashlib.sha256(urlopen(URL+"/files/forecasts.csv",timeout=90).read()).hexdigest()!=CSV_SHA:raise ValueError("Official CSV changed")
    performance=json.loads(Path("configs/campaign-v2-observed-throughput.json").read_text())
    text,registry,summary,intro=render(data,performance)
    files={"docs/campaign-v2-findings.md":text,"docs/campaign-v2-checkpoints.json":json.dumps(registry,indent=2)+"\n","docs/campaign-v2-final-status.json":json.dumps(summary,indent=2)+"\n","docs/campaign-v2-performance.json":json.dumps(performance,indent=2)+"\n"}
    sha=publish(files,intro)
    out=Path("artifacts/v2-final-report");out.mkdir(parents=True,exist_ok=True)
    receipt={"publication_sha":sha,"url":"https://github.com/"+os.environ["GITHUB_REPOSITORY"]+"/commit/"+sha,**summary}
    (out/"publication.json").write_text(json.dumps(receipt,indent=2))
    print("V2_FINAL_PUBLICATION:"+json.dumps(receipt),flush=True)
if __name__=="__main__":main()
