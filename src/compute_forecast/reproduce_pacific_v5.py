"""One-command credential-free reproduction from an unchanged licensed Pacific pack."""
import argparse,csv,hashlib,io,json,os,subprocess
from pathlib import Path
from .starter_probe import verify_manifest
from .pricing_contract import FORECAST_SHA
def reproduce(pack,out):
    root=Path(pack).resolve();out=Path(out).resolve()
    if root==out or root in out.parents:raise ValueError("Outputs must be outside the immutable pack")
    if verify_manifest(root)!=672:raise ValueError("Pack identity")
    before=hashlib.sha256((root/"MANIFEST.sha256").read_bytes()).hexdigest();out.mkdir(parents=True,exist_ok=True)
    def run(args):
        p=subprocess.run(["python","-I","-B",str(root/"starter"/args[0]),*map(str,args[1:])],capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"))
        if p.returncode:raise RuntimeError(p.stderr[-2000:])
    history=out/"history.csv";catalog=out/"catalog.csv";all_fc=out/"all-horizons.csv"
    run(["build_series.py","--pack",root,"--cutoff","2026-11-06","--out",history,"--catalog",catalog,"--report",out/"history-report.json"])
    run(["baselines.py","--history",history,"--origin","2026-11-06","--method","last_value_empirical","--catalog",catalog,"--tier","headline","--frozen","--out",all_fc])
    with catalog.open() as f:ids={r["series_id"] for r in csv.DictReader(f) if r["tier"]=="headline"}
    with all_fc.open() as f:rows=[r for r in csv.DictReader(f) if r["series_id"] in ids and int(r["horizon_days"]) in (1,3,7)]
    rows.sort(key=lambda r:(r["series_id"],int(r["horizon_days"])))
    text=io.StringIO();w=csv.DictWriter(text,fieldnames=["series_id","origin_date","horizon_days","q10","q50","q90"],extrasaction="ignore");w.writeheader();w.writerows(rows);raw=text.getvalue().encode()
    if len(rows)!=111 or hashlib.sha256(raw).hexdigest()!=FORECAST_SHA:raise ValueError("Official CSV does not reproduce exactly")
    if before!=hashlib.sha256((root/"MANIFEST.sha256").read_bytes()).hexdigest() or verify_manifest(root)!=672:raise ValueError("Pack modified")
    (out/"forecasts.csv").write_bytes(raw)
    result={"status":"byte_identical","forecast_rows":len(rows),"headline_series":len(ids),"forecast_csv_sha256":FORECAST_SHA,"protected_outcomes_loaded":False,"pack_unchanged":True}
    (out/"reproduction.json").write_text(json.dumps(result,indent=2));return result
def main():
    p=argparse.ArgumentParser();p.add_argument("--pack",required=True);p.add_argument("--out",required=True);a=p.parse_args();print(json.dumps(reproduce(a.pack,a.out)))
if __name__=="__main__":main()
