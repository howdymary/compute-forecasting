"""Exa is called here: search_methods(). Disabled without a shared reservation."""
import datetime,hashlib,json,os,urllib.request
def search_methods(query,ledger,upper_bound_usd=1.0):
    reservation=ledger.reserve("exa","codegarden",upper_bound_usd)
    body={"query":query,"type":"auto","numResults":4,"contents":{"highlights":True}}
    request=urllib.request.Request("https://api.exa.ai/search",data=json.dumps(body).encode(),
      headers={"x-api-key":os.environ["EXA_API_KEY"],"Content-Type":"application/json"})
    raw=urllib.request.urlopen(request,timeout=60).read();result=json.loads(raw)
    cost=result.get("costDollars")
    actual=cost.get("total") if isinstance(cost,dict) else cost if isinstance(cost,(int,float)) else None
    ledger.settle(reservation,actual)
    return {"query":query,"request":body,"request_id":result.get("requestId"),
      "retrieved_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "response_sha256":hashlib.sha256(raw).hexdigest(),"cost_dollars":cost,
      "sources":[{"url":r["url"],"title":r.get("title"),"published":r.get("publishedDate"),
        "highlights_sha256":hashlib.sha256(json.dumps(r.get("highlights")).encode()).hexdigest()} for r in result.get("results",[])],
      "extracted_method":None,"influenced_experiment_ids":[]}
