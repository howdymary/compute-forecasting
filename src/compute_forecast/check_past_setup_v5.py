"""Bounded identifier regression check; does not ingest or run model decisions."""
import hashlib,json,os,urllib.request,urllib.error,uuid
from datetime import datetime,timezone
from pathlib import Path
def main():
    token=os.environ["PAST_API_KEY"];identifier=uuid.uuid4().hex
    cases=[
        ("legacy_audience_short_actors","cf-value-v5-"+identifier,["cf-v5-cur-"+identifier[:16]+"-"+r for r in ("researcher","scientist","skeptic")]),
        ("short_audience_legacy_actors","cf-v5-check-"+identifier[:16],["cf-value-v5-current-"+identifier+"-"+r for r in ("researcher","scientist","skeptic")]),
        ("short_control","cf-v5-ok-"+identifier[:16],["cf-v5-cur-"+identifier[:16]+"-"+r for r in ("researcher","scientist","skeptic")])]
    report={"source_sha":os.environ.get("GITHUB_SHA"),"checked_at":datetime.now(timezone.utc).isoformat(),"records_ingested":0,"model_calls":0,"cases":[]}
    for name,audience,actors in cases:
        body=json.dumps({"kind":"fixed","name":"Compute Forecast identifier regression check","identities":actors}).encode()
        request=urllib.request.Request("https://api.past.dev/api/v1/audiences/"+audience,data=body,headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},method="PUT")
        try:
            with urllib.request.urlopen(request,timeout=60) as response:status=response.status;raw=response.read()
        except urllib.error.HTTPError as error:status=error.code;raw=error.read()
        row={"case":name,"audience_length":len(audience),"actor_lengths":list(map(len,actors)),"status_code":status,"response_sha256":hashlib.sha256(raw).hexdigest()}
        if status>=400:row["error_detail"]=raw.decode(errors="replace")[:1500].replace(token,"[redacted]")
        report["cases"].append(row)
    assert report["cases"][-1]["status_code"] in (200,201),"Working identifier regression failed"
    out=Path("artifacts/past-setup-v5");out.mkdir(parents=True,exist_ok=True)
    (out/"setup-diagnostic.json").write_text(json.dumps(report,indent=2)+"\n")
    print("PAST_SETUP_DIAGNOSTIC:"+json.dumps(report),flush=True)
if __name__=="__main__":main()
