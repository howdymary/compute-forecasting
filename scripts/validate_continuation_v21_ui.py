"""PNG-only verification of the actual deployed quantile interface and source arithmetic."""
import asyncio,hashlib,json,os,pathlib,time
import httpx
from playwright.async_api import async_playwright,expect
from compute_forecast.verify_continuation_v21 import verify
BASE="https://howdymary--compute-forecast-evidence-v14-web.us-east.modal.run"
out=pathlib.Path("artifacts/ce-continuation-v21-validation");out.mkdir(parents=True,exist_ok=True)
async def main():
    pointer=json.loads(pathlib.Path("results/ce-continuation-v21/latest.json").read_bytes())
    async with httpx.AsyncClient(http2=True,timeout=90) as client:
        response=await client.get(BASE+"/api/continuation-v21");assert response.status_code==200
        report=response.json();assert report["public_report_sha256"]==pointer["report_sha256"]
        assert response.headers["x-source-artifact-sha256"]==pointer["report_sha256"];assert report["runs"],"No completed training run to visualize"
        arithmetic=verify(report)
        batches=[]
        for batch in range(2):
            requests=await asyncio.gather(*(client.get(BASE+path) for path in ("/continuation","/api/continuation-v21","/api/continuation-v21/future","/assets/note.ttf") for _ in range(3)))
            assert all(r.status_code==200 and r.http_version=="HTTP/2" for r in requests)
            batches.append({"requests":len(requests),"statuses":[r.status_code for r in requests],"http_versions":sorted({r.http_version for r in requests})})
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        page=await browser.new_page(viewport={"width":1280,"height":1024},device_scale_factor=1,reduced_motion="reduce")
        errors=[];page.on("pageerror",lambda error:errors.append(str(error)))
        future_gate=asyncio.Event()
        async def slow_future(route):
            await future_gate.wait();await route.continue_()
        await page.route("**/api/continuation-v21/future",slow_future)
        await page.goto(BASE+"/continuation",wait_until="domcontentloaded")
        await page.locator("#experience:not([hidden])").wait_for(timeout=45000)
        assert await page.locator("#future").inner_text()=="Loading the separate commitment ledger…","Primary chart did not load independently"
        future_gate.set()
        assert await page.locator("#price-chart svg").count()==1
        assert not await page.locator("svg").evaluate_all("(xs)=>xs.some(x=>/NaN|Infinity/.test(x.innerHTML))")
        assert await page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
        await expect(page.locator("#future")).not_to_contain_text("Loading the separate")
        await page.screenshot(path=str(out/"live-desktop.png"),full_page=True)
        await page.locator("#arm").select_option("expanded")
        checkpoints=await page.locator("#checkpoint option").evaluate_all("(xs)=>xs.map(x=>x.value)")
        await page.locator("#checkpoint").select_option(checkpoints[-1])
        await page.locator("#horizon").select_option("3")
        await page.locator("#pin").click()
        pin=await page.locator("#pins").text_content()
        cases=await page.locator("#case option").evaluate_all("(xs)=>xs.map(x=>x.value)")
        await page.locator("#case").select_option(cases[1])
        assert await page.locator("#pins").text_content()==pin,"Pin mutated with selection"
        before=await page.locator("#case").input_value();cp=await page.locator("#checkpoint").input_value()
        await page.locator("#refresh").click()
        await expect(page.locator("#status")).to_contain_text("actual optimizer updates")
        assert await page.locator("#case").input_value()==before and await page.locator("#checkpoint").input_value()==cp
        assert await page.evaluate("document.activeElement.id")=="refresh"
        async def fail(route):await route.fulfill(status=503,json={"status":"test_error"})
        await page.route("**/api/continuation-v21",fail);chart=await page.locator("#price-chart").inner_html()
        await page.locator("#refresh").click();await expect(page.locator("#status")).to_contain_text("Retaining the last verified chart")
        assert await page.locator("#price-chart").inner_html()==chart
        await page.unroute("**/api/continuation-v21",fail);await page.locator("#refresh").click()
        await expect(page.locator("#status")).to_contain_text("actual optimizer updates")
        assert not errors,errors
        mobile=await browser.new_context(viewport={"width":390,"height":844},device_scale_factor=1,is_mobile=True,has_touch=True,reduced_motion="reduce")
        m=await mobile.new_page();m.on("pageerror",lambda error:errors.append(str(error)))
        await m.goto(BASE+"/continuation",wait_until="domcontentloaded")
        await m.locator("#experience:not([hidden])").wait_for(timeout=45000)
        assert await m.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
        await m.locator("#price-chart svg").focus();await m.keyboard.press("ArrowLeft")
        assert "3d" in await m.locator("#point").inner_text()
        box=await m.locator("#price-chart svg").bounding_box();await m.touchscreen.tap(box["x"]+box["width"]-24,box["y"]+100)
        assert "7d" in await m.locator("#point").inner_text()
        await m.locator("#pin").tap();assert await m.locator("#pins li").count()==1
        await m.screenshot(path=str(out/"live-mobile.png"),full_page=True)
        assert not errors,errors
        await browser.close()
    result={"status":"passed","live_url":BASE+"/continuation","public_report_sha256":pointer["report_sha256"],"arithmetic":arithmetic,"concurrent_http2_batches":batches,"checks":["actual rendered desktop/mobile","future requests do not delay primary figure","keyboard/touch forecast inspection","immutable full-source pins","refresh selections and focus","error retains verified chart and retry recovers","narrow-page overflow","no NaN or Infinity geometry","no browser errors","reduced motion"],"pngs":[{"name":f.name,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()} for f in out.glob("*.png")],"video_recorded":False}
    (out/"validation.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
if __name__=="__main__":asyncio.run(main())
