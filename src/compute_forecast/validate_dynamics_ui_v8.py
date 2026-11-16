"""PNG-only remote browser validation for the new study and existing price timeline."""
import base64,hashlib,json,math,os
from pathlib import Path
from .price_dynamics_v8 import summarize
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def main():
    from playwright.sync_api import sync_playwright,expect
    out=Path("artifacts/dynamics-ui-v8");out.mkdir(parents=True,exist_ok=True)
    report={"status":"running","recording":False,"widths":[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width,height in ((1512,1050),(390,844),(320,780)):
            context=browser.new_context(viewport={"width":width,"height":height},is_mobile=width<760,has_touch=width<760,reduced_motion="reduce")
            page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(URL,wait_until="domcontentloaded",timeout=90000)
            page.wait_for_selector("#price-chart",timeout=90000)
            page.wait_for_function("() => D8!==null && D!==undefined",timeout=90000)
            health=page.request.get(URL+"/health");assert health.ok
            report["ui_revision"]=health.json()["ui_revision"]
            if os.environ.get("SOURCE_SHA"):assert health.json()["ui_revision"]==os.environ["SOURCE_SHA"]
            response=page.request.get(URL+"/api/price-dynamics-v8");assert response.ok
            v=response.json();assert len(v["cells"])==2432 and v["cohort"]["eligible_cells"]==304
            official=page.request.get(URL+"/files/forecasts.csv");assert official.ok
            assert hashlib.sha256(official.body()).hexdigest()==v["official_export_sha256"]
            page.locator('nav [data-view="research"]').click()
            page.locator('[data-research="dynamics"]').click()
            page.wait_for_selector("#d8-h")
            for method in "ABCDEF":
                actual=page.evaluate("(m)=>d8Stats(m)",method);expected=summarize(v["cells"],method,7)
                for k in ("n","loss","coverage","width","fallbacks"):assert math.isclose(actual[k],expected[k],rel_tol=1e-12,abs_tol=1e-14)
            page.locator('[data-d8-arm="C"]').first.focus()
            page.keyboard.press("Enter")
            assert page.evaluate("D8S.selected")=="C"
            (page.locator("#d8-pin").tap() if width<760 else page.locator("#d8-pin").click());pin=page.evaluate("JSON.stringify(D8S.pins[0])")
            page.locator("#d8-h").select_option("3")
            page.locator("#d8-series").select_option(v["cohort"]["series_ids"][0])
            page.locator("#d8-outcome").select_option("changed")
            assert page.evaluate("JSON.stringify(D8S.pins[0])")==pin
            page.locator("#d8-provenance summary").click()
            page.evaluate("render()")
            assert page.locator("#d8-provenance").evaluate("(e)=>e.open")
            page.locator('nav [data-view="explore"]').click()
            page.wait_for_selector("#price-chart")
            page.locator('nav [data-view="research"]').click()
            assert page.locator("#d8-h").input_value()=="3"
            page.locator("#d8-h").select_option("7");page.locator("#d8-series").select_option("all");page.locator("#d8-outcome").select_option("all")
            assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth"),"Horizontal page overflow"
            page.locator(".d8-header").scroll_into_view_if_needed()
            page.screenshot(path=str(out/(str(width)+".png")),full_page=True)
            assert not errors,errors
            report["widths"].append({"width":width,"no_overflow":True,"metric_agreement":True,"keyboard":True,"pins_immutable":True,"navigation_and_disclosures":True})
            context.close()
        context=browser.new_context(viewport={"width":390,"height":844});page=context.new_page();held=[]
        page.route("**/api/price-dynamics-v8",lambda r:held.append(r))
        page.goto(URL,wait_until="domcontentloaded",timeout=90000);page.wait_for_selector("#price-chart",timeout=15000)
        assert held,"Study request not independent"
        held[0].fulfill(status=503,content_type="application/json",body='{"error":"synthetic unavailable transport"}')
        page.wait_for_function("() => D8Error!==null && D!==undefined",timeout=90000)
        page.locator('nav [data-view="research"]').click();page.locator('[data-research="dynamics"]').click()
        page.wait_for_selector("#d8-retry")
        page.unroute("**/api/price-dynamics-v8");page.locator("#d8-retry").click()
        page.wait_for_selector("#d8-h",timeout=90000)
        report["independent_pricing_loading_error_retry"]=True
        context.close();browser.close()
    report["status"]="passed"
    (out/"report.json").write_text(json.dumps(report,indent=2))
    print("V8_UI_VALIDATION:"+json.dumps(report),flush=True)
    for path in sorted(out.glob("*.png")):
        raw=path.read_bytes();s=base64.b64encode(raw).decode()
        print("V8_PNG_META:"+json.dumps({"name":path.name,"sha256":hashlib.sha256(raw).hexdigest(),"chunks":(len(s)+11999)//12000}),flush=True)
        for i in range(0,len(s),12000):print("V8_PNG:"+json.dumps({"name":path.name,"index":i//12000,"base64":s[i:i+12000]}),flush=True)
if __name__=="__main__":main()
