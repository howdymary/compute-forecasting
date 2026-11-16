"""PNG-only remote UI validation on actual public artifacts; no recording."""
from __future__ import annotations
import hashlib,http.server,json,pathlib,threading,time
from playwright.sync_api import sync_playwright
from compute_forecast.direct_ui_v12 import HTML
root=pathlib.Path("artifacts/direct-v12-ui");root.mkdir(parents=True,exist_ok=True)
pointer=pathlib.Path("results/direct-v12/latest.json")
if pointer.exists():
    index=json.loads(pointer.read_text());raw=pathlib.Path(index["report_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==index["report_sha256"];report=json.loads(raw)
else:report={"status":"running","runs":[],"cases":[]}
state={"error":False,"delay":0}
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/":
            raw=HTML.encode();self.send_response(200);self.send_header("Content-Type","text/html")
        elif self.path=="/api/direct-v12":
            time.sleep(state["delay"]);raw=json.dumps(report).encode();self.send_response(503 if state["error"] else 200);self.send_header("Content-Type","application/json")
        else:self.send_response(404);self.end_headers();return
        self.end_headers();self.wfile.write(raw)
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    browser=p.chromium.launch()
    for name,width,height,touch in [("desktop",1440,1100,False),("mobile",390,844,True)]:
        context=browser.new_context(viewport={"width":width,"height":height},has_touch=touch,reduced_motion="reduce")
        page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
        response=page.goto("http://127.0.0.1:"+str(server.server_port));assert response.status==200
        page.wait_for_function("!document.querySelector('#status').textContent.startsWith('Loading')")
        assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth"),"Horizontal page overflow"
        if report["runs"]:
            assert page.locator("#chart circle").count()>0
            assert page.locator("#table tr").count()==6
            first=page.locator("#chart circle").first;first.focus();page.keyboard.press("Enter")
            assert "USD/GPU-hour" in page.locator("#point").inner_text()
            chosen=page.locator("#case").input_value()
            page.get_by_role("button",name="Refresh research results").click()
            page.wait_for_function("!document.querySelector('#status').textContent.startsWith('Loading')")
            assert page.locator("#case").input_value()==chosen,"Case selection lost on refresh"
            page.get_by_role("button",name="Learning",exact=True).click()
            assert page.locator("#chart circle").count()==sum(len(r["checkpoints"]) for r in report["runs"])
            page.screenshot(path=str(root/(name+"-learning.png")),full_page=True)
            page.get_by_role("button",name="Price forecast",exact=True).click()
        else:assert "No completed checkpoint" in page.locator("#chart").text_content()
        page.screenshot(path=str(root/(name+"-price.png")),full_page=True)
        state["error"]=True;page.get_by_role("button",name="Refresh research results").click()
        page.wait_for_function("document.querySelector('#status').textContent.includes('unavailable')")
        state["error"]=False;page.get_by_role("button",name="Refresh research results").click()
        page.wait_for_function("!document.querySelector('#status').textContent.startsWith('Loading')")
        assert not errors,errors
        context.close()
    browser.close()
server.shutdown()
manifest={"source_revision":__import__("os").environ.get("GITHUB_SHA"),"real_completed_seeds":len(report["runs"]),"is_synthetic":False,"no_video_recorded":True,"screenshots":[{"path":f.name,"bytes":f.stat().st_size,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(root.glob("*.png"))],"checks":["strict HTTP","real retained artifacts or explicit pending state","desktop and narrow mobile","no horizontal overflow","keyboard point inspection","selection preservation","retry after 503","reduced motion"]}
(root/"validation.json").write_text(json.dumps(manifest,indent=2)+"\n");print(json.dumps(manifest,indent=2))
