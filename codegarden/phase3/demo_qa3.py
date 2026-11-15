"""Headless verification of the recorded demo, decoding and downloaded explicit witness."""
import datetime,functools,hashlib,http.server,importlib.metadata,importlib.util,json,os,pathlib,sys,threading
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity,verify
from playwright.sync_api import sync_playwright
check_integrity();out=ROOT/"artifacts/phase3/demo_qa_005";out.mkdir(parents=True,exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
handler=functools.partial(Handler,directory=str(ROOT/"demo"));server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();data=json.loads((ROOT/"demo/data.json").read_text());errors=[];decodes=[];viewports=[]
try:
 with sync_playwright() as p:
  downloads=ROOT/".tmp/playwright-downloads";downloads.mkdir(parents=True,exist_ok=True);browser=p.chromium.launch(headless=True,downloads_path=str(downloads));version=browser.version
  for label,width,height in [("desktop",1440,1000),("mobile",390,844)]:
   context=browser.new_context(viewport={"width":width,"height":height},accept_downloads=True);page=context.new_page();page.on("pageerror",lambda error:errors.append(str(error)));page.goto("http://127.0.0.1:"+str(server.server_port)+"/index.html",wait_until="networkidle")
   page.wait_for_function("document.querySelector('#best').textContent==='226'");assert "Target227 remains open" in page.locator("#phase3-summary").inner_text();assert "solver-closed" in page.locator("#phase3-hypothesis").inner_text()
   for i,a,b in [(0,2,7),(1,0,15),(42,4,11),(147,1,8),(225,5,13)]:
    page.select_option("#word",str(i));page.fill("#d1",str(a));page.fill("#d2",str(b));page.click("#decode");word=data["best"]["words"][i];received="".join(c for j,c in enumerate(word) if j not in [a,b]);assert page.locator("#original").inner_text()=="Original: "+word;assert page.locator("#received").inner_text()=="Received: "+received;assert len(received)==14;assert page.locator("#recovered").inner_text()=="Unique recovery: "+word;decodes.append({"viewport":label,"word":word,"deleted_positions":[a,b],"descendant":received,"unique_recovery":True})
   page.fill("#d1","2");page.fill("#d2","2");page.click("#decode");assert "distinct positions" in page.locator("#recovered").inner_text()
   page.fill("#d2","7");page.click("#decode")
   with page.expect_download() as info:page.click("#download")
   path=out/(label+"_downloaded_witness.txt");info.value.save_as(str(path));v=verify(path);assert v["cardinality"]==226 and v["reports"][0]["witness_sha256"]==data["best"]["sha256"]
   layout=page.evaluate("({viewport:innerWidth,body:document.body.scrollWidth,root:document.documentElement.scrollWidth})");assert layout["root"]<=width+1,layout
   page.screenshot(path=str(out/(label+".png")),full_page=True);viewports.append({"label":label,"width":width,"height":height,"layout":layout,"download_verification":v,"screenshot":label+".png"});context.close()
  browser.close()
 assert not errors,errors
 a="0"*16;b="0"*15+"1";spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);shared=set(D.descendants(a))&set(D.descendants(b));assert "0"*14 in shared
 report={"source_sha":os.environ["GITHUB_SHA"],"checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"data_capture_at":data["capture_utc"],"best_verified":226,"target_achieved":False,"replay_not_live":True,"playwright":importlib.metadata.version("playwright"),"chromium":version,"viewports":viewports,"decoding_examples":decodes,"duplicate_deletion_positions_rejected":True,"collision_example":{"words":[a,b],"shared_descendant":"0"*14,"deletion_positions":[[0,1],[0,15]],"rejected":True},"page_errors":errors,"screenshots":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("*.png")},"scope":"Actual browser-rendered recorded demo. Download and decoder use the reproduced226 witness, not a new construction. Headless rendering is on a free remote runner; no desktop or provider credentials are used."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("DEMO_QA_PASSED",json.dumps({"viewports":2,"decoding_examples":len(decodes),"download_cardinality":226,"target_achieved":False}),flush=True)
finally:server.shutdown();server.server_close()
