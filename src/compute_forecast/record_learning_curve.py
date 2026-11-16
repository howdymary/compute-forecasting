"""One continuous, deterministic learning-curve film from immutable saved SFT results."""
from __future__ import annotations
import argparse,base64,hashlib,io,json,math,os,subprocess,time,urllib.request,zipfile
from pathlib import Path
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
def sha(b):return hashlib.sha256(b).hexdigest()
def fetch(url):return urllib.request.urlopen(url,timeout=90).read()
def write(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n")
def inputs(out):
    config_raw=Path("configs/learning-curve-video.json").read_bytes();cfg=json.loads(config_raw)
    if (cfg["output_seconds"],cfg["fps"],cfg["frames"],cfg["width"],cfg["height"])!=(30,30,900,1920,1080):raise ValueError("Locked render configuration")
    registry=Path("docs/campaign-v2-checkpoints.json").read_bytes()
    status_raw=Path("docs/campaign-v2-final-status.json").read_bytes()
    ck=json.loads(registry);status=json.loads(status_raw)
    legacy=Path("results/terminal-v10/runs/43815591384/training-video")
    lm=json.loads((legacy/"manifest.json").read_text())
    if sha((legacy/"replay-data.json").read_bytes())!=lm["replay_data_sha256"]:raise ValueError("Previous replay identity")
    old=json.loads((legacy/"replay-data.json").read_text())
    raw=fetch(status["archive"]["url"])
    if sha(raw)!=status["archive"]["sha256"]:raise ValueError("Immutable archive identity")
    archive=zipfile.ZipFile(io.BytesIO(raw))
    def member(name):
        raw=archive.read(name)
        if sha(raw)!=status["archive"]["members"][name]["sha256"]:raise ValueError("Archive member hash")
        return json.loads(raw)
    runs=[];members={};denominators=set();origins=set()
    for r in ck["runs"]:
        if r["mode"]!="sft":continue
        oid=f'{r["objective"]}-{r["seed"]}'
        if r["actual_optimizer_updates"]!=100 or [c["update"] for c in r["checkpoints"]]!=[0,20,50,100]:raise ValueError("SFT checkpoint contract")
        points=[]
        for c in r["checkpoints"]:
            name=f'runs/campaign/campaign-v2-policy-{oid}/v2-policy/development-{c["update"]}.json'
            d=member(name);members[name]=status["archive"]["members"][name]["sha256"]
            cases=[case for t in d["traces"] for case in t["cases"]]
            n=sum(t["n_cells"] for t in d["traces"])
            if n!=len(cases) or any(t["n_cells"]!=len(t["cases"]) for t in d["traces"]):raise ValueError("Development denominator")
            reconstructed=sum(v["loss"] for v in cases)/n
            if not math.isclose(d["pinball"],c["development_pinball"],abs_tol=1e-14) or not math.isclose(reconstructed,d["pinball"],abs_tol=1e-14):raise ValueError("Checkpoint arithmetic")
            denominators.add((n,len(d["traces"])));origins.add(tuple(sorted({t["origin"] for t in d["traces"]})))
            points.append({"update":c["update"],"loss":c["development_pinball"],"checkpoint_id":c["checkpoint_id"]})
        selected=min(points,key=lambda p:(p["loss"],p["update"]))["update"]
        if selected!=r["selected_update"]:raise ValueError("Original selection / earliest-tie rule")
        oldrun=next(x for x in old["runs"] if x["objective"]==r["objective"] and x["seed"]==r["seed"])
        if oldrun["checkpoints"]!=r["checkpoints"] or oldrun["selected_update"]!=selected:raise ValueError("Previous film evidence differs")
        runs.append({"id":oid,"objective":r["objective"],"seed":r["seed"],"selected":selected,"points":points})
    if len(runs)!=6 or len(denominators)!=1 or len(origins)!=1:raise ValueError("Unmatched development cohorts")
    groups={}
    for r in runs:groups.setdefault(tuple((p["update"],p["loss"]) for p in r["points"]),[]).append(r)
    grouped=[]
    for key,rr in groups.items():
        grouped.append({"id":"hard" if len(rr)>1 else rr[0]["id"],"runs":[r["id"] for r in rr],"points":rr[0]["points"],"selected":rr[0]["selected"]})
    hard=next(g for g in grouped if g["id"]=="hard")
    if set(hard["runs"])!={"hard-17","hard-29","hard-43"} or len(grouped)!=4:raise ValueError("Exact trajectory grouping")
    shared={}
    for r in runs:
        for a,b in zip(r["points"],r["points"][1:]):shared.setdefault((a["update"],a["loss"],b["update"],b["loss"]),[]).append(r["id"])
    segments=[{"from_update":k[0],"from_loss":k[1],"to_update":k[2],"to_loss":k[3],"members":v} for k,v in shared.items()]
    op=next(r for r in runs if r["id"]=="soft-17")
    reduction=(1-op["points"][-1]["loss"]/op["points"][0]["loss"])*100
    if abs(reduction-38.94260079742078)>1e-10:raise ValueError("Development reduction")
    if len({r["points"][2]["loss"] for r in runs})!=1:raise ValueError("Update-50 annotation")
    if sum(r["points"][-1]["loss"]==hard["points"][-1]["loss"] for r in runs)!=5:raise ValueError("Final tie annotation")
    official=fetch(URL+"/files/forecasts.csv")
    if sha(official)!=status["official_csv_sha256"]:raise ValueError("Official CSV changed")
    font=fetch(URL+"/notebook-assets/caveat-f84acf2c.ttf");license_bytes=fetch(URL+"/notebook-assets/OFL.txt")
    (out/"OFL.txt").write_bytes(license_bytes)
    n,nt=next(iter(denominators));dates=list(next(iter(origins)))
    payload={"schema_version":2,"runs":runs,"groups":grouped,"shared_segments":segments,"development_cells":n,"development_tasks":nt,"development_dates":dates,"operational":"soft-17","development_reduction_percent":reduction,"y_domain":[.008,.020],"x_domain":[0,100],"provenance":{"source_commit":os.environ.get("GITHUB_SHA"),"config_sha256":sha(config_raw),"registry_sha256":sha(registry),"status_sha256":sha(status_raw),"archive_url":status["archive"]["url"],"archive_sha256":sha(raw),"member_sha256":members,"previous_replay_sha256":lm["replay_data_sha256"],"official_csv_sha256":sha(official),"font_sha256":sha(font),"font_license_sha256":sha(license_bytes)}}
    write(out/"chart-data.json",payload)
    return payload,font

HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Compute Forecast — Learning curves</title>
<style>@font-face{font-family:Fieldnote;src:url(data:font/ttf;base64,__FONT__) format("truetype");font-weight:400 700}
*{box-sizing:border-box}html,body{width:1920px;height:1080px;overflow:hidden;margin:0;background:#f7f3e9}svg{display:block;width:1920px;height:1080px}text{font-family:Arial,sans-serif;font-variant-numeric:tabular-nums}text.book{font-family:Georgia,serif}text.hand{font-family:Fieldnote,cursive}#metric{font-variant-numeric:tabular-nums}.guide{stroke-linecap:round;stroke-linejoin:round;fill:none}.dot{fill:#f7f3e9}.select{fill:none;stroke-width:2.6}.notes text{text-anchor:middle}#player{position:fixed;left:0;right:0;bottom:0;background:#f7f3e9e8;padding:8px 32px;display:flex;gap:20px;align-items:center;font:16px Arial}#player input{flex:1}button{font:inherit}
</style></head><body>
<svg id="figure" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" role="img" aria-label="Six SFT runs, development pinball loss versus optimizer updates.">
<defs><pattern id="paper" width="64" height="64" patternUnits="userSpaceOnUse"><path d="M64 0H0V64" fill="none" stroke="#455d4f" stroke-width=".5" opacity=".035"/></pattern><clipPath id="reveal"><rect id="clip" x="184" y="236" width="32" height="606"/></clipPath></defs>
<rect width="1920" height="1080" fill="#f7f3e9"/><rect width="1920" height="1080" fill="url(#paper)"/>
<text x="80" y="57" fill="#516963" font-size="16" letter-spacing="2.8">COMPUTE FORECAST / TINKER STUDY</text>
<text x="80" y="125" class="book" fill="#263d3e" font-size="55" letter-spacing="-1.2">Learning which forecast to try next.</text>
<text x="82" y="169" fill="#65766f" font-size="25">Six training runs. Four saved checkpoints. One uneven path to better selection.</text>
<g id="metric" opacity="0"><text x="1836" y="99" fill="#315dc1" font-size="55" text-anchor="end" letter-spacing="-1">38.9%</text><text x="1836" y="133" fill="#315dc1" font-size="20" text-anchor="end">lower development loss</text><text x="1836" y="162" fill="#65766f" font-size="17" text-anchor="end">soft / 17 · update 100 versus 0</text></g>
<text x="200" y="223" font-size="19" fill="#566e65">Development pinball loss</text><text x="1430" y="223" font-size="19" fill="#566e65" text-anchor="end">↓ Lower is better</text>
<g id="axes"></g><g id="paths" clip-path="url(#reveal)"></g><g id="points"></g><g id="selected"></g>
<g id="earlykey"></g><g id="labels"></g><g id="pointvalues"></g>
<g id="startnote"><text x="238" y="549" font-size="21" fill="#718078">Shared starting weights</text></g>
<g id="spikenote" opacity="0"><path d="M595 318 C552 298 523 282 461 322" stroke="#315dc1" stroke-width="1.4" fill="none"/><path d="M461 322 l11 -1 m-11 1 l4 -10" stroke="#315dc1" stroke-width="1.4" fill="none"/><text x="605" y="325" class="hand" font-size="31" fill="#315dc1">A step backward, first.</text></g>
<g id="same50" opacity="0"><text x="815" y="615" class="hand" text-anchor="middle" font-size="31" fill="#61736c">All six share this score.</text><path d="M816 624 Q823 635 815 647" fill="none" stroke="#829087" stroke-width="1.3"/></g>
<text x="815" y="903" fill="#4d655e" text-anchor="middle" font-size="21">Actual optimizer updates</text>
<g class="notes" id="notes"></g>
<text x="80" y="999" fill="#7c8982" font-size="17">Points are measured checkpoints. Straight joins guide the eye; intermediate losses were not evaluated.</text>
<line x1="80" y1="1023" x2="1840" y2="1023" stroke="#d6dbcf"/>
<text x="80" y="1056" fill="#65776d" font-size="17">Saved checkpoints · retrospective development results</text>
<text x="1840" y="1056" fill="#65776d" font-size="17" text-anchor="end">6 tasks · 3 dependent dates · model: Qwen3.5-4B</text>
</svg>
<div id="player"><button id="play">Play / pause</button><input type="range" id="scrub" min="0" max="30" step=".01" value="0" aria-label="Video time"><span id="clock">0.00s</span></div>
<script>
const D=__DATA__,S='http://www.w3.org/2000/svg',PAPER='#f7f3e9',C={hard:'#7b8880','soft-17':'#315dc1','soft-29':'#2e7b69','soft-43':'#b18a46'};
const X=u=>200+12.3*u,Y=v=>825-(v-.008)/.012*585;
const ease=t=>{t=Math.max(0,Math.min(1,t));return t*t*(3-2*t)},ramp=(t,a,b)=>ease((t-a)/(b-a)),range=(t,a,b,c,d)=>ramp(t,a,b)*(1-ramp(t,c,d));
function add(parent,tag,attrs,text){const e=document.createElementNS(S,tag);for(const[k,v]of Object.entries(attrs||{}))e.setAttribute(k,String(v));if(text!==undefined)e.textContent=text;document.getElementById(parent).appendChild(e);return e}
function tx(parent,x,y,t,size=18,color='#6f8076',more={}){return add(parent,'text',{x,y,fill:color,'font-size':size,...more},t)}
for(let i=0;i<=6;i++){const v=.008+i*.002,yy=Y(v);add('axes','line',{x1:200,x2:1430,y1:yy,y2:yy,stroke:'#dce0d5','stroke-width':1,opacity:i===0?.85:.65});tx('axes',175,yy+6,v.toFixed(3),18,'#7b8980',{'text-anchor':'end'})}
for(const u of [0,20,50,100]){add('axes','line',{x1:X(u),x2:X(u),y1:240,y2:825,stroke:'#dce0d5','stroke-width':1,opacity:.45,'stroke-dasharray':'2 7'});tx('axes',X(u),862,String(u),22,'#586e63',{'text-anchor':'middle'})}
const groupBy=Object.fromEntries(D.groups.map(g=>[g.id,g]));
for(const id of ['hard','soft-17','soft-29','soft-43']){const g=groupBy[id],path=g.points.map((p,i)=>(i?'L':'M')+X(p.update)+','+Y(p.loss)).join(' ');add('paths','path',{id:'path-'+id,d:path,stroke:C[id],'stroke-width':id==='hard'?6:id==='soft-17'?4.7:3,'stroke-dasharray':id==='soft-43'?'5 10':id==='hard'?'2 7':'',opacity:id==='hard'?.55:1,class:'guide','data-members':g.runs.join(',')})}
const pts=[],sels=[];
for(const g of D.groups){for(const p of g.points){const e=add('points','circle',{cx:X(p.update),cy:Y(p.loss),r:g.id==='soft-17'?5.8:4.3,stroke:C[g.id],'stroke-width':2.2,class:'dot',opacity:0,'data-update':p.update,'data-loss':p.loss,'data-members':g.runs.join(',')});pts.push({e,p,id:g.id});}const p=g.points.find(p=>p.update===g.selected);const e=add('selected','circle',{cx:X(p.update),cy:Y(p.loss),r:8,stroke:C[g.id],class:'select',opacity:0,'data-update':p.update,'data-loss':p.loss,'data-members':g.runs.join(',')});sels.push({e,p,id:g.id});}
const keydefs=[['hard',200,'Hard · seeds 17 / 29 / 43'],['soft-17',629,'Soft · seed 17'],['soft-29',925,'Soft · seed 29'],['soft-43',1225,'Soft · seed 43']];
for(const[id,x,label]of keydefs){add('earlykey','line',{x1:x,x2:x+28,y1:197,y2:197,stroke:C[id],'stroke-width':id==='hard'?4:3,'stroke-dasharray':id==='soft-43'?'4 5':id==='hard'?'2 5':''});tx('earlykey',x+40,203,label,17,C[id])}
const labels=[{id:'hard',y:576,title:'Hard · seeds 17 / 29 / 43',sub:'identical path · kept update 20'},{id:'soft-29',y:641,title:'Soft · seed 29',sub:'kept update 20'},{id:'soft-43',y:706,title:'Soft · seed 43',sub:'kept update 50'},{id:'soft-17',y:790,title:'Soft · seed 17',sub:'kept update 100 · operational'}];
for(const a of labels){const g=groupBy[a.id],end=g.points.at(-1),yy=Y(end.loss);const layer=add('labels','g',{id:'label-'+a.id,opacity:0});const append=(tag,attrs,t)=>{const e=document.createElementNS(S,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(t)e.textContent=t;layer.appendChild(e);return e};append('path',{d:'M'+(X(100)+10)+','+yy+' L1463,'+yy+' L1500,'+(a.y-7)+' L1515,'+(a.y-7),stroke:C[a.id],'stroke-width':1.4,fill:'none',opacity:.7});append('text',{x:1530,y:a.y,fill:C[a.id],'font-size':a.id==='hard'?22:25},a.title);append('text',{x:1530,y:a.y+26,fill:'#7b8980','font-size':17},a.sub);}
const values=[{u:0,v:D.runs[0].points[0].loss,x:219,y:475,anchor:'start',id:'v0'},{u:20,v:groupBy['soft-17'].points[1].loss,x:441,y:309,anchor:'middle',id:'v20'},{u:50,v:groupBy['soft-17'].points[2].loss,x:815,y:697,anchor:'middle',id:'v50'},{u:100,v:groupBy['soft-17'].points[3].loss,x:1416,y:738,anchor:'end',id:'v100'}];
for(const v of values)tx('pointvalues',v.x,v.y,v.v.toFixed(6),20,v.u===100?'#315dc1':'#697c72',{'text-anchor':v.anchor,id:v.id,opacity:0});
const noteSpecs=[{id:'n0',text:'Start together. Let the experiments separate them.',a:0,b:.9,c:2.5,d:3.1},{id:'n1',text:'Two soft-target runs regress at update 20.',a:6,b:6.6,c:8.4,d:8.9},{id:'n2',text:'At update 50, all six have the same development loss.',a:11.7,b:12.2,c:13.3,d:13.8},{id:'n3',text:'Rings mark the checkpoints originally kept.',a:18,b:18.6,c:23.8,d:24.4},{id:'n4',text:'Improvement is not a straight line.',a:24.3,b:25,c:31,d:32}];
for(const n of noteSpecs)tx('notes',960,955,n.text,37,'#315dc1',{class:'hand',id:n.id,opacity:0});
const measuredTime={0:0,20:6,50:11.7,100:17.8};
function progress(t){if(t<2.8)return 0;if(t<6)return 20*ramp(t,2.8,6);if(t<8.7)return 20;if(t<11.7)return 20+30*ramp(t,8.7,11.7);if(t<13.6)return 50;if(t<17.8)return 50+50*ramp(t,13.6,17.8);return 100}
function render(t){const u=progress(t);document.getElementById('clip').setAttribute('width',X(u)-184+16);document.getElementById('paths').setAttribute('opacity',ramp(t,.7,1.4));
for(const a of pts)a.e.setAttribute('opacity',ramp(t,measuredTime[a.p.update],measuredTime[a.p.update]+.5));
const ringTime={hard:18,'soft-29':19,'soft-43':20,'soft-17':21.2};
for(const a of sels){const k=ramp(t,ringTime[a.id],ringTime[a.id]+.8);a.e.setAttribute('opacity',k);a.e.setAttribute('r',8+3*Math.sin(Math.PI*k));}
for(let i=0;i<labels.length;i++)document.getElementById('label-'+labels[i].id).setAttribute('opacity',ramp(t,18.1+i*.55,18.9+i*.55));
document.getElementById('earlykey').setAttribute('opacity',1-ramp(t,17.8,18.7));
document.getElementById('startnote').setAttribute('opacity',range(t,.2,1,2.1,2.8));
document.getElementById('spikenote').setAttribute('opacity',range(t,6.3,6.8,8.2,8.7));
document.getElementById('same50').setAttribute('opacity',range(t,11.9,12.3,13.1,13.6));
document.getElementById('metric').setAttribute('opacity',ramp(t,24.6,25.5));
for(const v of values)document.getElementById(v.id).setAttribute('opacity',ramp(t,measuredTime[v.u]+.35,measuredTime[v.u]+.8));
for(const n of noteSpecs)document.getElementById(n.id).setAttribute('opacity',range(t,n.a,n.b,n.c,n.d));
document.getElementById('scrub').value=t;document.getElementById('clock').textContent=t.toFixed(2)+'s';return {time:t,reveal_update:u,clip_width:X(u)-184+16,geometry:D.groups.map(g=>({id:g.id,points:g.points.map(p=>({update:p.update,loss:p.loss,x:X(p.update),y:Y(p.loss)}))}))};}
window.renderFrame=render;
let playing=false,start=0,current=0;function loop(ts){if(!playing)return;current=Math.min(30,(ts-start)/1000);render(current);if(current<30)requestAnimationFrame(loop);else playing=false}
document.getElementById('play').onclick=()=>{playing=!playing;if(playing){if(current>=30)current=0;start=performance.now()-current*1000;requestAnimationFrame(loop)}};
document.getElementById('scrub').oninput=e=>{playing=false;current=Number(e.target.value);render(current)};
window.prepareCapture=()=>{playing=false;document.getElementById('player').style.display='none';render(0)};
render(0);window.READY=true;
</script></body></html>'''

def validate_page(page,payload):
    page.evaluate("prepareCapture()")
    positions=page.locator("#points circle").evaluate_all("(es)=>es.map(e=>({u:+e.dataset.update,loss:+e.dataset.loss,x:+e.getAttribute('cx'),y:+e.getAttribute('cy'),members:e.dataset.members.split(',')}))")
    expanded={}
    for p in positions:
        if abs(p["x"]-(200+12.3*p["u"]))>1e-9 or abs(p["y"]-(825-(p["loss"]-.008)/.012*585))>1e-9:raise ValueError("Altered point geometry")
        for rid in p["members"]:expanded[rid,p["u"]]=p["loss"]
    expected={(r["id"],p["update"]):p["loss"] for r in payload["runs"] for p in r["points"]}
    if expanded!=expected or len(expanded)!=24:raise ValueError("Missing or altered plotted checkpoints")
    selected=page.locator("#selected circle").evaluate_all("(es)=>es.map(e=>({u:+e.dataset.update,loss:+e.dataset.loss,members:e.dataset.members.split(',')}))")
    if {rid:p["u"] for p in selected for rid in p["members"]}!={r["id"]:r["selected"] for r in payload["runs"]}:raise ValueError("Selected markers")
    samples=[page.evaluate("(t)=>renderFrame(t)",i/4) for i in range(121)]
    if any(a["reveal_update"]>b["reveal_update"] for a,b in zip(samples,samples[1:])):raise ValueError("Nonmonotone reveal geometry")
    for s in samples:
        if s["geometry"]!=samples[0]["geometry"]:raise ValueError("Measured values moved during animation")
    # Inspect every visible text rectangle for page clipping, at each major stage.
    clipping=[]
    for t in (1,7,12.6,18.5,23,28):
        page.evaluate("(t)=>renderFrame(t)",t)
        clipping+=page.locator("svg text").evaluate_all("(es)=>es.filter(e=>{let p=e;while(p&&p.tagName.toLowerCase()!=='svg'){if(+p.getAttribute('opacity')===0&&p.hasAttribute('opacity'))return false;p=p.parentElement}return true}).map(e=>({text:e.textContent,b:e.getBoundingClientRect().toJSON()})).filter(v=>v.b.x<0||v.b.y<0||v.b.right>1920||v.b.bottom>1080)")
    if clipping:raise ValueError(("Clipped text",clipping))
    page.evaluate("renderFrame(28)")
    labels=page.locator("#labels text").evaluate_all("(es)=>es.map(e=>({text:e.textContent,b:e.getBoundingClientRect().toJSON()}))")
    for i,a in enumerate(labels):
        for b in labels[i+1:]:
            if min(a["b"]["right"],b["b"]["right"])>max(a["b"]["left"],b["b"]["left"]) and min(a["b"]["bottom"],b["b"]["bottom"])>max(a["b"]["top"],b["b"]["top"]):raise ValueError("Direct label collision")
    font=page.evaluate("document.fonts.check('32px Fieldnote')")
    if not font:raise ValueError("Handwritten font failed")
    return {"status":"passed","source_checkpoints":24,"visible_full_trajectory_groups":4,"represented_runs":6,"selected_markers_verified":6,"geometry_samples":121,"fixed_axes":True,"point_geometry_immutable":True,"numeric_score_interpolation":False,"label_collisions":[],"page_clipping":[],"embedded_font_loaded":font,"animation_schedule":{"0-2.8":"common starting checkpoint","2.8-6":"reveal to update 20","6-8.7":"hold early regressions","8.7-11.7":"reveal to update 50","11.7-13.6":"hold six-way equal score","13.6-17.8":"reveal to update 100","18-24.6":"original selection rings and direct labels","24.6-30":"hold completed chart and development-only reduction"}}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--no-publish",action="store_true");args=parser.parse_args()
    from playwright.sync_api import sync_playwright
    from PIL import Image,ImageDraw
    out=Path("artifacts/learning-curve-video");out.mkdir(parents=True,exist_ok=True)
    payload,font=inputs(out)
    html=HTML.replace("__FONT__",base64.b64encode(font).decode()).replace("__DATA__",json.dumps(payload,allow_nan=False).replace("</","<\\/"))
    (out/"replay.html").write_text(html)
    movie=out/"terminal-30s.mp4";errors=[];started=time.perf_counter()
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={"width":1920,"height":1080},device_scale_factor=1)
        page.on("pageerror",lambda e:errors.append(str(e)));page.set_content(html,wait_until="load");page.evaluate("document.fonts.ready");page.wait_for_function("window.READY===true")
        report=validate_page(page,payload)
        if errors:raise ValueError(errors)
        write(out/"validation.json",report)
        for t in (1,7,12.6,18.5,23,28):
            page.evaluate("(t)=>renderFrame(t)",t);page.screenshot(path=str(out/f"stage-{t}.png"))
        with (out/"encoder.log").open("wb") as log:
            encoder=subprocess.Popen(["ffmpeg","-y","-f","image2pipe","-vcodec","png","-framerate","30","-i","pipe:0","-an","-c:v","libx264","-preset","medium","-crf","17","-pix_fmt","yuv420p","-movflags","+faststart","-frames:v","900",str(movie)],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
            try:
                for i in range(900):
                    page.evaluate("(t)=>renderFrame(t)",i/30)
                    encoder.stdin.write(page.screenshot(type="png",animations="disabled",caret="hide"))
                    if i%150==0:print("LEARNING_FRAME:"+json.dumps({"frame":i,"seconds":i/30}),flush=True)
                encoder.stdin.close()
                if encoder.wait(timeout=180):raise ValueError("Encoding failed; inspect encoder.log")
            except BaseException:
                encoder.kill();encoder.wait();raise
        browser.close()
    if errors:raise ValueError(errors)
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(movie)]))
    v=next(s for s in probe["streams"] if s["codec_type"]=="video");duration=float(probe["format"]["duration"])
    assert v["codec_name"]=="h264" and (v["width"],v["height"])==(1920,1080) and v["r_frame_rate"]=="30/1" and int(v["nb_frames"])==900 and abs(duration-30)<.001
    assert movie.stat().st_size<50_000_000
    sheet=Image.new("RGB",(1920,768),"#f7f3e9");draw=ImageDraw.Draw(sheet)
    for i,sec in enumerate((1,7,12.6,18.5,23,28)):
        frame=out/f"encoded-{sec}.png";subprocess.run(["ffmpeg","-y","-ss",str(sec),"-i",str(movie),"-frames:v","1",str(frame)],check=True,capture_output=True)
        im=Image.open(frame).convert("RGB")
        if sec==28:im.save(out/"poster.png")
        im.thumbnail((640,360));xx=i%3*640;yy=i//3*384;sheet.paste(im,(xx,yy));draw.text((xx+12,yy+364),f"{sec}s / one continuous chart",fill="#263d3e")
    sheet.save(out/"contact-sheet.png")
    # Encoded transition frames, not just source-page screenshots.
    strip=Image.new("RGB",(1920,1152),"#f7f3e9");sd=ImageDraw.Draw(strip)
    for i,sec in enumerate((3.0,3.3,3.6,3.9,4.2,4.5,4.8,5.1,5.4)):
        frame=out/f"motion-{i}.png";subprocess.run(["ffmpeg","-y","-ss",str(sec),"-i",str(movie),"-frames:v","1",str(frame)],check=True,capture_output=True)
        im=Image.open(frame).convert("RGB");im.thumbnail((640,360));xx=i%3*640;yy=i//3*384;strip.paste(im,(xx,yy));sd.text((xx+12,yy+364),f"Encoded transition / {sec:.1f}s",fill="#263d3e")
    strip.save(out/"motion-strip.png")
    caption="What does learning to choose forecasting experiments look like? Six Tinker SFT runs, all saved checkpoints, including regressions and plateaus. Soft/17 ends with 38.9% lower DEVELOPMENT loss than its starting checkpoint. Retrospective results; prospective accuracy remains unestablished. Rings mark the original development-selected checkpoints."
    (out/"caption.txt").write_text(caption+"\n")
    report.update({"encoded_frames":900,"encoded_seconds":duration,"fps":30,"codec":"h264","resolution":[1920,1080],"browser_errors":errors,"renderer_seconds":time.perf_counter()-started})
    write(out/"validation.json",report)
    manifest={"schema_version":2,"kind":"continuous_saved_checkpoint_learning_curve","source_commit":os.environ.get("GITHUB_SHA"),"run_id":os.environ.get("GITHUB_RUN_ID"),"recorded_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"output_seconds":duration,"fps":30,"frames":900,"resolution":[1920,1080],"deterministic_frame_times":True,"live_inference":False,"new_training":False,"new_numerical_experiments":False,"scope":"Retrospective development only: six A100 tasks across three dependent dates. No separate evaluation score is plotted.","grouping":"Three hard-target runs share exactly one path. Other coincident segments retain exact coordinates; stacked endpoint labels identify all six runs.","straight_join_semantics":"Visual guides between measured checkpoints; no intermediate loss measurements or spline smoothing","provenance":payload["provenance"],"data_sha256":sha((out/"chart-data.json").read_bytes()),"files":{f.name:{"sha256":sha(f.read_bytes()),"bytes":f.stat().st_size} for f in (movie,out/"poster.png",out/"contact-sheet.png",out/"motion-strip.png",out/"validation.json")}}
    write(out/"manifest.json",manifest)
    if args.no_publish:print("LEARNING_VIDEO_LOCAL_RENDER:"+json.dumps(report));return
    import modal
    volume=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2);run=os.environ["GITHUB_RUN_ID"]
    with volume.batch_upload() as upload:
        for name in ("terminal-30s.mp4","poster.png","contact-sheet.png","manifest.json"):upload.put_file(str(out/name),"/terminal-v10/media/"+run+"/"+name)
    base=URL+"/terminal/media/"+run+"/";public=fetch(base+"terminal-30s.mp4")
    if sha(public)!=manifest["files"]["terminal-30s.mp4"]["sha256"]:raise ValueError("Public video hash")
    response=urllib.request.urlopen(urllib.request.Request(base+"terminal-30s.mp4",headers={"Range":"bytes=0-1023"}),timeout=90)
    if response.status!=206 or len(response.read())!=1024:raise ValueError("Video range playback")
    receipt={"status":"passed","video_url":base+"terminal-30s.mp4","preview_url":base+"poster.png","manifest_url":base+"manifest.json","duration":duration,"width":1920,"height":1080,"fps":30,"sha256":sha(public),"implementation_commit":os.environ["GITHUB_SHA"],"range_verified":True}
    write(out/"publication.json",receipt)
    from .publication_terminal_v10 import publish
    names=("manifest.json","publication.json","poster.png","contact-sheet.png","motion-strip.png","validation.json","chart-data.json","replay.html","caption.txt","OFL.txt")
    dest="results/terminal-v10/runs/"+run+"/learning-curve/"
    commit=publish({dest+n:(out/n).read_bytes() for n in names})
    print("LEARNING_VIDEO_REPORT:"+json.dumps(receipt),flush=True);print("LEARNING_VIDEO_PUBLICATION:"+commit,flush=True)
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write("## One continuous learning-curve film\n\n"+receipt["video_url"]+"\n\n30 seconds, 900 deterministic frames, six SFT runs, 24 verified source checkpoints. Development results only; no new training.\n\nEvidence commit: "+commit+"\n")
if __name__=="__main__":main()
