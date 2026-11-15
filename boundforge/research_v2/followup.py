import copy,datetime as dt,hashlib,json,os,pathlib,shutil,sys,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
import verify,verify_independent,precision
from common import CampaignProviders,Disabled
from constructions import compose
def main():
    if not os.environ.get("GITHUB_ACTIONS"):raise SystemExit("remote only")
    previous=HERE/"previous";out=HERE/"followup";out.mkdir(exist_ok=True)
    shutil.copyfile(previous/"budget.sqlite",out/"budget.sqlite")
    original=json.loads((previous/"report.json").read_text())
    oldcases=[json.loads(l) for l in (previous/"cases.jsonl").read_text().splitlines() if l]
    bank=json.loads((previous/"law-bank.json").read_text())
    baseline=json.loads((ROOT/"results/best.json").read_text());best=copy.deepcopy(baseline)
    protected={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ["verify.py","verify_independent.py"]}
    precision.mp.mp.dps=110;nu=[float(x) for x in precision.dual(baseline)]
    cases=[];events=[];start=time.monotonic()
    def log(kind,payload):
        e={"timestamp":dt.datetime.now(dt.timezone.utc).isoformat(),"kind":kind,**payload};events.append(e)
        (out/"trace.jsonl").write_text("\n".join(json.dumps(x) for x in events)+"\n")
        print("BF2F_EVENT "+json.dumps(e),flush=True)
    providers=CampaignProviders(out,log)
    log("followup_protocol",{"source_run":"43675810337","case_count":len(oldcases),"protocol_sha256":hashlib.sha256((HERE/"NONDEGENERATE_FOLLOWUP.md").read_bytes()).hexdigest(),"entropy_floor":1,"protected_sha256":protected})
    # Saved law bank order is baseline laws followed by every successful case.
    assert len(bank)==len(baseline["laws"])+len(oldcases)
    specs=[]
    for i,c in enumerate(oldcases):
        law=bank[len(baseline["laws"])+i]
        digest=hashlib.sha256(json.dumps(law["points"]).encode()).hexdigest()
        assert digest==c["support_sha256"],"paired support mismatch"
        initial=None
        if c["arm"]=="basin-mutation":
            k=int(c["program"].split("-")[0][3:])
            initial=[a/b for a,b in baseline["laws"][k]["weights"]]
        specs.append({"points":law["points"],"seed":c["seed"],"initial":initial,"arm":c["arm"],"program":c["program"],"original":c})
    providers.ledger.reserve("modal",2)
    import modal
    app=modal.App("boundforge-entropy-constrained")
    image=(modal.Image.debian_slim(python_version="3.11").pip_install("numpy==2.2.6","scipy==1.15.3")
       .add_local_file(str(HERE/"constructions.py"),"/root/boundforge/constructions.py")
       .add_local_file(str(HERE/"nondegenerate.py"),"/root/boundforge/nondegenerate.py"))
    @app.function(image=image,cpu=2,memory=1024,timeout=75,max_containers=6,serialized=True)
    def worker(spec,nu):
        import sys
        sys.path.insert(0,"/root/boundforge")
        from nondegenerate import optimize
        return optimize(spec["points"],nu,spec["seed"],spec["initial"])
    with app.run():
        for startidx in range(0,len(specs),12):
            pending=[]
            for spec in specs[startidx:startidx+12]:
                try:providers.ledger.reserve("modal",0.15)
                except Disabled as e:log("budget_stop",{"reason":str(e)});break
                pending.append((spec,worker.spawn(spec,nu)))
            for spec,call in pending:
                try:
                    result=call.get();bank.append(result["law"])
                    row={k:v for k,v in result.items() if k!="law"}
                    row.update(arm=spec["arm"],program=spec["program"],seed=spec["seed"],original_F=spec["original"]["free_energy"],original_nondegenerate=spec["original"]["nondegenerate"])
                    cases.append(row);log("paired_case",row)
                except Exception as e:log("case_failed",{"arm":spec["arm"],"program":spec["program"],"seed":spec["seed"],"error":str(e)[:400]})
            candidate,lp=compose(bank)
            if verify.improves(candidate,best):best=candidate
            (out/"best.json").write_text(json.dumps(best,indent=2))
            (out/"cases.jsonl").write_text("\n".join(json.dumps(c) for c in cases)+"\n")
            (out/"law-bank.json").write_text(json.dumps(bank))
            log("composition",{"bank_size":len(bank),"lp":lp,"strict_improvement":verify.improves(best,baseline)})
    lo,hi=verify_independent.check(best);bl,bh=verify_independent.check(baseline)
    improved=verify.improves(best,baseline)
    if improved and not lo>bh:raise RuntimeError("second checker did not confirm gain")
    for n,h in protected.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h
    summary={"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"cases":len(cases),"strict_improvement":improved,
      "best":verify.report(best),"independent_interval":[verify_independent.decimal(lo),verify_independent.decimal(hi,True)],
      "arms":{arm:{"cases":sum(c["arm"]==arm for c in cases),"nondegenerate":sum(c["arm"]==arm and c["nondegenerate"] for c in cases),
        "positive_oracles":sum(c["arm"]==arm and c["nondegenerate"] and c["free_energy"]>1e-9 for c in cases),
        "best_F":max((c["free_energy"] for c in cases if c["arm"]==arm),default=None),
        "cpu_seconds":sum(c["cpu_seconds"] for c in cases if c["arm"]==arm),
        "wall_worker_seconds":sum(c["seconds"] for c in cases if c["arm"]==arm)} for arm in original["arms"]},
      "elapsed_seconds":time.monotonic()-start,"providers":providers.ledger.summary(),"protected_sha256":protected,
      "scope":"Exploratory paired optimizer correction on saved supports; entropy floor restricts search, not mathematical validity."}
    (out/"report.json").write_text(json.dumps(summary,indent=2))
    print("BF2F_FINAL "+json.dumps(summary),flush=True)
if __name__=="__main__":main()
