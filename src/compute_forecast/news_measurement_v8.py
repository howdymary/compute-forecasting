"""New evidence-measurement namespace. Never mutates signals-v6 inputs."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib,json,os,re,urllib.request,xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from .price_dynamics_v8 import digest
def stamp():return datetime.now(timezone.utc).isoformat()
def event_key(item):
    # One source's canonical URL is a deterministic duplicate key. Cross-source
    # similar stories remain unresolved, rather than silently over-merged.
    return item["url"].split("#")[0].rstrip("/")
def measurement(results,request,received_at):
    cap=request["numResults"];seen=set();out=[]
    for row in results:
        key=event_key(row)
        if key in seen:continue
        seen.add(key)
        out.append({"event_id":digest({"source":key}),"source_url":key,"title":row.get("title"),"publication_timestamp":row.get("publishedDate"),"first_observed_at":received_at,"retrieved_at":received_at,"content_sha256":digest(row),"extraction_version":"v8-source-metadata-1","status":"unverified_event_metadata","event_type":"unclassified","announced_vs_operational":"unresolved","sku":None,"region":None,"contract":None,"quantity":None,"effective_date":None,"evidence_span":None})
    return {"query":request["query"],"requested_cap":cap,"returned_items":len(results),"deduplicated_events":len(out),"cap_reached":len(results)>=cap,"possibly_truncated":len(results)>=cap,"pagination_supported_by_this_request":False,"collection_coverage":"Search-discovery sample; market-wide recall unknown","zero_means":"No items returned by this query, not no market events","events":out}
def capture(private,previous=None):
    private.mkdir(parents=True,exist_ok=True);receipts=[];errors=[];at=stamp()
    request={"query":"GPU rental provider price changes, NVIDIA hardware launches, and operational cloud GPU capacity announcements. Prefer dated primary sources with effective dates.","type":"auto","numResults":24,"includeDomains":["nvidianews.nvidia.com","aws.amazon.com","cloud.google.com","lambda.ai","coreweave.com"],"contents":{"highlights":True}}
    report={"schema_version":8,"study_id":"evidence-measurement-v8","captured_at":at,"signals_v6_unchanged":True,"bls_handling":"Original signals-v6 vintages and release-age fields preserved; no backfilled revisions","requests":[],"collections":[],"errors":errors}
    def fetch(url,body=None):
        headers={"User-Agent":"ComputeForecastResearch/1.0"}
        if body:headers.update({"Content-Type":"application/json","x-api-key":os.environ["EXA_API_KEY"]})
        req=urllib.request.Request(url,data=json.dumps(body).encode() if body else None,headers=headers)
        with urllib.request.urlopen(req,timeout=40) as r:
            raw=r.read(2_000_001)
            if len(raw)>2_000_000:raise ValueError("Source byte limit")
            receipt={"url":url,"retrieved_at":stamp(),"status":r.status,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"etag":r.headers.get("ETag")}
        p=private/(receipt["sha256"]+".raw")
        if not p.exists():p.write_bytes(raw)
        receipts.append(receipt);return raw,receipt
    try:
        raw,r=fetch("https://api.exa.ai/search",request);v=json.loads(raw)
        sample=measurement(v.get("results",[]),request,r["retrieved_at"])
        previous_events={e["event_id"]:e for e in (previous or {}).get("discovery",{}).get("events",[])}
        for e in sample["events"]:
            if e["event_id"] in previous_events:e["first_observed_at"]=previous_events[e["event_id"]]["first_observed_at"]
        report["discovery"]=sample;report["provider_cost"]=v.get("costDollars");report["request_id"]=v.get("requestId")
    except Exception as e:errors.append({"collection":"Exa discovery","error":type(e).__name__,"detail":str(e)[:250]})
    # Defined, bounded primary-source collection. A finite RSS document does not
    # establish exhaustive historical coverage. Failed or incomplete feeds stay explicit.
    url="https://nvidianews.nvidia.com/releases.xml"
    try:
        raw,r=fetch(url);root=ET.fromstring(raw);items=root.findall(".//item");events=[]
        for item in items[:100]:
            link=item.findtext("link");published=item.findtext("pubDate")
            if not link:continue
            try:published=parsedate_to_datetime(published).isoformat()
            except (TypeError,ValueError):pass
            events.append({"url":link,"title":item.findtext("title"),"publishedDate":published})
        measured=measurement(events,{"numResults":100,"query":"NVIDIA Newsroom RSS document"},r["retrieved_at"])
        measured.update(source_url=url,document_sha256=r["sha256"],pagination="No pagination declared by RSS; earlier events not covered",collection_coverage="Items in one retrieved RSS document only",date_min=min((e["publishedDate"] for e in events if e["publishedDate"]),default=None),date_max=max((e["publishedDate"] for e in events if e["publishedDate"]),default=None))
        report["collections"].append(measured)
    except Exception as e:errors.append({"collection":url,"error":type(e).__name__,"detail":str(e)[:250]})
    report["requests"]=receipts
    report["signal_value_experiment"]="Not tested: evidence capture is separate from the six-arm price-only study"
    return report
