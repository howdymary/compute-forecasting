"""Requested 60-second browser capture, exported as 30 seconds at 2x. Hosted runners only."""
import base64,hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def digest(raw):return hashlib.sha256(raw).hexdigest()
def run():
    from playwright.sync_api import sync_playwright
    from PIL import Image,ImageDraw
    config=json.loads(Path("configs/terminal-v10-video.json").read_text())
    assert config["source_seconds"]==60 and config["speed"]==2 and config["output_seconds"]==30
    out=Path("artifacts/terminal-v10-video");out.mkdir(parents=True,exist_ok=True)
    health={}
    for attempt in range(30):
        health=json.loads(urllib.request.urlopen(URL+"/health",timeout=90).read())
        if health["ui_revision"]==config["ui_revision"]:break
        time.sleep(3)
    assert health.get("ui_revision")==config["ui_revision"],("UI revision changed",health)
    snapshots={}
    for endpoint in ("/api/pricing","/api/value-v5"):
        raw=urllib.request.urlopen(URL+endpoint,timeout=90).read();snapshots[endpoint]={"raw":raw,"sha256":digest(raw)}
    inputs=out/"inputs";inputs.mkdir(exist_ok=True)
    for endpoint,obj in snapshots.items():(inputs/(endpoint.rsplit("/",1)[1]+".json")).write_bytes(obj["raw"])
    pricing=json.loads(snapshots["/api/pricing"]["raw"]);history=json.loads(snapshots["/api/value-v5"]["raw"])
    assert pricing["forecast_csv_sha256"]=="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
    assert len(pricing["series"])==37
    approved={d["series_id"] for d in history["history"]["publication_decisions"] if d["approved"]}
    hs={s["id"] for s in history["history"]["series"] if s["id"] in approved}
    primary=next(s["id"] for s in pricing["series"] if "H100" in s["gpu_model"] and "neocloud" in s["market"].lower() and s["id"] in hs)
    a100=next(s["id"] for s in pricing["series"] if "A100" in s["gpu_model"] and s["id"] in hs)
    series=sorted(pricing["series"],key=lambda s:(0 if "H100" in s["gpu_model"] else 1 if "A100" in s["gpu_model"] else 2,s["id"]))
    trace=[];visited=set()
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        context=browser.new_context(viewport={"width":1920,"height":1080},device_scale_factor=1,record_video_dir=str(out/"raw"),record_video_size={"width":1920,"height":1080},reduced_motion="reduce")
        for path,obj in snapshots.items():
            context.route("**"+path,lambda route,raw=obj["raw"]:route.fulfill(status=200,content_type="application/json",body=raw))
        page_start=time.perf_counter();page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto(URL+"/terminal?capture=1",wait_until="domcontentloaded",timeout=90000)
        page.wait_for_function("()=>document.body.dataset.ready==='true' && V10!==null",timeout=90000)
        page.locator("#terminal-series").select_option(primary)
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.wait_for_timeout(1000)
        begin=time.perf_counter();offset=begin-page_start
        def until(second):
            remain=begin+second-time.perf_counter()
            if remain>0:page.wait_for_timeout(remain*1000)
        def note(event):
            trace.append({"source_second":round(time.perf_counter()-begin,4),"event":event,"state":page.evaluate("({mode:T10.mode,series:T10.series,range:T10.range,horizon:T10.horizon,months:T10.months,instrument:T10.instrument,basis:T10.basis,hours:T10.hours,rates:T10.rates,inspected:POINTS10[T10.index],anchor:P10?anchor10():null})")})
        def select(id):
            page.locator("#terminal-series").select_option(id);visited.add(id)
        def slider(selector,value):
            page.locator(selector).evaluate("(e,v)=>{e.value=String(v);e.dispatchEvent(new Event('input',{bubbles:true}))}",value)
        note("Opening H100 matched history and archived quantiles")
        for i in range(8):
            until(i*.5);slider("#terminal-cursor",round(i/7*(page.evaluate("POINTS10.length")-1)))
        for i,s in enumerate(series):
            until(4+i*20/len(series));select(s["id"])
            page.locator('[data-horizon="'+str((1,3,7)[i%3])+'"]').click();note("Submitted series "+str(i+1)+"/"+str(len(series)))
        until(24);select(a100);page.locator('[data-horizon="7"]').click();page.locator('[data-range="30"]').click();note("A100 historical window")
        until(26);page.locator('[data-range="all"]').click();page.locator("#ema-toggle").click();note("Full history with descriptive EMA")
        until(28);select(primary);page.locator("#tab-scenario").click();note("Published rental assumptions, index 100")
        for i in range(16):
            until(28+i*.25);slider("#terminal-cursor",round(i/15*36))
        initial=page.evaluate("T10.rates.rental")
        for k in range(100):
            until(32+k*.1);f=(k+1)/100
            rates=[round(initial[i]+(target-initial[i])*f) for i,target in enumerate((-15,-5,12))]
            page.evaluate("(values)=>values.forEach((v,i)=>{const e=document.querySelector('#terminal-rate-'+i);e.value=String(v);e.dispatchEvent(new Event('input',{bubbles:true}))})",rates)
            if k%10==0:note("Annual rental assumptions change")
        until(42);page.locator("#scenario-basis").select_option("usd");page.locator('[data-months="24"]').click();note("Dated published dollar anchor, 24 months")
        for i in range(30):
            until(42+i*.2);slider("#scenario-hours",1000+100*i)
            if i%10==0:note("Monthly GPU-hour budget changes")
        until(48);select(a100);page.locator('[data-months="36"]').click();note("A100 rental scenarios with its own matched anchor")
        for i in range(24):
            until(48+i*.25);slider("#terminal-rate-1",round(-5-13*(i+1)/24))
        until(54);page.locator("#scenario-instrument").select_option("resale");note("Separate hardware resale index")
        original=page.evaluate("T10.rates.resale")
        for i in range(20):
            until(54+i*.2);slider("#terminal-rate-1",min(90,round(original[1]+15*(i+1)/20)))
        until(58);select(primary);page.locator("#scenario-instrument").select_option("rental");page.locator("#scenario-reset").click();note("Published assumptions restored")
        until(60);end=time.perf_counter();page.wait_for_timeout(1000)
        assert len(visited)==37,(len(visited),len(series));assert not errors,errors
        video=page.video;context.close();rawvideo=video.path();browser.close()
    assert end-begin>=60
    target=out/"terminal-30s.mp4"
    subprocess.run(["ffmpeg","-y","-ss",str(offset),"-i",str(rawvideo),"-an","-vf","trim=duration=60,setpts=0.5*(PTS-STARTPTS),fps=30,format=yuv420p","-t","30","-c:v","libx264","-preset","medium","-crf","18","-movflags","+faststart",str(target)],check=True,capture_output=True)
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(target)]))
    stream=next(s for s in probe["streams"] if s["codec_type"]=="video")
    assert stream["codec_name"]=="h264" and stream["width"]==1920 and stream["height"]==1080
    assert stream["r_frame_rate"]=="30/1" and abs(float(probe["format"]["duration"])-30)<.05
    assert target.stat().st_size<50_000_000
    sheet=Image.new("RGB",(1920,768),"#0a101c");draw=ImageDraw.Draw(sheet)
    for i,sec in enumerate((1,6,12,18,24,29)):
        frame=out/("frame-"+str(sec)+".png")
        subprocess.run(["ffmpeg","-y","-ss",str(sec),"-i",str(target),"-frames:v","1",str(frame)],check=True,capture_output=True)
        im=Image.open(frame).convert("RGB")
        assert im.getextrema()[0][1]-im.getextrema()[0][0]>30
        if i==0:im.save(out/"poster.png")
        im.thumbnail((640,360));x=i%3*640;y=i//3*384;sheet.paste(im,(x,y));draw.text((x+12,y+364),str(sec)+" seconds / 2x actual browser playback",fill="#c3d2e9")
    sheet.save(out/"contact-sheet.png")
    manifest={"schema_version":10,"kind":"recorded_public_ui_exploration","ui_revision":config["ui_revision"],"recorder_revision":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"recorded_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source_seconds":60,"playback_speed":2,"output_seconds":float(probe["format"]["duration"]),"width":1920,"height":1080,"fps":30,"codec":"h264","audio":False,"series_visited":len(visited),"all_submitted_series":sorted(visited),"api_snapshots":{p:{"sha256":o["sha256"],"bytes":len(o["raw"])} for p,o in snapshots.items()},"official_csv_sha256":pricing["forecast_csv_sha256"],"trace":trace,"claim":"Archived forecasts and assumption-based calculations; no live inference or new accuracy result.","files":{p.name:{"sha256":digest(p.read_bytes()),"bytes":p.stat().st_size} for p in (target,out/"poster.png",out/"contact-sheet.png")},"sources":{"pricing":URL+"/api/pricing","history":URL+"/api/value-v5"}}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2,allow_nan=False))
    import modal
    vol=modal.Volume.from_name("compute-forecast-public",version=2);prefix="/terminal-v10/media/"+os.environ["GITHUB_RUN_ID"]+"/"
    with vol.batch_upload() as upload:
        for name in ("terminal-30s.mp4","poster.png","contact-sheet.png","manifest.json"):upload.put_file(str(out/name),prefix+name)
    base=URL+"/terminal/media/"+os.environ["GITHUB_RUN_ID"]+"/"
    raw=urllib.request.urlopen(base+"terminal-30s.mp4",timeout=90).read();assert digest(raw)==manifest["files"]["terminal-30s.mp4"]["sha256"]
    request=urllib.request.Request(base+"terminal-30s.mp4",headers={"Range":"bytes=0-1023"})
    response=urllib.request.urlopen(request,timeout=90);assert response.status==206 and len(response.read())==1024
    receipt={"status":"passed","ui_revision":config["ui_revision"],"video_url":base+"terminal-30s.mp4","manifest_url":base+"manifest.json","poster_url":base+"poster.png","contact_sheet_url":base+"contact-sheet.png","duration":manifest["output_seconds"],"speed":2,"series_visited":len(visited),"video_sha256":digest(raw),"bytes":len(raw),"range_request_verified":True}
    (out/"publication.json").write_text(json.dumps(receipt,indent=2))
    print("T10_VIDEO_REPORT:"+json.dumps(receipt),flush=True)
    for p in (out/"contact-sheet.png",out/"poster.png"):
        data=base64.b64encode(p.read_bytes()).decode()
        for i in range(0,len(data),12000):print("T10_VIDEO_PNG:"+json.dumps({"name":p.name,"index":i//12000,"base64":data[i:i+12000]}),flush=True)
if __name__=="__main__":run()
