"""Namespaced real past.dev records. Local witnesses/logs remain authoritative."""
import datetime,hashlib,json,os,time,urllib.request,uuid
BASE="https://api.past.dev/api/v1"
def request(method,path,payload=None):
    raw=None if payload is None else json.dumps(payload).encode()
    r=urllib.request.Request(BASE+path,method=method,data=raw,
      headers={"Authorization":"Bearer "+os.environ["PAST_API_KEY"],"Content-Type":"application/json"})
    with urllib.request.urlopen(r,timeout=60) as response:return json.load(response)
class Memory:
    def __init__(self,run_id,ledger):
        self.run_id=run_id;self.ledger=ledger;self.audience="codegarden-"+run_id[:24]
        self.actors={r:"codegarden-"+run_id+"-"+r for r in ["researcher","strategist","analyst"]}
        self.events=[]
    def configure(self):
        return request("PUT","/audiences/"+self.audience,
          {"kind":"fixed","name":"CodeGarden "+self.run_id,"identities":list(self.actors.values())})
    def write(self,role,kind,content,experiment_id,parents=(),upper_bound_credits=100):
        reservation=self.ledger.reserve("past.dev","codegarden",upper_bound_credits)
        identifier="codegarden-"+self.run_id+"-"+uuid.uuid4().hex
        record={"author":self.actors[role],"kind":kind,"experiment_id":experiment_id,
          "parent_source_ids":list(parents),"content":content,"project":"codegarden"}
        payload={"id":identifier,"identity":self.actors[role],"audience":self.audience,
          "timestamp":datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "label":"CodeGarden "+kind,"content":json.dumps(record,sort_keys=True)}
        result=request("POST","/ingest",payload)
        # The provider does not necessarily return final charged credits here; keep reserved.
        self.ledger.settle(reservation,None)
        for _ in range(60):
            status=request("GET","/ingest/"+result["ingestionId"])
            if status["status"]=="completed":
                self.events.append({"event":"write","role":role,"source_id":identifier,"experiment_id":experiment_id})
                return identifier
            if status["status"]=="failed":raise RuntimeError("Past ingestion failed")
            time.sleep(2)
        raise TimeoutError("Past ingestion did not complete")
    def read(self,role,query,required_source):
        result=request("POST","/recall",{"identity":self.actors[role],"query":query,"level":"low"})
        sources={s["sourceId"] for r in result.get("results",[]) for s in r.get("sources",[])}
        if required_source not in sources:raise RuntimeError("Required cross-agent source not recalled")
        self.events.append({"event":"read","role":role,"used_source_ids":sorted(sources),"required_source":required_source})
        return result
