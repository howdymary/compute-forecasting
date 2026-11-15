"""Preregistered three-start C3c construction-program and complementary-law pilot."""
import copy,datetime as dt,hashlib,json,os,pathlib,sys,time
import numpy as np
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
import verify,verify_independent,precision
from common import CampaignProviders,Disabled
from constructions import support,validate,structured,random_programs,compose
SEEDS=[101,202,303]
def main():
    if not os.environ.get("GITHUB_ACTIONS"):raise SystemExit("remote execution only")
    out=HERE/"output";out.mkdir(exist_ok=True)
    events=[];cases=[];programs=[];bank=[];start=time.monotonic()
    def log(kind,payload):
        payload=copy.deepcopy(payload)
        if kind=="exa_sources":
            for r in payload.get("results",[]):
                text=r.pop("text","");r["text_sha256"]=hashlib.sha256(text.encode()).hexdigest();r["excerpt"]=text[:120]
        row={"timestamp":dt.datetime.now(dt.timezone.utc).isoformat(),"kind":kind,**payload};events.append(row)
        (out/"trace.jsonl").write_text("\n".join(json.dumps(e) for e in events)+"\n")
        print("BF2_EVENT "+json.dumps(row),flush=True)
    baseline=json.loads((ROOT/"results/best.json").read_text())
    assert verify.report(baseline)["claim_certified"]
    protected={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ["verify.py","verify_independent.py"]}
    bank=copy.deepcopy(baseline["laws"]);best=copy.deepcopy(baseline)
    # Estimate the proposal dual at high precision.
    precision.mp.mp.dps=110;nu=[float(x) for x in precision.dual(baseline)]
    log("frozen_protocol",{"review_sha256":hashlib.sha256((HERE/"COMPARATIVE_REVIEW.md").read_bytes()).hexdigest(),"preregistration_sha256":hashlib.sha256((HERE/"DIRECTION_AND_PREREGISTRATION.md").read_bytes()).hexdigest(),"seeds":SEEDS,"baseline":verify.report(baseline),"dual":nu,"protected_sha256":protected})
    providers=CampaignProviders(out,log)
    source_events=[]
    def research(query):
        try:source_events.append(providers.exa(query))
        except Exception as e:log("source_search_failed",{"error":type(e).__name__})
    research("AlphaEvolve search mode arithmetic Kakeya entropy discrete Gaussian construction programs")
    try:
        sid,ready=providers.write("literature","v2-review","BoundForge comparative review: keep C3c, stop tail-only search. FunSearch replay verifies 512 versus constant 256. Test new construction programs and complementary entropy vectors. Numerical ranking outperformed four model choices in the earlier pilot.",{"review":"research_v2/COMPARATIVE_REVIEW.md"})
        if ready:providers.read("proposer","BoundForge comparative review new construction programs entropy vectors",sid)
    except Exception as e:log("memory_unavailable",{"error":type(e).__name__})
    from worker import app,run_case
    providers.ledger.reserve("modal",2)
    def run_batch(specs):
        nonlocal best,bank
        pending=[]
        for spec in specs:
            try:providers.ledger.reserve("modal",0.15)
            except Disabled as e:log("budget_stop",{"reason":str(e)});break
            pending.append((spec,run_case.spawn(spec,nu)))
        for spec,call in pending:
            try:
                result=call.get()
                row={k:v for k,v in result.items() if k!="law"}
                row.update(arm=spec["arm"],program=spec["name"],expr=spec.get("expr"))
                cases.append(row);bank.append(result["law"])
                (out/"cases.jsonl").write_text("\n".join(json.dumps(c) for c in cases)+"\n")
                (out/"law-bank.json").write_text(json.dumps(bank))
                log("case",row)
            except Exception as e:log("case_failed",{"arm":spec["arm"],"program":spec["name"],"seed":spec["seed"],"error":type(e).__name__+": "+str(e)[:300]})
        candidate,lp=compose(bank)
        accepted=verify.improves(candidate,best)
        if accepted:best=candidate
        (out/"best.json").write_text(json.dumps(best,indent=2))
        log("composition",{"bank_size":len(bank),"lp":lp,"accepted":accepted,"candidate":verify.report(candidate),"retained":verify.report(best)})
    heavy=[]
    for law in baseline["laws"]:
        heavy.append(sorted(zip(law["points"],[a/b for a,b in law["weights"]]),key=lambda x:-x[1])[:10])
    fixed=[{**p,"arm":"structured"} for p in structured()]
    random=[{**p,"arm":"random"} for p in random_programs()]
    for p in fixed+random:validate(p["expr"]);support(p["expr"]);programs.append(p)
    generator=None
    try:
        from model import Generator
        generator=Generator(providers)
    except Exception as e:log("model_disabled",{"error":type(e).__name__})
    with app.run():
        # Development start only; hold out 202 and 303 until programs are frozen.
        run_batch([{**p,"seed":101} for p in programs])
        for generation in range(3):
            proposed=[]
            for k in range(2):
                index=generation*2+k
                if generator is None:log("invalid_program",{"index":index,"reason":"model unavailable; no extra replacement proposal"});continue
                feedback=[{k:c[k] for k in ("arm","program","free_energy","nondegenerate","ratio")} for c in cases if c["seed"]==101]
                try:
                    p=generator.propose(index,feedback,nu,heavy,source_events)
                    validate(p["expr"]);support(p["expr"])
                    canonical=json.dumps(p["expr"],sort_keys=True)
                    if canonical in [json.dumps(q["expr"],sort_keys=True) for q in programs]:raise ValueError("duplicate program")
                    p={"name":"model-"+str(index)+"-"+str(p.get("name",""))[:40],"expr":p["expr"],"arm":"model","reason":str(p.get("reason",""))[:800]}
                    programs.append(p);proposed.append(p)
                    log("valid_program",p)
                except Exception as e:log("invalid_program",{"index":index,"reason":type(e).__name__+": "+str(e)[:300],"counts_against_model_budget":True})
            run_batch([{**p,"seed":101} for p in proposed])
            if generation==0:
                research("PatternBoost extremal construction representation seed diversity local optimization plateau")
                try:
                    sid,ready=providers.write("proposer","v2-development","BoundForge development results "+json.dumps([{"arm":c["arm"],"F":c["free_energy"],"nondegenerate":c["nondegenerate"]} for c in cases])[:2400]+". Point-mass F=0 is not success; do not train on collapsed or duplicated laws.")
                    if ready:providers.read("verifier","BoundForge development collapsed point mass free energy not success",sid)
                    providers.write("verifier","v2-guard","BoundForge verification guard: a numerical positive dual-oracle score is a proposal only, not a universal inequality or record. Require both unchanged exact checkers. Preserve old best if all candidates fail.")
                    providers.read("proposer","BoundForge verifier guard numerical oracle no universal inequality")
                except Exception as e:log("memory_unavailable",{"error":type(e).__name__})
        frozen={"programs":programs,"sha256":hashlib.sha256(json.dumps(programs,sort_keys=True).encode()).hexdigest(),"held_out_seeds":[202,303],"freeze_timestamp":dt.datetime.now(dt.timezone.utc).isoformat()}
        (out/"program-freeze.json").write_text(json.dumps(frozen,indent=2));log("program_freeze",{"sha256":frozen["sha256"],"program_count":len(programs)})
        run_batch([{**p,"seed":seed} for p in programs for seed in [202,303]])
        # Separate incumbent-basin diagnostic; not part of the matched program comparison.
        specs=[]
        for k,law in enumerate(baseline["laws"]):
            p=np.array([a/b for a,b in law["weights"]]);heavy_ids=np.flatnonzero(p>1e-6)
            for seed in SEEDS:
                rng=np.random.default_rng(seed+k*1000)
                for width in [2,4,8,12,16,24]:
                    pts=copy.deepcopy(law["points"])
                    chosen=rng.choice(heavy_ids,size=min(width,len(heavy_ids)),replace=False)
                    for i in chosen:
                        change=int(rng.choice([-2,-1,1,2]))
                        pts[int(i)][0]+=change;pts[int(i)][1]+=change # preserve each target difference
                    specs.append({"arm":"basin-mutation","name":f"law{k}-width{width}","seed":seed,"points":pts,"initial":p.tolist()})
        run_batch(specs)
    if generator:generator.close()
    for n,h in protected.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h
    lo,hi=verify_independent.check(best);blo,bhi=verify_independent.check(baseline)
    improved=verify.improves(best,baseline)
    if improved and not lo>bhi:raise RuntimeError("independent check did not confirm improvement")
    stats={}
    for arm in ["structured","random","model","basin-mutation"]:
        rows=[c for c in cases if c["arm"]==arm]
        stats[arm]={"cases":len(rows),"nondegenerate":sum(c["nondegenerate"] for c in rows),"positive_oracles_over_1e-9":sum(c["nondegenerate"] and c["free_energy"]>1e-9 for c in rows),"best_free_energy":max((c["free_energy"] for c in rows),default=None),"function_evaluations":sum(c["calls"] for c in rows),"worker_seconds":sum(c["seconds"] for c in rows),"per_seed":{str(seed):max((c["free_energy"] for c in rows if c["seed"]==seed and c["nondegenerate"]),default=None) for seed in SEEDS}}
    report={"date":dt.datetime.now(dt.timezone.utc).isoformat(),"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"strict_improvement":improved,"baseline":verify.report(baseline),"best":verify.report(best),"independent_interval":[verify_independent.decimal(lo),verify_independent.decimal(hi,True)],"arms":stats,"model_proposals_budget":6,"model_programs_valid":sum(p["arm"]=="model" for p in programs),"model_inference_calls":sum(e["kind"]=="model_inference" for e in events),"training":"not performed: this pilot does not supply a diverse independent training/evaluation corpus","claims":"Descriptive three-start diagnostic on one C3c representation; no universal bound, optimality, model advantage or publication acceptance follows.","providers":providers.ledger.summary(),"protected_sha256":protected,"elapsed_seconds":time.monotonic()-start}
    (out/"report.json").write_text(json.dumps(report,indent=2));(out/"best.json").write_text(json.dumps(best,indent=2));(out/"sources.json").write_text(json.dumps([{"query":e["query"],"results":[{"title":r.get("title"),"url":r.get("url"),"text_sha256":hashlib.sha256(r.get("text","").encode()).hexdigest()} for r in e["results"]]} for e in source_events],indent=2))
    print("BF2_FINAL "+json.dumps(report),flush=True)
if __name__=="__main__":main()
