"""Validate and record only the public observatory; no account pages or live inference."""
from __future__ import annotations
import hashlib,json,subprocess,time,urllib.request,textwrap
from pathlib import Path
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"

def fetch(path):return urllib.request.urlopen(URL+path,timeout=90).read()
def srt_time(t):return f"{t//3600:02d}:{t//60%60:02d}:{t%60:02d},000"

def main():
    from playwright.sync_api import sync_playwright
    out=Path("artifacts");out.mkdir(exist_ok=True)
    raw=fetch("/api/release");data=json.loads(raw);health=json.loads(fetch("/health"))
    digest=hashlib.sha256(raw).hexdigest()
    assert health["release_sha256"]==digest and health["training_updates"]==50 and health["final_origins"]==5 and health["actual_cross_agent_use"]
    assert hashlib.sha256(fetch("/files/forecasts.csv")).hexdigest()==data["submission"]["forecast_csv_sha256"]
    start_loss=next(r["pooled_pinball"] for r in data["final"]["comparisons"] if r["policy"]=="starting_policy")
    trained_loss=next(r["pooled_pinball"] for r in data["final"]["comparisons"] if r["policy"]=="frozen_trained_policy")
    change=(trained_loss/start_loss-1)*100
    captions=[(0,12,"Compute Forecast: an auditable experiment in GPU rental forecasting."),(12,27,f"50 genuine Tinker updates. Frozen SFT loss {trained_loss:.6f}; starting loss {start_loss:.6f}. SFT is {abs(change):.2f}% {'worse' if change>0 else 'better'} here."),(27,42,"24 representations and model settings. Official targets and chronological scoring stay fixed."),(42,65,"Recorded actual policy decisions. Same observations, same six-trial reveal budget; no live inference in this replay."),(65,91,"Exa evidence, three past.dev writers and readers, then criticism changes the next configuration. Experiments are cached, hash-verified results."),(91,106,"111 official forecasts cover 37 headline series. Future competition truth was never loaded."),(106,120,"Five dependent final dates. No demonstrated research-policy improvement. Inspect the source, every trace and the limitations.")]
    srt="\n".join(f"{i+1}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n" for i,(a,b,text) in enumerate(captions))
    (out/"demo.srt").write_text(srt)
    errors=[];responses=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        mobile=browser.new_context(viewport={"width":390,"height":844},device_scale_factor=1)
        phone=mobile.new_page();phone.goto(URL,wait_until="networkidle");phone.get_by_role("heading",name="A market forecast you can audit.").wait_for()
        assert phone.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"),"Mobile horizontal overflow"
        phone.screenshot(path=str(out/"mobile.png"),full_page=True);mobile.close()
        context=browser.new_context(viewport={"width":1600,"height":900},record_video_dir=str(out/"raw-video"),record_video_size={"width":1600,"height":900},reduced_motion="reduce")
        origin=time.monotonic();page=context.new_page()
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("response",lambda r:responses.append({"url":r.url,"status":r.status}) if r.url.startswith(URL) and r.status>=400 and not r.url.endswith("/favicon.ico") else None)
        page.goto(URL,wait_until="networkidle");page.get_by_role("heading",name="A market forecast you can audit.").wait_for()
        page.get_by_text("50 updates",exact=True).wait_for();page.screenshot(path=str(out/"desktop.png"),full_page=True)
        started=time.monotonic();trim_start=started-origin
        def until(second):
            remaining=second-(time.monotonic()-started)
            if remaining>0:page.wait_for_timeout(remaining*1000)
        until(12)
        page.get_by_role("heading",name="Frozen final comparison",exact=True).scroll_into_view_if_needed()
        until(27)
        page.get_by_role("button",name="02 Benchmarks",exact=True).click()
        page.get_by_role("heading",name="Representation is an experiment.",exact=True).wait_for()
        page.locator("#origin").select_option("2026-08-08")
        assert page.locator("#method option").count()==28
        page.locator("#method").select_option(index=27)
        assert page.locator("#horizons tbody tr").count()==3
        until(42)
        page.get_by_role("button",name="03 Policy replay",exact=True).click()
        dates=data["traces"]["starting"]["traces"]
        changed=next((a["origin"] for a in dates if a["selected_config_id"]!=next(b for b in data["traces"]["trained"]["traces"] if b["origin"]==a["origin"])["selected_config_id"]),dates[0]["origin"])
        page.locator("#replay-origin").select_option(changed)
        for k in range(4):
            until(46+k*3);page.get_by_role("button",name="Next experiment →",exact=True).click()
        for which in ("starting","trained"):
            trace=next(r for r in data["traces"][which]["traces"] if r["origin"]==changed)
            page.get_by_text(f"{trace['future_pinball']:.6f}",exact=True).first.wait_for()
        until(65)
        page.get_by_role("button",name="04 Evidence & memory",exact=True).click()
        page.get_by_role("heading",name="Research, with named authors.",exact=True).wait_for()
        assert page.locator(".event").count()==len(data["memory"]["events"])
        until(75);page.locator(".event").filter(has_text="skeptic").last.scroll_into_view_if_needed()
        until(83);page.locator(".event").last.scroll_into_view_if_needed()
        until(91)
        page.get_by_role("button",name="01 Overview",exact=True).click()
        page.get_by_role("heading",name="The submitted forecast, in view.",exact=True).scroll_into_view_if_needed()
        assert page.locator("#forecast-series option").count()==37
        assert page.locator("#forecast-chart svg").count()==1
        until(98);page.locator("#forecast-series").select_option(index=1)
        until(106)
        page.get_by_role("button",name="05 Reproduce",exact=True).click()
        page.get_by_role("heading",name="Follow the evidence all the way down.",exact=True).wait_for()
        until(120.5)
        video=page.video;context.close();path=video.path();browser.close()
    assert not errors,errors
    assert not responses,responses
    filters="drawbox=x=0:y=ih-126:w=iw:h=126:color=0x162730@0.97:t=fill"
    for i,(a,b,text) in enumerate(captions):
        lines=textwrap.wrap(text,86)
        for j,line in enumerate(lines):
            (out/f"caption-{i}-{j}.txt").write_text(line)
            y=900-126+(126-len(lines)*36)/2+j*36
            filters+=f",drawtext=textfile=artifacts/caption-{i}-{j}.txt:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=28:fontcolor=white:x=(w-text_w)/2:y={y}:enable='gte(t,{a})*lt(t,{b})'"
    subprocess.run(["ffmpeg","-y","-ss",str(trim_start),"-i",str(path),"-vf",filters,"-t","120","-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p","-movflags","+faststart","-an",str(out/"demo.mp4")],check=True)
    duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(out/"demo.mp4")],text=True))
    assert 119.8<=duration<=120.2,duration
    movie=(out/"demo.mp4").read_bytes()
    manifest={"mode":"recorded_actual_public_results","live_inference":False,"replay_origin":changed,"caption_rendering":"one_drawtext_per_line","duration_seconds":duration,"video_sha256":hashlib.sha256(movie).hexdigest(),"release_sha256":digest,"release_code_sha":data["code_sha"],"validated_views":["overview","benchmarks","recorded_policy_replay","evidence_and_memory","reproduce"],"mobile_width":390,"console_errors":errors,"failed_public_requests":responses,"captions":captions,"source_url":URL}
    (out/"demo-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__":main()
