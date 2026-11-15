"""Strict source-to-screen research checks. Remote PNGs only, no recording."""
from __future__ import annotations
import hashlib,json,math,os,subprocess,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from .history_contract_v3 import validate_assets
from .validate_notebook_ui import capture,contrast_ratio
from .validate_pricing_ui import URL
from .remote_validation_http import get_bytes as get,snapshot
CSV_SHA="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
def main():
    from playwright.sync_api import sync_playwright,expect
    out=Path("artifacts/research-explorer");out.mkdir(parents=True,exist_ok=True)
    assets=validate_assets(json.loads(get("/api/research-assets")));control=json.loads(get("/api/chronos-control"));expanded=json.loads(get("/api/experimental"))
    assert control["status"]=="completed" and control["scope"]["cells"]==12
    assert len(control["scored_cell_keys"])==len({tuple(k) for k in control["scored_cell_keys"]})==12
    assert control["config"]["model_revision"]=="29ec3766d36d6f73f0696f85560a422f50e8498c"
    assert math.isclose(control["metrics"]["pinball"],.012113554233974892,abs_tol=1e-12)
    assert control["prospective"]["outcomes_loaded"] is False and control["prospective"]["forecast_count"]==42
    assert expanded["campaign_status"]=="completed" and len(expanded["policy_reports"])==9
    assert sum(p["actual_optimizer_updates"] for p in expanded["policy_reports"] if p["mode"]=="rl")==99
    assert all(p["selected_update"]==0 for p in expanded["policy_reports"] if p["mode"]=="rl")
    assert hashlib.sha256(get("/files/forecasts.csv")).hexdigest()==CSV_SHA
    for s in assets["history_context"]["series"]:
        assert s["observations"]==234 and s["missing_calendar_days"]==65
        assert s["points"][0]["date"]=="2026-01-12" and s["points"][-1]["date"]=="2026-11-06"
        assert s["benchmark_overlay_allowed"] is False
    process=None;log=None
    paths=["/api/research-assets","/api/chronos-control","/api/pricing","/api/experimental","/api/notebook","/notebook-assets/caveat-f84acf2c.ttf","/files/forecasts.csv"]*3
    def probe(p):
        t=time.monotonic()
        try:raw=get(p)
        except Exception as error:
            print("RESEARCH_HTTP_FAILURE:"+json.dumps({"path":p,"seconds":time.monotonic()-t,"error":str(error)}),flush=True)
            raise
        if p.endswith(".csv"):assert hashlib.sha256(raw).hexdigest()==CSV_SHA
        elif p.endswith(".ttf"):assert len(raw)>100000
        else:
            j=json.loads(raw)
            if p=="/api/research-assets":validate_assets(j)
        return {"path":p,"status":200,"seconds":time.monotonic()-t,"bytes":len(raw)}
    errors=[];checks=[];failed=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width,height in ((1512,982),(390,844),(320,740)):
            context=browser.new_context(viewport={"width":width,"height":height},is_mobile=width<500,has_touch=width<500,reduced_motion="reduce")
            page=context.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
            page.on("response",lambda r:failed.append({"status":r.status,"url":r.url}) if r.url.startswith(URL) and r.status>=400 and not r.url.endswith("/favicon.ico") else None)
            page.goto(URL,wait_until="domcontentloaded",timeout=90000);page.locator("#price-chart").wait_for(timeout=90000)
            page.get_by_role("button",name="Historical context",exact=True).click();page.locator("[data-history-value]").wait_for(timeout=90000)
            assert page.locator("#history-select option").count()==2
            assert page.locator("[data-history-segment]").count()>1,"Missing dates were joined"
            series=assets["history_context"]["series"][0]
            close=lambda a,b:math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12)
            assert close(float(page.locator("[data-history-value]").get_attribute("data-history-value")),series["points"][-1]["value"])
            page.evaluate("scrollTo(0,0)");capture(page,out,str(width)+"-history-all")
            page.locator("#time-cursor").evaluate("(el)=>{el.value='0';el.dispatchEvent(new Event('input',{bubbles:true}))}")
            assert close(float(page.locator("[data-history-value]").get_attribute("data-history-value")),series["points"][0]["value"])
            page.locator("#price-chart").focus();page.keyboard.press("ArrowRight")
            assert page.locator("#time-cursor").input_value()=="1"
            assert close(float(page.locator("[data-history-value]").get_attribute("data-history-value")),series["points"][1]["value"])
            page.get_by_role("button",name="＋ Pin this observation",exact=True).click()
            pin=page.evaluate("structuredClone(S.pins[0])")
            assert pin["kind"]=="historical_observation" and pin["date"]==series["points"][1]["date"] and pin["points_sha256"]==series["points_sha256"]
            page.get_by_role("button",name="30 days",exact=True).click()
            page.locator("#history-select").select_option(assets["history_context"]["series"][1]["id"])
            assert page.evaluate("S.pins[0]")==pin
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
            page.evaluate("scrollTo(0,0)");capture(page,out,str(width)+"-history")
            if width<500:
                chart=page.locator("#price-chart");chart.scroll_into_view_if_needed();box=chart.bounding_box()
                page.touchscreen.tap(box["x"]+box["width"]*.6,box["y"]+100);expect(page.locator("#chart-tooltip")).to_be_visible()
            page.get_by_role("button",name="Research",exact=True).click()
            page.get_by_role("button",name="Research atlas",exact=True).click()
            page.locator("#atlas-run").wait_for(timeout=90000)
            operational=next(p for p in expanded["policy_reports"] if p["run_id"]=="c24ee0b5943f48c2bfa17032598f42f4")
            selected=next(m for m in operational["comparisons"] if m["policy"]=="selected_sft_soft")
            row=page.locator('[data-comparison-policy="selected_sft_soft"]')
            assert close(float(row.get_attribute("data-pinball")),selected["pinball"]) and row.get_attribute("data-cells")=="12"
            assert close(float(page.locator('[data-comparison-policy="chronos2"]').get_attribute("data-pinball")),control["metrics"]["pinball"])
            assert page.locator("#learning-figure [data-checkpoint-update]").count()==len(operational["checkpoints"])
            for cp in operational["checkpoints"]:
                mark=page.locator('#learning-figure [data-checkpoint-update="'+str(cp["update"])+'"]')
                assert close(float(mark.get_attribute("data-development-score")),cp["development_pinball"])
            details=page.locator(".research-figure details").first;details.locator("summary").click()
            page.locator("#refresh-atlas").focus();page.locator("#refresh-atlas").click()
            page.wait_for_timeout(1500)
            assert page.locator("#refresh-atlas").evaluate("(el)=>el===document.activeElement")
            assert page.locator(".research-figure details").first.get_attribute("open") is not None
            for scope,denom in (("h:3",4),("s:afhubbard.hyperscaler_spot.A100_40GB.spot.median",3),("all",12)):
                page.locator("#atlas-scope").select_option(scope)
                assert all(int(v)==denom for v in page.locator("[data-comparison-policy]").evaluate_all("(es)=>es.map(e=>e.dataset.cells)"))
                expected=selected if scope=="all" else selected["by_horizon"]["3"] if scope=="h:3" else selected["by_series"][scope[2:]]
                assert close(float(page.locator('[data-comparison-policy="selected_sft_soft"]').get_attribute("data-pinball")),expected["pinball"])
            assert page.locator("#paired-task option").count()==4 and page.locator(".action-sequence li").count()==12
            page.locator("#paired-task").select_option("1")
            task=assets["paired_traces"]["pairs"][1]
            sequences=page.locator(".action-sequence").evaluate_all("(es)=>es.map(e=>[...e.querySelectorAll('li span')].map(n=>n.textContent))")
            assert sequences==[task["feedback"]["revealed"],task["hidden"]["revealed"]]
            page.evaluate("scrollTo(0,0)");capture(page,out,str(width)+"-research")
            page.locator("#loss-bars").scroll_into_view_if_needed();capture(page,out,str(width)+"-comparisons")
            rl=next(p for p in expanded["policy_reports"] if p["mode"]=="rl" and p["seed"]==43)
            page.locator("#atlas-run").select_option(rl["run_id"])
            assert "Update zero is the frozen SFT parent" in page.locator(".margin-observation").first.inner_text()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
            page.get_by_role("button",name="Explore",exact=True).click()
            assert page.evaluate("S.pins[0]")==pin
            assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
            checks.append({"width":width,"history_points_exact":True,"gaps":True,"matched_scopes":True,"paired_trace":True,"pin_immutable":True,"focus_and_disclosures":True,"overflow":False})
            context.close()
        # All research responses can be delayed without blocking the primary scenario chart.
        context=browser.new_context(viewport={"width":390,"height":844});page=context.new_page();held=[]
        for path in ("release","notebook","experimental","chronos-control"):page.route("**/api/"+path,lambda route:held.append(route))
        page.goto(URL,wait_until="domcontentloaded",timeout=90000);page.locator("#price-chart").wait_for(timeout=15000)
        assert page.locator("[data-point-value]").count()==3 and len(held)==4
        for route in held:route.abort()
        context.close()
        # Explicit historical error/retry state; other chart modes remain functional.
        context=browser.new_context();page=context.new_page();attempts=[0]
        def history_route(route):
            attempts[0]+=1
            if attempts[0]==1:route.fulfill(status=503,content_type="application/json",body='{"error":"test unavailable"}')
            else:route.fulfill(status=200,content_type="application/json",body=json.dumps(assets))
        page.route("**/api/research-assets",history_route)
        page.goto(URL,wait_until="domcontentloaded",timeout=90000);page.locator("#price-chart").wait_for(timeout=90000)
        page.get_by_role("button",name="Historical context",exact=True).click()
        page.get_by_role("button",name="Retry historical context",exact=True).click()
        page.locator("[data-history-value]").wait_for(timeout=90000)
        assert attempts[0]==2
        context.close();browser.close()
    # Keep the full strict stress assertion; screenshots are captured first so a
    # transport failure does not prevent visual diagnosis.
    if os.environ.get("VALIDATE_PUBLICATION")=="1":
        log=(out/"publication-stdout.txt").open("w")
        process=subprocess.Popen(["modal","run","-m","compute_forecast.research_assets_v3","--inputs","inputs"],stdout=log,stderr=subprocess.STDOUT)
    with ThreadPoolExecutor(max_workers=8) as pool:http=list(pool.map(probe,paths))
    assert snapshot()["maximum_observed_in_flight"]==8
    if process:
        assert process.wait(timeout=300)==0,"Atomic republish failed"
        log.close()
    assert not errors,errors
    assert not failed,failed
    assert hashlib.sha256(get("/files/forecasts.csv")).hexdigest()==CSV_SHA
    report={"status":"passed","ui_revision":json.loads(get("/health"))["ui_revision"],"checks":checks,"concurrent_requests":http,"http_transport":snapshot(),"concurrent_validated_publication":process is not None,"historical_series":2,"historical_observations":468,"context_only":True,"comparator_pinball":control["metrics"]["pinball"],"prospective":"pending","campaign_reports":9,"page_errors":errors,"unexpected_http_failures":failed,"recording":False}
    (out/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    print("RESEARCH_EXPLORER_VALIDATION:"+json.dumps(report),flush=True)
if __name__=="__main__":main()
