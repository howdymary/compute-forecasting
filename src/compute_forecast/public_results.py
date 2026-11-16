"""Version and verify allowlisted public research artifacts on GitHub."""
from __future__ import annotations
import argparse,base64,csv,hashlib,io,json,math,os,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import unquote,urlsplit
from .history_contract_v3 import validate_assets
from .pricing_contract import validate as validate_pricing
from .notebook_diagnostics import build as diagnostics
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
BRANCH="compute-observatory"
FORECAST_SHA="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
SOURCE_UI_SHA="80bf0d6af21bed45cd236d9d756d9f1b1a130983"
ENDPOINTS={
"results/frozen-v1/forecasts.csv":"/files/forecasts.csv",
"results/frozen-v1/release.json":"/api/release",
"results/frozen-v1/outlook.md":"/files/outlook.md",
"results/frozen-v1/outlook-scenarios.json":"/files/outlook-scenarios.json",
"results/expanded-v2/summary.json":"/api/experimental",
"results/explorer-v3/chronos-control.json":"/api/chronos-control",
"results/explorer-v3/history-and-traces.json":"/api/research-assets",
"results/explorer-v3/diagnostics.json":"/api/notebook",
"results/explorer-v3/series-metadata.json":"/api/pricing",
}
SCREENSHOTS={
"docs/images/pricing-scenarios.png":{"source_run":43691563067,"artifact":"notebook-ui-"+SOURCE_UI_SHA+"-43691563067","source_filename":"desktop-scenarios.png"},
"docs/images/historical-context.png":{"source_run":43691563100,"artifact":"research-explorer-ui-"+SOURCE_UI_SHA+"-43691563100","source_filename":"1512-history-all.png"},
"docs/images/research-atlas.png":{"source_run":43691563100,"artifact":"research-explorer-ui-"+SOURCE_UI_SHA+"-43691563100","source_filename":"1512-research.png"},
}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,indent=2,allow_nan=False)+"\n").encode()
# Exact verified public article URL: its SK Telecom slug is not an API key.
# All other token-pattern strings, including other URLs, remain rejected.
VERIFIED_PUBLIC_URL_EXCEPTIONS={"https://nvidianews.nvidia.com/news/nvidia-rebellions-and-sk-telecom-announce-collaboration-to-advance-sovereign-ai-infrastructure-with-nvidia-nvlink-fusion"}
def private_guard(value):
    if isinstance(value,dict):
        forbidden={"state_path","sampler_path","weights_access_token","api_key","access_token","refresh_token","authorization","raw_response","permitted_private_method_context"}
        if {str(k).lower() for k in value}&forbidden:raise ValueError("Excluded private field in public artifact")
        for v in value.values():private_guard(v)
    elif isinstance(value,list):
        for v in value:private_guard(v)
    elif isinstance(value,str) and value not in VERIFIED_PUBLIC_URL_EXCEPTIONS and (value.startswith("tinker://") or re.search(r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{24,}|gh[pousr]_[A-Za-z0-9]{24,})",value)):raise ValueError("Excluded private credential or checkpoint URI")
def check_bundle(raw):
    if set(raw)!=set(ENDPOINTS):raise ValueError("Unexpected public artifact set")
    for name,data in raw.items():
        if name.endswith(".json"):private_guard(json.loads(data))
    if sha(raw["results/frozen-v1/forecasts.csv"])!=FORECAST_SHA:raise ValueError("Official CSV bytes changed")
    rows=list(csv.DictReader(io.StringIO(raw["results/frozen-v1/forecasts.csv"].decode())))
    if len(rows)!=111 or len({r["series_id"] for r in rows})!=37:raise ValueError("Official forecast scope")
    for row in rows:
        q=[float(row[k]) for k in ("q10","q50","q90")]
        if q!=sorted(q) or any(not math.isfinite(v) or v<=0 for v in q):raise ValueError("Official quantiles")
    p=validate_pricing(json.loads(raw["results/explorer-v3/series-metadata.json"]))
    actual={(r["series_id"],int(r["horizon_days"])):r for r in rows}
    for series in p["series"]:
        for point in series["forecasts"]:
            row=actual[(series["id"],point["horizon_days"])]
            if any(point[k]!=float(row[k]) for k in ("q10","q50","q90")):raise ValueError("Pricing snapshot and official export disagree")
    a=validate_assets(json.loads(raw["results/explorer-v3/history-and-traces.json"]))
    if sum(len(s["points"]) for s in a["history_context"]["series"])!=468:raise ValueError("Historical publication scope")
    e=json.loads(raw["results/expanded-v2/summary.json"]);reports=e["policy_reports"]
    if e["campaign_status"]!="completed" or len(reports)!=9 or sum(r["mode"]=="sft" for r in reports)!=6:raise ValueError("Incomplete campaign")
    if sum(r["actual_optimizer_updates"] for r in reports if r["mode"]=="sft")!=600 or sum(r["actual_optimizer_updates"] for r in reports if r["mode"]=="rl")!=99:raise ValueError("Optimizer accounting")
    if any(r["selected_update"]!=0 for r in reports if r["mode"]=="rl"):raise ValueError("Frozen RL selection changed")
    n=json.loads(raw["results/explorer-v3/diagnostics.json"]);expected=diagnostics(e)
    if any(n[k]!=expected[k] for k in ("calibration","feedback","ledger","scope")):raise ValueError("Diagnostics do not match saved campaign reports")
    c=json.loads(raw["results/explorer-v3/chronos-control.json"])
    if c["scope"]["cells"]!=12 or len(c["scored_cell_keys"])!=12 or len({tuple(k) for k in c["scored_cell_keys"]})!=12:raise ValueError("Comparator cohort")
    if c["config"]["model_revision"]!="29ec3766d36d6f73f0696f85560a422f50e8498c" or not math.isclose(c["metrics"]["pinball"],.012113554233974892,abs_tol=1e-12):raise ValueError("Fixed control changed")
    if c["official_export_changed"] or c["selector_registry_changed"] or c["future_competition_truth_loaded"] or c["prospective"]["outcomes_loaded"]:raise ValueError("Frozen/future boundary")
    from .release_payload import validate
    validate(json.loads(raw["results/frozen-v1/release.json"]))
    return {"official_rows":111,"headline_series":37,"completed_policy_reports":9,"context_series":2,"context_observations":468,"selector_cells":12,"prospective":"pending"}
def github(method,path,data=None):
    token=os.environ["GH_TOKEN"];url="https://api.github.com/"+path
    body=None if data is None else json.dumps(data).encode()
    request=Request(url,data=body,method=method,headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","Content-Type":"application/json"})
    with urlopen(request,timeout=60) as response:return json.load(response)
def publish():
    if os.environ.get("GITHUB_REF")!="refs/heads/"+BRANCH:raise ValueError("Publication branch")
    import httpx
    raw={}
    with httpx.Client(http2=True,timeout=90,verify=True,follow_redirects=False) as client:
        for path,endpoint in ENDPOINTS.items():
            response=client.get(URL+endpoint);response.raise_for_status()
            if response.status_code!=200:raise ValueError("Expected exact HTTP 200")
            raw[path]=response.content
    scope=check_bundle(raw);repo=os.environ["GITHUB_REPOSITORY"]
    branch=github("GET","repos/"+repo+"/branches/"+BRANCH);parent=branch["commit"]["sha"]
    if parent!=os.environ["GITHUB_SHA"]:raise ValueError("Branch advanced; restart publication from fresh head")
    manifest={"schema_version":1,"published_at":datetime.now(timezone.utc).isoformat(),"publisher_source_sha":os.environ["GITHUB_SHA"],"source_ui_sha":SOURCE_UI_SHA,"snapshot_workflow_run_id":os.environ["GITHUB_RUN_ID"],"scope":scope,"publication":"Public derived research outputs and explicitly licensed independent context; raw competition inputs, private checkpoints, sessions and restricted excerpts excluded","files":{path:{"bytes":len(data),"sha256":sha(data),"source_url":URL+ENDPOINTS[path]} for path,data in raw.items()},"screenshots":{}}
    for path,source in SCREENSHOTS.items():
        data=Path(path).read_bytes()
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):raise ValueError("PNG expected")
        manifest["screenshots"][path]={**source,"source_ui_sha":SOURCE_UI_SHA,"bytes":len(data),"sha256":sha(data),"type":"Actual rendered application PNG"}
    raw["results/manifest.json"]=encoded(manifest)
    elements=[]
    for path,data in raw.items():
        blob=github("POST","repos/"+repo+"/git/blobs",{"content":base64.b64encode(data).decode(),"encoding":"base64"})
        elements.append({"path":path,"mode":"100644","type":"blob","sha":blob["sha"]})
    tree=github("POST","repos/"+repo+"/git/trees",{"base_tree":branch["commit"]["commit"]["tree"]["sha"],"tree":elements})
    commit=github("POST","repos/"+repo+"/git/commits",{"message":"Publish verified public research snapshots and exact forecast export","tree":tree["sha"],"parents":[parent]})
    if github("GET","repos/"+repo+"/branches/"+BRANCH)["commit"]["sha"]!=parent:raise ValueError("Branch advanced before publication")
    github("PATCH","repos/"+repo+"/git/refs/heads/"+BRANCH,{"sha":commit["sha"],"force":False})
    receipt={"status":"published","commit_sha":commit["sha"],"parent_sha":parent,"files":list(raw),"scope":scope}
    out=Path("artifacts");out.mkdir(exist_ok=True);(out/"public-snapshot-receipt.json").write_bytes(encoded(receipt));print("PUBLIC_SNAPSHOT_RECEIPT:"+json.dumps(receipt),flush=True)
def check_links(root):
    missing=[]
    for path in root.rglob("*.md"):
        if any(p in ("inputs","artifacts",".git") for p in path.parts):continue
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)",path.read_text()):
            target=target.strip().split(" ",1)[0].strip("<>")
            if not target or target.startswith(("#","http:","https:","mailto:")):continue
            target=unquote(urlsplit(target).path)
            if target and not (path.parent/target).resolve().exists():missing.append(str(path.relative_to(root))+": "+target)
    if missing:raise ValueError("Broken repository links: "+json.dumps(missing))
def verify():
    root=Path.cwd();m=json.loads(Path("results/manifest.json").read_text());raw={}
    if set(m["files"])!=set(ENDPOINTS):raise ValueError("Unexpected committed file set")
    for path,row in m["files"].items():
        data=Path(path).read_bytes()
        if sha(data)!=row["sha256"] or len(data)!=row["bytes"]:raise ValueError("Committed artifact checksum mismatch: "+path)
        raw[path]=data
    scope=check_bundle(raw);check_links(root)
    paths=[p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and not any(part in (".git","inputs","artifacts") for part in p.parts)]
    forbidden=[p for p in paths if re.search(r"(^|/)(?:prompts?(?:/|\.|$)|AGENTS\.md$|CLAUDE\.md$)",p,re.I) or p.endswith((".prompt",".pem",".key")) or Path(p).name.startswith(".env")]
    if forbidden:raise ValueError("Excluded public package files: "+json.dumps(forbidden))
    for path in paths:
        if Path(path).suffix in (".py",".md",".json",".toml",".yml",".yaml",".cff"):
            text=Path(path).read_text()
            if re.search(r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{24,}|gh[pousr]_[A-Za-z0-9]{24,})",text):raise ValueError("Potential committed credential: "+path)
    citation=Path("CITATION.cff").read_text()
    if not all(key in citation for key in ("cff-version: 1.2.0","family-names: Liu","given-names: Mary","repository-code:")):raise ValueError("Citation metadata")
    for path,row in m["screenshots"].items():
        matches=list(Path("inputs/ui").rglob(row["source_filename"]))
        if len(matches)!=1:raise ValueError("Ambiguous source screenshot")
        data=Path(path).read_bytes()
        if sha(data)!=row["sha256"] or data!=matches[0].read_bytes():raise ValueError("PNG differs from original successful UI evidence")
    report={"status":"passed","source_sha":os.environ.get("SOURCE_SHA"),"scope":scope,"artifact_files":len(raw),"relative_markdown_links":"verified","screenshot_provenance":"exact original PNG bytes","prompt_files":0,"credentials":"no matching literal secret patterns","raw_pack_published":False}
    out=Path("artifacts");out.mkdir(exist_ok=True);(out/"public-package-validation.json").write_bytes(encoded(report));print("PUBLIC_PACKAGE_VALIDATION:"+json.dumps(report),flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument("mode",choices=("publish","verify"));mode=parser.parse_args().mode
    (publish if mode=="publish" else verify)()
if __name__=="__main__":main()
