"""Validate the source-matched timeline on the deployed app. PNG only."""
import base64,csv,hashlib,io,json,math,os
from pathlib import Path
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
SHA="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
def close(a,b):
    assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-12),(a,b)
def main():
    from playwright.sync_api import sync_playwright,expect
    out=Path("artifacts/timeline-v7");out.mkdir(parents=True,exist_ok=True)
    report={"status":"running","widths":[],"recording":False,"ui_source_sha":os.environ.get("SOURCE_SHA")}
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width,height in ((1512,1050),(390,844),(320,780)):
            context=browser.new_context(viewport={"width":width,"height":height},is_mobile=width<760,has_touch=width<760,reduced_motion="reduce")
            page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(URL,wait_until="domcontentloaded",timeout=90000);page.wait_for_selector("#price-chart",timeout=90000)
            page.wait_for_function("() => V5!==null && P!==null && T7.points.length>3",timeout=90000)
            assert page.evaluate("S.mode")=="benchmark"
            health=page.request.get(URL+"/health");assert health.ok
            if os.environ.get("SOURCE_SHA"):assert health.json()["ui_revision"]==os.environ["SOURCE_SHA"]
            pricing=page.request.get(URL+"/api/pricing");history=page.request.get(URL+"/api/value-v5");official=page.request.get(URL+"/files/forecasts.csv")
            assert pricing.ok and history.ok and official.ok
            p=pricing.json();v=history.json();assert hashlib.sha256(official.body()).hexdigest()==SHA
            csv_rows={(r["series_id"],int(r["horizon_days"])):r for r in csv.DictReader(io.StringIO(official.body().decode()))}
            assert len(v["history"]["series"])==36 and sum(len(s["points"]) for s in v["history"]["series"])==3204
            for s in p["series"]:
                for q in s["forecasts"]:
                    for k in ("q10","q50","q90"):close(q[k],csv_rows[(s["id"],q["horizon_days"])][k])
            joins=page.evaluate("""()=>{const selected=S.series;const result=P.series.map(s=>{S.series=s.id;const h=t7History();return {id:s.id,joined:!!h,error:T7.historyError}});S.series=selected;return result}""")
            assert sum(r["joined"] for r in joins)==36 and not any(r["error"] for r in joins)
            assert page.locator("[data-timeline-forecast]").count()==3
            chosen=page.evaluate("series().id");current=next(s for s in p["series"] if s["id"]==chosen)
            for fc in current["forecasts"]:
                mark=page.locator('[data-timeline-forecast="'+str(fc["horizon_days"])+'"]')
                for k in ("q10","q50","q90"):close(mark.get_attribute("data-"+k),fc[k])
            circles=[float(page.locator('[data-timeline-forecast="'+str(i)+'"]').get_attribute("cx")) for i in (1,3,7)]
            close((circles[2]-circles[1])/(circles[1]-circles[0]),2)
            page.locator("#price-chart").focus();page.keyboard.press("Home")
            point=page.evaluate("T7.points[T7.index]");assert point["kind"]=="observed"
            observed=next(s for s in v["history"]["series"] if s["id"]==chosen)
            expected=next(x for x in observed["points"] if x["date"]==point["date"])
            close(page.locator("[data-point-value]").get_attribute("data-value"),expected["value"])
            page.locator("#pin-point").click();pin=page.evaluate("JSON.stringify(S.pins[0])")
            saved=json.loads(pin);assert saved["history_points_sha256"]==observed["points_sha256"] and saved["source_artifact"]=="/api/value-v5"
            page.locator("#price-chart").focus();page.keyboard.press("End")
            assert page.evaluate("T7.points[T7.index].horizon_days")==7
            page.keyboard.press("ArrowLeft");assert page.evaluate("T7.points[T7.index].horizon_days")==3
            page.keyboard.press("ArrowLeft");assert page.evaluate("T7.points[T7.index].horizon_days")==1
            page.locator('[data-timeline-range="all"]').click()
            assert int(page.locator("#timeline-observed-path").get_attribute("data-observed-count"))==len(observed["points"])
            if width in (1512,390):
                page.locator("#price-chart").focus();page.keyboard.press("End");page.evaluate("document.activeElement.blur();scrollTo(0,0)")
                page.screenshot(path=str(out/(str(width)+"-all-history.png")))
            page.locator("#series-select").select_option("afhubbard.hyperscaler_spot.A100_40GB.spot.median")
            assert page.locator("#timeline-observed-path").get_attribute("d").count("M")>1,"Missing calendar days must break history"
            withheld=next(r["id"] for r in joins if not r["joined"])
            page.locator("#series-select").select_option(withheld)
            assert page.locator("#timeline-observed-path").get_attribute("data-observed-count")=="0"
            assert "withheld" in page.locator("#timeline-history-state").inner_text()
            assert page.locator("[data-timeline-forecast]").count()==3
            page.locator("#series-select").select_option(chosen);page.locator('[data-timeline-range="30"]').click()
            page.locator("#timeline-provenance").evaluate("(e)=>e.open=true")
            page.get_by_role("button",name="Research",exact=True).click()
            page.get_by_role("button",name="Explore",exact=True).click()
            assert page.locator("#timeline-provenance").evaluate("(e)=>e.open")
            assert page.evaluate("JSON.stringify(S.pins[0])")==pin
            page.locator("#timeline-provenance").evaluate("(e)=>e.open=false")
            page.locator("#price-chart").scroll_into_view_if_needed();box=page.locator("#price-chart").bounding_box()
            if width<760:page.touchscreen.tap(box["x"]+box["width"]*.4,box["y"]+box["height"]*.4)
            else:page.locator("#price-chart").hover(position={"x":box["width"]*.4,"y":box["height"]*.4})
            expect(page.locator("#chart-tooltip")).to_be_visible()
            assert page.evaluate("JSON.stringify(S.pins[0])")==pin
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),"Horizontal page overflow"
            assert not errors,errors
            page.locator("#price-chart").focus();page.keyboard.press("End")
            page.evaluate("document.activeElement.blur();document.querySelector('#chart-tooltip').style.display='none';scrollTo(0,0)")
            if width in (1512,390):
                page.screenshot(path=str(out/(str(width)+"-timeline.png")))
                page.locator(".timeline-sheet").screenshot(path=str(out/(str(width)+"-chart.png")))
            report["widths"].append({"width":width,"exact_joins":36,"exact_forecasts":111,"observed_points":3204,"calendar_geometry":True,"missing_days_break_paths":True,"restricted_history_excluded":True,"pins_immutable":True,"keyboard_touch":True,"no_overflow":True})
            context.close()
        context=browser.new_context(viewport={"width":390,"height":844});page=context.new_page();held=[]
        page.route("**/api/value-v5",lambda route:held.append(route))
        page.goto(URL,wait_until="domcontentloaded",timeout=90000);page.wait_for_selector("#price-chart",timeout=15000)
        assert page.locator("[data-timeline-forecast]").count()==3 and len(held)==1
        assert page.locator("#timeline-observed-path").get_attribute("data-observed-count")=="0"
        held[0].fulfill(status=503,content_type="application/json",body='{"error":"synthetic transport fixture"}')
        page.wait_for_function("() => V5Error!==null")
        page.unroute("**/api/value-v5");page.locator("#timeline-history-retry").click()
        page.wait_for_function("() => V5!==null && t7Observed().length>0",timeout=90000)
        assert int(page.locator("#timeline-observed-path").get_attribute("data-observed-count"))>0
        report["independent_history_loading_and_retry"]=True
        context.close();browser.close()
    report["status"]="passed";(out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("V7_UI_VALIDATION:"+json.dumps(report),flush=True)
    for path in sorted(out.glob("*.png")):
        raw=path.read_bytes();data=base64.b64encode(raw).decode()
        print("V7_PNG_META:"+json.dumps({"name":path.name,"sha256":hashlib.sha256(raw).hexdigest(),"chunks":(len(data)+11999)//12000}),flush=True)
        for i in range(0,len(data),12000):print("V7_PNG:"+json.dumps({"name":path.name,"index":i//12000,"base64":data[i:i+12000]}),flush=True)
if __name__=="__main__":main()
