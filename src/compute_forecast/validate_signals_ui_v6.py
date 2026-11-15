"""Remote source-to-screen verification of real pending forecasts; PNG only."""
import base64,hashlib,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
from .review_v4 import digest
SHA="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def main():
    out=Path("artifacts/signals-ui-v6");out.mkdir(parents=True,exist_ok=True);report={"status":"running","widths":[],"video_recorded":False,"test_source_sha":os.environ.get("GITHUB_SHA")}
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width in (1512,390,320):
            context=browser.new_context(viewport={"width":width,"height":1000},is_mobile=width<760,has_touch=width<760,reduced_motion="reduce")
            page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(URL+"/#signals",wait_until="domcontentloaded",timeout=90000);page.wait_for_selector("#sig-plot svg",timeout=120000)
            response=page.request.get(URL+"/api/signals-v6");assert response.ok;index=response.json()
            assert index["schema_version"]==6 and index["snapshot_count"]>=1 and len(index["cohort"])==4
            assert index["registration"]["source_sha"]=="0f1c55f3852fc973f9dec1a787902605e6400901"
            assert index["prospective_improvement_established"] is False and index["primary_scored_cells"]==0
            record=page.request.get(URL+index["ledger"][0]["artifact"]).json()
            assert digest(record)==index["ledger"][0]["id"] and len(record["rows"])==48
            assert record["kind"]=="cold_start_reference_pilot" and record["outcome_status"]=="pending"
            report["ui_revision"]=page.request.get(URL+"/health").json()["ui_revision"]
            for family in ("A100","H100"):
                target=next(t for t in index["cohort"] if t["family"]==family)
                page.locator("#sig-series").select_option(target["id"])
                for method in ("last_value_empirical","drift"):
                    page.locator("#sig-forecaster").select_option(method)
                    for i,h in enumerate((1,3,7)):
                        page.locator('[data-sig-point="'+str(i)+'"]').focus();page.keyboard.press("Enter")
                        expected=next(r for r in record["rows"] if r["series_id"]==target["id"] and r["forecaster"]==method and r["horizon_days"]==h)
                        assert float(page.locator("[data-sig-q50]").get_attribute("data-sig-q50"))==expected["q50"]
            page.locator("#sig-pin").click();pin=page.evaluate("JSON.stringify(GS.pins[0])")
            page.locator("#sig-contract").evaluate("(e)=>e.open=true")
            if width in (1512,390):
                page.evaluate("scrollTo(0,0)");page.screenshot(path=str(out/(str(width)+"-commitments.png")))
            page.locator('[data-sig-tab="learning"]').click()
            assert page.locator(".sig-table tbody tr").count()==8
            assert page.get_by_text("No eligible primary outcomes yet.",exact=True).count()==1
            assert page.get_by_text("48 committed rows",exact=True).count()==1
            # Explicit synthetic geometry contract only; never inserted into or published as market data.
            fixture={"classification":"synthetic_contract_fixture","trajectory":[{"origin":"2027-02-01","matched_cells":4,"comparisons":[{"difference":-.004,"mean_interval_width":.05,"coverage_numerator":3,"coverage_denominator":4}]},{"origin":"2027-02-08","matched_cells":3,"comparisons":[{"difference":.002,"mean_interval_width":.07,"coverage_numerator":2,"coverage_denominator":3}]}]}
            geometry=page.evaluate("""value=>{let html=sigResearchPlot(value);let doc=new DOMParser().parseFromString(html,'text/html');return {svgs:doc.querySelectorAll('svg').length,actions:doc.querySelectorAll('[data-sig-origin]').length,bad:html.includes('NaN'),synthetic:html.includes('Synthetic UI contract fixture')}}""",fixture)
            assert geometry=={"svgs":3,"actions":4,"bad":False,"synthetic":True}
            if width in (1512,390):
                page.evaluate("scrollTo(0,0)");page.screenshot(path=str(out/(str(width)+"-learning.png")))
            page.locator('[data-sig-tab="evidence"]').click()
            page.wait_for_selector('[data-sig-memory="true"]',timeout=120000)
            memory=page.request.get(URL+"/api/signals-v6/memory").json()
            assert memory["eligibility"]["writers"]==3 and memory["eligibility"]["readers"]==3
            assert memory["eligibility"]["cross_role_uses"]>=5 and memory["actual_tinker_decisions"]==4
            assert memory["accuracy_improvement"] is None and memory["new_optimizer_updates"]==0
            assert str(index["latest_snapshot"]["features"]["electricity_ppi_index"]) in page.locator("#app").inner_text()
            if width in (1512,390):
                page.evaluate("scrollTo(0,0)");page.screenshot(path=str(out/(str(width)+"-signals.png")))
            page.get_by_role("button",name="Explore",exact=True).click();page.wait_for_selector("#price-chart")
            page.get_by_role("button",name="Signals",exact=True).click()
            assert page.evaluate("JSON.stringify(GS.pins[0])")==pin
            page.locator('[data-sig-tab="commitments"]').click()
            assert page.locator("#sig-contract").get_attribute("open") is not None
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),"Signals page overflow"
            assert not errors,errors
            results=page.evaluate("""async()=>await Promise.all(Array.from({length:8},async(_,i)=>{let r=await fetch(i%2?'/api/signals-v6':'/api/pricing',{cache:'no-store'});return r.status}))""")
            assert results==[200]*8
            report["widths"].append({"width":width,"exact_commitments":True,"pending_claims":True,"memory_verified":True,"pins_immutable":True,"no_overflow":True,"keyboard_touch":True,"concurrent_requests":8})
            context.close()
        context=browser.new_context(viewport={"width":390,"height":850});page=context.new_page()
        page.route("**/api/signals-v6",lambda r:r.fulfill(status=503,content_type="application/json",body='{"error":"synthetic transport fixture"}'))
        page.goto(URL,wait_until="domcontentloaded",timeout=90000);page.wait_for_selector("#price-chart",timeout=90000)
        page.get_by_role("button",name="Signals",exact=True).click();page.wait_for_selector("#sig-retry",timeout=90000)
        page.unroute("**/api/signals-v6");page.locator("#sig-retry").click();page.wait_for_selector("#sig-plot svg",timeout=90000)
        assert hashlib.sha256(page.request.get(URL+"/files/forecasts.csv").body()).hexdigest()==SHA
        context.close();browser.close()
    report["status"]="passed";(out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("V6_UI_VALIDATION:"+json.dumps(report),flush=True)
    for path in sorted(out.glob("*.png")):
        raw=path.read_bytes();data=base64.b64encode(raw).decode()
        print("V6_PNG_META:"+json.dumps({"name":path.name,"sha256":hashlib.sha256(raw).hexdigest(),"chunks":(len(data)+11999)//12000}),flush=True)
        for i in range(0,len(data),12000):print("V6_PNG:"+json.dumps({"name":path.name,"index":i//12000,"base64":data[i:i+12000]}),flush=True)
if __name__=="__main__":main()
