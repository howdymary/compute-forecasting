"""Phase-one literature discovery only. No numerical search or model training."""
import datetime as dt,hashlib,json,os,pathlib,subprocess,urllib.request,urllib.error
HERE=pathlib.Path(__file__).resolve().parent
OUT=HERE/"evidence";OUT.mkdir(exist_ok=True)
QUERIES=[
("funsearch","FunSearch Romera Paredes Nature 2023 program search cap sets official repository evaluator limitations"),
("alphaevolve","AlphaEvolve mathematical exploration discovery at scale 2511.02864 search mode evaluation cost ablations arithmetic Kakeya"),
("patternboost","PatternBoost 2411.00566 Charton Ellenberg Wagner Williamson official code constructions local search training"),
("wagner","Adam Zsolt Wagner Constructions in combinatorics via neural networks 2104.14516 cross entropy method code"),
("alphatensor","AlphaTensor Fawzi Nature 2022 matrix multiplication algorithms tensor game verification official code"),
("arithmetic-kakeya","Green Ruzsa arithmetic Kakeya entropy sum differences 1712.02108 C3c"),
("jaswal","Manvir Jaswal C3c 23289305 two law entropy certificate free energy Newton stationary"),
("negative-replication","Towards Learning-Guided Discovery Extremal Geometric Constructions PatternBoost Study 2610.19980 diversity"),
("current-frontier","four slope arithmetic Kakeya C3c 1.674894211307116 new bound entropy certificate"),
("dual-oracles","entropy inequality optimization finite random variables support optimization sum difference dual column generation")
]
def req(url,key,payload=None,header="Authorization"):
    data=None if payload is None else json.dumps(payload).encode()
    h={header:("Bearer " if header=="Authorization" else "")+key,"Content-Type":"application/json"}
    with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=h),timeout=60) as r:return json.load(r)
def main():
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    past=req("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])
    probes={}
    for name,args in [("modal",["modal","billing","summary","--json"])]:
        p=subprocess.run(args,capture_output=True,text=True,timeout=60)
        probes[name]=json.loads(p.stdout) if p.returncode==0 else {"unavailable":True}
    snapshot={"timestamp":now,"source_sha":os.environ.get("GITHUB_SHA"),"phase":"literature discovery only","providers":{
      "exa":{"initial_cap":119.52,"unit":"USD prepaid","verified":"Authenticated dashboard, 2026-11-15 around 04:00 UTC","prior_unresolved_allowance":0.232,"phase1_cap":2,"phase3_proposed_cap":8,"billing_boundary":"Free tier; no payment method; no automatic top-up","expiration":"not exposed"},
      "modal":{"initial_cap":249.24,"unit":"USD compute credit","verified":"Authenticated dashboard","prior_unresolved_allowance":22,"phase1_cap":0,"phase3_proposed_cap":60,"expiration":"grant expires 2027-11-30","billing_boundary":"Starter no-payment usage cap; no settings changed","read_only_probe":probes["modal"]},
      "tinker":{"initial_cap":281.71,"unit":"USD prepaid","verified":"Authenticated dashboard; auto-reload off; free checkpoint storage 20GB, 71/100 checkpoints","prior_unresolved_allowance":1.2,"phase1_cap":0,"phase3_proposed_cap":20,"expiration":"not exposed"},
      "past":{"initial_cap":past.get("balance",{}).get("left"),"unit":"credits","verified":"GET /usage before paid work","prior_unresolved_allowance":20,"phase1_cap":0,"phase3_proposed_cap":400,"read_only_probe":{k:past.get(k) for k in ["month","balance","metered"]}}
    },"policy":"No purchases, upgrades, auto-reload, or unverified billing. Phase 3 requires completed evidence-backed review."}
    (OUT/"budget-snapshot.json").write_text(json.dumps(snapshot,indent=2))
    print("BF2_BUDGET "+json.dumps(snapshot),flush=True)
    reserved=0;actual=0;events=[]
    for slug,query in QUERIES:
        if reserved+0.1+actual>2:break
        reserved+=0.1
        try:
            response=req("https://api.exa.ai/search",os.environ["EXA_API_KEY"],{"query":query,"type":"auto","numResults":5,"contents":{"text":{"maxCharacters":9000}}},"x-api-key")
            cost=response.get("costDollars",{}).get("total")
            if cost is not None and not 0<=cost<=0.1:raise ValueError("cost exceeded reservation")
            if cost is not None:reserved-=0.1;actual+=cost
            event={"slug":slug,"query":query,"retrieved_at":dt.datetime.now(dt.timezone.utc).isoformat(),"request_id":response.get("requestId"),"cost_usd":cost,"results":[]}
            private=[]
            for r in response.get("results",[]):
                text=r.get("text","")
                event["results"].append({"title":r.get("title"),"url":r.get("url"),"published_date":r.get("publishedDate"),"text_sha256":hashlib.sha256(text.encode()).hexdigest(),"excerpt":text[:100]})
                private.append({"url":r.get("url"),"text":text})
            # Full retrieved source text is a transient research input, excluded from publication.
            (OUT/(slug+"-working.json")).write_text(json.dumps(private))
            events.append(event)
            (OUT/"discovery.json").write_text(json.dumps(events,indent=2))
            print("BF2_DISCOVERY "+json.dumps(event),flush=True)
        except Exception as error:
            print("BF2_FAILED "+json.dumps({"slug":slug,"error_type":type(error).__name__,"reservation_retained":0.1}),flush=True)
    usage={"exa_response_cost_usd":actual,"exa_unresolved_reserved_usd":reserved,"requests_succeeded":len(events),"modal_billable_calls":0,"tinker_billable_calls":0,"past_billable_calls":0}
    (OUT/"usage.json").write_text(json.dumps(usage,indent=2))
    print("BF2_USAGE "+json.dumps(usage),flush=True)
if __name__=="__main__":main()
