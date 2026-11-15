"""Provider access with durable, atomic, conservative reservations.
Never purchase credits or change plans. Unknown cost stays reserved after failures.
Single orchestration process owns this ledger; Modal workers receive no API keys.
"""
import datetime as dt, hashlib, json, os, pathlib, sqlite3, time, urllib.request, subprocess, csv, io
ROOT=pathlib.Path(__file__).resolve().parent
class Disabled(RuntimeError): pass
def http(url,key,payload=None,header="Authorization"):
    headers={header:("Bearer " if header=="Authorization" else "")+key,"Content-Type":"application/json"}
    body=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=body,headers=headers)
    with urllib.request.urlopen(req,timeout=50) as r: return json.load(r)
class Ledger:
    def __init__(self,out):
        self.snapshot=json.loads((ROOT/"budget-snapshot.json").read_text())
        self.db=sqlite3.connect(str(out/"budget.sqlite"),timeout=30)
        self.db.execute("create table if not exists reservations(id text primary key, provider text, reserved real, actual real, status text)")
        old=ROOT/"historical-usage.json"
        if old.exists():
            history=json.loads(old.read_text())
            for provider,amount in history["usage"].items():
                self.db.execute("insert or ignore into reservations values(?,?,?,?,?)",("historical-"+history["source_run"]+"-"+provider,provider,amount,amount,"historical conservative accounting"))
        self.db.execute("create table if not exists freezes(provider text primary key, reason text)")
        self.db.commit()
    def reserve(self,provider,amount,observed=None):
        p=self.snapshot["providers"][provider]
        if not p.get("enabled") or p.get("initial_cap") is None: raise Disabled(provider+": unverified balance")
        cap=min(float(p["initial_cap"]),float(p.get("operational_cap",0)))
        if provider=="modal":
            from preflight import cli
            billing=cli("modal","billing","summary","--json")
            if billing.get("status")!=200:raise Disabled("Modal live usage unavailable")
            cost=float(billing["data"]["metered_cost"])
            observed=max(0,float(p["initial_cap"])-max(0,cost-1.64005948))
        if provider=="tinker":
            # Account-wide gross usage is conservatively deducted in full, including
            # pre-snapshot usage. Missing/lagged spend is covered by large headroom.
            now=dt.datetime.now(dt.timezone.utc)
            end=(now.replace(minute=0,second=0,microsecond=0)+dt.timedelta(hours=1)).isoformat().replace("+00:00","Z")
            result=subprocess.run(["tinker","billing","usage","2026-11-14T00:00:00Z",end,"--csv","-"],capture_output=True,text=True,timeout=45)
            if result.returncode:raise Disabled("Tinker live usage unavailable")
            rows=list(csv.DictReader(io.StringIO(result.stdout)))
            if rows and "estimated_cost_usd" not in rows[0]:raise Disabled("Tinker cost schema unavailable")
            total_cost=sum(float(r.get("estimated_cost_usd") or 0) for r in rows)
            observed=max(0,float(p["initial_cap"])-total_cost-20) # guard for pending/lagged jobs
        self.db.execute("begin immediate")
        if self.db.execute("select reason from freezes where provider=?",(provider,)).fetchone():
            self.db.rollback();raise Disabled(provider+": frozen after accounting failure")
        total=self.db.execute("select coalesce(sum(coalesce(actual,reserved)),0) from reservations where provider=?",(provider,)).fetchone()[0]
        if amount<0 or total+amount>cap or (observed is not None and amount+10>observed):
            self.db.rollback();raise Disabled(provider+": budget reservation refused")
        ident=hashlib.sha256(f"{provider}:{time.time_ns()}".encode()).hexdigest()
        self.db.execute("insert into reservations values(?,?,?,?,?)",(ident,provider,amount,None,"pending"))
        self.db.commit();return ident
    def settle(self,ident,actual):
        row=self.db.execute("select reserved from reservations where id=?",(ident,)).fetchone()
        if actual is None:return # unknown remains fully reserved; no automatic retry
        if actual<0 or actual>row[0]:
            provider=self.db.execute("select provider from reservations where id=?",(ident,)).fetchone()[0]
            self.db.execute("insert or replace into freezes values(?,?)",(provider,"cost exceeded reservation"))
            self.db.commit()
            raise Disabled("actual cost exceeds reservation; provider frozen")
        self.db.execute("update reservations set actual=?,status='settled' where id=?",(actual,ident));self.db.commit()
    def summary(self):
        return {p:{"initial_cap":d.get("initial_cap"),"units":d.get("unit"),"enabled":d.get("enabled"),"operational_cap":d.get("operational_cap"),"reserved_or_actual":self.db.execute("select coalesce(sum(coalesce(actual,reserved)),0) from reservations where provider=?",(p,)).fetchone()[0]} for p,d in self.snapshot["providers"].items()}
class Providers:
    def __init__(self,out,log):
        self.out=out;self.log=log;self.ledger=Ledger(out)
        self.run_id=os.environ.get("GITHUB_RUN_ID",str(time.time_ns()))
    def exa(self,query):
        if not os.environ.get("EXA_API_KEY"):raise Disabled("Exa key absent")
        # Five results, no summaries/agent/websets; reserve 10 cents, far above
        # dashboard Lite tariff of $0.004 + at most $0.005 contents.
        token=self.ledger.reserve("exa",0.10)
        r=http("https://api.exa.ai/search",os.environ["EXA_API_KEY"],
               {"query":query,"type":"lite","numResults":5,"contents":{"text":{"maxCharacters":4500}}},"x-api-key")
        cost=r.get("costDollars",{}).get("total")
        self.ledger.settle(token,cost)
        entries=[{"title":x.get("title"),"url":x.get("url"),"text":x.get("text","")[:4500],"publishedDate":x.get("publishedDate")} for x in r.get("results",[])]
        event={"query":query,"request_id":r.get("requestId"),"cost_usd":cost,"results":entries}
        self.log("exa_sources",event)
        return event
    def past_usage(self):
        r=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])
        if not r.get("metered") or not isinstance(r.get("balance",{}).get("left"),(int,float)):raise Disabled("past balance unavailable")
        # New credits can never increase initial cap; live lower balances reduce usable allowance.
        return r
    def write(self,role,kind,content,metadata=None):
        if not os.environ.get("PAST_API_KEY"):raise Disabled("past key absent")
        stamp=dt.datetime.now(dt.timezone.utc).isoformat()
        sid=f"boundforge-{self.run_id}-{role}-{kind}"
        item={"id":sid,"identity":"boundforge-"+role,"audience":"project","label":"BoundForge "+kind,"content":content,"timestamp":stamp,"metadata":{"project":"boundforge","role":role,**(metadata or {})}}
        est=http("https://api.past.dev/api/v1/ingest/estimate",os.environ["PAST_API_KEY"],{"items":[item]})
        if not est.get("fits") or not est.get("metered") or not isinstance(est.get("credits"),(int,float)):raise Disabled("past estimate unavailable")
        live=self.past_usage()["balance"]["left"]
        token=self.ledger.reserve("past",est["credits"],live)
        r=http("https://api.past.dev/api/v1/ingest",os.environ["PAST_API_KEY"],{**item,"idempotencyKey":sid})
        self.ledger.settle(token,est["credits"])
        ing=r.get("ingestionId");ready=r.get("status")=="completed"
        for _ in range(15):
            if ready:break
            time.sleep(2)
            state=http("https://api.past.dev/api/v1/ingest/"+ing,os.environ["PAST_API_KEY"])
            ready=state.get("status")=="completed"
            if state.get("status")=="failed":break
        self.log("memory_write",{"role":role,"source_id":sid,"ready":ready,"estimated_credits":est["credits"]})
        return sid,ready
    def read(self,role,query,required=None):
        if not os.environ.get("PAST_API_KEY"):raise Disabled("past key absent")
        live=self.past_usage()["balance"]["left"]
        token=self.ledger.reserve("past",1,live)
        r=http("https://api.past.dev/api/v1/recall",os.environ["PAST_API_KEY"],{"query":query,"identity":"boundforge-"+role,"maxTokens":2000,"limit":12})
        self.ledger.settle(token,1) # conservative even when included recall is free
        body=json.dumps(r)
        ids={s.get("sourceId") for doc in r.get("results",[]) for s in doc.get("sources",[])}
        present=required is not None and required in ids
        # Only BoundForge result documents are retained; unrelated project memory is not published.
        documents=[x for x in r.get("results",[]) if "boundforge" in json.dumps(x).lower()]
        safe=[{"id":doc.get("id"),"content_sha256":hashlib.sha256(doc.get("content","").encode()).hexdigest(),"source_ids":[s.get("sourceId") for s in doc.get("sources",[]) if str(s.get("sourceId","")).startswith("boundforge-")]} for doc in documents]
        self.log("memory_read",{"role":role,"required_source":required,"cross_role_source_present":present,"documents":safe})
        return documents,present

def prepare_output(out):
    """Keep a fresh campaign separate from evidence committed by earlier runs."""
    out.mkdir(parents=True,exist_ok=True)
    previous=[p for p in out.iterdir() if p.is_file() and p.name!=".gitkeep"]
    if previous:
        archive=out/"previous-source"/os.environ.get("GITHUB_RUN_ID",str(time.time_ns()))
        archive.mkdir(parents=True,exist_ok=True)
        for p in previous:p.rename(archive/p.name)
