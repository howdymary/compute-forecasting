"""Focused remote interaction and exact-value checks; PNGs only."""
import base64,hashlib,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
from .review_v4 import validate
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def main():
    out=Path("artifacts/review-ui-v4");out.mkdir(parents=True,exist_ok=True)
    expected=validate(json.loads(Path("results/review-v4/findings.json").read_bytes()))
    report={"status":"running","test_source_sha":os.environ.get("SOURCE_SHA",os.environ.get("GITHUB_SHA")),"widths":[],"video_recorded":False}
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width in (1512,390,320):
            context=browser.new_context(viewport={"width":width,"height":1000},is_mobile=width<760,has_touch=width<760,reduced_motion="reduce")
            page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(URL,wait_until="domcontentloaded",timeout=90000)
            page.wait_for_selector("#price-chart",timeout=90000)
            page.get_by_role("button",name="Research",exact=True).click()
            page.get_by_role("button",name="Findings",exact=True).click()
            page.wait_for_selector("#v4-contribution-chart",timeout=90000)
            assert page.locator("#v4-candidate").inner_text()==format(expected["comparisons"][0]["candidate_pinball"],".8f")
            assert page.locator(".v4-bar").count()==2
            page.wait_for_selector("#v4-interval-loss",timeout=90000)
            operations=page.request.get(URL+"/api/review-v4/operations").json()
            report["ui_revision"]=page.request.get(URL+"/health").json()["ui_revision"]
            init=operations["operations"]["initialize"]["payload"]
            market=operations["operations"]["market"]["payload"]
            assert market["actual_tinker_decisions"]==2 and market["historical_benchmark_inputs_changed"] is False
            expected_sources=[s for s in market["sources"] if s["status"]=="retrieved_primary_source"]
            assert page.locator("#v4-market-sources details").count()==len(expected_sources)
            if expected_sources:
                detail=page.locator("#v4-market-sources details").first
                detail.locator("summary").focus();page.keyboard.press("Enter")
                assert detail.get_attribute("open") is not None
                detail_id=detail.get_attribute("id")
            raw_market=page.request.get(URL+"/api/review-v4/artifacts/"+operations["operations"]["market"]["artifact"]).body()
            assert hashlib.sha256(raw_market).hexdigest()==operations["operations"]["market"]["sha256"]
            assert page.locator("#v4-interval-loss").inner_text()==format(init["interval"]["metrics"]["candidate_pinball"],".8f")
            if "feedback" in operations["operations"]:
                feedback=operations["operations"]["feedback"]["payload"]
                assert page.locator("#v4-feedback-table tbody tr").count()==len(feedback["results"])
            page.screenshot(path=str(out/(str(width)+"-default.png")))
            page.locator(".v4-grid").screenshot(path=str(out/(str(width)+"-contributions.png")))
            numeric=page.locator(".v4-table-wrap td").first
            assert numeric.evaluate("(e)=>getComputedStyle(e).whiteSpace")=="nowrap"
            table_region=page.locator(".v4-table-wrap").first
            assert table_region.get_attribute("tabindex")=="0"
            if width<760:
                table_region.focus();page.keyboard.press("ArrowRight")
                assert table_region.evaluate("(e)=>e.scrollWidth>e.clientWidth")
                table_region.evaluate("(e)=>e.scrollLeft=0")
            page.locator("#v4-live-operations").evaluate("(e)=>e.scrollIntoView({block:'start'})")
            page.screenshot(path=str(out/(str(width)+"-operations.png")))
            page.locator("#v4-market-sources").evaluate("(e)=>e.scrollIntoView({block:'start'})")
            page.evaluate("document.activeElement?.blur()")
            page.screenshot(path=str(out/(str(width)+"-market.png")))
            page.locator("#v4-comparison").select_option("static")
            if expected_sources:assert page.locator("#"+detail_id).get_attribute("open") is not None
            assert page.locator("#v4-delta").inner_text()==format(expected["comparisons"][1]["delta"],"+.8f")
            page.locator("#v4-pin-group").click()
            pin=page.evaluate("JSON.stringify(V4S.pins[0])")
            page.locator("#v4-dimension").select_option("origin")
            assert page.locator(".v4-bar").count()==3
            page.locator("#v4-comparison").select_option("hidden")
            assert float(page.locator("#v4-delta").inner_text())==0
            assert page.evaluate("JSON.stringify(V4S.pins[0])")==pin
            page.locator(".v4-bar").first.focus();page.keyboard.press("Enter")
            assert page.locator(".v4-bar[aria-pressed=true]").count()==1
            page.locator("[data-v4-cell]").nth(5).click()
            page.locator("#v4-pin-cell").click()
            page.locator("#v4-source").evaluate("(e)=>e.open=true")
            page.get_by_role("button",name="Explore",exact=True).click()
            page.wait_for_selector("#price-chart")
            page.get_by_role("button",name="Research",exact=True).click()
            page.wait_for_selector("#v4-contribution-chart")
            assert page.locator(".v4-pin").count()==2
            assert page.locator("#v4-source").get_attribute("open") is not None
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),"Page overflow"
            assert not errors,errors
            page.screenshot(path=str(out/(str(width)+"-findings.png")),full_page=True)
            # Viewport image is kept separately for visual review.
            page.evaluate("scrollTo(0,0)")
            page.screenshot(path=str(out/(str(width)+"-viewport.png")))
            report["widths"].append({"width":width,"exact_values":True,"pin_immutable":True,"navigation_preserved":True,"no_overflow":True})
            context.close()
        context=browser.new_context(viewport={"width":390,"height":850})
        page=context.new_page()
        page.route("**/api/review-v4",lambda route:route.fulfill(status=503,content_type="application/json",body='{"error":"synthetic transport test"}'))
        page.goto(URL,wait_until="domcontentloaded",timeout=90000);page.wait_for_selector("#price-chart",timeout=90000)
        page.get_by_role("button",name="Research",exact=True).click();page.get_by_role("button",name="Findings",exact=True).click()
        page.wait_for_selector("#v4-retry",timeout=90000);page.unroute("**/api/review-v4");page.locator("#v4-retry").click();page.wait_for_selector("#v4-contribution-chart",timeout=90000)
        assert page.request.get(URL+"/files/forecasts.csv").ok
        raw=page.request.get(URL+"/files/forecasts.csv").body()
        assert hashlib.sha256(raw).hexdigest()==expected["official_csv_sha256"]
        protocol=page.request.get(URL+"/api/review-v4/protocols").json()
        assert len(protocol["prospective"]["origins"])==8
        context.close();browser.close()
    report["status"]="passed";(out/"report.json").write_text(json.dumps(report,indent=2))
    print("V4_UI_VALIDATION:"+json.dumps(report),flush=True)
    for name in ("1512-default.png","1512-contributions.png","390-default.png","390-contributions.png","1512-operations.png","390-operations.png","1512-market.png","390-market.png"):
        raw=(out/name).read_bytes();data=base64.b64encode(raw).decode()
        print("V4_PNG_META:"+json.dumps({"name":name,"sha256":hashlib.sha256(raw).hexdigest(),"chunks":(len(data)+11999)//12000}),flush=True)
        for i in range(0,len(data),12000):print("V4_PNG:"+json.dumps({"name":name,"index":i//12000,"base64":data[i:i+12000]}),flush=True)
if __name__=="__main__":main()
