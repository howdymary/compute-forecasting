"""Qualify a new original BLS release only for the registered future panel."""
import hashlib,json,os,pathlib,urllib.request
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from capture_bls_evidence_v14 import extract
from compute_forecast.direct_forecast_v12 import digest
cfg=json.loads(pathlib.Path("configs/evidence-future-bls-v15.json").read_text());at=datetime.now(timezone.utc).isoformat()
body=json.dumps({"urls":[cfg["source_url"]],"text":{"maxCharacters":cfg["max_characters"]}}).encode()
request=urllib.request.Request("https://api.exa.ai/contents",data=body,headers={"Content-Type":"application/json","x-api-key":os.environ["EXA_API_KEY"]})
with urllib.request.urlopen(request,timeout=180) as response:reply=json.load(response)
result=next(r for r in reply.get("results",[]) if r.get("text"));text=result["text"]
values=extract(text,cfg["period"],cfg["independent_check"]);assert values["indices"]==cfg["independent_check"]["indices"]
release=datetime.fromisoformat(cfg["release_date"]+"T"+cfg["release_time"]).replace(tzinfo=ZoneInfo(cfg["release_timezone"])).astimezone(timezone.utc).isoformat()
assert "October 2026" in text[:3000] and "Nov. 13, 2026" in text[:12000]
record={"status":"qualified_pending_spot_check","independent_pdf_check_completed":True,"source_url":cfg["source_url"],"publisher":"US Bureau of Labor Statistics","series_id":cfg["series_id"],"reference_period":cfg["period"],"retrieved_at":at,"first_observed_at":at,"available_at":release,"permission_url":cfg["permission_url"],"content_sha256":hashlib.sha256(text.encode()).hexdigest(),"content_hash_scope":"Full Exa-extracted PDF text, not original binary PDF","characters":len(text),"values":values,"independent_check":cfg["independent_check"],"exa_request_id":reply.get("requestId"),"cost_dollars":reply.get("costDollars")}
out={"study_id":cfg["study_id"],"capture_version":15,"source_sha":os.environ["GITHUB_SHA"],"config_sha256":digest(cfg),"classification":cfg["classification"],"ready":True,"records":[record],"protected_GPU_outcomes_loaded":False}
root=pathlib.Path("artifacts/evidence-v14-audit");root.mkdir(parents=True,exist_ok=True);(root/"future-bls-vintage.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"period":cfg["period"],"available_at":release,"retrieved_at":at,"status":"qualified","source_content_sha256":record["content_sha256"],"historical_training_changed":False}),flush=True)
