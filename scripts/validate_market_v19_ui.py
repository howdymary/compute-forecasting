"""PNG-only remote validation, source arithmetic, live HTTP/2 and accessible interactions."""
import concurrent.futures,hashlib,http.server,json,pathlib,threading,time,urllib.request
from playwright.sync_api import sync_playwright,expect
from compute_forecast.market_ui_v19 import HTML
from compute_forecast.ui_http_v18 import live_urlopen
from compute_forecast.verify_market_v19 import verify,verify_progress
root=pathlib.Path("artifacts/market-state-v19-ui");root.mkdir(parents=True,exist_ok=True)
pointer_path=pathlib.Path("results/market-state-v19/latest.json")
if not pointer_path.exists():pointer_path=pathlib.Path("results/market-state-v19/progress/latest.json")
pointer=json.loads(pointer_path.read_bytes());raw=pathlib.Path(pointer["report_path"]).read_bytes()
assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"]
report=json.loads(raw);checks=verify_progress(report) if report["study_id"]=="market-state-v19-progress" else verify(report);report["public_report_sha256"]=pointer["report_sha256"]
font=urllib.request.urlopen("https://raw.githubusercontent.com/google/fonts/a85fc09e44c70c7159761adfdc9d5dd007792c15/ofl/caveat/Caveat%5Bwght%5D.ttf",timeout=60).read()
assert hashlib.sha1(b"blob "+str(len(font)).encode()+b"\0"+font).hexdigest()=="f84acf2ce2d1b3329b194749530dbaec047e6df6"
state={"error":False,"empty":False,"delay":False,"synthetic_future":False}
import importlib.util
spec=importlib.util.spec_from_file_location("synthetic_future_contracts","tests/test_market_commitments_v19.py");fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
fixture_commitment,_=fixtures.commitment();task=fixture_commitment["price_inputs"][0]
synthetic_future={"issued_origins":1,"public_report_sha256":"synthetic-test-only","forecast_cases":[{"id":task["task_id"],"origin":task["origin"],"issued_at":fixture_commitment["issued_at"],"metadata":task["metadata"],"history":task["context"],"predictions":[r for r in fixture_commitment["rows"] if r["series_id"]==task["series_id"] and r["method"] in ("price","market")],"outcomes":[],"market_state":task["market_state"],"publication_receipt":{"eligible_publication_window":True},"input_sha256":"synthetic-test-only","commitment_sha256":"synthetic-test-only"}],"paired_by_origin":[]}
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        code=200
        if self.path=="/market":value=HTML.encode();kind="text/html"
        elif self.path=="/assets/note.ttf":value=font;kind="font/ttf"
        elif self.path=="/api/market-v19":
            if state["delay"]:time.sleep(2)
            value=json.dumps({"runs":[]} if state["empty"] else report).encode();kind="application/json"
            if state["error"]:code=503
        elif self.path=="/api/market-v19/future":value=json.dumps(synthetic_future if state["synthetic_future"] else {"issued_origins":0,"reasons":["insufficient_retained_price_days"]}).encode();kind="application/json"
        else:self.send_response(404);self.end_headers();return
        self.send_response(code);self.send_header("Content-Type",kind);self.end_headers();self.wfile.write(value)
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
def inspect(page,touch):
    try:expect(page.locator("#results")).to_be_visible(timeout=90000)
    except Exception:
        print("UI_STATUS",page.locator("#status").inner_text(),flush=True)
        page.screenshot(path=str(root/"failure.png"),full_page=True)
        raise
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    for selector in ("#price text","#learning text"):
        actual=page.locator(selector).first.evaluate("(e)=>parseFloat(getComputedStyle(e).fontSize)*e.getScreenCTM().a")
        assert actual>=11,("Unreadable axis",selector,actual)
    circle=page.locator("#price circle[tabindex]").first
    if touch:circle.tap()
    else:circle.focus();page.keyboard.press("Enter")
    expect(page.locator("#point")).to_contain_text("Historical observation")
    page.locator("#pin").click();page.locator("details").filter(has=page.locator("#pins")).locator("summary").click()
    original=page.locator("#pins").inner_text()
    pin=json.loads(page.locator("#pins .pin").last.get_attribute("data-snapshot"));assert pin["source_report_sha256"]==report["public_report_sha256"]
    assert pin["observation"]["value"]==next(r["value"] for r in report["cases"][0]["history"] if r["date"]==pin["observation"]["date"])
    axes=page.locator("#price text").all_text_contents()
    page.locator("#seed").select_option("29");page.locator("#checkpoint").select_option(page.locator("#checkpoint option").last.get_attribute("value"))
    assert page.locator("#price text").all_text_contents()==axes,"Price axes changed between measured checkpoints"
    page.locator("#horizon").select_option("1")
    page.locator("#refresh").click();expect(page.locator("#status")).to_contain_text("updates",timeout=90000)
    assert page.locator("#seed").input_value()=="29" and page.locator("#horizon").input_value()=="1"
    assert page.locator("#refresh").evaluate("(e)=>e===document.activeElement")
    assert page.locator("#pins").inner_text()==original
with sync_playwright() as pw:
    browser=pw.chromium.launch()
    for name,width,height,touch in (("desktop",1440,1100,False),("mobile",390,844,True)):
        ctx=browser.new_context(viewport={"width":width,"height":height},has_touch=touch,reduced_motion="reduce")
        page=ctx.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
        assert page.goto("http://127.0.0.1:"+str(server.server_port)+"/market").status==200
        inspect(page,touch);page.screenshot(path=str(root/(name+".png")),full_page=True)
        state["error"]=True;page.locator("#refresh").click();expect(page.locator("#retry")).to_be_visible()
        state["error"]=False;page.locator("#retry").click();expect(page.locator("#retry")).to_be_hidden()
        state["empty"]=True;page.locator("#refresh").click();expect(page.locator("#status")).to_contain_text("pending")
        state["empty"]=False;page.locator("#retry").click();expect(page.locator("#retry")).to_be_hidden()
        state["synthetic_future"]=True;page.reload();expect(page.locator("#future-figure")).to_be_visible()
        expect(page.locator("#future-point")).to_contain_text("synthetic")
        assert page.locator("#future-prices circle").count()==6 and page.locator("#future-paired").is_hidden(),("Future fixture geometry",page.locator("#future-prices circle").count(),page.locator("#future-paired").is_hidden())
        page.locator("#future-pin").click();expect(page.locator("#future-pin-feedback")).to_have_text("Saved to pinned observations.")
        expect(page.locator("#pins")).to_contain_text("synthetic")
        state["synthetic_future"]=False
        assert not errors,errors;ctx.close()
    base="https://howdymary--compute-forecast-evidence-v14-web.us-east.modal.run"
    def fetch(path):
        with live_urlopen(base+path,timeout=90) as r:
            assert r.status==200;body=r.read()
            return path,body
    batches=[]
    for batch in range(2):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:items=list(pool.map(fetch,["/market","/api/market-v19","/api/market-v19/future","/probability","/api/probability-v18"]*3))
        for path,body in items:
            if path=="/api/market-v19":assert json.loads(body)["public_report_sha256"]==pointer["report_sha256"]
        batches.append({"requests":len(items),"http_version":"HTTP/2","all_status":200})
    for name,width,height in (("live-desktop",1440,1100),("live-mobile",390,844)):
        ctx=browser.new_context(viewport={"width":width,"height":height},has_touch=width<600,reduced_motion="reduce");page=ctx.new_page()
        assert page.goto(base+"/market",timeout=90000).status==200;inspect(page,width<600);page.screenshot(path=str(root/(name+".png")),full_page=True);ctx.close()
    browser.close()
server.shutdown()
(root/"validation.json").write_text(json.dumps({"status":"passed","source_report_sha256":pointer["report_sha256"],"arithmetic":checks,"http_batches":batches,"screenshots":["desktop.png","mobile.png","live-desktop.png","live-mobile.png"],"synthetic_future_controls_tested":True,"synthetic_market_data_published":False,"video_recorded":False},indent=2)+"\n")
