"""Quant-dashboard verification. Published artifacts only; PNG screenshots, no recording."""
import base64,hashlib,json,math,os
from pathlib import Path
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-11),(a,b)
def main():
    from playwright.sync_api import sync_playwright,expect
    out=Path("artifacts/terminal-v9");out.mkdir(parents=True,exist_ok=True)
    report={"status":"running","recording":False,"widths":[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width,height in ((1512,1050),(390,844),(320,780)):
            context=browser.new_context(viewport={"width":width,"height":height},is_mobile=width<760,has_touch=width<760,reduced_motion="reduce")
            page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(URL,wait_until="domcontentloaded",timeout=90000);page.wait_for_selector("#price-chart",timeout=90000)
            page.wait_for_function("() => V5!==null && P!==null && T7.points.length>3",timeout=90000)
            health=page.request.get(URL+"/health");assert health.ok
            revision=health.json()["ui_revision"];report["ui_revision"]=revision
            if os.environ.get("SOURCE_SHA"):assert revision==os.environ["SOURCE_SHA"]
            official=page.request.get(URL+"/files/forecasts.csv");assert official.ok
            assert hashlib.sha256(official.body()).hexdigest()=="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
            assert page.locator("header").evaluate("(e)=>getComputedStyle(e).backgroundColor")=="rgb(16, 29, 49)"
            assert page.locator("#price-chart").get_attribute("data-axis-mode")=="fit"
            chart=page.locator("#price-chart");first=page.locator('[data-timeline-forecast="1"]').bounding_box()
            assert first["y"]+first["height"]<height-24,("Opening forecast outside viewport",width,first)
            observed=page.evaluate("t7History().points.at(-1)")
            close(page.locator(".q9-quote [data-q9-value]").first.get_attribute("data-q9-value"),observed["value"])
            for mark in page.locator("[data-timeline-forecast]").all():
                for field in ("q10","q50","q90"):
                    assert float(mark.get_attribute("data-"+field))>0
                q50=float(mark.get_attribute("data-q50"))
                expected=page.evaluate("(v)=>plotGeom.y(v)",q50)
                close(mark.get_attribute("cy"),expected)
                assert page.evaluate("(v)=>plotGeom.y(v)>=plotGeom.T && plotGeom.y(v)<=plotGeom.h-plotGeom.B",q50)
            date_boxes=page.locator(".q9-date-tick").evaluate_all("(es)=>es.map(e=>{const b=e.getBoundingClientRect();return {left:b.left,right:b.right}})")
            assert all(a["right"]+3<=b["left"] for a,b in zip(date_boxes,date_boxes[1:])),("Overlapping date labels",width,date_boxes)
            # Axis changes alter geometry only, never point values, dates or immutable pins.
            chart.focus();page.keyboard.press("Home");page.locator("#pin-point").click()
            pin=page.evaluate("JSON.stringify(S.pins[0])");values=page.locator("[data-timeline-forecast]").evaluate_all("(es)=>es.map(e=>[e.dataset.timelineForecast,e.dataset.q10,e.dataset.q50,e.dataset.q90])")
            page.locator("#q9-scale-zero").click()
            assert page.locator("#price-chart").get_attribute("data-axis-mode")=="zero"
            close(page.evaluate("plotGeom.low"),0)
            close(page.evaluate("plotGeom.y(0)"),page.evaluate("plotGeom.h-plotGeom.B"))
            assert page.locator("[data-timeline-forecast]").evaluate_all("(es)=>es.map(e=>[e.dataset.timelineForecast,e.dataset.q10,e.dataset.q50,e.dataset.q90])")==values
            assert page.evaluate("JSON.stringify(S.pins[0])")==pin
            page.locator("#q9-scale-fit").click()
            assert "FITTED" in page.locator("#q9-axis-note").inner_text()
            page.locator('[data-timeline-range="all"]').click()
            assert int(page.locator("#timeline-observed-path").get_attribute("data-observed-count"))==len(observed and page.evaluate("t7History().points"))
            page.locator("#price-chart").focus();page.keyboard.press("End")
            page.locator("#timeline-provenance").evaluate("(e)=>e.open=true")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
            page.locator("#timeline-provenance").evaluate("(e)=>e.open=false")
            page.evaluate("document.activeElement.blur();document.querySelector('#chart-tooltip').style.display='none';scrollTo(0,0)")
            page.screenshot(path=str(out/(str(width)+"-benchmark.png")))
            page.get_by_role("button",name="Long-term scenarios",exact=True).click()
            assert page.locator(".q9-heading").count()==1
            assert page.locator(".value-small").filter(has_text="New: matching history").count()==0
            vals=page.locator("[data-point-value]").evaluate_all("(es)=>es.map(e=>+e.dataset.value)")
            for a,b in zip(vals,[27.4625,61.4125,115.7625]):close(a,b)
            page.locator("#rate-0").evaluate("(e)=>{e.value='-20';e.dispatchEvent(new Event('input',{bubbles:true}))}")
            close(page.locator("[data-point-value]").first.get_attribute("data-value"),51.2)
            page.get_by_role("button",name="Reset to published assumptions ↺",exact=True).click()
            assert page.evaluate("JSON.stringify(S.pins[0])")==pin
            if width in (1512,390):
                page.evaluate("scrollTo(0,0)");page.screenshot(path=str(out/(str(width)+"-scenarios.png")),full_page=True)
            page.get_by_role("button",name="Research",exact=True).click();page.locator('[data-research="dynamics"]').click()
            page.wait_for_selector("#d8-h",timeout=90000)
            assert page.evaluate("D8.cells.length")==2432
            if width in (1512,390):
                page.evaluate("scrollTo(0,0)");page.screenshot(path=str(out/(str(width)+"-research.png")))
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
            assert not errors,errors
            report["widths"].append({"width":width,"opening_chart_visible":True,"exact_values_after_axis_change":True,"source_bound_quote_strip":True,"scenario_math":True,"pins_immutable":True,"no_overflow":True,"keyboard":True})
            context.close()
        browser.close()
    report["status"]="passed";(out/"report.json").write_text(json.dumps(report,indent=2))
    print("Q9_VALIDATION:"+json.dumps(report),flush=True)
    for path in sorted(out.glob("*.png")):
        raw=path.read_bytes();s=base64.b64encode(raw).decode()
        print("Q9_PNG_META:"+json.dumps({"name":path.name,"sha256":hashlib.sha256(raw).hexdigest(),"chunks":(len(s)+11999)//12000}),flush=True)
        for i in range(0,len(s),12000):print("Q9_PNG:"+json.dumps({"name":path.name,"index":i//12000,"base64":s[i:i+12000]}),flush=True)
if __name__=="__main__":main()
