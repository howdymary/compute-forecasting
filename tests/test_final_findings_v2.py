import base64
import pytest
from compute_forecast import final_findings_v2 as report

def test_incomplete_reports_cannot_publish_completed_findings():
    with pytest.raises(ValueError,match="Complete six-SFT/three-RL"):
        report.validate({"policy_reports":[]})

def test_metagame_and_other_refs_are_rejected_before_api_calls(monkeypatch):
    monkeypatch.setenv("GITHUB_REF","refs/heads/metagame")
    monkeypatch.setattr(report,"gh",lambda *args,**kwargs:pytest.fail("Unexpected API call"))
    with pytest.raises(ValueError,match="Wrong publication branch"):
        report.publish({},"")

def test_publication_refuses_unapproved_paths_before_creating_blobs(monkeypatch):
    monkeypatch.setenv("GITHUB_REF","refs/heads/compute-observatory")
    monkeypatch.setenv("GITHUB_REPOSITORY","howdymary/compute-forecasting")
    mutations=[]
    def api(path,method="GET",body=None):
        if method!="GET":mutations.append(path);pytest.fail("Unexpected mutation")
        if "/git/ref/" in path:return {"object":{"sha":"head"}}
        if "/git/commits/" in path:return {"tree":{"sha":"tree"}}
        return {"content":base64.b64encode(b"[Experimental Research v2](example)").decode()}
    monkeypatch.setattr(report,"gh",api)
    with pytest.raises(ValueError,match="Unexpected publication path"):
        report.publish({"metagame.txt":"bad"},"replacement")
    assert mutations==[]

def test_renderer_reports_improving_tied_and_worsening_rl_without_api_calls():
    # Explicit unit fixtures only; never submitted as an experiment or public live result.
    def metric(label,value):
        return {"policy":label,"pinball":value,"baseline_pinball":.25,"n_cells":12}
    reports=[]
    for seed in (17,29,43):
        for objective in ("hard","soft"):
            comparisons=[metric(k,v) for k,v in (
                ("starting_policy",.2),("selected_sft_"+objective,.1),
                ("selected_no_observation",.1),("selected_with_criticism",.12),
                ("selected_with_method_evidence",.11),("training_selected_static",.13),
                ("random_100_seed_distribution",.14),("gp_expected_improvement",.15))]
            reports.append({"mode":"sft","objective":objective,"seed":seed,"actual_optimizer_updates":100,"selected_update":20,"checkpoints":[{"update":20,"development_pinball":.1,"checkpoint_id":"unit-fixture"}],"future_competition_truth_loaded":False,"v1_final_used":False,"comparisons":comparisons})
    for seed,value in ((17,.09),(29,.1),(43,.11)):
        reports.append({"mode":"rl","objective":"hard","seed":seed,"actual_optimizer_updates":20,"selected_update":20,"checkpoints":[{"update":20,"development_pinball":.1,"checkpoint_id":"unit-fixture"}],"future_competition_truth_loaded":False,"v1_final_used":False,"comparisons":[metric("selected_rl_hard",value),metric("sft_parent",.1)]})
    data={"policy_reports":reports,"analysis":{"complete_encoding_gp_control":{"pinball":.12},"stronger_static_control":{"pinball":.13},"training_selected_fixed_forecaster":{"pinball":.14,"config_id":"unit-fixture"},"evaluation_temporal_origins":["2026-08-29","2026-09-05","2026-09-12"]},"artifact_archive":{"url":"https://example.invalid/unit-fixture.zip","sha256":"0"*64},"autonomy_runs":[]}
    perf={"origins":18,"method_origin_results":756,"stage_wall_seconds":541.215,"origins_per_minute":1.9955,"sum_function_elapsed_seconds":2462.55}
    text,registry,summary,intro=report.render(data,perf)
    assert (summary["rl_improving_seeds"],summary["rl_tied_seeds"],summary["rl_worsening_seeds"])==(1,1,1)
    assert summary["rl_updates"]==60 and len(registry["runs"])==9
    assert "1 lower loss versus their SFT parent, 1 tie and 1 increase loss" in text
    assert "1 improve, 1 tie, 1 worsen" in intro
    assert "tinker://" not in str(registry)
