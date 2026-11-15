"""Remote browser assertions and PNG inspection evidence; no video capture."""
from __future__ import annotations
import asyncio,base64,hashlib,json,os
from pathlib import Path
from urllib.request import urlopen
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
async def run():
    from playwright.async_api import async_playwright
    out=Path("artifacts/v2-ui");out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
    def get(path):return urlopen(URL+path,timeout=90).read()
    raw=get("/api/experimental");data=json.loads(raw)
    assert data["schema_version"]==2 and b"tinker://" not in raw and b"TINKER_API_KEY" not in raw
    assert hashlib.sha256(get("/files/forecasts.csv")).hexdigest()=="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
    release=json.loads(get("/api/release"));assert release["development"]["actual_training_updates"]==50
    numerical=[r for r in data.get("forecasting",{}).get("rows",[]) if r["phase"]=="development"]
    assert len(numerical)==42
    for r in numerical:
        assert r["n_cells"]>0 and 0<=r["coverage"]<=1
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        for label,width,height in (("desktop",1440,1000),("mobile",390,844)):
            context=await browser.new_context(viewport={"width":width,"height":height},device_scale_factor=1,reduced_motion="reduce")
            page=await context.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
            # Hold one genuine server response stable while testing interactions.
            await page.route("**/api/experimental",lambda route:route.fulfill(status=200,content_type="application/json",body=raw))
            await page.goto(URL+"/experimental",wait_until="networkidle",timeout=120000)
            await page.locator("#question").wait_for()
            assert await page.locator("h1").inner_text()=="Can a researcher learn\nto research?"
            assert await page.evaluate("document.documentElement.scrollWidth<=window.innerWidth"),label+" overflow"
            await page.locator("#question").select_option("composition")
            assert await page.locator("#question").input_value()=="composition"
            await page.locator("#stage").select_option("rl");await page.locator("#stage").select_option("sft")
            await page.locator("#phase").select_option("development");await page.locator("#horizon").select_option("3")
            assert await page.locator("#phase").input_value()=="development" and await page.locator("#horizon").input_value()=="3"
            table=page.locator("section").filter(has=page.locator("#phase")).locator("tbody tr").first
            expected=min(numerical,key=lambda r:r["by_horizon"]["3"]["pinball"])
            assert expected["config"]["id"] in await table.inner_text()
            assert format(expected["by_horizon"]["3"]["pinball"],".8f") in await table.inner_text()
            await page.evaluate("load()")
            assert await page.locator("#question").input_value()=="composition"
            assert await page.locator("#phase").input_value()=="development"
            assert await page.locator("#horizon").input_value()=="3"
            await page.locator("#question").focus();await page.keyboard.press("Tab")
            assert await page.evaluate("document.activeElement!==document.body")
            await page.evaluate("window.scrollTo(0,0)")
            image=await page.screenshot(path=str(out/(label+".png")),full_page=False)
            for n in range(0,len(base64.b64encode(image)),2048):
                print("V2_SCREENSHOT:"+label+":"+str(n//2048)+":"+base64.b64encode(image)[n:n+2048].decode(),flush=True)
            for section_name,index in (("learning",0),("activity",1),("forecasting",2),("evidence",3)):
                section=page.locator("section").nth(index)
                await section.evaluate("(el)=>el.scrollIntoView({block:'start',behavior:'instant'})")
                capture=await page.screenshot(path=str(out/(label+"-"+section_name+".png")),full_page=False)
                if section_name in ("learning","activity"):
                    encoded=base64.b64encode(capture)
                    for n in range(0,len(encoded),2048):
                        print("V2_SCREENSHOT:"+label+"-"+section_name+":"+str(n//2048)+":"+encoded[n:n+2048].decode(),flush=True)
            await context.close();checks.append({"viewport":label,"width":width,"height":height,"no_page_overflow":True,"selectors":True,"keyboard":True,"reduced_motion":True})
        failure=await browser.new_context(viewport={"width":390,"height":844})
        page=await failure.new_page()
        await page.route("**/api/experimental",lambda route:route.fulfill(status=503,content_type="application/json",body='{"error":"validation outage"}'))
        await page.goto(URL+"/experimental",wait_until="networkidle")
        await page.get_by_role("alert").wait_for();assert await page.locator("#retry").is_visible()
        await page.unroute("**/api/experimental")
        await page.route("**/api/experimental",lambda route:route.fulfill(status=200,content_type="application/json",body=raw))
        await page.locator("#retry").click();await page.locator("#question").wait_for()
        await failure.close();checks.append({"error_retry_recovery":True,"real_response_frozen_for_assertions":True,"numerical_rows_match_api":True,"selection_preserved_on_refresh":True})
        await browser.close()
    assert not errors,errors
    report={"status":"passed","checks":checks,"page_errors":errors,"forecast_sha256":hashlib.sha256(get("/files/forecasts.csv")).hexdigest(),"experimental_source_sha":data.get("source_sha"),"validated_at_source":os.environ.get("GITHUB_SHA"),"recording":False}
    current={"policy_reports":[{k:p.get(k) for k in ("seed","objective","mode","actual_optimizer_updates","selected_update","comparisons","rl_gate")} for p in data.get("policy_reports",[])],"curves":data.get("checkpoint_runs",[]),"provider_usage":data.get("provider_usage"),"adaptation":[{"question":r["question_id"],"origin":r["origin"],"status":r["status"],"trials":len(r["trials"]),"new_executions":r["new_executions"],"memory_reads":r.get("actual_cross_role_reads"),"context_changed":r.get("adaptation_changes"),"results_changed":sum(e.get("results_changed_choice",False) for e in r["events"])} for r in data.get("autonomy_runs",[])]}
    print("V2_CURRENT_RESULTS:"+json.dumps(current),flush=True)
    (out/"report.json").write_text(json.dumps(report,indent=2));print("V2_UI_REPORT:"+json.dumps(report))
if __name__=="__main__":asyncio.run(run())
