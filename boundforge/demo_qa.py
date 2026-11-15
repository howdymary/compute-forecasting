"""Remote browser validation of actual demo and exact witness download."""
import json,pathlib
def check():
    from playwright.sync_api import sync_playwright
    root=pathlib.Path(__file__).resolve().parent;out=root/"results"
    expected=json.loads((out/"best.json").read_text())
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for name,width,height in (("desktop",1440,1000),("mobile",390,844)):
            page=browser.new_page(viewport={"width":width,"height":height},accept_downloads=True)
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto((out/"demo.html").as_uri())
            assert page.locator("h1").inner_text()=="BoundForge"
            assert page.locator("svg circle").count()>0
            page.locator("#check").click()
            assert page.locator("#checks").inner_text().startswith("PASS")
            page.locator("#law").select_option("1")
            page.locator("#projection").select_option("3")
            page.locator("#step").fill(page.locator("#step").get_attribute("max"))
            assert " / " in page.locator("#eventTitle").inner_text()
            with page.expect_download() as download:
                page.locator("#download").click()
            target=out/("qa-"+name+"-witness.json");download.value.save_as(target)
            assert json.loads(target.read_text())==expected
            target.unlink()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"),"horizontal overflow"
            assert not errors,errors
            page.screenshot(path=str(out/("demo-"+name+".png")),full_page=True)
            page.close()
        browser.close()
    print("BOUNDFORGE_BROWSER_QA passed: desktop, mobile, exact structural checks, download round trip, no page errors")
if __name__=="__main__":check()
