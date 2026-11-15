"""Remote notebook interaction, provenance and accessibility checks. PNGs only."""
from __future__ import annotations
import base64,hashlib,json,math,os,re,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.request import urlopen
from .notebook_diagnostics import build
from .validate_pricing_ui import main as validate_existing_pricing
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def get(path):
    from .remote_validation_http import get_bytes
    return get_bytes(path)
def close(a,b):
    assert len(a)==len(b) and all(math.isclose(x,y,rel_tol=1e-10,abs_tol=1e-12) for x,y in zip(a,b)),(a,b)
def contrast_ratio(foreground,background):
    def luminance(color):
        channels=[float(n)/255 for n in re.findall(r"[0-9.]+",color)[:3]]
        if len(channels)!=3:raise ValueError("Unexpected computed color")
        linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in channels]
        return sum(v*w for v,w in zip(linear,(.2126,.7152,.0722)))
    a,b=sorted((luminance(foreground),luminance(background)))
    return (b+.05)/(a+.05)
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
    concurrent_paths=["/notebook-assets/caveat-f84acf2c.ttf","/files/forecasts.csv","/api/pricing","/api/notebook"]*3
    def concurrent_probe(path):
        started=time.monotonic()
        try:
            raw=get(path);row={"path":path,"status":200,"bytes":len(raw),"seconds":round(time.monotonic()-started,4)}
        except Exception as error:
            raw=None;row={"path":path,"error":type(error).__name__+": "+str(error),"seconds":round(time.monotonic()-started,4)}
        print("NOTEBOOK_CONCURRENT_HTTP:"+json.dumps(row),flush=True)
        return path,raw,row
    concurrent_results=[];concurrent_observations=[]
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures=[executor.submit(concurrent_probe,path) for path in concurrent_paths]
        for future in as_completed(futures):
            path,raw,row=future.result();concurrent_results.append((path,raw));concurrent_observations.append(row)
    assert all(raw is not None for _,raw in concurrent_results),concurrent_observations
    from .remote_validation_http import snapshot
    assert snapshot()["maximum_observed_in_flight"]==8
    for path,raw in concurrent_results:
        assert raw
        if path.endswith(".csv"):
            assert hashlib.sha256(raw).hexdigest()=="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
        elif path.endswith(".ttf"):assert raw==font
        elif path=="/api/notebook":assert json.loads(raw)["kind"]=="descriptive_audit_of_saved_results"
        else:assert json.loads(raw)["schema_version"]==1
    errors=[];checks=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        independent=browser.new_context(viewport={"width":390,"height":844},reduced_motion="reduce")
        first=independent.new_page();held=[]
        first.route("**/api/release",lambda route:held.append(route))
        first.route("**/api/notebook",lambda route:held.append(route))
        first.goto(URL,wait_until="domcontentloaded",timeout=90000)
        first.locator("#price-chart").wait_for(timeout=15000)
        first.locator("#pin-point").click()
        assert first.locator(".pinned-note").count()==1
        assert len(held)==2
        frozen_release=get("/api/release").decode()
        for route in held:
            route.fulfill(status=200,content_type="application/json",body=json.dumps(notes) if route.request.url.endswith("/api/notebook") else frozen_release)
        first.get_by_role("button",name="Research",exact=True).click()
        first.get_by_role("button",name="Study notes",exact=True).click()
        first.get_by_role("heading",name="Better questions for the results.",exact=True).wait_for()
        first.get_by_role("button",name="Explore",exact=True).click()
        assert first.locator(".pinned-note").count()==1
        independent.close()
        for label,width,height,mobile in (("desktop",1512,1000,False),("mobile",390,844,True),("small-mobile",320,780,True)):
            context=browser.new_context(viewport={"width":width,"height":height},is_mobile=mobile,has_touch=mobile,reduced_motion="reduce")
            page=context.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
            page.route("**/api/notebook",lambda route:route.fulfill(status=200,content_type="application/json",body=json.dumps(notes)))
            page.goto(URL,wait_until="domcontentloaded",timeout=90000)
            page.locator("#price-chart").wait_for(timeout=90000)
            page.get_by_role("heading",name="See what compute could cost.",exact=True).wait_for()
            loaded_faces=page.evaluate("document.fonts.load('24px Caveat','Notes on the price of compute').then(faces=>faces.length)")
            assert loaded_faces>=1, "The self-hosted handwriting face did not load"
            assert page.evaluate("document.fonts.check('24px Caveat')")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),label
            axis_color=page.locator("#price-chart text").first.evaluate("(el)=>getComputedStyle(el).fill")
            plot_background=page.locator(".plotpanel").evaluate("(el)=>getComputedStyle(el).backgroundColor")
            axis_contrast=contrast_ratio(axis_color,plot_background)
            assert axis_contrast>=4.5,axis_contrast
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
            assert format(values()[1],".1f") in page.locator("#notebook-note").inner_text()
            page.locator("#pin-point").click()
            assert page.locator(".pinned-note").count()==2
            page.get_by_text("Add a dollar anchor & spending example",exact=True).click()
            page.get_by_role("button",name="24 months",exact=True).click()
            assert page.locator(".settings details").evaluate("(el)=>el.open")
            page.get_by_role("button",name="Research",exact=True).click()
            page.get_by_role("button",name="Study notes",exact=True).click()
            page.get_by_role("heading",name="Better questions for the results.",exact=True).wait_for()
            assert page.locator("#coverage-audit tbody tr").count()==6
            first=next(r for r in notes["calibration"] if r["mode"]=="sft")
            assert str(first["reference"]["covered_cells"])+" / "+str(first["reference"]["n_cells"]) in page.locator("#coverage-reference").inner_text()
            assert "SFT runs" in page.locator("#feedback-interpretation").inner_text()
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
            checks.append({"viewport":label,"width":width,"no_overflow":True,"axis_text_contrast":round(axis_contrast,3),"touch":mobile,"keyboard":True,"pin_snapshot_immutable":True,"pin_cap_and_remove":True,"selection_and_disclosures_preserved":True})
            context.close()
        context=browser.new_context(viewport={"width":390,"height":844},reduced_motion="reduce")
        page=context.new_page()
        page.route("**/api/pricing",lambda route:route.fulfill(status=503,content_type="application/json",body='{"error":"validation outage"}'))
        page.goto(URL,wait_until="domcontentloaded",timeout=90000)
        page.get_by_role("heading",name="Verified pricing data is temporarily unavailable.",exact=True).wait_for()
        page.unroute("**/api/pricing");page.get_by_role("button",name="Try again",exact=True).click()
        page.locator("#price-chart").wait_for()
        context.close();browser.close()
    assert not errors,errors
    report={"status":"passed","checks":checks,"source_sha":os.environ.get("SOURCE_SHA"),"font_license_and_blob_verified":True,"explicit_loaded_font_faces":loaded_faces,"concurrent_asset_and_data_requests":len(concurrent_results),"concurrent_request_observations":concurrent_observations,"peer_sources":15,"diagnostic_report_count":len(notes["calibration"]),"diagnostic_api_roundtrip_seconds":round(elapsed,4),"diagnostics_match_public_saved_results":True,"pricing_outage_retry":True,"primary_chart_independent_of_research_requests":True,"http_transport":snapshot(),"page_errors":errors,"reduced_motion":True,"recording":False}
    (out/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"diagnostic-snapshot.json").write_text(json.dumps(notes,indent=2)+"\n")
    print("NOTEBOOK_UI_REPORT:"+json.dumps(report),flush=True)
if __name__=="__main__":main()
