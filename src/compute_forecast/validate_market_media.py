"""Verify the served interactive figure and real-time encoded playback remotely."""
import json,os,time,urllib.request,urllib.error
from pathlib import Path
from .record_learning_curve import sha,write
def main():
    from playwright.sync_api import sync_playwright
    cfg=json.loads(Path("configs/market-media-validation.json").read_text())
    out=Path("artifacts/market-media-validation");out.mkdir(parents=True,exist_ok=True)
    base=cfg["base_url"]+"/terminal/media/"+str(cfg["media_run_id"])+"/"
    def get(name):return urllib.request.urlopen(base+name,timeout=90).read()
    deadline=time.monotonic()+cfg["max_wait_seconds"]
    while True:
        try:manifest=json.loads(get("manifest.json"));break
        except urllib.error.HTTPError as e:
            if e.code not in (404,502,503,504) or time.monotonic()>=deadline:raise
            time.sleep(5)
    if manifest["implementation_commit"]!=cfg["expected_render_commit"]:raise ValueError("Render revision")
    if (manifest["source_seconds"],manifest["output_seconds"],manifest["playback_speed"],manifest["frames"])!=(60,30,2,900):raise ValueError("Video timing")
    hashes={}
    for name in ("replay.html","terminal-30s.mp4","poster.png","validation.json","horizon-audit.json"):
        raw=get(name);hashes[name]=sha(raw)
        if sha(raw)!=manifest["files"][name]["sha256"]:raise ValueError("Public file hash: "+name)
    validation=json.loads(get("validation.json"));horizon=json.loads(get("horizon-audit.json"))
    if validation["frame_sync_checks"]!=900 or validation["history_observations"]!=234 or validation["existing_control_cell_losses_reconstructed"]!=36 or len(horizon["retained_control_diagnostics"])!=4:raise ValueError("Numerical source reports")
    response=urllib.request.urlopen(urllib.request.Request(base+"terminal-30s.mp4",headers={"Range":"bytes=0-1023"}),timeout=90)
    if response.status!=206 or len(response.read())!=1024:raise ValueError("Live range response")
    errors=[];screens=[];chapters=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page(viewport={"width":1920,"height":1080},device_scale_factor=1)
        page.on("pageerror",lambda e:errors.append(str(e)))
        response=page.goto(base+"replay.html",wait_until="load")
        if response.status!=200 or "text/html" not in response.headers["content-type"]:raise ValueError("Public HTML")
        page.wait_for_function("window.READY===true");page.evaluate("document.fonts.ready")
        if not page.evaluate("document.fonts.check('32px Fieldnote')"):raise ValueError("Live embedded font")
        for value,mode in (("0","OBSERVED HISTORY"),("17","ARCHIVED STATISTICAL FORECAST"),("23","CONDITIONAL RENTAL SCENARIOS"),("29","CONDITIONAL RENTAL SCENARIOS"),("35","CONDITIONAL RENTAL SCENARIOS"),("41","SAVED CHECKPOINT REPLAY"),("45","SAVED CHECKPOINT REPLAY"),("49","SAVED CHECKPOINT REPLAY"),("51","SAVED CHECKPOINT REPLAY")):
            page.locator("#chapter").select_option(value)
            if float(page.locator("#scrub").input_value())!=float(value) or mode not in page.locator("#mode").text_content():raise ValueError("Live chapter selection")
            chapters.append({"source_time":float(value),"mode":page.locator("#mode").text_content()})
        page.locator("#scrub").focus();page.keyboard.press("ArrowRight")
        if float(page.locator("#scrub").input_value())<=51:raise ValueError("Live keyboard scrub")
        for value,name in (("17","public-forecast.png"),("35","public-scenario.png")):
            page.locator("#chapter").select_option(value);page.screenshot(path=str(out/name));screens.append(name)
        page.set_viewport_size({"width":390,"height":844});page.emulate_media(reduced_motion="reduce")
        page.reload(wait_until="load");page.wait_for_function("window.READY===true");page.wait_for_timeout(200)
        if float(page.locator("#scrub").input_value())!=0 or page.evaluate("document.documentElement.scrollWidth>innerWidth"):raise ValueError("Narrow layout/no-autoplay")
        page.locator("#chapter").select_option("35");page.screenshot(path=str(out/"public-mobile.png"),full_page=True);screens.append("public-mobile.png")
        movie=browser.new_page(viewport={"width":1920,"height":1080},device_scale_factor=1)
        movie.on("pageerror",lambda e:errors.append(str(e)))
        movie.set_content('<html><body style="margin:0;background:#f7f3e9"><video muted playsinline preload="auto" style="width:1920px;height:1080px" src="'+base+'terminal-30s.mp4"></video></body></html>')
        movie.wait_for_function("document.querySelector('video').readyState>=3",timeout=90000)
        movie.evaluate("document.querySelector('video').play()");playback=[]
        for sec in cfg["playback_sample_seconds"]:
            movie.wait_for_function("(t)=>document.querySelector('video').currentTime>=t",arg=sec,timeout=45000)
            actual=movie.evaluate("document.querySelector('video').currentTime")
            name="playback-"+str(sec)+".png";movie.screenshot(path=str(out/name));screens.append(name)
            playback.append({"requested_output_time":sec,"actual_output_time":actual,"equivalent_source_time":actual*2,"screenshot":name})
        movie.wait_for_function("document.querySelector('video').ended",timeout=15000)
        quality=movie.evaluate("(()=>{const v=document.querySelector('video'),q=v.getVideoPlaybackQuality();return{duration:v.duration,ended:v.ended,playbackRate:v.playbackRate,totalVideoFrames:q.totalVideoFrames,droppedVideoFrames:q.droppedVideoFrames,error:v.error?.message||null}})()")
        if not quality["ended"] or quality["duration"]!=30 or quality["playbackRate"]!=1 or quality["error"] or quality["totalVideoFrames"]<=0:raise ValueError("Real-time MP4 playback")
        fraction=quality["droppedVideoFrames"]/quality["totalVideoFrames"]
        if fraction>cfg["max_playback_drop_fraction"]:raise ValueError("Playback frame drops exceed fixed 5% limit")
        browser.close()
    if errors:raise ValueError(errors)
    report={"status":"passed","media_run_id":cfg["media_run_id"],"render_commit":cfg["expected_render_commit"],"validation_commit":os.environ["GITHUB_SHA"],"checked_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"interactive_url":base+"replay.html","video_url":base+"terminal-30s.mp4","public_file_sha256":hashes,"range_status":206,"chapters":chapters,"keyboard_scrub":True,"mobile_no_overflow":True,"reduced_motion_no_autoplay":True,"actual_encoded_playback":quality,"playback_drop_fraction":fraction,"real_time_samples":playback,"browser_errors":errors,"new_training":False}
    write(out/"validation.json",report)
    from .publication_terminal_v10 import publish
    dest="results/terminal-v10/runs/"+os.environ["GITHUB_RUN_ID"]+"/market-playback/"
    commit=publish({dest+n:(out/n).read_bytes() for n in ["validation.json"]+screens})
    print("MARKET_PUBLIC_UI_VALIDATION:"+json.dumps(report),flush=True);print("MARKET_PUBLIC_UI_PUBLICATION:"+commit,flush=True)
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write("## Public figure and real-time playback verified\n\n"+base+"replay.html\n\nChapter, keyboard, narrow layout, no-autoplay, source hashes, range playback and complete 30-second playback checked. Evidence commit: "+commit+"\n")
if __name__=="__main__":main()
