"""Validate real v18 artifacts, desktop/mobile interactions and deployed PNGs; no recording."""
import concurrent.futures,hashlib,http.server,json,os,pathlib,re,threading,time,urllib.request
from playwright.sync_api import sync_playwright,expect
from compute_forecast.probability_ui_v18 import HTML
root=pathlib.Path("artifacts/probability-v18-ui");root.mkdir(parents=True,exist_ok=True)
pointer=json.loads(pathlib.Path("results/probability-v18/latest.json").read_bytes())
raw=pathlib.Path(pointer["report_path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"]
report=json.loads(raw);report["public_report_sha256"]=pointer["report_sha256"];state={"error":False,"empty":False}
font=urllib.request.urlopen("https://raw.githubusercontent.com/google/fonts/a85fc09e44c70c7159761adfdc9d5dd007792c15/ofl/caveat/Caveat%5Bwght%5D.ttf",timeout=60).read()
assert hashlib.sha1(b"blob "+str(len(font)).encode()+b"\0"+font).hexdigest()=="f84acf2ce2d1b3329b194749530dbaec047e6df6"
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/probability":raw=HTML.encode();kind="text/html";status=200
        elif self.path=="/assets/note.ttf":raw=font;kind="font/ttf";status=200
        elif self.path=="/api/probability-v18":
            value={"study_id":"direct-probability-v18","status":"pending_campaign","runs":[]} if state["empty"] else report
            raw=json.dumps(value).encode();kind="application/json";status=503 if state["error"] else 200
        else:self.send_response(404);self.end_headers();return
        self.send_response(status);self.send_header("Content-Type",kind);self.end_headers();self.wfile.write(raw)
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
def ready(page):
    expect(page.locator("#status")).not_to_have_text(re.compile("^Loading"),timeout=90000)
    assert "unavailable" not in page.locator("#status").inner_text().lower()
def verify_shapes(page,source):
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"),"Horizontal page overflow"
    assert page.locator("#case option").count()==len(source["cases"]["retrospective"])
    assert page.locator("#prices circle").count()>0
    assert page.evaluate("async()=>{await document.fonts.load('24px Caveat');await document.fonts.ready;return document.fonts.check('24px Caveat')}"),"Annotation font unavailable"
    for selector in ("#prices text","#distribution text"):
        page.wait_for_function("(selector)=>{let e=document.querySelector(selector);return e&&parseFloat(getComputedStyle(e).fontSize)*e.getScreenCTM().a>=11}",arg=selector,timeout=5000)
        size=page.locator(selector).first.evaluate("(e)=>parseFloat(getComputedStyle(e).fontSize)*e.getScreenCTM().a")
        assert size>=11,("Unreadable settled axis",selector,size)
def interact(page,source,touch):
    page.locator("#prices circle").first.focus();page.keyboard.press("Enter")
    value=json.loads(page.locator("#inspection").inner_text());assert value["kind"]=="Historical observed median"
    page.locator("#pin").click();pinned=page.locator("#pins li").first.get_attribute("data-snapshot")
    assert json.loads(pinned)["source_report_sha256"]==source["public_report_sha256"]
    page.locator("#seed").select_option("29");before=page.locator("#case").input_value()
    page.locator("details").first.locator("summary").click()
    page.locator("#refresh").click();ready(page)
    assert page.locator("#seed").input_value()=="29" and page.locator("#case").input_value()==before
    assert page.locator("details").first.get_attribute("open") is not None
    assert page.locator("#refresh").evaluate("(e)=>document.activeElement===e"),"Refresh lost focus"
    assert page.locator("#pins li").first.get_attribute("data-snapshot")==pinned
    page.locator("#show-ce").uncheck();page.locator("#show-crps").uncheck()
    if touch:page.locator("#distribution circle").first.tap()
    else:page.locator("#distribution circle").first.hover()
    detail=json.loads(page.locator("#inspection").inner_text());assert detail["kind"]=="Forecast probability" and detail["model"]=="Untuned"
    page.locator("#show-ce").check();page.locator("#show-crps").check()
    page.locator("#horizon").select_option("1")
    assert "1-day forecast" in page.locator("#distribution-sub").inner_text()
    page.locator("#scope").select_option("development")
    seed_runs=[r for r in source["runs"] if r["seed"]==29]
    if seed_runs:
        ys=page.locator("#prices text").all_text_contents()
        step=seed_runs[0]["checkpoints"][-1]["update"]
        page.get_by_role("button",name="Inspect optimizer update "+str(step),exact=True).click()
        assert page.locator("#prices text").all_text_contents()==ys,"Price axes changed with checkpoint"
        marker=page.locator("#learning circle[tabindex]").first;marker.focus();page.keyboard.press("Enter")
        assert page.locator("#updates button[aria-pressed=true]").inner_text()=="Update 0"
        assert page.locator("#learning circle:focus").count()==1,"SVG focus lost during rerender"
        assert page.locator("#pins li").first.get_attribute("data-snapshot")==pinned
    else:assert "Awaiting" in page.locator("#note").inner_text() or not source["runs"]
    page.locator("#horizon").select_option("7")
with sync_playwright() as p:
    browser=p.chromium.launch()
    for name,width,height,touch in (("desktop",1440,1100,False),("mobile",390,844,True)):
        context=browser.new_context(viewport={"width":width,"height":height},has_touch=touch,reduced_motion="reduce")
        page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
        assert page.goto("http://127.0.0.1:"+str(server.server_port)+"/probability").status==200
        ready(page);verify_shapes(page,report);interact(page,report,touch);assert not errors,errors
        page.screenshot(path=str(root/(name+".png")),full_page=True)
        state["error"]=True;page.locator("#refresh").click();expect(page.locator("#status")).to_contain_text("unavailable",timeout=90000)
        state["error"]=False;page.locator("#refresh").click();ready(page)
        state["empty"]=True;page.locator("#refresh").click();ready(page);expect(page.locator("#empty")).to_be_visible()
        state["empty"]=False;page.locator("#refresh").click();ready(page);context.close()
    base="https://howdymary--compute-forecast-evidence-v14-web.us-east.modal.run"
    for attempt in range(18):
        try:
            with urllib.request.urlopen(base+"/probability",timeout=90) as response:
                assert response.status==200
                deployed_html=response.read().decode()
            if deployed_html==HTML:break
        except Exception:
            if attempt==17:raise
        time.sleep(5)
    else:raise AssertionError("Live HTML is not the current figure implementation")
    def probe(i):
        route=("/api/probability-v18","/api/evidence-v14","/api/probability-v18/future")[i%3]
        started=time.monotonic();print(json.dumps({"probe":"start","i":i,"route":route}),flush=True)
        try:
            with urllib.request.urlopen(base+route,timeout=90) as response:
                assert response.status==200;raw=response.read();value=json.loads(raw)
                assert value["study_id"]==("direct-probability-v18","direct-evidence-v14","direct-probability-v18-prospective")[i%3]
            print(json.dumps({"probe":"passed","i":i,"route":route,"bytes":len(raw),"seconds":time.monotonic()-started}),flush=True)
        except Exception as error:
            print(json.dumps({"probe":"failed","i":i,"route":route,"error_type":type(error).__name__,"seconds":time.monotonic()-started}),flush=True);raise
        return True
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:assert all(pool.map(probe,range(12)))
    for attempt in range(12):
        live=json.load(urllib.request.urlopen(base+"/api/probability-v18",timeout=90))
        live_pointer=json.load(urllib.request.urlopen("https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/results/probability-v18/latest.json",timeout=60))
        raw=urllib.request.urlopen("https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/"+live_pointer["report_path"],timeout=90).read()
        assert hashlib.sha256(raw).hexdigest()==live_pointer["report_sha256"]
        canonical=json.loads(raw);canonical["public_report_sha256"]=live_pointer["report_sha256"]
        if live==canonical:break
        time.sleep(5)
    else:raise AssertionError("Live report differs from immutable canonical source")
    for name,width,height,touch in (("live-desktop",1440,1100,False),("live-mobile",390,844,True)):
        context=browser.new_context(viewport={"width":width,"height":height},has_touch=touch,reduced_motion="reduce")
        page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
        assert page.goto(base+"/probability",wait_until="domcontentloaded",timeout=90000).status==200
        ready(page);verify_shapes(page,live);interact(page,live,touch);assert not errors,errors
        page.locator("#scope").select_option("retrospective");page.locator("#seed").select_option("17")
        page.screenshot(path=str(root/(name+".png")),full_page=True);context.close()
    browser.close()
server.shutdown()
value={"study_id":"direct-probability-v18","source_sha":os.environ.get("VALIDATION_SOURCE_SHA",os.environ["GITHUB_SHA"]),"report_sha256":pointer["report_sha256"],"live_report_sha256":live_pointer["report_sha256"],"completed_final_runs":len(live["runs"]),"training_interactions_pending":len(live["runs"])<6,"synthetic_market_values":False,"video_recorded":False,"checks":["strict HTTP and live canonical SHA","probability source-bound inspection","touch and keyboard parity","fixed price axes across checkpoints where available","focus and selection persistence","immutable pins","actual empty/error/retry","concurrent independent v14/v18 requests","desktop/mobile no overflow","axis text >=11px","reduced motion"],"screenshots":[{"path":f.name,"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size} for f in sorted(root.glob("*.png"))]}
(root/"validation.json").write_text(json.dumps(value,indent=2)+"\n");print(json.dumps(value),flush=True)
