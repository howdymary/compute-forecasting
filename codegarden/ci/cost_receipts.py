"""Read-only billing schema/attribution. No account settings or paid operations."""
import csv,datetime as dt,io,json,pathlib,subprocess,sys,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def run(name,*args):
    p=subprocess.run([str(pathlib.Path(sys.executable).parent/name),*args],text=True,capture_output=True,timeout=90)
    return p
out={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),"read_only":True,"actual_attribution_complete":False}
try:
    p=run("modal","billing","report","--for","today","--tag-names","project","--json")
    if p.returncode:
        out["modal"]={"available":False,"reason":"Read-only detailed billing report unavailable on current plan; reservations retained."}
    else:
        d=json.loads(p.stdout);out["modal"]={"available":True,"schema":list(d) if isinstance(d,dict) else "list",
          "response_sha256":hashlib.sha256(p.stdout.encode()).hexdigest()}
        rows=d if isinstance(d,list) else d.get("rows",d.get("entries",d.get("data",[])))
        own=[r for r in rows if isinstance(r,dict) and isinstance(r.get("tags"),dict) and r["tags"].get("project")=="codegarden"] if isinstance(rows,list) else []
        out["modal"]["attributed_rows"]=own
        out["modal"]["note"]="Only explicitly project-tagged rows are published. Empty rows do not mean zero cost; billing may lag."
except Exception as e:out["modal"]={"available":False,"error_type":type(e).__name__}
try:
    end=(dt.datetime.now(dt.timezone.utc).replace(minute=0,second=0,microsecond=0)+dt.timedelta(hours=1)).isoformat().replace("+00:00","Z")
    p=run("tinker","billing","usage","2026-11-15T00:00:00Z",end,"--csv","-")
    if p.returncode:raise RuntimeError("Tinker usage query unavailable")
    rows=list(csv.DictReader(io.StringIO(p.stdout)))
    out["tinker"]={"available":True,"columns":list(rows[0]) if rows else [],
      "note":"Token accounting is estimated gross usage, not final invoiced or prepaid-net charges."}
    own=[r for r in rows if any("codegarden" in str(v).lower() for k,v in r.items() if k in {"display_name","session_name","project_name","project"})]
    out["tinker"]["explicitly_attributed_rows"]=own
    out["tinker"]["attribution_gap"]=not bool(own)
except Exception as e:out["tinker"]={"available":False,"error_type":type(e).__name__}
(ROOT/"artifacts/live/billing_receipts.json").write_text(json.dumps(out,indent=2))
print("CODEGARDEN_BILLING "+json.dumps(out))
