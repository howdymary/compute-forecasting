"""Remote interaction, exact-source and public-memory verification; PNG only."""
import base64,hashlib,json,math,os
from pathlib import Path
from playwright.sync_api import sync_playwright
from .economics_v5 import calculate
from .verify_value_v5 import verify,SHA
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-10),(a,b)
def main():
    verify();out=Path("artifacts/value-ui-v5");out.mkdir(parents=True,exist_ok=True)
    report={"status":"running","test_source_sha":os.environ.get("SOURCE_SHA",os.environ.get("GITHUB_SHA")),"widths":[],"video_recorded":False}
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width in (1512,390,320):
            context=browser.new_context(viewport={"width":width,"height":1000},is_mobile=width<760,has_touch=width<760,reduced_motion="reduce")
            page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(URL+"/#value",wait_until="domcontentloaded",timeout=90000)
            page.wait_for_selector("#value-chart",timeout=90000)
            health=page.request.get(URL+"/health");assert health.ok;report["ui_revision"]=health.json()["ui_revision"]
            raw=page.request.get(URL+"/api/value-v5");assert raw.ok;v=raw.json()
            assert len(v["history"]["series"])==36 and v["official_csv_sha256"]==SHA
            assert page.evaluate("v5Series().gpu_model.includes('H100 SXM')")
            page.locator("#value-chart").focus();page.keyboard.press("End")
            chosen=page.evaluate("v5Points()[VS.point]");assert chosen["kind"]=="forecast" and chosen["horizon_days"]==7
            close(page.locator("[data-value-exact]").get_attribute("data-value-exact"),chosen["q50"])
            page.keyboard.press("ArrowLeft");assert page.evaluate("v5Points()[VS.point].horizon_days")==3
            page.locator("#value-pin").click();pin=page.evaluate("JSON.stringify(VS.pins[0])")
            page.locator("#value-history-source").evaluate("(e)=>e.open=true")
            if width in (1512,390):
                page.evaluate("scrollTo(0,0)");page.screenshot(path=str(out/(str(width)+"-history.png")))
            page.locator("#value-series").select_option("afhubbard.hyperscaler_spot.A100_40GB.spot.median")
            page.locator("#value-range").select_option("all")
            path=page.locator("#value-chart path").first.get_attribute("d");assert path.count("M")>1,"Historical gaps must break paths"
            if width<760:page.locator("#value-chart").tap(position={"x":100,"y":100})
            else:page.locator("#value-chart").hover(position={"x":200,"y":100})
            assert page.evaluate("JSON.stringify(VS.pins[0])")==pin
            page.locator('[data-value-tab="economics"]').click();page.wait_for_selector("#value-econ-chart")
            # Select the same explicit SXM80 rate-card anchor used in the economic finding.
            page.locator("#value-series").select_option("gpurentalprices.neocloud_rate_card.H100_SXM_80GB.on_demand.median")
            page.locator("#value-reset").click()
            anchor=page.evaluate("v5Series().points.at(-1).value")
            expected=calculate(anchor,-.15,36,active_w=700)
            close(page.locator("[data-value-pv]").get_attribute("data-value-pv"),expected["present_value_operating_cashflows"])
            close(page.locator("[data-value-residual]").get_attribute("data-value-residual"),expected["income_based_residual_proxy"])
            page.evaluate("window.keptSlider=document.querySelector('#value-utilization')")
            page.locator("#value-utilization").evaluate("(e)=>{e.value='0';e.dispatchEvent(new Event('input',{bubbles:true}))}")
            assert page.evaluate("keptSlider===document.querySelector('#value-utilization')"),"Slider DOM replaced during drag"
            assert float(page.locator("[data-value-net]").get_attribute("data-value-net"))<0
            page.locator("#value-reset").click()
            page.locator("#value-annual").evaluate("(e)=>{e.value='-25';e.dispatchEvent(new Event('input',{bubbles:true}))}")
            close(page.locator("[data-value-rental]").get_attribute("data-value-rental"),anchor*.75**3)
            page.locator("#value-pin").click();economic_pin=page.evaluate("JSON.stringify(VS.pins.at(-1))")
            page.locator("#value-reset").click();assert page.evaluate("VS.rates[1]")==-.15
            page.locator('[data-value-months="24"]').click();expected=calculate(anchor,-.15,24,active_w=700)
            close(page.locator("[data-value-pv]").get_attribute("data-value-pv"),expected["present_value_operating_cashflows"])
            page.locator("#value-econ-chart").focus();page.keyboard.press("ArrowLeft")
            assert page.evaluate("VS.cursor")==23
            page.locator('[data-value-months="36"]').click()
            page.locator("#value-month").evaluate("(e)=>{e.value='36';e.dispatchEvent(new Event('input',{bubbles:true}))}")
            assert page.evaluate("JSON.stringify(VS.pins.at(-1))")==economic_pin
            if width in (1512,390):
                page.evaluate("scrollTo(0,0)");page.screenshot(path=str(out/(str(width)+"-economics.png")))
                page.locator(".value-grid").screenshot(path=str(out/(str(width)+"-economic-results.png")))
            page.locator('[data-value-tab="research"]').click()
            page.wait_for_selector('[data-value-memory-verified="true"]',timeout=90000)
            memory_response=page.request.get(URL+"/api/value-v5/memory");assert memory_response.ok;memory=memory_response.json()
            assert memory["eligibility"]=={"successful_writers":3,"successful_readers":3,"cross_role_use":6,"requirements_met":True}
            assert page.locator(".value-memory-step").count()==len(memory["steps"])==5
            assert "3 writers" in page.locator(".value-proof").inner_text()
            for key in ("llm_server","llm_offline","cross_benchmark"):
                page.locator("#value-workload").select_option(key)
                expected=page.evaluate("(()=>{let b=V5.capability.units_a100_reference.find(r=>r.gpu_generation==='H100'&&r.benchmark_set_id.endsWith('_precmatch')&&(VS.workload==='cross_benchmark'?r.benchmark_set_id.includes('cross_benchmark_median'):r.benchmark_set_id.includes(VS.workload)));return V5.capability.rental_pairs[0].rental_premium/(+b.capability_units_per_accelerator)})()")
                close(page.locator("[data-value-capability]").get_attribute("data-value-capability"),expected)
            page.locator("#value-capability-source").evaluate("(e)=>e.open=true")
            page.locator("#value-memory-retry").click();page.wait_for_timeout(1000)
            assert page.locator("#value-capability-source").get_attribute("open") is not None
            page.locator("#value-capability-source").evaluate("(e)=>e.open=false")
            if width in (1512,390):
                page.locator(".value-proof").evaluate("(e)=>e.scrollIntoView({block:'start'})")
                page.screenshot(path=str(out/(str(width)+"-memory.png")))
                page.locator("#value-workload").evaluate("(e)=>e.scrollIntoView({block:'start'})")
                page.screenshot(path=str(out/(str(width)+"-capability.png")))
            page.get_by_role("button",name="Explore",exact=True).click();page.wait_for_selector("#price-chart")
            page.get_by_role("button",name="GPU value",exact=True).click()
            assert page.locator("#value-workload").input_value()=="cross_benchmark"
            assert page.evaluate("JSON.stringify(VS.pins.at(-1))")==economic_pin
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),"Page overflow"
            assert not errors,errors
            report["widths"].append({"width":width,"history_gaps":True,"exact_forecasts":True,"economic_math":True,"continuous_controls":True,"pins_immutable":True,"memory_verified":True,"no_overflow":True,"keyboard_and_pointer":True})
            context.close()
        context=browser.new_context(viewport={"width":390,"height":850})
        page=context.new_page()
        page.route("**/api/value-v5",lambda r:r.fulfill(status=503,content_type="application/json",body='{"error":"synthetic transport fixture"}'))
        page.goto(URL,wait_until="domcontentloaded",timeout=90000);page.wait_for_selector("#price-chart",timeout=90000)
        assert page.locator("#price-chart").is_visible(),"Pricing blocked by value-study failure"
        page.get_by_role("button",name="GPU value",exact=True).click();page.wait_for_selector("#value-retry",timeout=90000)
        page.unroute("**/api/value-v5");page.locator("#value-retry").click();page.wait_for_selector("#value-chart",timeout=90000)
        assert hashlib.sha256(page.request.get(URL+"/files/forecasts.csv").body()).hexdigest()==SHA
        assert page.request.get(URL+"/value-notices/ATTRIBUTION.md").ok
        assert page.request.get(URL+"/value-notices/afhubbard_DATA_LICENSE.txt").ok
        response=page.request.get(URL+"/api/value-v5/memory");assert response.ok and response.json()["status"]=="completed_verified_memory"
        requests=page.evaluate("""async()=>await Promise.all(Array.from({length:8},async(_,i)=>{const path=i%2?'/api/value-v5/memory':'/api/value-v5';const r=await fetch(path,{cache:'no-store'});const x=await r.json();return {status:r.status,valid:i%2?x.eligibility?.requirements_met===true:x.history?.series?.length===36}}))""")
        assert all(r["status"]==200 and r["valid"] for r in requests),requests
        report["concurrent_value_and_memory_reads"]={"callers":8,"passed":True,"automatic_retries":0}
        report["independent_loading_and_retry"]=True
        context.close();browser.close()
    report["status"]="passed";(out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("V5_UI_VALIDATION:"+json.dumps(report),flush=True)
    for image in sorted(out.glob("*.png")):
        raw=image.read_bytes();data=base64.b64encode(raw).decode()
        print("V5_PNG_META:"+json.dumps({"name":image.name,"sha256":hashlib.sha256(raw).hexdigest(),"chunks":(len(data)+11999)//12000}),flush=True)
        for i in range(0,len(data),12000):print("V5_PNG:"+json.dumps({"name":image.name,"index":i//12000,"base64":data[i:i+12000]}),flush=True)
if __name__=="__main__":main()
