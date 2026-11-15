"""Remote notebook interaction, provenance and accessibility checks. PNGs only."""
from __future__ import annotations
import base64,hashlib,json,math,os,time
from pathlib import Path
from urllib.request import urlopen
from .notebook_diagnostics import build
from .validate_pricing_ui import main as validate_existing_pricing
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def get(path):return urlopen(URL+path,timeout=90).read()
def close(a,b):
    assert len(a)==len(b) and all(math.isclose(x,y,rel_tol=1e-10,abs_tol=1e-12) for x,y in zip(a,b)),(a,b)
def capture(page,out,label):
    raw=page.screenshot(path=str(out/(label+".png")),full_page=False)
    encoded=base64.b64encode(raw).decode()
    for i in range(0,len(encoded),2400):print("NOTEBOOK_SCREENSHOT:"+label+":"+str(i//2400)+":"+encoded[i:i+2400],flush=True)
def main():
    from playwright.sync_api import sync_playwright,expect
    validate_existing_pricing()
    out=Path("artifacts/notebook");out.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();notes=json.loads(get("/api/notebook"));elapsed=time.monotonic()-start
    actual=json.loads(get("/api/experimental"));expected=build(actual)
    indexed={r["run_id"]:r for r in expected["calibration"]}
    for row in notes["calibration"]:
        assert row["run_id"] in indexed
        assert row["selected"]==indexed[row["run_id"]]["selected"]
        assert row["by_horizon"]==indexed[row["run_id"]]["by_horizon"]
    assert notes["ledger"]["cached_result_reveals_per_task"]==6
    assert notes["scope"]["retrospective_reused_dates"] is True
    assert notes["scope"]["independent_population_interval"] is False
    review=json.loads(get("/notebook-assets/peer-studies.json"))
    assert len(review["sources"])==15 and review["historical_input_use"] is False
    assert all(all(k in s for k in ("question","data","horizon","method","evaluation","result","limitations","availability","adopt","difference","type")) for s in review["sources"])
    assert b"SIL OPEN FONT LICENSE" in get("/notebook-assets/OFL.txt")
    font=get("/notebook-assets/caveat-f84acf2c.ttf")
    assert hashlib.sha1(b"blob "+str(len(font)).encode()+b"\0"+font).hexdigest()=="f84acf2ce2d1b3329b194749530dbaec047e6df6"
    errors=[];checks=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for label,width,height,mobile in (("desktop",1512,1000,False),("mobile",390,844,True),("small-mobile",320,780,True)):
            context=browser.new_context(viewport={"width":width,"height":height},is_mobile=mobile,has_touch=mobile,reduced_motion="reduce")
            page=context.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
            page.route("**/api/notebook",lambda route:route.fulfill(status=200,content_type="application/json",body=json.dumps(notes)))
            page.goto(URL,wait_until="networkidle",timeout=120000)
            page.get_by_role("heading",name="See what compute could cost.",exact=True).wait_for()
            page.evaluate("document.fonts.ready")
            assert page.evaluate("document.fonts.check('24px Caveat')")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),label
            def values():return [float(v) for v in page.locator("[data-point-value]").evaluate_all("(es)=>es.map(e=>e.dataset.value)")]
            original=values()
            page.locator("#pin-point").click()
            assert page.locator(".pinned-note").count()==1
            pinned=page.evaluate("S.pins[0]")
            close(pinned["values"],original)
            assert pinned["kind"]=="assumption_calculation" and pinned["starting_value"]==100
            page.locator("#rate-0").evaluate("(el)=>{el.value='-20';el.dispatchEvent(new Event('input',{bubbles:true}))}")
            assert values()[0]!=original[0]
            close(page.evaluate("S.pins[0].values"),original)
            assert "annual" in page.locator("#notebook-note").inner_text()
            page.locator("#pin-point").click()
            assert page.locator(".pinned-note").count()==2
            page.get_by_text("Add a dollar anchor & spending example",exact=True).click()
            page.get_by_role("button",name="24 months",exact=True).click()
            assert page.locator(".settings details").evaluate("(el)=>el.open")
            page.get_by_role("button",name="Research",exact=True).click()
            page.get_by_role("button",name="Study notes",exact=True).click()
            page.get_by_role("heading",name="Better questions for the results.",exact=True).wait_for()
            assert page.locator("#coverage-audit tbody tr").count()==6
            for r in notes["calibration"]:
                if r["mode"]!="sft":continue
                row=page.locator('[data-diagnostic-run="'+r["run_id"]+'"]')
                assert format(r["selected"]["pinball"],".8f") in row.inner_text()
                assert str(r["selected"]["covered_cells"])+" / "+str(r["selected"]["n_cells"]) in row.inner_text()
            page.get_by_text("Horizon and series details, including completed RL reports",exact=True).click()
            page.get_by_role("button",name="Explore",exact=True).click()
            assert page.locator(".pinned-note").count()==2
            assert page.locator("#time-cursor").input_value()=="24"
            assert page.locator(".settings details").evaluate("(el)=>el.open")
            page.get_by_role("button",name="Submitted forecast",exact=True).click()
            page.get_by_role("button",name="7 days",exact=True).click()
            page.locator("#pin-point").click()
            assert page.locator(".pinned-note").count()==3
            saved=page.evaluate("S.pins[2]")
            assert saved["kind"]=="submitted_forecast" and saved["horizon_days"]==7
            assert saved["forecast_csv_sha256"]=="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
            close(saved["values"],values())
            page.locator("#price-chart").focus();page.keyboard.press("ArrowLeft")
            assert page.locator("#time-cursor").input_value()=="1"
            page.keyboard.press("ArrowLeft")
            assert page.locator("#time-cursor").input_value()=="0"
            assert "day 1" in page.locator("#notebook-note").inner_text().casefold()
            if mobile:
                page.locator("#price-chart").scroll_into_view_if_needed()
                box=page.locator("#price-chart").bounding_box()
                page.touchscreen.tap(box["x"]+box["width"]*.8,box["y"]+box["height"]*.4)
                assert page.locator("#chart-tooltip").is_visible()
            page.locator("#pin-point").click()
            assert page.locator(".pinned-note").count()==3
            assert page.evaluate("S.pins[0].id")==2
            page.locator(".remove-pin").first.click()
            assert page.locator(".pinned-note").count()==2
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),label
            if label!="small-mobile":
                page.evaluate("scrollTo(0,0)");capture(page,out,label+"-benchmark")
                page.get_by_role("button",name="Long-term scenarios",exact=True).click()
                page.get_by_role("button",name="36 months",exact=True).click()
                page.locator("#reset-assumptions").click()
                page.evaluate("scrollTo(0,0)");capture(page,out,label+"-scenarios")
                if not mobile:
                    page.locator("#pinned-notes").scroll_into_view_if_needed();capture(page,out,"desktop-pins")
                    page.get_by_role("button",name="Research",exact=True).click()
                    page.get_by_role("button",name="Study notes",exact=True).click()
                    page.evaluate("scrollTo(0,0)");capture(page,out,"desktop-diagnostics")
            checks.append({"viewport":label,"width":width,"no_overflow":True,"touch":mobile,"keyboard":True,"pin_snapshot_immutable":True,"pin_cap_and_remove":True,"selection_and_disclosures_preserved":True})
            context.close()
        context=browser.new_context(viewport={"width":390,"height":844},reduced_motion="reduce")
        page=context.new_page()
        page.route("**/api/pricing",lambda route:route.fulfill(status=503,content_type="application/json",body='{"error":"validation outage"}'))
        page.goto(URL,wait_until="networkidle")
        page.get_by_role("heading",name="Verified pricing data is temporarily unavailable.",exact=True).wait_for()
        page.unroute("**/api/pricing");page.get_by_role("button",name="Try again",exact=True).click()
        page.locator("#price-chart").wait_for()
        context.close();browser.close()
    assert not errors,errors
    report={"status":"passed","checks":checks,"source_sha":os.environ.get("SOURCE_SHA"),"font_license_and_blob_verified":True,"peer_sources":15,"diagnostic_report_count":len(notes["calibration"]),"diagnostic_api_roundtrip_seconds":round(elapsed,4),"diagnostics_match_public_saved_results":True,"pricing_outage_retry":True,"page_errors":errors,"reduced_motion":True,"recording":False}
    (out/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"diagnostic-snapshot.json").write_text(json.dumps(notes,indent=2)+"\n")
    print("NOTEBOOK_UI_REPORT:"+json.dumps(report),flush=True)
if __name__=="__main__":main()
