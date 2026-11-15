"""Publish the completed paired diagnostic and final, scoped claims; no paid calls."""
import argparse,datetime as dt,hashlib,json,os,pathlib,sqlite3,sys,subprocess
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
import verify,verify_independent
from publish import api,download,REPO,BRANCH
def main():
    if not os.environ.get("GITHUB_ACTIONS"):raise SystemExit("remote only")
    ap=argparse.ArgumentParser();ap.add_argument("--publish",action="store_true");a=ap.parse_args()
    out=HERE/"followup";out.mkdir(exist_ok=True)
    provenance=download("43676577601","boundforge-nondegenerate",out)
    r=json.loads((out/"report.json").read_text());best=json.loads((out/"best.json").read_text())
    baseline=json.loads((ROOT/"results/best.json").read_text())
    for name,h in r["protected_sha256"].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
    exact=verify.report(best);lo,hi=verify_independent.check(best);bl,bh=verify_independent.check(baseline)
    improved=verify.improves(best,baseline);assert improved==r["strict_improvement"]
    if improved:assert lo>bh
    cases=[json.loads(l) for l in (out/"cases.jsonl").read_text().splitlines() if l]
    assert len(cases)==87 and all(c["nondegenerate"] for c in cases)
    rows="\n".join(f"| {arm} | {s['cases']} | {s['nondegenerate']} | {s['positive_oracles']} | {s['best_F']:.9g} | {s['cpu_seconds']:.2f} | {s['wall_worker_seconds']:.2f} |" for arm,s in r["arms"].items())
    db=sqlite3.connect("file:"+str(out/"budget.sqlite")+"?mode=ro",uri=True)
    reservations=[dict(zip(("id","provider","reserved","actual","status"),row)) for row in db.execute("select id,provider,reserved,actual,status from reservations")]
    db.close();(out/"budget.sqlite").unlink()
    (out/"reservations.json").write_text(json.dumps(reservations,indent=2))
    pilot=json.loads((HERE/"output/report.json").read_text())
    usage=dict(pilot["usage"])
    usage.update(cumulative_ledger=r["providers"],followup_modal_allowance_usd=15.05,
      modality="No new Exa, Tinker or past.dev paid calls in the paired follow-up.",
      unresolved="Modal actual billed charge unavailable: retain cumulative USD52.10 allowance including prior USD22. Tinker token estimate is not an invoice; retain USD2.40 cumulative allowance including prior USD1.20. Exa cumulative USD0.31 includes prior USD0.232; new receipts USD0.078. past.dev cumulative 78 credits includes prior69 and new9 estimated. No active jobs remain; holds await provider reconciliation.",
      cpu_measurement="First pilot reports worker wall time and evaluations; actual process CPU was not captured there. Follow-up records process CPU separately. CPU time is not allocated vCPU-seconds or an invoice.")
    (out/"usage.json").write_text(json.dumps(usage,indent=2))
    r.update(publication_exact_check=exact,publication_independent_interval=[verify_independent.decimal(lo),verify_independent.decimal(hi,True)],publication_provenance=provenance,usage=usage)
    (out/"report.json").write_text(json.dumps(r,indent=2));(out/"provenance.json").write_text(json.dumps(provenance,indent=2))
    note=f"""# Final assessment: research-led C3c campaign

Research date: November 14, 2026 (America/Los_Angeles); execution receipts span November 14–15 UTC.
[Review](../COMPARATIVE_REVIEW.md) · [Preregistration](../DIRECTION_AND_PREREGISTRATION.md) · [First pilot](../output/RESEARCH_NOTE.md) · [Paired protocol](../NONDEGENERATE_FOLLOWUP.md) · [Remote run]({provenance['url']})

## Outcome and stopping decision

No new improvement in this campaign. Retain the earlier exact certificate:
[{verify_independent.decimal(lo)}, {verify_independent.decimal(hi,True)}].

That witness improves Jaswal's published exact construction by approximately 2.21 × 10⁻²²,
mostly by removing digit-count rounding loss; it is not a substantial new mathematical bound.
Its leading 15 digits are unchanged. No universal upper bound or optimality result was established.

The original 87-case pilot mostly collapsed onto point masses, where the numerical score F=0
is uninformative. The registered paired follow-up changes the optimizer and requires H(X−Y)≥1 nat.
All 87 saved support/seed pairs became nondegenerate; none exceeded the F>1e−9 screen.
Finite-bank compositions did not improve the retained certificate.
This disentangles one optimizer failure from support quality, but does not prove these supports
cannot improve under another optimizer, entropy scale, probability landscape or composition.
The floor and graph-support grammar are search restrictions, not mathematical reductions.

| Arm | Cases | Nondegenerate | F>1e−9 | Best F | Process CPU seconds | Worker wall seconds |
|---|---:|---:|---:|---:|---:|---:|
{rows}

Across both batches: 174 support/start cases, three probability initializations each.
Five of six actual Tinker program proposals parsed; one invalid JSON response retained and not replaced.
The paired study reused the same programs: no additional model calls and no retraining.
Structured proposals performed best in this limited score comparison; general superiority is not established.
No learning or shared-memory performance advantage is demonstrated. Six model calls are insufficient
for a broad cost-effectiveness claim. No fine-tuning was justified.

Stop scaling this grammar and optimizer pairing: no positive separator warrants further composition
work, and more equivalent trials have weak expected benefit. Unspent credits are not a reason to continue.
A future study would need a meaningfully broader, mathematically motivated representation and new
preregistered comparisons. Such a study has not been executed here.

## Contribution and reviewer objections

The present contribution is a reproducible engineering and negative-methodology case study,
plus a tiny pre-existing certified refinement. It is not yet a compelling substantial mathematics paper
or demonstrated autonomous-discovery framework advance. A workshop/demo submission might be feasible
after specialist review, but no venue acceptance is predicted and nothing has been submitted.

Strong objections: a one-target study, narrow graph grammar, small model sample, no training experiment,
non-global numerical optimization, an exploratory rather than untouched-held-out optimizer correction,
and incomplete billed-cost reconciliation. The initial incumbent-basin diagnostic is distinct from the
fixed/random/model program comparison. Budgets were bounded, not compute-identical across all arms.
A finite-bank LP sparsity observation is standard linear programming, not a new theorem.

## Claim-by-claim evidence

| Claim | Type | Evidence and limit |
|---|---|---|
| Nine primary-source precedents reviewed before new implementation | Provenance | ../COMPARATIVE_REVIEW.md and source commits |
| Official FunSearch priority yields 512, constant256, random256–262 | Exact diagnostic | ../evidence/funsearch-replay.json; construction replay, not historical discovery |
| Model generated six bounded proposals | Empirical | First-pilot trace; five parsed, one invalid; no model-written Python executed |
| Point-mass collapse prevented in paired diagnostic | Empirical | 87 saved cases, Htarget floor, nondegenerate measurements |
| No separator in tested follow-up | Empirical | cases.jsonl; does not prove no separator exists |
| No new certificate in this campaign | Certified computational comparison | Both unchanged independent checkers against earlier best |
| Existing exact witness remains valid | Certified computational result | best.json; intervals above, protected checker hashes in report |
| At most four laws suffice for an optimal fixed finite-bank LP | Standard mathematical observation | ../MATHEMATICAL_SCOPE.md; not a statement about all laws |
| Model/memory improves discovery efficiency | Not established | No claimed advantage |
| Publication-level mathematical advance | Not established | No substantial new bound, construction principle or theorem |

## Costs and remaining holds

New Exa API response receipts: USD0.078 (USD0.070 review plus USD0.008 in-loop).
Six Tinker calls, uncached-rate token estimate: USD{usage['tinker_token_estimate_usd']:.7f};
estimate is not a final charge. New past.dev estimated usage:9 credits.
Modal process CPU in the paired study: {sum(s['cpu_seconds'] for s in r['arms'].values()):.2f}s;
worker wall time and GitHub elapsed time are separate. First-pilot process CPU is unavailable.

Conservative cumulative ledger, including earlier work: Exa USD0.31, Modal USD52.10,
Tinker USD2.40, past.dev78 credits. The new campaign adds at most USD30.10 in Modal
allowances and USD1.20 Tinker holds. Unknown actual charges remain reserved; do not label
these held amounts as spent. A pre-launch Modal serialization integration error started
no paid worker; its failed local ledger is not an additional completed-job charge.
All dispatched paid search jobs have ended. No paid resources are intentionally left running.
See usage.json and reservations.json for explicit unresolved reconciliation.

Initial verified balances/caps and billing boundaries: ../campaign-budget.json.
No credits were bought, auto-reload enabled, plans upgraded or provider balances pooled.

## Reproduction and artifact map

Both protected checkers ran on the source campaign, in its separate checking step and again
during publication. The independent rational-series verifier imports neither the search nor Arb.
The browser checks exact integer/rational structural conditions only; it does not prove entropy bounds.

    python boundforge/verify.py boundforge/research_v2/followup/best.json --baseline boundforge/results/best.json
    python boundforge/verify_independent.py boundforge/research_v2/followup/best.json boundforge/results/best.json
    python -m pytest -q -p no:cacheprovider boundforge/test_core.py boundforge/research_v2/test_v2.py

Raw follow-up: cases.jsonl, law-bank.json, trace.jsonl, best.json, report.json.
First pilot: ../output/ including model outputs, programs, sources, plot and offline demo.html.
Paired scientific plot: paired-scores.svg. All source code and artifacts live remotely in this repository;
no workstation project files were created.
"""
    (out/"FINAL_RESEARCH_NOTE.md").write_text(note)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,5))
    for arm in r["arms"]:
        cc=[(i,c) for i,c in enumerate(cases) if c["arm"]==arm]
        ax.scatter([i for i,c in cc],[c["free_energy"] for i,c in cc],s=22,label=arm)
    ax.axhline(1e-9,ls="--",c="black",lw=.8);ax.set_yscale("symlog",linthresh=1e-9)
    ax.set(xlabel="Paired case index",ylabel="Numerical free-energy score F",title="Entropy-constrained follow-up: all scores nonpositive")
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/"paired-scores.svg");plt.close(fig)
    print("BF2F_PUBLICATION "+json.dumps({"strict_improvement":improved,"cases":len(cases),"positive_oracles":sum(s["positive_oracles"] for s in r["arms"].values()),"usage":usage}),flush=True)
    if a.publish:
        paths=[p for p in out.iterdir() if p.is_file() and p.suffix in (".json",".jsonl",".md",".svg",".txt")]
        tree=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in paths]
        assert all(x["path"].startswith("boundforge/research_v2/followup/") for x in tree)
        for attempt in range(3):
            head=api("git/ref/heads/"+BRANCH)["object"]["sha"];base=api("git/commits/"+head)["tree"]["sha"]
            t=api("git/trees","POST",{"base_tree":base,"tree":tree})["sha"]
            commit=api("git/commits","POST",{"message":"Publish paired C3c diagnostic, exact retained certificate and honest final assessment","tree":t,"parents":[head]})["sha"]
            try:api("git/refs/heads/"+BRANCH,"PATCH",{"sha":commit,"force":False});break
            except RuntimeError:
                if attempt==2:raise
        print("BF2F_PUBLISHED "+commit,flush=True)
if __name__=="__main__":main()
