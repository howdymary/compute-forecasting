"""Publish a bounded study with exact checks, factual claims and an actual replay."""
import argparse,copy,datetime as dt,hashlib,io,json,os,pathlib,sqlite3,subprocess,sys,zipfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
import verify,verify_independent,demo
REPO="howdymary/compute-forecasting";BRANCH="compute-observatory"
def api(path,method="GET",payload=None):
    cmd=["gh","api",f"repos/{REPO}/{path}"]
    if method!="GET":cmd+=["--method",method,"--input","-"]
    r=subprocess.run(cmd,input=None if payload is None else json.dumps(payload).encode(),capture_output=True,timeout=120)
    if r.returncode:raise RuntimeError("GitHub operation failed: "+path+" "+r.stderr.decode()[:200])
    return json.loads(r.stdout)
def download(run_id,name,out):
    run=api(f"actions/runs/{run_id}")
    if run["conclusion"]!="success":raise ValueError("source run is not independently successful")
    art=next(a for a in api(f"actions/runs/{run_id}/artifacts")["artifacts"] if a["name"]==name)
    raw=subprocess.check_output(["gh","api",f"repos/{REPO}/actions/artifacts/{art['id']}/zip"])
    z=zipfile.ZipFile(io.BytesIO(raw))
    for e in z.infolist():
        p=pathlib.PurePosixPath(e.filename)
        if p.is_absolute() or ".." in p.parts or len(p.parts)!=1 or e.file_size>10_000_000:raise ValueError("unexpected artifact path")
        if not e.is_dir():(out/p.name).write_bytes(z.read(e))
    return {"run_id":run_id,"source_sha":run["head_sha"],"artifact_sha256":hashlib.sha256(raw).hexdigest(),"url":run["html_url"]}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--run",required=True);ap.add_argument("--publish",action="store_true");a=ap.parse_args()
    if not os.environ.get("GITHUB_ACTIONS"):raise SystemExit("remote only")
    out=HERE/"output";out.mkdir(exist_ok=True)
    provenance=download(a.run,"boundforge-structural-v2",out)
    r=json.loads((out/"report.json").read_text());best=json.loads((out/"best.json").read_text())
    baseline=json.loads((ROOT/"results/best.json").read_text())
    exact=verify.report(best);lo,hi=verify_independent.check(best)
    bl,bh=verify_independent.check(baseline)
    strict=verify.improves(best,baseline)
    if strict and not lo>bh:raise RuntimeError("independent checker did not prove improvement")
    if strict!=r["strict_improvement"]:raise RuntimeError("source claim mismatch")
    for name,digest in r["protected_sha256"].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise RuntimeError("verifier source changed")
    events=[json.loads(l) for l in (out/"trace.jsonl").read_text().splitlines() if l]
    cases=[json.loads(l) for l in (out/"cases.jsonl").read_text().splitlines() if l]
    for arm,summary in r["arms"].items():
        rows=[c for c in cases if c["arm"]==arm and c["nondegenerate"]]
        summary["best_nondegenerate_free_energy"]=max((c["free_energy"] for c in rows),default=None)
        summary["distinct_supports"]=len({c["support_sha256"] for c in cases if c["arm"]==arm})
    estimates=sum(e.get("estimated_gross_usd",0) for e in events if e["kind"]=="model_inference")
    exa=0.07+sum(e.get("cost_usd",0) or 0 for e in events if e["kind"]=="exa_sources")
    past_est=sum(e.get("estimated_credits",0) for e in events if e["kind"]=="memory_write")+sum(e["kind"]=="memory_read" for e in events)
    reservations=[]
    db=sqlite3.connect("file:"+str(out/"budget.sqlite")+"?mode=ro",uri=True)
    for row in db.execute("select id,provider,reserved,actual,status from reservations"):
        reservations.append(dict(zip(("id","provider","reserved","actual","status"),row)))
    db.close();(out/"budget.sqlite").unlink()
    own=[x for x in reservations if not x["id"].startswith(("historical-","literature-"))]
    usage={"campaign_exa_response_usd":exa,"tinker_token_estimate_usd":estimates,"past_estimated_credits":past_est,
           "unreconciled_or_held_by_provider":{p:sum(x["reserved"] for x in own if x["provider"]==p and x["actual"] is None) for p in ("exa","modal","tinker","past")},
           "note":"Preserved prior allowances are separate. Gross token estimates and held allowances are not invoices. No purchases/upgrades/reloads."}
    (out/"reservations.json").write_text(json.dumps(reservations,indent=2))
    (out/"usage.json").write_text(json.dumps(usage,indent=2))
    (out/"provenance.json").write_text(json.dumps(provenance,indent=2))
    r["publication_exact_check"]=exact;r["publication_independent_interval"]=[verify_independent.decimal(lo),verify_independent.decimal(hi,True)]
    r["publication_provenance"]=provenance;r["usage"]=usage
    (out/"report.json").write_text(json.dumps(r,indent=2))
    meaningful=sum(v["positive_oracles_over_1e-9"] for v in r["arms"].values())
    decision=("Investigate the positive numerical separation candidates with coordinated law/probability refinement; do not claim a record from a dual score." if meaningful and not strict else
              "Retain the old exact certificate. Stop scaling this grammar/optimizer pairing; the bounded experiment does not justify more of the same search." if not strict else
              "A stronger exact witness is certified. Assess numerical magnitude, attribution and structural explanation before claiming publication readiness.")
    rows="\n".join(f"| {arm} | {s['cases']} | {s['nondegenerate']} | {s['positive_oracles_over_1e-9']} | {s['best_nondegenerate_free_energy']} | {s['function_evaluations']} | {s['worker_seconds']:.2f} |" for arm,s in r["arms"].items())
    note=f"""# Research-led BoundForge study

Research date: November 14, 2026, America/Los_Angeles. Raw receipts use UTC.
Review was committed before implementation of this pilot.
[Comparative review](../COMPARATIVE_REVIEW.md) · [Frozen direction/criteria](../DIRECTION_AND_PREREGISTRATION.md)
[Actual campaign]({provenance['url']})

## Main finding

Strict improvement over the retained 59/49-point certificate: **{strict}**.
{decision}

This study adapts prior methods. It does not establish that our framework is novel or superior,
nor guarantee journal acceptance. A negative result here is scoped to the tested representation,
initializations and resource budget.

## What was researched and reproduced

Nine primary-source precedents were reviewed, including FunSearch, AlphaEvolve, PatternBoost,
Wagner's cross-entropy approach, AlphaTensor, a recent geometric PatternBoost study and
direct entropy/sum-difference work. Costs or implementation details not verified are marked unknown.

Official FunSearch construction replay: size 512 at dimension 8; constant priority 256;
ten random priorities 256–262. Independent exact pair checks passed.
This is replay of released construction/evaluation code, not reproduction of the historical LLM search.

## Executed comparison

Model inference calls: {r['model_inference_calls']}; valid model programs: {r['model_programs_valid']}/6.
Model proposals outside the deterministic menu use a bounded integer-expression grammar.
All programs share the same numerical optimization procedure.
Start 101 supplies development feedback; programs are frozen before starts 202 and 303.
These are three starts on one mathematical target, not independent mathematical problems.

| Arm | Cases | Nondegenerate | F>1e−9 | Best nondegenerate F | Function evaluations | Worker seconds |
|---|---:|---:|---:|---:|---:|---:|
{rows}

A point mass has F=0 and is not a successful separator. The table excludes collapsed laws from
the best-nondegenerate column. Invalid model proposals consume proposal slots; no replacement
calls are silently added. The incumbent-basin mutation arm is a separate diagnostic, not the same
program-generation comparison. Case counts, CPU effort and model overhead are distinct resources.

A positive F is a numerical proposal score. It is not a bound for all random variables, nor alone
proof that a finite-bank composition improves. See [mathematical scope](../MATHEMATICAL_SCOPE.md).
No fine-tuning was run: this archive does not establish sufficient independent construction-family
coverage for a meaningful training/evaluation split.

## Exact result and claims

Retained ratio interval:
[{verify_independent.decimal(lo)}, {verify_independent.decimal(hi,True)}].

Both protected verifiers were unchanged and rerun. Final witnesses, all numerical cases, law bank,
model outputs, source links, program freeze and reservation ledger are retained in this folder.
The original incumbent and its author attribution remain unchanged.

| Claim | Evidence | Status |
|---|---|---|
| Comparative research preceded the new search | Review/preregistration commits and source hashes in trace | Established provenance |
| Released FunSearch construction replays at 512 | ../evidence/funsearch-replay.json; run 43675332783 | Exact diagnostic passed |
| Tinker generated bounded programs | model_inference / valid_program / invalid_program events | Actual calls, invalid attempts retained |
| Modal performed numerical search | per-case timing, function evaluations and saved law bank | Actual bounded executions |
| A new C3c lower bound was found | Both interval checkers against retained witness | {strict} |
| Model generation is generally superior | Three-start limited comparison | Not established |
| A universal entropy upper bound was proved | No universal certificate exists | Not claimed |
| Work is ready as a substantial mathematics paper | Requires substantive new construction/theory and specialist review | Not established |

## Usage and reproducibility

Exa response costs including phase-one discovery: {exa:.6f} USD.
Tinker uncached-rate token estimate: {estimates:.6f} USD.
past.dev estimated ingests plus conservatively metered recalls: {past_est} credits.
Held allowances for this numerical campaign: {usage['unreconciled_or_held_by_provider']}.
These are not final billed charges; prior pending allowances remain in reservations.json.

No credits were purchased, auto-reload enabled or plans upgraded. Initial balances and their
verification are in ../campaign-budget.json. Provider-specific caps are never pooled.
Scientific verification uses GitHub Actions and does not need paid APIs.

    python boundforge/verify.py boundforge/research_v2/output/best.json --baseline boundforge/results/best.json
    python boundforge/verify_independent.py boundforge/research_v2/output/best.json boundforge/results/best.json

demo.html is generated from actual source-run artifacts. oracle-scores.svg displays numerical
proposal scores, with collapsed solutions marked separately. Neither is a mathematical proof.
"""
    (out/"RESEARCH_NOTE.md").write_text(note)
    # Standalone scientific plot; no inferred confidence intervals.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,5));colors={"structured":"#19735e","random":"#a17424","model":"#5369b5","basin-mutation":"#b34b62"}
    for arm,color in colors.items():
        cc=[(i,c) for i,c in enumerate(cases) if c["arm"]==arm and c["nondegenerate"]]
        ax.scatter([i for i,c in cc],[c["free_energy"] for i,c in cc],s=25,label=arm,color=color)
    collapsed=[i for i,c in enumerate(cases) if not c["nondegenerate"]]
    ax.scatter(collapsed,[0]*len(collapsed),s=13,marker="x",c="#aaa",label="collapsed / uninformative")
    ax.axhline(1e-9,color="black",ls="--",lw=.8,label="numerical screen, not proof")
    ax.set_yscale("symlog",linthresh=1e-9);ax.set_xlabel("Recorded case index");ax.set_ylabel("Free-energy proposal score F (higher is better)")
    ax.legend(fontsize=8);ax.set_title("Bounded C3c pilot: actual numerical cases");fig.tight_layout();fig.savefig(out/"oracle-scores.svg");plt.close(fig)
    # Reuse the already-tested exact-integer replay generator on these actual artifacts.
    view=HERE/"view/results";view.mkdir(parents=True,exist_ok=True)
    adapted=copy.deepcopy(r);adapted["source_commit"]=r["source_sha"];adapted["workflow_run"]=r["run_id"]
    for name,body in [("report.json",adapted),("best.json",best),("sources.json",json.loads((out/"sources.json").read_text()))]:
        (view/name).write_text(json.dumps(body))
    (view/"trace.jsonl").write_text((out/"trace.jsonl").read_text())
    demo.ROOT=HERE/"view";demo.build()
    page_text=(view/"demo.html").read_text().replace("</style>", """
*{box-sizing:border-box}main{grid-template-columns:minmax(0,1.2fr) minmax(0,1fr)}
select{max-width:100%}h3,#checks,#lawdata{overflow-wrap:anywhere}pre{max-width:100%}
@media(max-width:760px){main{grid-template-columns:minmax(0,1fr)}}
</style>""")
    page_text=page_text.replace("Incumbent reproduced","Prior certified refinement retained").replace("No new record: the strongest retained result is the attributed incumbent.","No improvement in this study. The retained witness is the earlier certified refinement of Jaswal's construction.")
    (out/"demo.html").write_text(page_text)
    script=(out/"demo.html").read_text().rsplit("<script>",1)[1].split("</script>",1)[0]
    check=subprocess.run(["node","--check"],input=script,text=True,capture_output=True)
    if check.returncode:raise RuntimeError("demo JavaScript syntax error")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in [1440,390]:
            page=browser.new_page(viewport={"width":width,"height":900},accept_downloads=True)
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto((out/"demo.html").as_uri());page.locator("#check").click()
            assert page.locator("#checks").inner_text().startswith("PASS")
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            with page.expect_download() as download_event:page.locator("#download").click()
            p=out/"download-check.json";download_event.value.save_as(p);assert json.loads(p.read_text())==best;p.unlink()
            assert not errors
            page.screenshot(path=str(out/f"demo-{width}.png"),full_page=True);page.close()
        browser.close()
    print("BF2_PUBLICATION "+json.dumps({"strict_improvement":strict,"cases":len(cases),"positive_oracles":meaningful,"decision":decision,"usage":usage,"browser_checks":"desktop/mobile, exact download, no page errors"}),flush=True)
    if a.publish:
        paths=[p for p in out.iterdir() if p.is_file() and p.suffix in (".json",".jsonl",".md",".svg",".html",".txt")]
        tree=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in paths]
        assert all(x["path"].startswith("boundforge/research_v2/output/") for x in tree)
        for attempt in range(3):
            head=api("git/ref/heads/"+BRANCH)["object"]["sha"];base=api("git/commits/"+head)["tree"]["sha"]
            t=api("git/trees","POST",{"base_tree":base,"tree":tree})["sha"]
            commit=api("git/commits","POST",{"message":"Publish research-led C3c pilot, exact checks and publication assessment","tree":t,"parents":[head]})["sha"]
            try:api("git/refs/heads/"+BRANCH,"PATCH",{"sha":commit,"force":False});break
            except RuntimeError:
                if attempt==2:raise
        print("BF2_PUBLISHED "+commit,flush=True)
if __name__=="__main__":main()
