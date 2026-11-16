"""Freeze a source-bound paired dataset before either arm is optimized."""
import collections,hashlib,json,os,pathlib,shutil
from datetime import datetime,timezone
from compute_forecast.direct_forecast_v12 import digest
from compute_forecast.evidence_v14 import feature_at,eligibility,messages
def main():
    root=pathlib.Path("inputs/original");out=pathlib.Path("inputs/evidence-v14");out.mkdir(parents=True,exist_ok=True)
    p=json.loads(pathlib.Path("configs/direct-evidence-v14-final.json").read_text())
    original=json.loads((root/"dataset.json").read_text());old_audit=json.loads((root/"audit.json").read_text());assert digest(original)==old_audit["dataset_sha256"]
    releases=json.loads(pathlib.Path(os.environ["BLS_SOURCE_FILE"]).read_text())
    if not releases["ready"]:raise ValueError("Evidence source gate has not passed")
    if len(releases["records"])!=10:raise ValueError("Missing registered monthly release")
    groups=original["groups"]
    for phase,tasks in groups.items():
        for task in tasks:
            task["bls"]=feature_at(releases["records"],task["origin"])
            if task["bls"] is None:raise ValueError("Matched task lacks eligible BLS vintage")
            if phase=="training" and max(task["target_dates"])>p["data"]["train_labels_through"]:raise ValueError("Immature training label")
            # Both arms must receive precisely the same task targets and histories.
            assert messages(task,"price_only")[0]==messages(task,"price_evidence")[0]
    readiness=eligibility(groups,releases["records"])
    if readiness["origin_coverage"]<.9 or readiness["distinct_releases"]<3:raise ValueError("Evidence variation/coverage gate failed")
    repair=json.loads(pathlib.Path("inputs/reference/reference-repair.json").read_text())
    assert repair["existing_rows_unchanged"] and repair["original_rows_sha256"]==digest(original["baselines"])
    dataset={**original,"study_id":p["study_id"],"protocol_sha256":digest(p),"groups":groups,"baselines":repair["rows"],"bls_source_manifest_sha256":digest(releases)}
    audit={**old_audit,"study_id":p["study_id"],"protocol_sha256":digest(p),"dataset_sha256":digest(dataset),"price_only_ready":True,"evidence_ready":True,"evidence_gate_reason":"Ten original BLS releases, ordered monthly captions and exact industry row verified; current revised history excluded","evidence_readiness":readiness,"parent_dataset_sha256":old_audit["dataset_sha256"],"source_manifest_sha256":digest(releases),"native_reference_repair_sha256":digest(repair),"training_by_family":dict(collections.Counter("H100" if t["metadata"]["gpu_model"].startswith("H100") else "A100" for t in groups["training"])),"training_by_source":dict(collections.Counter(t["metadata"]["source_id"] for t in groups["training"])),"training_by_instrument":dict(collections.Counter(t["metadata"]["instrument_class"] for t in groups["training"])),"training_monthly_releases":sorted({t["bls"]["reference_period"] for t in groups["training"]}),"created_at":datetime.now(timezone.utc).isoformat(),"news_used":False,"infrastructure_used":False,"provider_cost_usd":None}
    for name,value in (("dataset.json",dataset),("audit.json",audit),("bls-vintages.json",releases)):
        (out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    shutil.copy(root/"requirements-lock.txt",out/"requirements-lock.txt")
    print(json.dumps({"study_id":p["study_id"],"dataset_sha256":audit["dataset_sha256"],"readiness":readiness,"phase_tasks":audit["phase_tasks"],"training_by_family":audit["training_by_family"],"training_releases":audit["training_monthly_releases"]}),flush=True)
if __name__=="__main__":main()
