"""Existing-credit-only provider access. One serialized CodeGarden orchestrator.

Static account allocation deducts BoundForge's FULL operational caps, a separate
forecasting/pending guard and final-verification reserves. This does not pretend
that another project's private SQLite participates in ours.
"""
import csv,datetime as dt,hashlib,io,json,os,pathlib,sqlite3,subprocess,sys,time,urllib.request,uuid
ROOT=pathlib.Path(__file__).resolve().parent
class Disabled(RuntimeError):pass
def http(url,key,payload=None,header="Authorization",method=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,method=method,
      headers={header:("Bearer " if header=="Authorization" else "")+key,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=75) as r:return json.load(r)
def cli(name,*args):
    p=subprocess.run([str(pathlib.Path(sys.executable).parent/name),*args],capture_output=True,text=True,timeout=90)
    if p.returncode:raise Disabled(name+" read-only account query unavailable")
    return p.stdout
class Ledger:
    def __init__(self,out):
        self.spec=json.loads((ROOT/"budget/shared-allocation.json").read_text())
        expiry=dt.datetime.fromisoformat(self.spec["expires_at"].replace("Z","+00:00"))
        if dt.datetime.now(dt.timezone.utc)>expiry:raise Disabled("Allocation snapshot expired; obtain a fresh shared allocation")
        self.db=sqlite3.connect(str(out/"live-budget.sqlite"),isolation_level=None)
        self.db.execute("CREATE TABLE IF NOT EXISTS reservations(id TEXT PRIMARY KEY,provider TEXT,reserved REAL,actual REAL,status TEXT)")
    def reserve(self,provider,project,amount):
        provider="past" if provider=="past.dev" else provider
        p=self.spec["providers"][provider];remaining=float(p["balance_at_snapshot"])
        if provider=="past":
            usage=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])
            live=usage.get("balance",{}).get("left")
            if not isinstance(live,(int,float)):raise Disabled("Live past prepaid balance unknown")
            remaining=min(remaining,live)
        elif provider=="modal":
            data=json.loads(cli("modal","billing","summary","--json"))
            # Deduct all account usage since the authenticated snapshot, not just ours.
            remaining-=max(0,float(data["metered_cost"])-1.64005948)
        elif provider=="tinker":
            end=(dt.datetime.now(dt.timezone.utc).replace(minute=0,second=0,microsecond=0)+dt.timedelta(hours=1)).isoformat().replace("+00:00","Z")
            rows=list(csv.DictReader(io.StringIO(cli("tinker","billing","usage","2026-11-14T00:00:00Z",end,"--csv","-"))))
            if rows and "estimated_cost_usd" not in rows[0]:raise Disabled("Tinker gross cost schema unavailable")
            remaining-=sum(float(r.get("estimated_cost_usd") or 0) for r in rows)
        available=remaining-p["boundforge_reserved"]-p["forecasting_pending_guard"]-p["verification_reserve"]
        self.db.execute("BEGIN IMMEDIATE")
        try:
            spent=self.db.execute("SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM reservations WHERE provider=?",(provider,)).fetchone()[0]
            if amount<=0 or spent+amount>p["codegarden_cap"] or spent+amount>available:
                raise Disabled(provider+" allocation exhausted after other projects and reserves")
            ident=uuid.uuid4().hex
            self.db.execute("INSERT INTO reservations VALUES(?,?,?,NULL,'pending')",(ident,provider,amount))
            self.db.execute("COMMIT");return ident
        except Exception:self.db.execute("ROLLBACK");raise
    def settle(self,identifier,actual):
        if actual is None:return
        row=self.db.execute("SELECT reserved FROM reservations WHERE id=?",(identifier,)).fetchone()
        if not row or actual<0 or actual>row[0]:raise Disabled("Accounting outside reservation; freeze campaign")
        self.db.execute("UPDATE reservations SET actual=?,status='settled' WHERE id=?",(actual,identifier))
    def summary(self):
        return {p:{"cap":d["codegarden_cap"],"other_project_reserves":d["boundforge_reserved"]+d["forecasting_pending_guard"],
          "verification_reserve":d["verification_reserve"],
          "reserved":self.db.execute("SELECT COALESCE(SUM(reserved),0) FROM reservations WHERE provider=? AND actual IS NULL",(p,)).fetchone()[0],
          "provider_reported_or_estimated":self.db.execute("SELECT COALESCE(SUM(actual),0) FROM reservations WHERE provider=?",(p,)).fetchone()[0]}
          for p,d in self.spec["providers"].items()}
class Providers:
    def __init__(self,out,log):
        self.out=out;self.log=log;self.ledger=Ledger(out)
        self.run_id="codegarden-"+os.environ.get("GITHUB_RUN_ID",uuid.uuid4().hex)
        self.actors={r:self.run_id+"-"+r for r in ["analyst","researcher","strategist"]}
        self.audience=self.run_id
    def setup_memory(self):
        return http("https://api.past.dev/api/v1/audiences/"+self.audience,os.environ["PAST_API_KEY"],
          {"kind":"fixed","name":self.run_id,"identities":list(self.actors.values())},method="PUT")
    def exa(self,query,experiment):
        token=self.ledger.reserve("exa","codegarden",.10)
        result=http("https://api.exa.ai/search",os.environ["EXA_API_KEY"],
          {"query":query,"type":"auto","numResults":4,"contents":{"highlights":True}},"x-api-key")
        cost=result.get("costDollars",{}).get("total")
        self.ledger.settle(token,cost)
        safe=[]
        for r in result.get("results",[]):
            snippets=r.get("highlights",[]) or []
            safe.append({"title":r.get("title"),"url":r["url"],"published":r.get("publishedDate"),
              "excerpt":" ".join(" ".join(snippets).split()[:10]),
              "content_sha256":hashlib.sha256(json.dumps(snippets).encode()).hexdigest()})
        event={"query":query,"request_id":result.get("requestId"),"cost_dollars":result.get("costDollars"),
          "sources":safe,"influenced_experiment":experiment}
        self.log("exa_search",event);return event
    def write(self,role,kind,content,experiment,parents=()):
        sid=self.run_id+"-"+role+"-"+kind+"-"+uuid.uuid4().hex[:8]
        record={"project":"codegarden","author":self.actors[role],"kind":kind,"experiment_id":experiment,
          "parent_source_ids":list(parents),"content":content}
        item={"id":sid,"identity":self.actors[role],"audience":self.audience,
          "timestamp":dt.datetime.now(dt.timezone.utc).isoformat(),"label":"CodeGarden "+kind,"content":json.dumps(record)}
        estimate=http("https://api.past.dev/api/v1/ingest/estimate",os.environ["PAST_API_KEY"],{"items":[item]})
        if not estimate.get("fits") or not isinstance(estimate.get("credits"),(int,float)):raise Disabled("Memory estimate unavailable")
        token=self.ledger.reserve("past","codegarden",max(1,estimate["credits"]))
        result=http("https://api.past.dev/api/v1/ingest",os.environ["PAST_API_KEY"],{**item,"idempotencyKey":sid})
        self.ledger.settle(token,estimate["credits"])
        for _ in range(60):
            status=http("https://api.past.dev/api/v1/ingest/"+result["ingestionId"],os.environ["PAST_API_KEY"])
            if status["status"]=="completed":
                self.log("memory_write",{"role":role,"source_id":sid,"experiment":experiment,"parent_sources":list(parents),"estimated_credits":estimate["credits"]})
                return sid
            if status["status"]=="failed":raise Disabled("Memory ingestion failed")
            time.sleep(2)
        raise TimeoutError("Memory ingestion not ready")
    def read(self,role,query,required_source):
        for _ in range(4):
            token=self.ledger.reserve("past","codegarden",1)
            result=http("https://api.past.dev/api/v1/recall",os.environ["PAST_API_KEY"],
              {"identity":self.actors[role],"query":query,"maxTokens":2000})
            self.ledger.settle(token,1) # conservative estimate, even when plan includes recall
            ids={s["sourceId"] for r in result.get("results",[]) for s in r.get("sources",[])}
            if required_source in ids:
                self.log("memory_read",{"role":role,"required_source":required_source,
                  "returned_source_ids":sorted(x for x in ids if x.startswith(self.run_id)),"used_in_next_decision":True})
                return result
            time.sleep(2)
        raise Disabled("Required other-role source not present in real recall")
