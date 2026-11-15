"""Read-only primary-document audit for the Pacific value study."""
import csv,hashlib,json,os,re
from pathlib import Path
from datetime import datetime,timezone
import modal
from .starter_probe import PACK_NAME,PACK_SHA256,verify_manifest
app=modal.App("compute-forecast-pacific-audit-v5")
volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
@app.function(image=image,cpu=1,memory=1024,timeout=300,volumes={"/data":volume})
def audit():
    root=Path("/data/pacific")/PACK_NAME
    verified=verify_manifest(root);members=[p for p in root.rglob("*") if p.is_file()]
    listed={line.split(maxsplit=1)[1].lstrip(" *") for line in (root/"MANIFEST.sha256").read_text().splitlines() if line.strip()}
    docs={}
    for name in ("DATA.md","ATTRIBUTION.md","sources_register.csv"):
        p=root/name;s=p.read_text()
        terms=[]
        for line in s.splitlines():
            if re.search(r"compilation|pending|default|licen[cs]|redistribut|CC BY|Apache|permission|all rights",line,re.I):terms.append(line[:800])
        docs[name]={"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size,"licensing_lines":terms[:65],"header":s.splitlines()[:8]}
    registry=list(csv.DictReader((root/"sources_register.csv").open()))
    schemas={}
    candidates=[root/"daily_statistics.csv",root/"aggregator_medians.csv",root/"index_prints.csv",*sorted((root/"hardware_fundamentals").glob("*.csv")),*sorted((root/"capability").glob("*.csv"))]
    for p in candidates:
        with p.open() as f:
            reader=csv.DictReader(f);rows=list(reader)
        schemas[str(p.relative_to(root))]={"columns":reader.fieldnames,"rows":len(rows)}
    starter={}
    for name in ("baselines.py","scorer.py","build_series.py"):
        p=root/"starter"/name;s=p.read_text()
        # Source code is retained privately; public audit exposes only relevant definition excerpts.
        snippets=[]
        for target in (["def ","drift","log_changes","last_value_empirical"] if name=="baselines.py" else ["missing","fill","pooled","geometric","skill"] if name=="scorer.py" else ["headline","source_id","instrument_class","licence_id"]):
            matches=[i for i,line in enumerate(s.splitlines()) if target in line][:6]
            for i in matches:snippets.append({"line":i+1,"text":"\n".join(s.splitlines()[max(0,i-2):i+8])})
        starter[name]={"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"snippets":snippets[:25]}
    result={"schema_version":5,"study_id":"pacific-value-v5","checked_at":datetime.now(timezone.utc).isoformat(),"source_sha":os.environ.get("GITHUB_SHA"),"verified_manifest_entries":verified,"actual_files":len(members),"unlisted_files":sorted(str(p.relative_to(root)) for p in members if str(p.relative_to(root)) not in listed),"docs":docs,"source_registry":registry,"schemas":schemas,"starter":starter,"protected_outcomes_loaded":False}
    return result
def main():
    with app.run():result=audit.remote()
    out=Path("artifacts/pacific-v5");out.mkdir(parents=True,exist_ok=True);(out/"pack-audit.json").write_text(json.dumps(result,indent=2))
    print("PACIFIC_V5_AUDIT:"+json.dumps(result),flush=True)
if __name__=="__main__":main()
