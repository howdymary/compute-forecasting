"""Source-to-screen validation of the dark pricing terminal; PNGs only."""
import base64,hashlib,json,math,os
from pathlib import Path
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-10),(a,b)
def main():
    from playwright.sync_api import sync_playwright,expect
    out=Path("artifacts/terminal-v10");out.mkdir(parents=True,exist_ok=True)
    report={"status":"running","recording":False,"widths":[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width,height in ((1920,1080),(1512,1050),(390,844),(320,780)):
            context=browser.new_context(viewport={"width":width,"height":height},is_mobile=width<600,has_touch=width<600,reduced_motion="reduce")
            page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(URL+"/terminal",wait_until="domcontentloaded",timeout=90000)
            page.wait_for_function("() => document.body.dataset.ready==='true' && V10!==null",timeout=90000)
            health=page.request.get(URL+"/health");assert health.ok
            report["ui_revision"]=health.json()["ui_revision"]
            if os.environ.get("SOURCE_SHA"):assert report["ui_revision"]==os.environ["SOURCE_SHA"]
            csv=page.request.get(URL+"/files/forecasts.csv");assert csv.ok
            assert hashlib.sha256(csv.body()).hexdigest()=="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
            assert page.locator("#terminal-series option").count()==37
            assert page.locator(".top").evaluate("(e)=>getComputedStyle(e).backgroundColor")=="rgb(16, 23, 33)"
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
            raw=page.evaluate("JSON.stringify(P10)")
            observed=page.evaluate("observed10()")
            assert sum(int(x) for x in page.locator("[data-history-segment]").evaluate_all("(es)=>es.map(e=>e.dataset.historySegment)"))==len(observed)
            for mark in page.locator("[data-terminal-forecast]").all():
                horizon=int(mark.get_attribute("data-terminal-forecast"))
                p=page.evaluate("(h)=>s10().forecasts.find(p=>p.horizon_days===h)",horizon)
                assert p["q10"]<=p["q50"]<=p["q90"]
                for key in ("q10","q50","q90"):close(mark.get_attribute("data-"+key),p[key])
                close(mark.get_attribute("cy"),page.evaluate("(v)=>G10.y(v)",p["q50"]))
            # Identity mismatch excludes history; post-cutoff contamination is refused.
            assert page.evaluate("() => {const h=h10(),old=h.unit;h.unit='bad unit';const excluded=h10()===null;h.unit=old;return excluded}")
            assert page.evaluate("() => {const h=h10();h.points.push({date:'2026-11-07',value:999});try{h10();return false}catch(e){return String(e).includes('cutoff')}finally{h.points.pop()}}")
            page.locator("#terminal-chart").focus();page.keyboard.press("Home")
            assert page.evaluate("T10.index")==0
            page.locator("#terminal-pin").click();pin=page.evaluate("JSON.stringify(T10.pins[0])")
            page.locator("#axis-toggle").click();close(page.evaluate("G10.lo"),0)
            page.locator("#axis-toggle").click()
            page.locator('[data-range="30"]').click();page.locator('[data-range="all"]').click()
            assert page.evaluate("JSON.stringify(P10)")==raw
            page.locator("#terminal-chart").focus();page.keyboard.press("End")
            if width<600:
                box=page.locator("#terminal-chart").bounding_box()
                page.touchscreen.tap(box["x"]+box["width"]*.6,box["y"]+80)
                expect(page.locator("#terminal-tooltip")).to_be_visible()
            page.evaluate("document.querySelector('#terminal-tooltip').style.display='none';scrollTo(0,0)")
            page.screenshot(path=str(out/(str(width)+"-benchmark.png")))
            page.locator("#tab-scenario").click()
            for i,expected in enumerate((27.4625,61.4125,115.7625)):close(page.evaluate("(i)=>value10(i,36)",i),expected)
            page.locator("#terminal-rate-0").evaluate("(e)=>{e.value='-20';e.dispatchEvent(new Event('input',{bubbles:true}))}")
            close(page.evaluate("value10(0,36)"),51.2)
            page.locator("#scenario-basis").select_option("usd")
            close(page.evaluate("anchor10()"),page.evaluate("h10().points.at(-1).value"))
            page.locator("#scenario-hours").fill("2400");page.locator("#scenario-hours").dispatch_event("input")
            close(page.evaluate("value10(1,36)*T10.hours"),page.evaluate("h10().points.at(-1).value*Math.pow(.85,3)*2400"))
            page.locator("#scenario-reset").click()
            assert page.evaluate("JSON.stringify(T10.pins[0])")==pin
            assert page.evaluate("JSON.stringify(P10)")==raw
            if width in (1920,390):
                page.evaluate("scrollTo(0,0)");page.screenshot(path=str(out/(str(width)+"-scenarios.png")),full_page=width<600)
            page.locator("#scenario-instrument").select_option("resale")
            assert page.evaluate("T10.basis")=="index"
            assert page.locator("#scenario-basis option[value=usd]").is_disabled()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
            assert not errors,errors
            report["widths"].append({"width":width,"exact_forecasts":True,"history_identity_cutoff_gaps":True,"scenario_math":True,"pin_immutability":True,"keyboard_touch":True,"no_overflow":True})
            context.close()
        context=browser.new_context(viewport={"width":1512,"height":1050});page=context.new_page();held=[]
        page.route("**/api/value-v5",lambda r:held.append(r))
        page.goto(URL+"/terminal",wait_until="domcontentloaded",timeout=90000)
        page.wait_for_function("()=>document.body.dataset.ready==='true'",timeout=15000)
        assert page.locator("[data-terminal-forecast]").count()==3 and held
        held[0].fulfill(status=503,content_type="application/json",body='{"error":"synthetic transport outage"}')
        page.wait_for_function("()=>V10Error!==null",timeout=10000)
        assert "History unavailable" in page.locator("#history-status").inner_text()
        page.locator("#tab-scenario").click()
        close(page.evaluate("value10(1,36)"),61.4125)
        report["independent_forecast_loading_and_history_failure"]=True
        context.close();browser.close()
    report["status"]="passed";(out/"report.json").write_text(json.dumps(report,indent=2))
    print("T10_VALIDATION:"+json.dumps(report),flush=True)
    for p in sorted(out.glob("*.png")):
        data=p.read_bytes();s=base64.b64encode(data).decode()
        print("T10_PNG_META:"+json.dumps({"name":p.name,"sha256":hashlib.sha256(data).hexdigest()}),flush=True)
        for i in range(0,len(s),12000):print("T10_PNG:"+json.dumps({"name":p.name,"index":i//12000,"base64":s[i:i+12000]}),flush=True)
if __name__=="__main__":main()
