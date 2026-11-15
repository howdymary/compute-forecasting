"""Second campaign: high-precision composition and structural stationarity experiments."""
import argparse,copy,datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time
from decimal import Decimal,localcontext,ROUND_FLOOR
import verify,precision
from providers import Providers,Disabled,prepare_output
ROOT=pathlib.Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--structural-trials",type=int,default=6);ap.add_argument("--start");a=ap.parse_args()
    if not os.environ.get("GITHUB_ACTIONS"):raise SystemExit("Remote GitHub Actions only")
    if not 0<=a.structural_trials<=20:raise SystemExit("bounded trial limit")
    out=ROOT/"results";out.mkdir(exist_ok=True)
    prepare_output(out)
    history=[];sources=[];start=time.monotonic()
    def log(kind,payload):
        row={"timestamp":dt.datetime.now(dt.timezone.utc).isoformat(),"kind":kind,**payload}
        with (out/"trace.jsonl").open("a") as fp:fp.write(json.dumps(row,sort_keys=True)+"\n")
        print("BF_EVENT "+json.dumps(row),flush=True)
    protected={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ("verify.py","verify_independent.py")}
    baseline=json.loads((ROOT/"certificates/incumbent.json").read_text())
    verify.report(baseline);best=copy.deepcopy(baseline)
    if a.start:
        seed=json.loads(pathlib.Path(a.start).read_text())
        verify.report(seed)
        if verify.improves(seed,best):best=seed
    providers=Providers(out,log)
    log("baseline",verify.report(baseline))
    try:sources.append(providers.exa("Manvir Jaswal C3c four slope sum difference independent laws Newton multipliers certificate"))
    except Exception as e:log("provider_disabled",{"provider":"exa","reason":type(e).__name__})
    def accept(candidate,stats,label):
        nonlocal best
        report=verify.report(candidate);accepted=verify.improves(candidate,best)
        row={"label":label,"accepted":accepted,"strict_improvement_over_baseline":verify.improves(candidate,baseline),"stats":stats,"report":report}
        history.append(row)
        (out/f"precision-candidate-{len(history):02d}.json").write_text(json.dumps(candidate,indent=2))
        if accepted:best=copy.deepcopy(candidate)
        (out/"best.json").write_text(json.dumps(best,indent=2))
        (out/"precision-checkpoint.json").write_text(json.dumps({"history":history,"best":best}))
        log("precision_experiment",row)
    refined,stats=precision.refine_composition(best)
    accept(refined,stats,"high precision digit counts; original laws unchanged")
    scientist=None
    try:
        from tinker_policy import Scientist
        scientist=Scientist(providers)
    except Exception as e:log("provider_disabled",{"provider":"tinker","reason":type(e).__name__})
    providers.ledger.reserve("modal",2)
    from modal_worker import app,precision_worker
    with app.run():
        reservation=providers.ledger.reserve("modal",0.40)
        try:
            candidate,stats=precision_worker.remote(best,None)
            accept(candidate,stats,"refine incumbent stationary system")
        except Exception as e:
            log("failed_experiment",{"label":"stationary refinement","reason":str(e)[:1000]})
        used=set()
        for trial in range(a.structural_trials):
            options,nu=precision.proposals(best,limit=16,radius=24)
            options=[o for o in options if (o["law"],tuple(o["point"])) not in used]
            if not options:log("stop",{"reason":"no untested positive-exponent support candidates in bounded box"});break
            selected=0
            if scientist:
                try:selected=scientist.choose(options,history,sources)
                except Exception as e:log("tinker_invalid_action",{"reason":type(e).__name__+": "+str(e)[:500],"fallback":"top exact-formula heuristic"})
            proposal=options[selected];used.add((proposal["law"],tuple(proposal["point"])))
            try:
                sid,ready=providers.write("proposer","precision-plan-"+str(trial),"BoundForge high precision proposal "+json.dumps(proposal)+". Derived from stationary free-energy insertion score, requiring independent certification.",{"trial":trial})
                if ready:
                    _,present=providers.read("verifier","BoundForge high precision proposal "+str(proposal["point"]),sid)
                    log("skeptic_review",{"source_id":sid,"cross_role_recall_verified":present,"decision":"Run bounded numerical solve; no acceptance without exact check."})
            except Exception as e:log("memory_unavailable",{"reason":type(e).__name__})
            log("precision_decision",{"trial":trial,"proposal":proposal,"dual_estimate":nu,"source_urls":[r.get("url") for e in sources for r in e.get("results",[])]})
            try:providers.ledger.reserve("modal",0.40)
            except Disabled as error:
                log("stop",{"reason":str(error),"policy":"preserve strongest certified witness"})
                break
            try:
                candidate,stats=precision_worker.remote(best,proposal)
                accept(candidate,stats,"structural insertion "+str(proposal))
            except Exception as e:
                log("failed_experiment",{"label":"structural insertion","proposal":proposal,"reason":str(e)[:1000]})
            if trial==1:
                try:sources.append(providers.exa("C3c arithmetic Kakeya entropy stationary free energy support extensions numerical certificates"))
                except Exception as e:log("provider_disabled",{"provider":"exa","reason":type(e).__name__})
    if scientist:scientist.close()
    lo,hi,_=verify.measure(best)
    with localcontext() as ctx:
        ctx.prec=120
        scaled=(Decimal(lo.mid().str(100,radius=False))*Decimal(10)**70).to_integral_value(rounding=ROUND_FLOOR)
        claim=int(scaled)-1
    best["claimed_lower_bound"]=[claim,10**70]
    result=verify.report(best)
    if not result["claim_certified"]:raise RuntimeError("final decimal claim not certified")
    (out/"best.json").write_text(json.dumps(best,indent=2))
    p=subprocess.run([sys.executable,str(ROOT/"verify_independent.py"),str(out/"best.json"),str(ROOT/"certificates/incumbent.json")],capture_output=True,text=True,timeout=300)
    if p.returncode:raise RuntimeError("independent final certification failed: "+p.stderr[-1000:])
    independent=json.loads(p.stdout)
    log("independent_final",independent)
    for n,h in protected.items():
        if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise RuntimeError("protected verifier changed")
    summary={"result":"strict certified improvement to incumbent witness" if verify.improves(best,baseline) else "no certified improvement","strict_improvement":verify.improves(best,baseline),"independent":independent,"best":result,"baseline":verify.report(baseline),"experiments":history,"providers":providers.ledger.summary(),"elapsed_seconds":time.monotonic()-start,"source_commit":os.environ.get("GITHUB_SHA"),"workflow_run":os.environ.get("GITHUB_RUN_ID"),"protected_sha256":protected,"tinker_training":"Not run: early verified outcomes insufficient to support a useful held-out training comparison. Actual model decisions, if any, are counted from tinker_decision trace events.","claim_scope":"A stricter exact certificate than the published witness, if checks pass. Literature-priority and meaningful display-digit change require separate assessment; no sharp-constant claim."}
    (out/"report.json").write_text(json.dumps(summary,indent=2))
    (out/"sources.json").write_text(json.dumps(sources,indent=2))
    print("BOUNDFORGE_FINAL "+json.dumps(summary),flush=True)
if __name__=="__main__":main()
