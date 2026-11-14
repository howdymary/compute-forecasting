"""Hosted-runner entrypoints with verified official adapters and explicit data boundaries."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date,datetime,timezone
from importlib import metadata
from pathlib import Path
from uuid import uuid4
from .candidates import candidate_grid
from .contracts import Forecast,Observation,OfficialContract
from .cutoffs import visible_observations
from .scoring import pinball_loss,validate_forecast_groups

REQUIRED_SECRETS=("MODAL_TOKEN_ID","MODAL_TOKEN_SECRET","TINKER_API_KEY","EXA_API_KEY","PAST_API_KEY")
EXPECTED_ARCHIVE_SHA="f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c"

def write_json(path: str|Path,value: object)->None:
    destination=Path(path);destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(value,indent=2,default=str,allow_nan=False)+"\n")

def preflight()->dict:
    packages={}
    for name in ("compute-forecast","pydantic","numpy","pandas","scikit-learn","modal","tinker"):
        try:packages[name]=metadata.version(name)
        except metadata.PackageNotFoundError:packages[name]=None
    return {"schema_version":"1","generated_at":datetime.now(timezone.utc).isoformat(),"code_sha":os.environ.get("GITHUB_SHA"),"branch":os.environ.get("GITHUB_REF_NAME"),"scope":"presence_and_package_check_only_not_live_service_proof","credential_presence_only":{name:bool(os.environ.get(name)) for name in REQUIRED_SECRETS},"account_access_verified":False,"official_contract_verified":False,"official_results_available":False,"candidate_count":len(candidate_grid()),"packages":packages}

def synthetic_smoke()->dict:
    cutoff=datetime(2025,1,10,12,tzinfo=timezone.utc)
    known=Observation(target_key="SYNTHETIC_TARGET",period=date(2025,1,10),available_at=cutoff,value=2,unit="synthetic_units")
    future=known.model_copy(update={"period":date(2025,1,11),"available_at":datetime(2025,1,11,12,tzinfo=timezone.utc),"value":999})
    assert visible_observations([known,future],origin_period=date(2025,1,10),cutoff=cutoff)==[known]
    run_id=uuid4()
    forecasts=[Forecast(target_key="SYNTHETIC_TARGET",origin_ts=cutoff,horizon_days=h,quantile=q,value=value,unit_from_registry="synthetic_units",config_id="synthetic_contract_smoke",run_id=run_id) for h in (1,3,7) for q,value in ((.1,1.5),(.5,2.0),(.9,2.5))]
    validate_forecast_groups(forecasts)
    return {"schema_version":"1","is_synthetic":True,"purpose":"contract_and_cutoff_validation_only","official_schema_verified":False,"official_forecast_export":None,"market_results":None,"candidate_count":len(candidate_grid()),"cutoff_check_passed":True,"diagnostic_pinball":pinball_loss(2.25,2,.5),"internal_forecasts":[row.model_dump(mode="json") for row in forecasts]}

def reproduce(args)->int:
    spec=json.loads(Path(args.run_spec).read_text())
    OfficialContract.model_validate(spec["official_contract"]).require_ready()
    if spec["data"]["sha256"]!=EXPECTED_ARCHIVE_SHA or spec["data"]["redistribution_allowed"] is not False:
        raise RuntimeError("Unrecognized archive or unsupported raw-data redistribution")
    if os.environ.get("GITHUB_ACTIONS")!="true" or os.environ.get("GITHUB_REF_NAME")!="compute-observatory":
        raise RuntimeError("Use the hosted Reproduce workflow on compute-observatory; this project does not execute on the workstation")
    required=["MODAL_TOKEN_ID","MODAL_TOKEN_SECRET"]+(["TINKER_API_KEY"] if args.train_policy else [])
    missing=[name for name in required if not os.environ.get(name)]
    if missing:raise RuntimeError("Missing remote credentials: "+", ".join(missing))
    if args.train_policy and not args.full_grid:raise RuntimeError("Policy training requires the complete chronological grid")
    executable=shutil.which("modal")
    if not executable:raise RuntimeError("Install the Modal client on the hosted runner")
    # All outputs below are hosted Actions artifacts; Modal does numerical work.
    prerequisite=str(Path(args.output).with_name("starter-prerequisite.json"))
    subprocess.run([executable,"run","-m","compute_forecast.starter_probe","--cutoff","2026-07-24","--output",prerequisite],check=True)
    command=[executable,"run","-m","compute_forecast.representation_study","--output",args.output]
    if args.full_grid:command.append("--no-smoke")
    subprocess.run(command,check=True)
    if args.train_policy:
        subprocess.run([sys.executable,"-m","compute_forecast.search_policy","--grid",args.output,"--expected-source-sha",os.environ["GITHUB_SHA"]],check=True)
    print("Verified official-scored reproduction completed. Raw pack retained privately; final period unopened.")
    return 0

def main(argv: list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    check=commands.add_parser("preflight");check.add_argument("--output",default="artifacts/preflight.json")
    smoke=commands.add_parser("synthetic-smoke");smoke.add_argument("--output",default="artifacts/synthetic/smoke.json")
    run=commands.add_parser("reproduce");run.add_argument("--run-spec",default="configs/pacific.json");run.add_argument("--output",default="artifacts/representation-grid.json");run.add_argument("--full-grid",action="store_true");run.add_argument("--train-policy",action="store_true")
    args=parser.parse_args(argv)
    if args.command=="preflight":
        value=preflight();write_json(args.output,value);print(json.dumps(value,indent=2));return 0
    if args.command=="synthetic-smoke":
        value=synthetic_smoke();write_json(args.output,value);print("Synthetic contract validation completed; no official benchmark was run.");return 0
    try:return reproduce(args)
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.CalledProcessError) as exc:
        print(f"REPRODUCTION BLOCKED: {exc}");return 2
