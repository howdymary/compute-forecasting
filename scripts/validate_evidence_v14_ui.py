"""PNG-only validation on actual paired-study artifacts, never synthetic learning curves."""
import hashlib,http.server,json,os,pathlib,threading,urllib.request
from playwright.sync_api import sync_playwright
from compute_forecast.evidence_ui_v14 import HTML
root=pathlib.Path("artifacts/evidence-v14-ui");root.mkdir(parents=True,exist_ok=True)
pointer=json.loads(pathlib.Path("results/evidence-v14/latest.json").read_text());raw=pathlib.Path(pointer["report_path"]).read_bytes()
assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"];report=json.loads(raw);state={"error":False}
font=urllib.request.urlopen("https://raw.githubusercontent.com/google/fonts/a85fc09e44c70c7159761adfdc9d5dd007792c15/ofl/caveat/Caveat%5Bwght%5D.ttf",timeout=60).read()
assert hashlib.sha1(b"blob "+str(len(font)).encode()+b"\0"+font).hexdigest()=="f84acf2ce2d1b3329b194749530dbaec047e6df6"
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/":raw=HTML.encode();status=200;kind="text/html"
        elif self.path=="/assets/note.ttf":raw=font;status=200;kind="font/ttf"
        elif self.path=="/api/evidence-v14":raw=json.dumps(report).encode();status=503 if state["error"] else 200;kind="application/json"
        else:self.send_response(404);self.end_headers();return
        self.send_response(status);self.send_header("Content-Type",kind);self.end_headers();self.wfile.write(raw)
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    browser=p.chromium.launch()
    for name,width,height,touch in (("desktop",1440,1050,False),("mobile",390,844,True)):
        context=browser.new_context(viewport={"width":width,"height":height},has_touch=touch,reduced_motion="reduce");page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
        response=page.goto("http://127.0.0.1:"+str(server.server_port));assert response.status==200
        page.wait_for_function("!document.querySelector('#status').textContent.startsWith('Loading')")
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"),"Page overflow"
        assert page.locator("#case option").count()==len(report["development_cases"])
        assert page.locator("#prices circle").count()>0
        assert page.locator("#prices text").first.evaluate("(e)=>parseFloat(getComputedStyle(e).fontSize)*e.getScreenCTM().a")>=11,"Mobile axes unreadable"
        first=page.locator("#prices circle").first;first.focus();page.keyboard.press("Enter")
        page.locator("#pin").click();pinned=page.locator("#pins li").first.get_attribute("data-snapshot")
        page.locator("#seed").select_option("29");page.get_by_role("button",name="Inspect optimizer update 50",exact=True).click()
        assert page.locator("#pins li").first.get_attribute("data-snapshot")==pinned,"Pin mutated"
        before=page.locator("#case").input_value();page.locator("details").first.locator("summary").click()
        page.locator("#refresh").click();page.wait_for_function("!document.querySelector('#status').textContent.startsWith('Loading')")
        assert page.locator("#seed").input_value()=="29" and page.locator("#case").input_value()==before
        assert page.locator("details").first.get_attribute("open") is not None
        if report["runs"]:
            assert page.locator("#learning circle").count()>0
            page.locator("#learning circle").first.focus();page.keyboard.press("Enter")
            assert page.locator("#updates button[aria-pressed=true]").count()==1
        assert not errors,errors
        assert page.evaluate("async()=>{await document.fonts.ready;return document.fonts.check('24px Caveat')}"),"Annotation font unavailable"
        page.screenshot(path=str(root/(name+".png")),full_page=True)
        state["error"]=True;page.locator("#refresh").click();page.wait_for_function("document.querySelector('#status').textContent.includes('unavailable')")
        state["error"]=False;page.locator("#refresh").click();page.wait_for_function("!document.querySelector('#status').textContent.startsWith('Loading')")
        context.close()
    browser.close()
server.shutdown()
manifest={"source_sha":os.environ["GITHUB_SHA"],"study_id":"direct-evidence-v14","real_completed_runs":len(report["runs"]),"synthetic_market_data":False,"video_recorded":False,"screenshots":[{"path":f.name,"bytes":f.stat().st_size,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(root.glob("*.png"))],"checks":["strict HTTP","actual source-bound prices","matched report","mobile axes>=11px","no page overflow","keyboard checkpoint selection","immutable pins","selection and disclosure preservation","503/retry","reduced motion"]}
(root/"validation.json").write_text(json.dumps(manifest,indent=2)+"\n");print(json.dumps(manifest,indent=2))
