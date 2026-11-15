"""Public browser validation only. No media recording or private account access."""
import csv,hashlib,io,json,math,os,urllib.request
from pathlib import Path
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def get(path):return urllib.request.urlopen(URL+path,timeout=90).read()
def main():
    from playwright.sync_api import sync_playwright,expect
    out=Path("artifacts");out.mkdir(exist_ok=True)
    p=json.loads(get("/api/pricing"));health=json.loads(get("/health"));expected=os.environ.get("SOURCE_SHA")
    assert not expected or health["ui_revision"]==expected
    csv_bytes=get("/files/forecasts.csv")
    assert hashlib.sha256(csv_bytes).hexdigest()==p["forecast_csv_sha256"]
    rows={(r["series_id"],int(r["horizon_days"])):r for r in csv.DictReader(io.StringIO(csv_bytes.decode()))}
    for s in p["series"]:
        for point in s["forecasts"]:
            assert all(point[q]==float(rows[(s["id"],point["horizon_days"])][q]) for q in ("q10","q50","q90"))
    errors=[];failures=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        context=browser.new_context(viewport={"width":1512,"height":982},reduced_motion="reduce")
        page=context.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("response",lambda r:failures.append({"url":r.url,"status":r.status}) if r.url.startswith(URL) and r.status>=400 and not r.url.endswith("/favicon.ico") else None)
        page.goto(URL,wait_until="domcontentloaded",timeout=90000)
        page.locator("#price-chart").wait_for(timeout=90000)
        page.get_by_role("heading",name="See what compute could cost.",exact=True).wait_for()
        assert page.locator("#series-select option").count()==37
        def values():return [float(v) for v in page.locator("[data-point-value]").evaluate_all("(els)=>els.map(e=>e.dataset.value)")]
        def close(a,b):assert all(math.isclose(x,y,rel_tol=1e-10) for x,y in zip(a,b)),(a,b)
        close(values(),[27.4625,61.4125,115.7625])
        page.screenshot(path=str(out/"explore-desktop.png"),full_page=True)
        page.locator("#rate-0").evaluate("(el)=>{el.value='-20';el.dispatchEvent(new Event('input',{bubbles:true}))}")
        close(values(),[51.2,61.4125,115.7625])
        page.get_by_role("button",name="Reset to published assumptions ↺",exact=True).click()
        close(values(),[27.4625,61.4125,115.7625])
        page.get_by_role("button",name="24 months",exact=True).click()
        close(values(),[42.25,72.25,110.25])
        page.locator("#price-chart").focus();page.keyboard.press("ArrowLeft")
        assert page.locator("#time-cursor").input_value()=="23"
        expect(page.locator("#chart-tooltip")).to_be_visible()
        assert "Assumption calculation" in page.locator("#chart-tooltip").inner_text()
        assert "Index" in page.locator("#chart-tooltip").inner_text()
        tip=page.locator("#chart-tooltip").bounding_box();plot=page.locator("#price-chart").bounding_box()
        assert tip["x"]>=plot["x"]-1 and tip["x"]+tip["width"]<=plot["x"]+plot["width"]+1
        page.locator("#instrument").select_option("resale")
        close(values(),[100*.6**(23/12),100*.75**(23/12),100*.9**(23/12)])
        assert page.locator("#anchor").count()==0
        page.locator("#instrument").select_option("rental")
        page.get_by_role("button",name="36 months",exact=True).click()
        page.get_by_text("Add a dollar anchor & spending example",exact=True).click()
        page.locator("#anchor").fill("2.5");page.locator("#basis").select_option("usd")
        close(values(),[.6865625,1.5353125,2.8940625])
        assert page.get_by_text("Your dollar anchor is an assumption",exact=False).count()==1
        selected=page.locator("#series-select").input_value()
        page.get_by_role("button",name="Research",exact=True).click()
        page.get_by_role("heading",name="Did training improve experiment selection?",exact=True).wait_for()
        assert page.get_by_text("2.68% worse",exact=True).count()==1
        page.get_by_role("button",name="Representations",exact=True).click()
        assert page.locator("#horizons tbody tr").count()==3
        page.get_by_role("button",name="Policy traces",exact=True).click()
        for _ in range(4):page.get_by_role("button",name="Next experiment →",exact=True).click()
        assert page.get_by_text("6 / 6 trials revealed",exact=True).count()==1
        page.get_by_role("button",name="Evidence & memory",exact=True).click()
        page.get_by_role("heading",name="Research, with named authors.",exact=True).wait_for()
        page.get_by_role("button",name="Explore",exact=True).click()
        assert page.locator("#series-select").input_value()==selected
        assert page.locator("#anchor").input_value()=="2.5"
        page.get_by_role("button",name="Submitted forecast",exact=True).click()
        points=next(s for s in p["series"] if s["id"]==selected)["forecasts"]
        close(values(),[points[2][q] for q in ("q10","q50","q90")])
        assert "History before the cutoff is not published" in page.locator("#chart-note").inner_text()
        options=page.locator("#compare option").evaluate_all("(es)=>es.map(e=>e.value)")
        current=next(s for s in p["series"] if s["id"]==selected)
        assert set(options[1:])=={s["id"] for s in p["series"] if s["id"]!=selected and s["comparison_key"]==current["comparison_key"]}
        if len(options)>1:page.locator("#compare").select_option(options[1])
        page.screenshot(path=str(out/"benchmark-desktop.png"),full_page=True)
        page.get_by_role("button",name="3 days",exact=True).click()
        close(values(),[points[1][q] for q in ("q10","q50","q90")])
        page.locator("#price-chart").focus();page.keyboard.press("ArrowLeft")
        close(values(),[points[0][q] for q in ("q10","q50","q90")])
        page.locator("#series-select").select_option(p["series"][0]["id"])
        assert page.locator("#compare").input_value()==""
        page.get_by_role("button",name="Methods",exact=True).click()
        page.get_by_role("heading",name="Know what the line means.",exact=True).wait_for()
        page.get_by_role("button",name="Downloads",exact=True).click()
        assert page.locator('a[href="/files/forecasts.csv"]').count()==1
        mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,reduced_motion="reduce")
        phone=mobile.new_page();phone.on("pageerror",lambda e:errors.append(str(e)))
        phone.goto(URL,wait_until="domcontentloaded",timeout=90000)
        phone.locator("#price-chart").wait_for(timeout=90000)
        phone.get_by_role("heading",name="See what compute could cost.",exact=True).wait_for()
        assert phone.evaluate("document.documentElement.scrollWidth<=innerWidth+2"),"Mobile overflow"
        phone.locator("#price-chart").scroll_into_view_if_needed()
        box=phone.locator("#price-chart").bounding_box();phone.touchscreen.tap(box["x"]+box["width"]*.6,box["y"]+100)
        assert int(phone.locator("#time-cursor").input_value())<36
        expect(phone.locator("#chart-tooltip")).to_be_visible()
        phone.screenshot(path=str(out/"explore-mobile.png"),full_page=True)
        phone.get_by_role("button",name="Submitted forecast",exact=True).click()
        assert phone.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
        phone.screenshot(path=str(out/"benchmark-mobile.png"),full_page=True)
        mobile.close();context.close();browser.close()
    assert not errors,errors
    assert not failures,failures
    report={"status":"passed","ui_revision":health["ui_revision"],"pricing_sha":p["code_sha"],"series_verified":37,"forecast_points_verified":111,"official_csv_sha256":p["forecast_csv_sha256"],"history_published":False,"scenario_endpoints_match":True,"validated_views":["Explore scenarios","Archived forecast","Research results","Representations","Recorded policy traces","Evidence and memory","Methods","Downloads"],"mobile_width":390,"touch_and_keyboard_checked":True,"page_errors":errors,"failed_public_requests":failures,"media_recording":False}
    (out/"pricing-ui-validation.json").write_text(json.dumps(report,indent=2)+"\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write("# Pricing UI validation passed\n\n~~~json\n"+json.dumps(report,indent=2)+"\n~~~\n")
if __name__=="__main__":main()
