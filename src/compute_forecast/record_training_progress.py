"""Record a 30-second evidence replay from saved Tinker checkpoints. Remote runners only."""
from __future__ import annotations
import csv,hashlib,io,json,math,os,re,subprocess,time,urllib.request,zipfile
from datetime import date,timedelta
from pathlib import Path
import modal

URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
app=modal.App("compute-forecast-training-film")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
def sha(raw):return hashlib.sha256(raw).hexdigest()
def fetch(url):return urllib.request.urlopen(url,timeout=90).read()
def write(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n")

@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/data":data})
def retained_forecasts(request):
    """Read existing numerical files only; never fit, resample, train, or commit."""
    if not re.fullmatch(r"[0-9a-f]{32}",request["run_id"]):raise ValueError("Invalid retained run")
    if request["origin"]!="2026-08-22":raise ValueError("Fixed development replay origin changed")
    root=Path("/data/campaign-v2/experiments")/request["run_id"]
    summary=json.loads((root/"summary.json").read_text())
    if summary["origin"]!=request["origin"] or summary["dataset_sha256"]!=request["dataset_sha256"]:raise ValueError("Retained input identity")
    sid=request["series_id"]
    if "A100_SXM_80GB" not in sid:raise ValueError("A100 SXM case required")
    catalog=next(r for r in summary["catalog"] if r["series_id"]==sid)
    result={"catalog":catalog,"origin":request["origin"],"series_id":sid,"forecasts":{},"file_hashes":{}}
    for config in sorted(set(request["configs"])):
        if config not in {m["config_id"] for m in summary["methods"]} or not re.fullmatch(r"[A-Za-z0-9_.-]+",config):raise ValueError("Unregistered or unsafe configuration")
        file=root/(config+".csv");raw=file.read_bytes();result["file_hashes"][file.name]=sha(raw)
        rows=[r for r in csv.DictReader(io.StringIO(raw.decode())) if r["series_id"]==sid]
        if sorted(int(r["horizon_days"]) for r in rows)!=[1,3,7]:raise ValueError("Forecast cell mismatch")
        points=[]
        for row in sorted(rows,key=lambda r:int(r["horizon_days"])):
            if row["origin_date"]!=request["origin"]:raise ValueError("Wrong origin")
            qs=[float(row[k]) for k in ("q10","q50","q90")]
            if not all(math.isfinite(q) for q in qs) or not 0<qs[0]<=qs[1]<=qs[2]:raise ValueError("Quantile contract")
            h=int(row["horizon_days"]);points.append({"horizon":h,"date":(date.fromisoformat(request["origin"])+timedelta(days=h)).isoformat(),**dict(zip(("q10","q50","q90"),qs))})
        result["forecasts"][config]=points
    raw=(root/"truth.csv").read_bytes();result["file_hashes"]["truth.csv"]=sha(raw)
    ends={(date.fromisoformat(request["origin"])+timedelta(days=h)).isoformat() for h in (1,3,7)}
    truth={r["date"]:float(r["value"]) for r in csv.DictReader(io.StringIO(raw.decode())) if r["series_id"]==sid and r["date"] in ends and r["value"]}
    if set(truth)!=ends or not all(math.isfinite(v) and v>0 for v in truth.values()):raise ValueError("Missing compatible archived truth")
    result["truth"]=[{"date":d,"value":v} for d,v in sorted(truth.items())]
    return result

HTML=r'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Notes;src:url("https://howdymary--compute-forecast-observatory-web.us-east.modal.run/notebook-assets/caveat-f84acf2c.ttf")}*{box-sizing:border-box}
:root{--paper:#f6f2e8;--ink:#263d3d;--muted:#68766f;--blue:#355fc4;--green:#327c68;--amber:#b38238;--line:#dcdccc}
body{margin:0;width:1920px;height:1080px;overflow:hidden;background:var(--paper);color:var(--ink);font:20px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-variant-numeric:tabular-nums}
.wrap{padding:28px 48px}.nav{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:16px;font-size:19px;letter-spacing:.5px}.brand{font-weight:650}.badge{border:1px solid #c9cebd;border-radius:30px;padding:9px 16px;font-size:16px;color:var(--muted)}
header{display:flex;justify-content:space-between;align-items:end;margin:24px 0 20px}h1{font:500 44px/1.1 Georgia,serif;letter-spacing:-1.5px;margin:0 0 10px}.sub{color:var(--muted);font-size:21px}.totals{display:flex;gap:36px}.totals b{display:block;font-size:28px;font-weight:550}.totals span{font-size:15px;color:var(--muted)}
main{display:grid;grid-template-columns:1270px 1fr;gap:34px}.sheet{background:#fffdf7;border:1px solid #dddece;border-radius:16px;padding:20px 27px;height:600px;box-shadow:0 10px 35px #30413706}.sheethead{display:flex;justify-content:space-between;align-items:center}.eyebrow{text-transform:uppercase;letter-spacing:2px;color:var(--muted);font-size:14px}.legend{display:flex;gap:22px;font-size:16px;color:var(--muted)}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}.note{font:29px Notes,cursive;color:var(--blue);margin-top:2px}.chart{width:100%;height:440px;margin-top:8px}#chart svg{display:block;width:100%;height:100%}.chartfoot{font-size:15px;color:var(--muted);display:flex;justify-content:space-between;margin-top:5px}
aside{padding:8px 1px}h2{font:500 29px Georgia,serif;line-height:1.25;margin:12px 0 20px}.big{font-size:66px;letter-spacing:-3px;font-weight:500;line-height:1.1}.metriclabel{font-size:17px;color:var(--muted);margin-bottom:12px}.change{display:inline-block;margin:14px 0 24px;padding:8px 12px;border-radius:7px;background:#e7eee2;color:var(--green);font-size:18px}.detail{font-size:18px;line-height:1.55;color:var(--muted)}.ruled{height:1px;background:var(--line);margin:24px 0}.config{font:18px ui-monospace,SFMono-Regular,monospace;overflow-wrap:anywhere;margin:10px 0;color:var(--ink)}
.steps{display:flex;gap:11px;margin:18px 0 10px}.step{flex:1;padding:12px 4px;border-top:3px solid #d4d8ce;font-size:15px;text-align:center;color:var(--muted)}.step.on{border-color:var(--blue);color:var(--blue);font-weight:600}
footer{display:flex;justify-content:space-between;margin-top:12px;padding-top:14px;border-top:1px solid var(--line);font-size:16px;color:var(--muted)}.small{font-size:15px;color:var(--muted)}.trail{height:3px;background:#dedfce;margin-top:16px}.trail div{height:3px;background:var(--blue);width:0}.tag{font-size:16px;margin:15px 0}.fade{animation:arrive .35s ease-out}@keyframes arrive{from{opacity:.25;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}} 
</style></head><body><div class="wrap"><div class="nav"><div class="brand">↗ COMPUTE FORECAST <span style="font-weight:400;color:var(--muted);margin-left:16px">Research notebook</span></div><div class="badge">Tinker checkpoint replay · actual saved results</div></div>
<header><div><h1 id="title">Learning which forecast to try next.</h1><div class="sub" id="subtitle">One A100 case. Four checkpoints. The regressions stay in.</div></div><div class="totals"><div><b>6</b><span>SFT runs</span></div><div><b>600</b><span>optimizer updates</span></div><div><b>42</b><span>candidate configurations</span></div></div></header>
<main><section class="sheet"><div class="sheethead"><div class="eyebrow" id="scope">A100 SXM 80GB · hyperscaler spot median</div><div class="legend" id="legend"></div></div><div class="note" id="annotation"></div><div class="chart" id="chart"></div><div class="chartfoot"><span id="axisnote"></span><span id="seriesnote"></span></div></section>
<aside id="panel"></aside></main><div class="steps" id="steps"></div><footer><span id="foot"></span><span>Saved artifacts · no live inference · prospective accuracy pending</span></footer><div class="trail"><div id="progress"></div></div></div>
<script>
const D=__DATA__;const BLUE='#355fc4',INK='#52645e',GREEN='#327c68',AMBER='#b38238';let STAGE=-1;
const money=v=>'$'+Number(v).toFixed(3),loss=v=>Number(v).toFixed(6),el=id=>document.getElementById(id);
const seg=(points,x,y,key='value')=>points.map((p,i)=>(i?'L':'M')+x(p).toFixed(2)+','+y(p[key]).toFixed(2)).join(' ');
const line=(x1,y1,x2,y2,color='#e6e7dc',dash='')=>'<line x1="'+x1+'" y1="'+y1+'" x2="'+x2+'" y2="'+y2+'" stroke="'+color+'" '+(dash?'stroke-dasharray="'+dash+'"':'')+'/>';
const txt=(x,y,t,size=15,color='#748078',anchor='start')=>'<text x="'+x+'" y="'+y+'" text-anchor="'+anchor+'" fill="'+color+'" font-size="'+size+'" font-family="Arial,sans-serif">'+t+'</text>';
const svg=s=>'<svg viewBox="0 0 1210 492" xmlns="http://www.w3.org/2000/svg">'+s+'</svg>';
const point=(x,y,c,r=5)=>'<circle cx="'+x+'" cy="'+y+'" r="'+r+'" fill="'+c+'" stroke="#fffdf7" stroke-width="2"/>';
function frameAxis(min,max,ticks=5){let s='';for(let i=0;i<=ticks;i++){const v=min+(max-min)*i/ticks,y=430-i*360/ticks;s+=line(75,y,1170,y)+txt(61,y+5,money(v),15,'#748078','end')}return s}
function price(i){
 const state=D.states[i],pts=D.retained.forecasts[state.config],hist=D.history,truth=D.retained.truth;
 const values=[...hist.map(p=>p.value),...truth.map(p=>p.value),...Object.values(D.retained.forecasts).flatMap(ps=>ps.flatMap(p=>[p.q10,p.q90]))];
 const lo=Math.min(...values),hi=Math.max(...values),pad=Math.max((hi-lo)*.14,.025),mn=Math.max(0,lo-pad),mx=hi+pad;
 const t0=Date.parse(hist[0].date),t1=Date.parse('2026-08-29'),x=p=>75+(Date.parse(p.date)-t0)/(t1-t0)*1095,y=v=>430-(v-mn)/(mx-mn)*360;
 let s=frameAxis(mn,mx),originX=x({date:D.origin});s+='<rect x="'+originX+'" y="40" width="'+(1170-originX)+'" height="390" fill="#355fc405"/>';
 const ds=hist.map(p=>({date:p.date,value:p.value}));let part=[];for(let j=0;j<ds.length;j++){if(j&&Date.parse(ds[j].date)-Date.parse(ds[j-1].date)>86400000){s+='<path d="'+seg(part,x,y)+'" fill="none" stroke="'+INK+'" stroke-width="3"/>';part=[]}part.push(ds[j])}s+='<path d="'+seg(part,x,y)+'" fill="none" stroke="'+INK+'" stroke-width="3"/>';
 s+=line(originX,40,originX,440,'#9ca89c','5 6')+txt(originX-10,30,'22 AUG · ORIGIN',13,'#68766f','end');
 const band=seg(pts,x,y,'q10')+' '+pts.slice().reverse().map(p=>'L'+x(p)+','+y(p.q90)).join(' ')+' Z';
 s+='<path d="'+band+'" fill="#355fc420"/><path d="'+seg(pts,x,y,'q50')+'" fill="none" stroke="'+BLUE+'" stroke-width="3" stroke-dasharray="7 6"/>';
 pts.forEach(p=>{const xx=x(p);s+=line(xx,y(p.q10),xx,y(p.q90),BLUE)+point(xx,y(p.q50),BLUE,6)});
 truth.forEach(p=>{s+=point(x(p),y(p.value),AMBER,5)});
 [hist[0],hist[Math.floor(hist.length/2)],{date:D.origin},{date:'2026-08-29'}].forEach(p=>s+=txt(x(p),465,p.date.slice(5).replace('-',' / '),15,'#748078','middle'));
 return svg(s);
}
function curves(){
 const colors=[INK,BLUE,'#aeb8af',GREEN,'#c5cbbf',AMBER],y=v=>430-(v-.007)/(.019-.007)*350,x=v=>80+v/100*1080;let s='';
 for(let v=.008;v<=.0181;v+=.002)s+=line(80,y(v),1160,y(v))+txt(62,y(v)+5,v.toFixed(3),15,'#748078','end');
 [0,20,50,100].forEach(v=>s+=txt(x(v),467,String(v),17,'#748078','middle'));
 D.runs.forEach((r,j)=>{const p=r.checkpoints.map(c=>({x:c.update,value:c.development_pinball})),xx=a=>x(a.x);s+='<path d="'+seg(p,xx,y)+'" fill="none" stroke="'+colors[j]+'" stroke-width="'+(j===1?4:2)+'" opacity="'+(r.objective==='hard'?.35:1)+'"/>';p.forEach(c=>s+=point(xx(c),y(c.value),colors[j],j===1?6:4));const c=r.checkpoints.find(c=>c.update===r.selected_update);s+='<circle cx="'+x(c.update)+'" cy="'+y(c.development_pinball)+'" r="11" fill="none" stroke="'+colors[j]+'" stroke-width="2"/>'});
 return svg(s);
}
function comparison(){
 const vals=[D.eval.starting,D.eval.sft],labels=['Starting policy','Development-selected SFT'],x0=290,w=770,max=.017;let s='';
 vals.forEach((v,i)=>{const yy=145+i*150;s+=txt(270,yy+26,labels[i],22,'#52645e','end')+'<rect x="'+x0+'" y="'+yy+'" width="'+v/max*w+'" height="44" rx="6" fill="'+(i?BLUE:'#a8b1a5')+'"/>'+txt(x0+v/max*w+17,yy+29,loss(v),23,INK)});
 s+=txt(290,405,'12 matched cells · 2 A100 series · 3 reused, dependent dates',22,INK);
 s+=txt(290,449,'A100 40GB worsened; pooled gain was concentrated in SXM 80GB.',17,'#748078');
 return svg(s);
}
function renderStage(k){
 STAGE=k;el('chart').classList.remove('fade');void el('chart').offsetWidth;el('chart').classList.add('fade');
 el('steps').innerHTML=['Starting weights','Update 20','Update 50','Update 100','Six-run comparison','Retrospective check'].map((s,j)=>'<div class="step '+(j===k?'on':'')+'">'+s+'</div>').join('');
 if(k<4){
 const a=D.states[k],base=D.states[0].development_pinball,delta=(a.development_pinball/base-1)*100;
 el('title').textContent='Learning which forecast to try next.';el('subtitle').textContent='One A100 case. Four checkpoints. The regressions stay in.';
 el('scope').textContent='A100 SXM 80GB · hyperscaler spot median';el('legend').innerHTML='<span><i class="dot" style="background:'+INK+'"></i>History</span><span><i class="dot" style="background:'+BLUE+'"></i>q10 / q50 / q90</span><span><i class="dot" style="background:'+AMBER+'"></i>Archived outcomes</span>';
 el('annotation').textContent=['Start with the untrained selector.','An early checkpoint gets worse.','The selected forecast changes again.','The development-selected checkpoint.'][k];el('chart').innerHTML=price(k);
 el('axisnote').textContent='USD per GPU-hour · 1, 3 and 7-day forecast points';el('seriesnote').textContent='Dashed joins are guides; no daily forecasts are implied.';
 el('panel').innerHTML='<div class="eyebrow">Operational run · soft targets · seed 17</div><h2>Checkpoint '+a.update+'</h2><div class="metriclabel">Development pinball loss · lower is better</div><div class="big">'+loss(a.development_pinball)+'</div><div class="change" style="'+(delta>0?'background:#f2e8d7;color:#9d6c27':'')+'">'+(k===0?'Starting checkpoint':Math.abs(delta).toFixed(1)+'% '+(delta>0?'higher':'lower')+' than start')+'</div><div class="detail">Score covers the full development cohort. The chart shows one fixed case.</div><div class="ruled"></div><div class="eyebrow">Chosen numerical forecaster</div><div class="config">'+a.config+'</div><div class="small">Tinker trains the selector. Numerical models produce the price quantiles.</div><div class="tag">Qwen3.5-4B · LoRA rank 16</div>';
 el('foot').textContent='Development replay · forecast origin 22 August 2026 · same case and axes throughout';
 }else if(k===4){
 el('title').textContent='Six runs. Improvement was uneven.';el('subtitle').textContent='All saved SFT checkpoints, including reversals and plateaus.';el('scope').textContent='Development forecast loss · lower is better';el('legend').innerHTML='<span>Cobalt: soft / 17</span><span>Emerald: soft / 29</span><span>Amber: soft / 43</span>';
 el('annotation').textContent='Circles mark development-selected checkpoints.';el('chart').innerHTML=curves();el('axisnote').textContent='Actual optimizer updates · evaluated at 0, 20, 50 and 100';el('seriesnote').textContent='Three hard-target runs overlap exactly.';
 el('panel').innerHTML='<div class="eyebrow">600 actual SFT optimizer updates</div><h2>Choose checkpoints using development data.</h2><div class="detail">Hard and soft decision targets.<br>Three seeds: 17, 29 and 43.<br>100 optimizer updates per run.</div><div class="ruled"></div><div class="metriclabel">Operational selection</div><div class="big" style="font-size:45px">Soft / 17</div><div class="tag">Update 100 · loss 0.009050</div><div class="detail">The lowest later evaluation score did not replace the development-selected operational policy.</div>';
 el('foot').textContent='Development cohort · 6 tasks / 3 dates · training seeds are not independent market samples';
 }else{
 el('title').textContent='A measured gain, with clear limits.';el('subtitle').textContent='The selected SFT policy improved pooled retrospective forecast loss.';el('scope').textContent='Separate retrospective evaluation · fixed eligible cells';el('legend').innerHTML='<span>Identical candidates and six-result reveal budget</span>';el('annotation').textContent='A useful result. Future accuracy still needs future tests.';el('chart').innerHTML=comparison();el('axisnote').textContent='Mean quantile pinball loss · q10 / q50 / q90';el('seriesnote').textContent='Previously inspected dates; not an untouched test.';
 el('panel').innerHTML='<div class="eyebrow">Selected SFT versus starting weights</div><h2>Retrospective pooled loss</h2><div class="big">22.8%</div><div class="change">lower pinball loss</div><div class="detail">12 matched cells across two A100 series and three dependent dates.</div><div class="ruled"></div><div class="eyebrow">RL follow-up</div><div class="tag">99 updates · 3 selected SFT parents</div><div class="detail">Additional RL benefit was not established. A post-hoc fixed portfolio also reproduces the operational terminal choices.</div>';
 el('foot').textContent='Retrospective evaluation · 29 August / 5 September / 12 September 2026 · no H100 policy claim';
 }
}
window.showTime=function(t){const k=t<5?0:t<10?1:t<15?2:t<20?3:t<25?4:5;if(k!==STAGE)renderStage(k);el('progress').style.width=Math.min(100,t/30*100)+'%'};
showTime(0);window.READY=true;
</script></body></html>'''

def build_payload(out):
    config=json.loads(Path("configs/training-progress-video.json").read_text())
    ck=json.loads(Path("docs/campaign-v2-checkpoints.json").read_text())
    status=json.loads(Path("docs/campaign-v2-final-status.json").read_text())
    bundle=fetch(status["archive"]["url"])
    if sha(bundle)!=status["archive"]["sha256"]:raise ValueError("Immutable research archive hash")
    z=zipfile.ZipFile(io.BytesIO(bundle))
    def read(member):
        raw=z.read(member)
        if sha(raw)!=status["archive"]["members"][member]["sha256"]:raise ValueError("Archive member hash: "+member)
        return json.loads(raw)
    grid=read("runs/campaign/campaign-v2-grid/v2/grid.json")
    analysis=read("runs/final/v2-analysis/analysis.json")
    runs=[r for r in ck["runs"] if r["mode"]=="sft"]
    if len(runs)!=6 or sum(r["actual_optimizer_updates"] for r in runs)!=600:raise ValueError("SFT run count")
    for r in runs:
        for p in r["checkpoints"]:
            member=f'runs/campaign/campaign-v2-policy-{r["objective"]}-{r["seed"]}/v2-policy/development-{p["update"]}.json'
            doc=read(member)
            if abs(doc["pinball"]-p["development_pinball"])>1e-12:raise ValueError("Checkpoint score source disagreement")
    op=next(r for r in runs if r["objective"]=="soft" and r["seed"]==17)
    if op["selected_update"]!=100:raise ValueError("Operational selection changed")
    states=[]
    for p in op["checkpoints"]:
        doc=read(f'runs/campaign/campaign-v2-policy-soft-17/v2-policy/development-{p["update"]}.json')
        eligible=[t for t in doc["traces"] if t["origin"]=="2026-08-22" and any("A100_SXM_80GB" in c["series_id"] for c in t["cases"])]
        if len(eligible)!=1:raise ValueError("Fixed replay task not unique")
        t=eligible[0];ids={c["series_id"] for c in t["cases"]}
        if len(ids)!=1:raise ValueError("Individual series replay requires one series")
        sid=next(iter(ids));states.append({**p,"config":t["selected_config_id"],"cases":t["cases"],"task_id":t["task_id"],"series_id":sid})
    if len({s["series_id"] for s in states})!=1 or len({s["task_id"] for s in states})!=1:raise ValueError("Unmatched checkpoint cases")
    sid=states[0]["series_id"];origin=next(g for g in grid["origins"] if g["origin"]=="2026-08-22")
    value_raw=fetch(URL+"/api/value-v5");value=json.loads(value_raw)
    permission=next(p for p in value["history"]["publication_decisions"] if p["series_id"]==sid)
    if permission["approved"] is not True:raise ValueError("Matching history publication permission required")
    history=next(s for s in value["history"]["series"] if s["id"]==sid)
    points=[p for p in history["points"] if "2026-07-11"<=p["date"]<="2026-08-22"]
    if len(points)<14 or points[-1]["date"]!="2026-08-22" or len({p["date"] for p in points})!=len(points):raise ValueError("History coverage")
    request={"run_id":origin["run_id"],"origin":origin["origin"],"series_id":sid,"configs":[s["config"] for s in states],"dataset_sha256":status["archive"]["dataset_sha256"]}
    retained=retained_forecasts.remote(request)
    truth={p["date"]:p["value"] for p in retained["truth"]}
    for s in states:
        for p in retained["forecasts"][s["config"]]:
            y=truth[p["date"]]
            score=sum(max(q*(y-p[k]),(q-1)*(y-p[k])) for q,k in zip((.1,.5,.9),("q10","q50","q90")))/3
            expected=next(c["loss"] for c in s["cases"] if c["horizon_days"]==p["horizon"])
            if abs(score-expected)>5.1e-7:raise ValueError(("Raw prediction / retained score mismatch",s["update"],p["horizon"],score,expected))
    ap=next(p for p in analysis["policies"] if p["mode"]=="sft" and p["objective"]=="soft" and p["seed"]==17)
    if abs(ap["candidate_pinball"]-.011569797542840439)>1e-12 or abs(ap["starting_pinball"]-.014995328587716763)>1e-12:raise ValueError("Evaluation score contract")
    payload={"origin":"2026-08-22","series_id":sid,"history":points,"states":states,"runs":runs,"retained":retained,"eval":{"starting":ap["starting_pinball"],"sft":ap["candidate_pinball"]},"provenance":{"research_archive_sha256":sha(bundle),"value_api_sha256":sha(value_raw),"permission":permission,"history_metadata":{k:v for k,v in history.items() if k!="points"},"checkpoint_source_sha256":sha(Path("docs/campaign-v2-checkpoints.json").read_bytes()),"source_commit":os.environ["GITHUB_SHA"]}}
    write(out/"replay-data.json",payload)
    return payload

@app.local_entrypoint()
def main():
    from playwright.sync_api import sync_playwright
    from PIL import Image,ImageDraw
    out=Path("artifacts/training-progress-video");out.mkdir(parents=True,exist_ok=True)
    payload=build_payload(out);html=HTML.replace("__DATA__",json.dumps(payload,allow_nan=False).replace("</","<\\/"))
    (out/"replay.html").write_text(html)
    errors=[];timeline=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={"width":1920,"height":1080},record_video_dir=str(out/"raw"),record_video_size={"width":1920,"height":1080},reduced_motion="reduce")
        init=time.perf_counter();page=context.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content(html,wait_until="load",timeout=90000);page.wait_for_function("window.READY===true")
        page.evaluate("document.fonts.ready");page.wait_for_timeout(600)
        if not page.evaluate("document.documentElement.scrollWidth<=innerWidth && document.documentElement.scrollHeight<=innerHeight"):raise ValueError("Film canvas overflow")
        start=time.perf_counter();offset=start-init
        for i in range(301):
            t=i/10;remain=start+t-time.perf_counter()
            if remain>0:page.wait_for_timeout(remain*1000)
            page.evaluate("(t)=>showTime(t)",t)
            if i%50==0:timeline.append({"second":t,"stage":page.evaluate("STAGE")})
        page.wait_for_timeout(400);video=page.video;context.close();raw=video.path();browser.close()
    if errors:raise ValueError(errors)
    movie=out/"terminal-30s.mp4"
    subprocess.run(["ffmpeg","-y","-ss",str(offset),"-i",str(raw),"-an","-vf","trim=duration=30,setpts=PTS-STARTPTS,fps=30,format=yuv420p","-t","30","-c:v","libx264","-preset","medium","-crf","18","-movflags","+faststart",str(movie)],check=True,capture_output=True)
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(movie)]))
    stream=next(s for s in probe["streams"] if s["codec_type"]=="video")
    assert stream["codec_name"]=="h264" and stream["width"]==1920 and stream["height"]==1080 and stream["r_frame_rate"]=="30/1"
    duration=float(probe["format"]["duration"]);assert abs(duration-30)<.05 and movie.stat().st_size<50_000_000
    sheet=Image.new("RGB",(1920,768),"#f6f2e8");draw=ImageDraw.Draw(sheet)
    for i,sec in enumerate((2,7,12,17,22,27)):
        frame=out/f"frame-{sec}.png";subprocess.run(["ffmpeg","-y","-ss",str(sec),"-i",str(movie),"-frames:v","1",str(frame)],check=True,capture_output=True)
        im=Image.open(frame).convert("RGB");assert im.getextrema()[0][1]-im.getextrema()[0][0]>50
        if sec==17:im.save(out/"poster.png")
        im.thumbnail((640,360));x=i%3*640;y=i//3*384;sheet.paste(im,(x,y));draw.text((x+12,y+364),f"{sec}s / actual saved checkpoint replay",fill="#263d3d")
    sheet.save(out/"contact-sheet.png")
    manifest={"schema_version":1,"kind":"saved_checkpoint_forecast_replay","recorded_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source_commit":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"output_seconds":duration,"width":1920,"height":1080,"fps":30,"audio":False,"live_inference":False,"new_training":False,"new_numerical_fits":False,"series_id":payload["series_id"],"development_replay_origin":payload["origin"],"checkpoints":[{k:s[k] for k in ("update","checkpoint_id","development_pinball","config")} for s in payload["states"]],"timeline":timeline,"provenance":payload["provenance"],"replay_data_sha256":sha((out/"replay-data.json").read_bytes()),"raw_numerical_file_hashes":payload["retained"]["file_hashes"],"limitations":["Retrospective development replay; forecast connections are visual guides between actual 1,3,7-day points.","Development aggregate scores and the single-case price chart have different scopes.","Separate 12-cell evaluation used three previously inspected dependent dates and two A100 series.","Additional RL benefit was not established; prospective improvement remains pending."],"files":{p.name:{"sha256":sha(p.read_bytes()),"bytes":p.stat().st_size} for p in (movie,out/"poster.png",out/"contact-sheet.png")}}
    write(out/"manifest.json",manifest)
    vol=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
    prefix="/terminal-v10/media/"+os.environ["GITHUB_RUN_ID"]+"/"
    with vol.batch_upload() as upload:
        for name in ("terminal-30s.mp4","poster.png","contact-sheet.png","manifest.json"):upload.put_file(str(out/name),prefix+name)
    base=URL+"/terminal/media/"+os.environ["GITHUB_RUN_ID"]+"/"
    public_movie=fetch(base+"terminal-30s.mp4");assert sha(public_movie)==manifest["files"]["terminal-30s.mp4"]["sha256"]
    response=urllib.request.urlopen(urllib.request.Request(base+"terminal-30s.mp4",headers={"Range":"bytes=0-1023"}),timeout=90)
    assert response.status==206 and len(response.read())==1024
    receipt={"status":"passed","video_url":base+"terminal-30s.mp4","poster_url":base+"poster.png","contact_sheet_url":base+"contact-sheet.png","manifest_url":base+"manifest.json","duration_seconds":duration,"video_sha256":sha(public_movie),"source_commit":os.environ["GITHUB_SHA"],"range_request_verified":True}
    write(out/"publication.json",receipt);print("TRAINING_VIDEO_REPORT:"+json.dumps(receipt),flush=True)
    from .publication_terminal_v10 import publish
    names=("manifest.json","publication.json","contact-sheet.png","poster.png","replay-data.json","replay.html")
    dest="results/terminal-v10/runs/"+os.environ["GITHUB_RUN_ID"]+"/training-video/"
    commit=publish({dest+n:(out/n).read_bytes() for n in names})
    print("TRAINING_VIDEO_PUBLICATION:"+commit,flush=True)
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write("## Saved-checkpoint forecast replay\n\n"+receipt["video_url"]+"\n\n30 seconds, 1920×1080 H.264. Actual saved forecasts and checkpoint scores; no new training or live inference.\n\nEvidence commit: "+commit+"\n")
