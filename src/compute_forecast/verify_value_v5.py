"""Credential-free reconstruction of permitted v5 publication contracts."""
import csv,hashlib,json,math
from pathlib import Path
from .review_v4 import digest
from .economics_v5 import calculate
from .capability_v5 import rental_pairs,benchmarks,analyze
STUDY="results/value-v5/runs/43757456253/study.json"
MEMORY="results/value-v5/runs/43758970371/memory.json"
SHA="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
def close(a,b):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12),(a,b)
def verify():
    raw=Path(STUDY).read_bytes();study=json.loads(raw);memory=json.loads(Path(MEMORY).read_bytes())
    official=Path("results/frozen-v1/forecasts.csv").read_bytes()
    assert hashlib.sha256(official).hexdigest()==SHA==study["official_csv_sha256"]
    forecasts=list(csv.DictReader(official.decode().splitlines()));assert len(forecasts)==111
    by_id={};eligible=set()
    for r in forecasts:
        assert r["origin_date"]=="2026-11-06" and int(r["horizon_days"]) in (1,3,7)
        assert 0<float(r["q10"])<=float(r["q50"])<=float(r["q90"])
        by_id.setdefault(r["series_id"],[]).append(r)
    assert len(by_id)==37 and len(study["history"]["series"])==36
    n=0
    for s in study["history"]["series"]:
        assert s["id"] in by_id and s["source_id"] in ("afhubbard","gpurentalprices","fastgpu_daily")
        assert s["license"]=="CC BY 4.0" and s["attribution"] and s["license_url"]
        assert s["instrument_class"]!="marketplace_ask" and s["unit"]=="USD per GPU-hour"
        assert digest(s["points"])==s["points_sha256"]
        dates=[p["date"] for p in s["points"]];assert dates==sorted(set(dates)) and dates[-1]<="2026-11-06"
        assert all(p["value"]>0 for p in s["points"]);n+=len(dates)
    losses=[]
    for m in study["baseline_audit"]["methods"]:
        assert m["n_cells"]==len(m["cells"])==12;keys=set()
        for c in m["cells"]:
            key=(c["series_id"],c["origin_date"],int(c["horizon_days"]));assert key not in keys;keys.add(key)
            assert float(c["q10"])<=float(c["q50"])<=float(c["q90"])
            computed=[]
            for q in (.1,.5,.9):
                predicted=float(c["q"+str(int(q*100))]);error=float(c["y"])-predicted
                computed.append(max(q*error,(q-1)*error))
            close(sum(computed)/3,float(c["loss"]))
        if eligible:assert keys==eligible
        else:eligible=keys
        mean=sum(float(c["loss"]) for c in m["cells"])/len(m["cells"])
        assert abs(mean-m["official_report"]["overall"]["pinball"])<=.00000051
        losses.append({"method":m["method"],"cells":12,"reconstructed_pinball":mean,"official_printed_pinball":m["official_report"]["overall"]["pinball"]})
    own={r["record_id"]:r for r in memory["records"]}
    writers={r["author"] for r in memory["records"] if r.get("ingestion_completed")};readers=set();uses=0
    for r in memory["reads"]:
        if r["actual_cross_role_use"]:
            source=own[r["required_source_id"]]
            assert r["required_source_id"] in r["returned_source_ids"]
            assert r["reader_role"]!=source["role"]
            assert r["consumed_content_sha256"]==source["content_sha256"]
            readers.add(r["reader"]);uses+=1
    assert len(writers)>1 and len(readers)>1 and uses==memory["verified_cross_role_reads"]==6
    assert memory["eligibility"]=={"successful_writers":len(writers),"successful_readers":len(readers),"cross_role_use":uses,"requirements_met":True}
    assert memory["status"]=="completed_verified_memory" and memory["new_optimizer_updates"]==0
    assert memory["final"]["changed_after_criticism"]==(memory["final"]["action"]!=memory["final"]["draft_action"])
    for step in memory["steps"]:
        assert step["record_id"] in own
        assert all(r in own for r in step["used_record_ids"])
    pair=rental_pairs(study)[0];economic=[]
    for gpu,anchor,power in (("H100 SXM80",pair["h100_rate"],700),("A100 SXM80",pair["a100_rate"],400)):
        for months in (24,36):
            for assumption in study["economic_config"]["scenarios"]:
                result=calculate(anchor,assumption["annual_change"],months,active_w=power)
                close(result["points"][-1]["rental_rate"],anchor*(1+assumption["annual_change"])**(months/12))
                close(result["combined_present_value_proxy"],result["present_value_operating_cashflows"]+result["discounted_residual_proxy"])
                economic.append({"gpu":gpu,"months":months,"path":assumption["label"],"annual_change":assumption["annual_change"],"rental_usd_gpu_hour":result["points"][-1]["rental_rate"],"operating_pv":result["present_value_operating_cashflows"],"income_residual_proxy_at_horizon":result["income_based_residual_proxy"],"break_even_utilization":result["points"][-1]["operating_break_even_utilization"]})
    capabilities=[analyze(study,pair["id"],key) for key in benchmarks(study)]
    for c in capabilities:close(c["h100_cost_per_matched_work_relative_to_a100"],c["pair"]["rental_premium"]/c["benchmark"]["throughput_ratio"])
    return {"status":"passed","study_file_sha256":hashlib.sha256(raw).hexdigest(),"official_csv_sha256":SHA,"historical_series":36,"historical_observations":n,"baseline_reconstruction":losses,"memory":{"writers":len(writers),"readers":len(readers),"cross_role_uses":uses,"forecast_improvement_established":False},"economic_calculations":economic,"conditional_capability_ratios":[{"benchmark":c["benchmark"]["id"],"relative_h100_rental_cost":c["h100_cost_per_matched_work_relative_to_a100"]} for c in capabilities],"limitations":"Public artifacts reproduce published arithmetic. Pack acquisition, private model sampling and independent outcome maturity remain separate requirements."}
def main():
    report=verify()
    publication=Path("results/value-v5/ui-publication.json")
    if publication.is_file():
        manifest=json.loads(publication.read_bytes());ui=json.loads(Path(manifest["report_path"]).read_bytes())
        assert ui["status"]=="passed" and ui["ui_revision"]==manifest["source_ui_sha"]
        assert manifest["video_recorded"] is False and ui["video_recorded"] is False
        for name,item in manifest["images"].items():
            assert name.startswith("docs/images/value-v5-") and name.endswith(".png")
            assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==item["sha256"]
        report["ui_publication"]={"validated_revision":ui["ui_revision"],"image_hashes_verified":len(manifest["images"]),"video_recorded":False}
    report["publication_files"]={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in (STUDY,MEMORY,"docs/pacific-value-v5.md","docs/past-dev-memory.md","docs/DATA_SOURCES.md","configs/pacific-value-v5.json")}
    out=Path("artifacts/public-value-v5");out.mkdir(parents=True,exist_ok=True)
    (out/"verification.json").write_text(json.dumps(report,indent=2)+"\n");print("VALUE_V5_PUBLIC_VERIFICATION:"+json.dumps(report),flush=True)
if __name__=="__main__":main()
