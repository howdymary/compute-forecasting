"""Remote, resumable autonomous research loop; no arbitrary generated code execution."""
import argparse, copy, datetime as dt, hashlib, json, os, pathlib, subprocess, sys, time
import numpy as np
import search,verify
from providers import Providers,Disabled,prepare_output
ROOT=pathlib.Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--trials",type=int,default=24)
    ap.add_argument("--seconds",type=int,default=12)
    ap.add_argument("--seed",type=int,default=20261115)
    ap.add_argument("--remote",action="store_true")
    ap.add_argument("--resume",action="store_true")
    a=ap.parse_args()
    if not os.environ.get("GITHUB_ACTIONS") and not os.environ.get("BOUNDFORGE_ALLOW_LOCAL"):raise SystemExit("Run this project on GitHub Actions; no workstation execution authorised.")
    if not 1<=a.trials<=240 or not 1<=a.seconds<=60:raise SystemExit("batch outside bounded limits")
    out=ROOT/"results";out.mkdir(exist_ok=True)
    if not a.resume and os.environ.get("BOUNDFORGE_OUTPUT_PREPARED")!="1":prepare_output(out)
    path=out/"trace.jsonl"
    def log(kind,payload):
        row={"timestamp":dt.datetime.now(dt.timezone.utc).isoformat(),"kind":kind,**payload}
        with path.open("a") as fp:fp.write(json.dumps(row,sort_keys=True)+"\n")
        print("BF_EVENT "+json.dumps(row,sort_keys=True),flush=True)
    protected={p.name:digest(p) for p in [ROOT/"verify.py",ROOT/"verify_independent.py"]}
    original=json.loads((ROOT/"certificates/incumbent.json").read_text())
    baseline=verify.report(original)
    if not baseline["claim_certified"]:raise RuntimeError("incumbent reproduction failed")
    log("baseline",baseline)
    # An independent exact-series check runs before search and again in a separate final job.
    p=subprocess.run([sys.executable,str(ROOT/"verify_independent.py"),str(ROOT/"certificates/incumbent.json")],capture_output=True,text=True,timeout=240)
    if p.returncode:raise RuntimeError("independent baseline verifier failed: "+p.stderr[-1000:])
    log("independent_baseline",json.loads(p.stdout))
    best=copy.deepcopy(original)
    history=[];pool=copy.deepcopy(original["laws"]);failures={k:0 for k in ["weights","augment","exchange","new-law"]}
    if a.resume and (out/"checkpoint.json").exists():
        ck=json.loads((out/"checkpoint.json").read_text())
        verify.validate(ck["best"])
        if verify.improves(ck["best"],best):best=ck["best"]
        history=ck["history"];failures.update(ck["failures"]);pool=ck["pool"]
    providers=Providers(out,log)
    # Bibliographic data retrieved here is untrusted data, never executable instructions.
    literature=[];method_hints=[]
    def investigate(query):
        try:
            ev=providers.exa(query);literature.append(ev)
            text=" ".join(x.get("text","") for x in ev["results"]).lower()
            if "newton" in text or "free energy" in text:method_hints.append("weights")
            if "tensor" in text or "independent" in text:method_hints.append("new-law")
            if "support" in text:method_hints.append("augment")
            log("source_to_method",{"source_urls":[x["url"] for x in ev["results"]],"selected_hints":method_hints,"rule":"Explicit keyword-to-operator mapping; no claimed new theorem."})
        except Exception as e:log("provider_disabled",{"provider":"exa","reason":str(e)[:200]})
    investigate("four slope sums differences C3c 1.674894211307116 Manvir Jaswal entropy free energy Newton independent digits")
    cross_role=False; prior_id=None
    try:
        sid,ready=providers.write("verifier","baseline",f"BoundForge C3c incumbent independently verified. Ratio interval {baseline['ratio_interval_arb']}. Independent digit-law composition is valid; mixing probabilities is different. Prioritise structural support changes after failed fixed-support trials.",{"certificate_sha256":digest(ROOT/"certificates/incumbent.json")})
        if ready:
            docs,cross_role=providers.read("proposer","BoundForge C3c verifier incumbent independent digit composition structural support changes",sid)
            prior_id=sid
    except Exception as e:log("provider_disabled",{"provider":"past","reason":str(e)[:200]})
    rng=np.random.default_rng(a.seed)
    start=time.monotonic()
    for i in range(len(history),a.trials):
        # Enforced escalation after two unsuccessful trials in a neighborhood.
        kinds=["weights","augment","exchange","new-law"]
        if i<len(kinds):kind=kinds[i]
        else:
            allowed=[k for k in kinds if failures[k]<2]
            if not allowed:failures={k:0 for k in kinds};allowed=kinds
            scores={k:sum(h.get("float_gain",0) for h in history if h["operator"]==k)+0.002/(1+sum(h["operator"]==k for h in history)) for k in allowed}
            if method_hints:
                for k in allowed:scores[k]+=0.0001*method_hints.count(k)
            kind=max(scores,key=scores.get)
        if cross_role and i==0:
            kind="augment" # actual use of verifier-written memory, logged rather than merely cited
        reason="Verifier-written memory recommends structural support exploration." if cross_role and i==0 else "Adaptive operator priority from observed gains, attempt counts, source hints and per-neighborhood failure limits."
        log("decision",{"trial":i,"operator":kind,"reason":reason,"failures":failures.copy(),"memory_source_used":prior_id if cross_role and i==0 else None})
        initial=search.mutate(best,kind,rng,i)
        trial_start=time.monotonic()
        if a.remote:
            from modal_worker import remote_optimize
            try:token=providers.ledger.reserve("modal",0.20)
            except Disabled as error:
                log("stop",{"reason":str(error),"policy":"preserve strongest certified witness"})
                break
            # Failure keeps full reservation; never retry a billable job automatically.
            candidate,stats=remote_optimize(initial,a.seconds)
            providers.ledger.settle(token,None)
        else:candidate,stats=search.optimize(initial,a.seconds)
        verify.validate(candidate)
        pool.extend(candidate["laws"])
        # Pool bounded to keep composition LP and checkpoint small.
        if len(pool)>70:pool=pool[:2]+pool[-68:]
        combined=search.compose(pool)
        if combined is not None and search.score(combined)>search.score(candidate):candidate=combined
        checked=verify.report(candidate)
        accepted=verify.improves(candidate,best)
        old_score=search.score(best)
        if accepted:best=candidate;failures[kind]=0
        else:failures[kind]+=1
        record={"trial":i,"operator":kind,"accepted":accepted,"strictly_beats_published_certificate":verify.improves(candidate,original),"float_score":search.score(candidate),"float_gain":search.score(candidate)-old_score,"seconds":time.monotonic()-trial_start,"solver":stats,"certificate_report":checked}
        history.append(record)
        (out/f"candidate-{i:03d}.json").write_text(json.dumps(candidate,sort_keys=True))
        (out/"best.json").write_text(json.dumps(best,indent=2))
        (out/"checkpoint.json").write_text(json.dumps({"best":best,"history":history,"pool":pool,"failures":failures,"seed":a.seed}))
        log("experiment",record)
        if i==max(3,a.trials//2):
            investigate("arithmetic Kakeya entropy sums differences optimization support augmentation variational dual multipliers")
            try:
                failed=[h["operator"] for h in history if not h["accepted"]]
                rid,ready=providers.write("proposer","failed-neighborhoods",f"BoundForge C3c bounded batch: {len(history)} completed trials. Failed attempted operator families: {failed}. This is bounded numerical evidence, NOT a proof these neighborhoods are exhausted. Next test should change support or add an independent law.",{"seed":a.seed})
                if ready:
                    _,used=providers.read("verifier","BoundForge proposer bounded failed neighborhoods next structural support change",rid)
                    log("skeptic_decision",{"memory_source_used":rid if used else None,"decision":"Keep incumbent unless exact interval check passes; treat numerical failures as local evidence only."})
                    # Both roles must actually read and write, no fabricated sponsor qualification.
                    providers.write("verifier","review",f"BoundForge skeptic reviewed proposer source {rid}. Cross-role recall contained required source: {used}. Failed bounded trials do not prove optimality. Certification remains independent.")
                    providers.read("proposer","BoundForge verifier skeptic bounded failures do not prove optimality")
            except Exception as e:log("provider_disabled",{"provider":"past","reason":str(e)[:200]})
    for name,h in protected.items():
        if digest(ROOT/name)!=h:raise RuntimeError("protected verifier changed")
    improved=verify.improves(best,original)
    final={"research_date":dt.datetime.now(dt.timezone.utc).isoformat(),"result":"certified improvement" if improved else "incumbent reproduced; no improvement","strict_improvement":improved,"baseline":baseline,"best":verify.report(best),"trials":len(history),"seed":a.seed,"search_wall_seconds":time.monotonic()-start,"providers":providers.ledger.summary(),"protected_sha256":protected,"source_commit":os.environ.get("GITHUB_SHA"),"workflow_run":os.environ.get("GITHUB_RUN_ID"),"exa_calls":len(literature),"cross_role_reuse":cross_role,"operators":{k:{"trials":sum(h["operator"]==k for h in history),"accepted":sum(h["operator"]==k and h["accepted"] for h in history)} for k in failures}}
    (out/"best.json").write_text(json.dumps(best,indent=2))
    (out/"report.json").write_text(json.dumps(final,indent=2))
    (out/"sources.json").write_text(json.dumps(literature,indent=2))
    log("final",final)
    print("BOUNDFORGE_FINAL "+json.dumps(final),flush=True)
if __name__=="__main__":
    if "--remote" in sys.argv:
        # Start only after a verified snapshot and a conservative image/build reservation.
        from providers import Ledger
        remote_out=ROOT/"results";remote_out.mkdir(exist_ok=True)
        if "--resume" not in sys.argv:
            prepare_output(remote_out)
            os.environ["BOUNDFORGE_OUTPUT_PREPARED"]="1"
        Ledger(remote_out).reserve("modal",2.0)
        from modal_worker import app
        with app.run():main()
    else:main()
