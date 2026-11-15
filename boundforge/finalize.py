"""Collect successful remote runs, recheck and publish only BoundForge artifacts."""
import argparse,copy,datetime as dt,hashlib,io,json,os,pathlib,sqlite3,subprocess,zipfile
import verify,verify_independent,demo
ROOT=pathlib.Path(__file__).resolve().parent
REPO="howdymary/compute-forecasting";BRANCH="compute-observatory"
def gh(path,method="GET",body=None):
    cmd=["gh","api","repos/"+REPO+"/"+path]
    if method!="GET":cmd+=["--method",method,"--input","-"]
    p=subprocess.run(cmd,input=None if body is None else json.dumps(body).encode(),capture_output=True,timeout=120)
    if p.returncode:raise RuntimeError("GitHub API failed: "+path+" "+p.stderr.decode()[:300])
    return json.loads(p.stdout)
def sanitize(e):
    e=copy.deepcopy(e)
    if e.get("kind")=="exa_sources":
        for r in e.get("results",[]):
            text=r.pop("text","");r["text_sha256"]=hashlib.sha256(text.encode()).hexdigest();r["excerpt"]=text[:120]
    if e.get("kind")=="memory_read":
        e["documents"]=[{"id":d.get("id"),"content_sha256":d.get("content_sha256") or hashlib.sha256(d.get("content","").encode()).hexdigest(),"source_ids":d.get("source_ids") or [s.get("sourceId") for s in d.get("sources",[]) if str(s.get("sourceId","")).startswith("boundforge-")]} for d in e.get("documents",[])]
    return e
def collect(rid,out):
    info=gh(f"actions/runs/{rid}")
    if info["conclusion"]!="success" or not info["name"].startswith("BoundForge"):raise ValueError("not a successful BoundForge run")
    art=next(a for a in gh(f"actions/runs/{rid}/artifacts")["artifacts"] if a["name"].startswith("boundforge-") and "preflight" not in a["name"])
    raw=subprocess.check_output(["gh","api",f"repos/{REPO}/actions/artifacts/{art['id']}/zip"])
    z=zipfile.ZipFile(io.BytesIO(raw));target=out/"runs"/str(rid);target.mkdir(parents=True,exist_ok=True)
    events=[];report=None;best=None;sources=[]
    for entry in z.infolist():
        p=pathlib.PurePosixPath(entry.filename)
        if p.is_absolute() or ".." in p.parts or entry.file_size>10_000_000:raise ValueError("unsafe archive path")
        if not entry.filename.startswith("results/") or entry.is_dir():continue
        name=p.name;data=z.read(entry)
        if name=="budget.sqlite":
            temp=target/"ledger.sqlite";temp.write_bytes(data)
            db=sqlite3.connect("file:"+str(temp)+"?mode=ro",uri=True)
            rows=db.execute("select id,provider,reserved,actual,status from reservations").fetchall();db.close();temp.unlink()
            (target/"reservations.json").write_text(json.dumps([dict(zip(("id","provider","reserved","actual","status"),r)) for r in rows],indent=2));continue
        if name=="trace.jsonl":
            events=[sanitize(json.loads(l)) for l in data.decode().splitlines() if l.strip()]
            data=("\n".join(json.dumps(e) for e in events)+"\n").encode()
        elif name=="sources.json":
            sources=json.loads(data)
            for ev in sources:
                for r in ev.get("results",[]):
                    text=r.pop("text","");r["text_sha256"]=hashlib.sha256(text.encode()).hexdigest();r["excerpt"]=text[:120]
            data=json.dumps(sources,indent=2).encode()
        elif name=="report.json":report=json.loads(data)
        elif name=="best.json":best=json.loads(data)
        if p.suffix in (".json",".jsonl",".txt"):(target/name).write_bytes(data)
    if report is None or best is None:raise ValueError("missing report/witness")
    (target/"provenance.json").write_text(json.dumps({"run_id":rid,"source_sha":info["head_sha"],"url":info["html_url"],"artifact_sha256":hashlib.sha256(raw).hexdigest()},indent=2))
    return report,best,events,sources
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--runs",nargs="+",required=True);ap.add_argument("--publish",action="store_true");a=ap.parse_args()
    if not os.environ.get("GITHUB_ACTIONS"):raise SystemExit("Remote only")
    out=ROOT/"results";out.mkdir(exist_ok=True)
    candidates=[];events=[];sources=[];summaries=[]
    for rid in a.runs:
        report,best,ev,src=collect(rid,out)
        verify.report(best);candidates.append((rid,best,report));events+=ev;sources+=src
        summaries.append({"run_id":rid,"source_sha":report["source_commit"],"trials":report.get("trials",len(report.get("experiments",[]))),"strict_improvement":report["strict_improvement"],"tinker_decisions":sum(e["kind"]=="tinker_decision" for e in ev),"tinker_failures":sum(e["kind"]=="tinker_invalid_action" for e in ev)})
    rid,best,winning=candidates[0]
    for cid,c,r in candidates[1:]:
        if verify.improves(c,best):rid,best,winning=cid,c,r
    lo,hi=verify_independent.check(best)
    baseline=json.loads((ROOT/"certificates/incumbent.json").read_text())
    bl,bh=verify_independent.check(baseline)
    if not(lo>bh and verify.improves(best,baseline)):raise ValueError("both checkers must prove strict improvement")
    report=copy.deepcopy(winning)
    report["workflow_run"]=rid;report["publication_workflow_run"]=os.environ.get("GITHUB_RUN_ID")
    report["independent"]={"valid":True,"strict_improvement":True,"method":"independent rational logarithm series; rechecked at publication","ratio_interval":[verify_independent.decimal(lo),verify_independent.decimal(hi,True)]}
    report["campaigns"]=summaries
    report["actual_tinker_decisions"]=sum(e["kind"]=="tinker_decision" for e in events)
    report["actual_exa_calls"]=sum(e["kind"]=="exa_sources" for e in events)
    report["cross_role_verified_recalls"]=sum(e["kind"]=="memory_read" and e.get("cross_role_source_present",False) for e in events)
    report["providers"]["exa"]["reserved_or_actual"]=sum(e.get("cost_usd",0) or 0 for e in events if e["kind"]=="exa_sources")
    report["providers"]["tinker"]["reserved_or_actual"]=sum(e.get("estimated_gross_usd",0) for e in events if e["kind"]=="tinker_decision")
    report["providers"]["past"]["reserved_or_actual"]=sum(e.get("estimated_credits",0) for e in events if e["kind"]=="memory_write")+sum(e["kind"]=="memory_read" for e in events)
    report["providers"]["modal"]["reserved_or_actual"]=2*len(a.runs)+0.2*16+0.4*sum(max(0,s["trials"]-1) for s in summaries[1:])
    report["cancelled_campaign"]={"run_id":"43671444344","reason":"Tokenizer returned a dictionary instead of token IDs; stopped and corrected before a successful inference.","held_allowances":{"modal_usd":4,"exa_usd":0.20,"past_credits":20,"tinker_usd":0.40},"accounting":"Conservative additional reserves; not actual charges."}
    report["providers"]["modal"]["reserved_or_actual"]+=4
    report["accounting_note"]="Includes an additional $4 Modal hold for the cancelled campaign; its unresolved provider allowances are listed separately. Exa: response costs. Tinker: uncached-rate token estimates. Past: estimated ingests plus 1 credit per recall. Modal: conservative upper reservations, not invoices."
    report["tinker_training"]="No fine-tuning: too few diverse verified decisions for a meaningful held-out comparison. Actual base-model decisions counted separately; failures retained."
    receipts={"timestamp":dt.datetime.now(dt.timezone.utc).isoformat(),"note":"Gross usage estimates may lag. No credit purchases or billing changes."}
    from preflight import cli,request
    receipts["modal_summary"]=cli("modal","billing","summary","--json")
    m=cli("modal","billing","report","--start","2026-11-15","--resolution","h","--json")
    if m.get("status")==200 and isinstance(m["data"],list):
        rows=[r for r in m["data"] if "boundforge" in str(r.get("description","")).lower()]
        receipts["modal_attributed"]={"rows":len(rows),"gross_reported_usd":sum(float(r.get("cost") or 0) for r in rows) if rows else None,"lagged":True}
    if os.environ.get("PAST_API_KEY"):
        p=request("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])
        if p.get("status")==200:receipts["past_current"]={"balance":p["data"].get("balance"),"month":p["data"].get("month"),"metered":p["data"].get("metered")}
    (out/"provider-receipts.json").write_text(json.dumps(receipts,indent=2))
    (out/"report.json").write_text(json.dumps(report,indent=2));(out/"best.json").write_text(json.dumps(best,indent=2))
    events.sort(key=lambda e:e.get("timestamp",""))
    (out/"trace.jsonl").write_text("\n".join(json.dumps(e) for e in events)+"\n")
    (out/"sources.json").write_text(json.dumps(sources,indent=2))
    from decimal import Decimal,localcontext
    with localcontext() as ctx:
        ctx.prec=100;gain=Decimal(verify_independent.decimal(lo))-Decimal(verify_independent.decimal(bh,True))
    note=f"""# BoundForge measured result

Research date: {receipts['timestamp']}.
Source runs: {', '.join(a.runs)}.

## Certified result

The exact witness ratio lies in
[{verify_independent.decimal(lo)}, {verify_independent.decimal(hi,True)}].
Its rigorous lower endpoint exceeds the published Jaswal witness's rigorous upper endpoint
by at least approximately {gain:.8E}. Arb and the independent rational-series checker both passed.
Final construction: {[len(l['points']) for l in best['laws']]} support sizes; base {best['base']};
exact positive rational weights and independent integer digit counts.

**This is an extremely small refinement, not a major new bound.**
The 15-digit leaderboard value is unchanged. Most gain removes the original digit-count rounding loss.
Added support points contribute much smaller positive gains. No sharp-constant solution,
proof-assistant verification, leaderboard acceptance, or substantial advance is claimed.
[Current table](https://teorth.github.io/optimizationproblems/constants/3c.html)
[Original certificate](https://zenodo.org/records/23289305)

## Attribution and research

Manvir Jaswal supplied the original two laws and stationary free-energy/Newton construction method.
BoundForge independently reproduces the result, searches projection-fibre intersections, estimates
profitable support insertions, refines at 110 digits, rounds to exact rational data and certifies changes.
The independent-digit encoding is checked for all five projections; a probability mixture is different.

Initial SLSQP campaign: 16 trials, zero improvements; numerical failures are retained.
High-precision trials and all actual model decisions are retained in trace.jsonl and runs/.
These bounded attempts do not establish local or global optimality.

## Actual integrations

Exa calls inside research loops: {report['actual_exa_calls']}.
Real Tinker decisions: {report['actual_tinker_decisions']}.
Verified cross-role past.dev recalls: {report['cross_role_verified_recalls']}.
Modal ran bounded CPU solves; fresh independent certification used GitHub Actions.
Failed Tinker integrations are not counted as successful model decisions.
No fine-tuning, memory performance benefit or model-selection advantage is claimed.

## Budgets and stopping

Initial balances and provenance: ../budget-snapshot.json.
No credits were bought, auto-replenishment enabled or plans upgraded.
Unknown costs stay reserved. Per-run ledgers are retained as reservations.json.
{report['accounting_note']}
Partial provider receipts are in provider-receipts.json; they may lag.

The bounded campaign stops after independent certification. Deep decimal refinements do not justify
calling this a major breakthrough or blindly consuming the remaining credits on the same tail search.
The next larger search should target different support geometry or a new complementary law.

## Reproduce remotely

    python boundforge/verify.py boundforge/results/best.json --baseline boundforge/certificates/incumbent.json
    python boundforge/verify_independent.py boundforge/results/best.json boundforge/certificates/incumbent.json

demo.html is a self-contained replay of these actual artifacts, with no credentials.
Its structural check uses BigInt and preserves large rational integers as strings.
The Python checkers certify entropy intervals; the browser does not prove logarithm bounds.
"""
    (out/"REPORT.md").write_text(note);demo.build()
    script=(out/"demo.html").read_text().rsplit("<script>",1)[1].split("</script>",1)[0]
    p=subprocess.run(["node","--check"],input=script,text=True,capture_output=True)
    if p.returncode:raise RuntimeError("demo JS syntax failed: "+p.stderr)
    import demo_qa
    demo_qa.check()
    print("BOUNDFORGE_PUBLICATION "+json.dumps({"best_source_run":rid,"strict_improvement":True,"gain_lower_approx":str(gain),"tinker_decisions":report["actual_tinker_decisions"],"providers":report["providers"]}),flush=True)
    if a.publish:
        outputs=[p for p in out.rglob("*") if p.is_file() and p.suffix in (".json",".jsonl",".txt",".md",".html")]
        tree=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in outputs]
        if any(not e["path"].startswith("boundforge/results/") for e in tree):raise ValueError("publication escaped project")
        for attempt in range(3):
            head=gh("git/ref/heads/"+BRANCH)["object"]["sha"]
            base=gh("git/commits/"+head)["tree"]["sha"]
            t=gh("git/trees","POST",{"base_tree":base,"tree":tree})["sha"]
            commit=gh("git/commits","POST",{"message":"Publish independently certified BoundForge result and actual research replay","tree":t,"parents":[head]})["sha"]
            try:gh("git/refs/heads/"+BRANCH,"PATCH",{"sha":commit,"force":False});break
            except RuntimeError:
                if attempt==2:raise
        print("BOUNDFORGE_PUBLISHED_COMMIT "+commit,flush=True)
if __name__=="__main__":main()
