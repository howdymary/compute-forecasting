"""Verify one cream price canvas against the unchanged published artifacts. PNGs only."""
import base64,hashlib,json,math,os
from pathlib import Path
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
TARGET="gpurentalprices.neocloud_rate_card.H100_SXM_80GB.on_demand.median"
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-11),(a,b)
def main():
    from playwright.sync_api import sync_playwright,expect
    out=Path("artifacts/price-canvas-v11");out.mkdir(parents=True,exist_ok=True)
    report={"status":"running","recording":False,"widths":[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width,height in ((1512,1000),(1920,1080),(390,844),(320,780)):
            context=browser.new_context(viewport={"width":width,"height":height},is_mobile=width<600,has_touch=width<600,reduced_motion="reduce")
            page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(URL+"/terminal",wait_until="domcontentloaded",timeout=90000)
            page.wait_for_function("()=>document.body.dataset.ready==='true' && C11.history!==null",timeout=90000)
            page.evaluate("document.fonts.load('24px Fieldnote')")
            expect(page.locator("#canvas-loading")).not_to_be_visible()
            expect(page.locator("#price-canvas")).to_be_visible()
            health=page.request.get(URL+"/health");assert health.ok;report["ui_revision"]=health.json()["ui_revision"]
            if os.environ.get("SOURCE_SHA"):assert report["ui_revision"]==os.environ["SOURCE_SHA"]
            csv=page.request.get(URL+"/files/forecasts.csv");assert csv.ok
            assert hashlib.sha256(csv.body()).hexdigest()=="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
            assert page.locator("#price-canvas").count()==1 and page.locator("aside").count()==0
            assert page.locator("#terminal-series").count()==0 and page.locator("#rate-controls").count()==0
            assert page.evaluate("getComputedStyle(document.body).backgroundColor")=="rgb(246, 242, 232)"
            assert page.locator("#price-canvas").get_attribute("data-series-id")==TARGET
            source=page.evaluate("JSON.stringify(C11.pricing)")
            history=page.evaluate("observed11()")
            assert sum(int(v) for v in page.locator("[data-history-count]").evaluate_all("(es)=>es.map(e=>e.dataset.historyCount)"))==len(history)
            assert all(p["date"]<="2026-11-06" for p in history)
            for el in page.locator("[data-canvas-forecast]").all():
                h=int(el.get_attribute("data-canvas-forecast"))
                point=page.evaluate("(h)=>series11().forecasts.find(p=>p.horizon_days===h)",h)
                assert point["q10"]>0 and point["q10"]<=point["q50"]<=point["q90"]
                for key in ("q10","q50","q90"):close(el.get_attribute("data-"+key),point[key])
                close(el.get_attribute("cy"),page.evaluate("(v)=>C11.geometry.y(v)",point["q50"]))
            first=page.locator('[data-canvas-forecast="1"]').bounding_box()
            assert first["y"]+first["height"]<height-15,("Forecast point below opening viewport",width,first)
            assert page.evaluate("()=>{const h=history11(),old=h.unit;h.unit='mismatched';const bad=history11()===null;h.unit=old;return bad}")
            assert page.evaluate("()=>{const h=history11();h.points.push({date:'2026-11-07',value:999});try{history11();return false}catch(e){return true}finally{h.points.pop()}}")
            page.locator("#price-canvas").focus();page.keyboard.press("Home")
            close(page.locator("#readout-value").get_attribute("data-exact-value"),history[0]["value"])
            page.keyboard.press("End");point=page.evaluate("series11().forecasts.find(p=>p.horizon_days===7)")
            close(page.locator("#readout-value").get_attribute("data-exact-value"),point["q50"])
            for key in ("q10","q90"):close(page.locator('[data-exact-quantile="'+key+'"]').get_attribute("data-value"),point[key])
            page.locator("#canvas-source summary").click()
            page.locator("#window-month").click()
            assert page.locator("#canvas-source").evaluate("(e)=>e.open")
            assert all(p["t"]>=-29 for p in page.evaluate("C11.points.filter(p=>p.kind==='observed')"))
            assert page.evaluate("JSON.stringify(C11.pricing)")==source
            page.locator("#window-all").click()
            page.locator("#canvas-source").evaluate("(e)=>e.open=false")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
            if width<600:
                chart=page.locator("#price-canvas");box=chart.bounding_box();page.touchscreen.tap(box["x"]+box["width"]*.6,box["y"]+110)
                expect(page.locator("#canvas-tooltip")).to_be_visible()
            page.evaluate("document.activeElement.blur();document.querySelector('#canvas-tooltip').style.display='none';document.querySelector('#canvas-cursor').innerHTML='';scrollTo(0,0)")
            page.screenshot(path=str(out/(str(width)+"-canvas.png")),full_page=True)
            assert not errors,errors
            report["widths"].append({"width":width,"single_series_single_chart":True,"exact_forecasts":True,"metadata_cutoff_gaps":True,"keyboard_touch":True,"disclosure_preserved":True,"no_overflow":True,"opening_forecast_visible":True})
            context.close()
        context=browser.new_context(viewport={"width":1512,"height":1000});page=context.new_page();held=[]
        page.route("**/api/value-v5",lambda r:held.append(r))
        page.goto(URL+"/terminal",wait_until="domcontentloaded",timeout=90000)
        page.wait_for_function("()=>document.body.dataset.ready==='true'",timeout=15000)
        assert held and page.locator("[data-canvas-forecast]").count()==3
        held[0].fulfill(status=503,content_type="application/json",body='{"error":"synthetic history transport outage"}')
        page.wait_for_selector("#retry-history",timeout=10000)
        page.unroute("**/api/value-v5");page.locator("#retry-history").click()
        page.wait_for_function("()=>history11()!==null",timeout=90000)
        report["independent_forecast_loading_history_error_retry"]=True
        # Legacy recording and advanced inspection preserve the old terminal.
        old=page.request.get(URL+"/terminal?capture=1");assert old.ok and b'id="terminal-series"' in old.body()
        advanced=page.request.get(URL+"/terminal/advanced");assert advanced.ok and b'id="terminal-series"' in advanced.body()
        report["advanced_and_existing_capture_compatibility"]=True
        context.close();browser.close()
    report["status"]="passed";(out/"report.json").write_text(json.dumps(report,indent=2))
    print("C11_VALIDATION:"+json.dumps(report),flush=True)
    for path in sorted(out.glob("*.png")):
        raw=path.read_bytes();data=base64.b64encode(raw).decode()
        print("C11_PNG_META:"+json.dumps({"name":path.name,"sha256":hashlib.sha256(raw).hexdigest()}),flush=True)
        for i in range(0,len(data),12000):print("C11_PNG:"+json.dumps({"name":path.name,"index":i//12000,"base64":data[i:i+12000]}),flush=True)
if __name__=="__main__":main()
