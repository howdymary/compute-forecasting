"""Synchronized saved-checkpoint price forecasts and six-run learning curves."""
from __future__ import annotations
import argparse,base64,hashlib,io,json,math,os,subprocess,time,zipfile,urllib.request
from datetime import date,timedelta
from pathlib import Path
from .record_learning_curve import inputs as learning_inputs,sha,fetch,write,URL
TIMES=(0.0,6.0,11.7,17.8)
UPDATES=(0,20,50,100)
CASE_ID="afhubbard.hyperscaler_spot.A100_SXM_80GB.spot.median"
def load_inputs(out):
    config_raw=Path("configs/checkpoint-forecast-video.json").read_bytes();config=json.loads(config_raw)
    if (config["seconds"],config["fps"],config["frames"],config["width"],config["height"])!=(30,30,900,1920,1080):raise ValueError("Render contract")
    learning,font=learning_inputs(out)
    path=Path("results/terminal-v10/runs/43815591384/training-video")
    raw=(path/"replay-data.json").read_bytes();manifest_raw=(path/"manifest.json").read_bytes()
    previous=json.loads(manifest_raw);old=json.loads(raw)
    if sha(raw)!=previous["replay_data_sha256"]:raise ValueError("Saved price replay hash")
    if old["series_id"]!=CASE_ID or old["origin"]!="2026-08-15":raise ValueError("Fixed retrospective case")
    if old["retained"]["series_id"]!=CASE_ID or old["retained"]["origin"]!=old["origin"]:raise ValueError("Forecast identity")
    meta=old["provenance"]["history_metadata"];cat=old["retained"]["catalog"];permission=old["provenance"]["permission"]
    if not permission["approved"] or permission["license"]!="CC-BY-4.0" or permission["series_id"]!=CASE_ID:raise ValueError("Publication permission")
    for key in ("source_id","gpu_model","instrument_class","pricing_tier","statistic"):
        if meta[key]!=cat[key]:raise ValueError("Incompatible source/configuration metadata")
    if meta["unit"]!="USD per GPU-hour" or meta["id"]!=CASE_ID or meta["instrument_class"]!="hyperscaler_spot":raise ValueError("Target units/instrument")
    if previous["raw_numerical_file_hashes"]!=old["retained"]["file_hashes"]:raise ValueError("Retained numerical provenance")
    history=old["history"];truth=old["retained"]["truth"];origin=date.fromisoformat(old["origin"])
    if len({p["date"] for p in history})!=len(history) or history!=sorted(history,key=lambda p:p["date"]):raise ValueError("Duplicate/unsorted history")
    if any(p["date"]>old["origin"] or not math.isfinite(p["value"]) or p["value"]<=0 for p in history):raise ValueError("History cutoff/value")
    expected_dates={(origin+timedelta(days=h)).isoformat() for h in (1,3,7)}
    if {p["date"] for p in truth}!=expected_dates or len(truth)!=3:raise ValueError("Compatible outcome dates")
    truth_map={p["date"]:p["value"] for p in truth}
    archive_raw=fetch(learning["provenance"]["archive_url"])
    if sha(archive_raw)!=learning["provenance"]["archive_sha256"]:raise ValueError("Research archive")
    z=zipfile.ZipFile(io.BytesIO(archive_raw));states=[];op=next(r for r in learning["runs"] if r["id"]=="soft-17")
    for i,s in enumerate(old["states"]):
        if s["update"]!=UPDATES[i] or s["checkpoint_id"]!=op["points"][i]["checkpoint_id"]:raise ValueError("Checkpoint identity")
        if s["development_pinball"]!=op["points"][i]["loss"]:raise ValueError("Aggregate development score")
        name=f'runs/campaign/campaign-v2-policy-soft-17/v2-policy/development-{s["update"]}.json';member=z.read(name)
        if sha(member)!=learning["provenance"]["member_sha256"][name]:raise ValueError("Development trace member")
        doc=json.loads(member);traces=[t for t in doc["traces"] if t["task_id"]==s["task_id"] and t["origin"]==old["origin"]]
        if len(traces)!=1:raise ValueError("Archived case identity")
        t=traces[0]
        if t["selected_config_id"]!=s["config"] or t["cases"]!=s["cases"] or s["series_id"]!=CASE_ID:raise ValueError("Checkpoint/model/case mapping")
        points=old["retained"]["forecasts"][s["config"]]
        if [p["horizon"] for p in points]!=[1,3,7]:raise ValueError("Forecast horizon contract")
        losses=[]
        for p in points:
            if p["date"]!=(origin+timedelta(days=p["horizon"])).isoformat():raise ValueError("Horizon target date")
            q=[p[k] for k in ("q10","q50","q90")]
            if not all(math.isfinite(v) and v>0 for v in q) or q!=sorted(q):raise ValueError("Quantile order/positivity")
            actual=truth_map[p["date"]]
            loss=sum(max(a*(actual-v),(a-1)*(actual-v)) for a,v in zip((.1,.5,.9),q))/3
            recorded=next(c for c in s["cases"] if c["horizon_days"]==p["horizon"])
            if recorded["series_id"]!=CASE_ID or not math.isclose(loss,recorded["loss"],abs_tol=1e-12) or not math.isclose(q[2]-q[0],recorded["width"],abs_tol=1e-12):raise ValueError("Case score/width reconstruction")
            losses.append(loss)
        case_loss=sum(losses)/3
        if not math.isclose(case_loss,t["pinball"],abs_tol=1e-12):raise ValueError("Case aggregate")
        states.append({"update":s["update"],"checkpoint_id":s["checkpoint_id"],"config":s["config"],"case_pinball":case_loss,"development_pinball":s["development_pinball"],"forecasts":points})
    if states[0]["forecasts"]!=states[2]["forecasts"]:raise ValueError("Preserve update-50 return to starting forecast")
    visible=[p for p in history if p["date"]>="2026-08-02"]
    if not visible or visible[-1]["date"]!=old["origin"]:raise ValueError("Visible history boundary")
    if any(not 1.72<=v<=2.0 for v in [*[p["value"] for p in visible],*[p["value"] for p in truth],*[p[k] for s in states for p in s["forecasts"] for k in ("q10","q50","q90")]]):raise ValueError("Fixed price domain clips data")
    payload={"schema_version":3,"learning":learning,"case":{"series_id":CASE_ID,"origin":old["origin"],"history":visible,"full_history_observations":len(history),"truth":truth,"states":states,"metadata":meta,"permission":permission,"price_domain":[1.72,2.0],"date_domain":["2026-08-02","2026-08-22"],"selection":"Illustrative case selected retrospectively, not a registered performance endpoint"},"schedule":{"checkpoint_seconds":list(TIMES),"crossfade_seconds":.45},"provenance":{"implementation_commit":os.environ.get("GITHUB_SHA"),"config_sha256":sha(config_raw),"price_replay_sha256":sha(raw),"price_manifest_sha256":sha(manifest_raw),"retained_numerical_file_hashes":old["retained"]["file_hashes"],"learning":learning["provenance"]}}
    write(out/"synchronized-data.json",payload);return payload,font

HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Compute Forecast — Checkpoints to forecasts</title><style>
@font-face{font-family:Fieldnote;src:url(data:font/ttf;base64,__FONT__) format("truetype");font-weight:400 700}*{box-sizing:border-box}html,body{width:1920px;height:1080px;margin:0;overflow:hidden;background:#f7f3e9}svg{display:block;width:1920px;height:1080px}text{font-family:Arial,sans-serif;font-variant-numeric:tabular-nums}.book{font-family:Georgia,serif}.hand{font-family:Fieldnote,cursive}.guide{fill:none;stroke-linecap:round;stroke-linejoin:round}
#player{position:fixed;bottom:0;left:0;right:0;display:flex;gap:20px;align-items:center;padding:8px 32px;background:#f7f3e9ed;font:16px Arial}#player input{flex:1}button{font:inherit}
</style></head><body>
<svg id="figure" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" role="img" aria-label="Saved A100 price forecasts synchronized with the operational Tinker checkpoint and six SFT learning curves">
<defs><pattern id="paper" width="64" height="64" patternUnits="userSpaceOnUse"><path d="M64 0H0V64" fill="none" stroke="#455d4f" stroke-width=".5" opacity=".03"/></pattern><clipPath id="learn-reveal"><rect id="lc-clip" x="1277" y="350" width="16" height="450"/></clipPath></defs>
<rect width="1920" height="1080" fill="#f7f3e9"/><rect width="1920" height="1080" fill="url(#paper)"/>
<text x="72" y="51" fill="#516963" font-size="16" letter-spacing="2.7">COMPUTE FORECAST / TINKER STUDY</text>
<text x="72" y="113" class="book" fill="#263d3e" font-size="51" letter-spacing="-1">From a checkpoint to a price forecast.</text>
<text x="74" y="158" fill="#65766f" font-size="23">A100 SXM 80GB · hyperscaler spot median · forecast origin 15 August 2026</text>
<text x="1844" y="55" fill="#65766f" font-size="15" text-anchor="end" letter-spacing="1.5">OPERATIONAL SOFT / 17</text>
<text x="1708" y="108" fill="#65766f" font-size="20" text-anchor="end">Checkpoint</text><text id="checkpoint" x="1844" y="112" fill="#315dc1" font-size="56" text-anchor="end">0</text>
<line x1="72" y1="188" x2="1848" y2="188" stroke="#d9ded1"/>
<text x="80" y="232" class="book" fill="#2c4440" font-size="31">Selected price forecast.</text>
<text x="80" y="260" fill="#697c72" font-size="17">USD per GPU-hour · 2–22 August 2026</text>
<text id="model" x="80" y="296" fill="#315dc1" font-size="19"></text>
<text x="1110" y="229" fill="#697c72" font-size="15" text-anchor="end">CASE PINBALL · 3 HORIZONS</text><text id="case-loss" x="1110" y="268" fill="#2c4440" font-size="32" text-anchor="end"></text>
<g id="price-legend"></g><g id="price-axes"></g><g id="history"></g><g id="forecast-layers"></g><g id="outcomes"></g>
<line x1="1175" y1="220" x2="1175" y2="855" stroke="#d9ded1"/>
<text x="1205" y="232" class="book" fill="#2c4440" font-size="30">Learning across six runs.</text>
<text x="1207" y="260" fill="#697c72" font-size="17">Development pinball loss · lower is better</text>
<g id="learning-key"></g><text x="1844" y="292" fill="#697c72" font-size="15" text-anchor="end">ALL 6 DEVELOPMENT TASKS</text><text id="development-loss" x="1844" y="328" fill="#315dc1" font-size="30" text-anchor="end"></text>
<g id="learning-axes"></g><g id="lc-paths" clip-path="url(#learn-reveal)"></g><g id="lc-points"></g><g id="lc-selected"></g>
<line id="checkpoint-guide" x1="1285" x2="1285" y1="360" y2="790" stroke="#315dc1" stroke-dasharray="3 7" opacity=".16"/><circle id="current-dot" r="6" fill="#315dc1" stroke="#f7f3e9" stroke-width="2"/>
<g id="learning-labels"></g>
<text x="145" y="850" fill="#697c72" font-size="17">Actual +1, +3 and +7-day quantiles; joins are visual guides.</text>
<text x="1475" y="850" fill="#697c72" font-size="17" text-anchor="middle">Optimizer updates · rings mark kept checkpoints</text>
<g id="notes"></g>
<text x="72" y="968" fill="#65766f" font-size="18">Tinker trains the selector; numerical models produce the price quantiles.</text>
<text x="1848" y="968" fill="#65766f" font-size="17" text-anchor="end">Illustrative case selected retrospectively · aggregate: 6 tasks / 3 dates</text>
<text x="72" y="1000" fill="#78877c" font-size="15">afhubbard.hyperscaler_spot.A100_SXM_80GB.spot.median · archived outcomes shown for comparison</text>
<line x1="72" y1="1021" x2="1848" y2="1021" stroke="#d9ded1"/>
<text x="72" y="1053" fill="#65766f" font-size="17">Saved checkpoint replay · retrospective development case</text><text x="1848" y="1053" fill="#65766f" font-size="17" text-anchor="end">Data: A. Hubbard / Pacific · CC BY 4.0</text>
</svg><div id="player"><button id="play">Play / pause</button><input id="scrub" type="range" min="0" max="30" step=".01" value="0" aria-label="Video time"><span id="clock">0.00s</span></div>
<script>
const D=__DATA__,L=D.learning,K=D.case,S='http://www.w3.org/2000/svg',BLUE='#315dc1',PAPER='#f7f3e9',AMBER='#ad812e',C={hard:'#718175','soft-17':BLUE,'soft-29':'#2e7b69','soft-43':'#ae873f'};
const P={l:145,r:1110,t:360,b:790},G={l:1285,r:1665,t:360,b:790},TS=D.schedule.checkpoint_seconds;
const px=d=>P.l+(Date.parse(d)-Date.parse(K.date_domain[0]))/(Date.parse(K.date_domain[1])-Date.parse(K.date_domain[0]))*(P.r-P.l),py=v=>P.b-(v-1.72)/.28*(P.b-P.t);
const lx=u=>G.l+u/100*(G.r-G.l),ly=v=>G.b-(v-.008)/.012*(G.b-G.t);
const ease=t=>{t=Math.max(0,Math.min(1,t));return t*t*(3-2*t)},ramp=(t,a,b)=>ease((t-a)/(b-a)),range=(t,a,b,c,d)=>ramp(t,a,b)*(1-ramp(t,c,d)),loss=v=>Number(v).toFixed(6);
function add(parent,tag,attrs,text){const e=document.createElementNS(S,tag);for(const[k,v]of Object.entries(attrs||{}))e.setAttribute(k,String(v));if(text!==undefined)e.textContent=text;(typeof parent==='string'?document.getElementById(parent):parent).appendChild(e);return e}
const text=(p,x,y,t,size=17,color='#697c72',attrs={})=>add(p,'text',{x,y,fill:color,'font-size':size,...attrs},t);
const line=(p,x1,y1,x2,y2,c='#dde1d7',attrs={})=>add(p,'line',{x1,y1,x2,y2,stroke:c,...attrs});
const path=(points,key)=>points.map((p,i)=>(i?'L':'M')+px(p.date)+','+py(p[key])).join(' ');
for(const v of [1.75,1.80,1.85,1.90,1.95,2.0]){line('price-axes',P.l,py(v),P.r,py(v));text('price-axes',P.l-17,py(v)+6,'$'+v.toFixed(2),19,'#738276',{'text-anchor':'end'})}
for(const[d,label]of [['2026-08-02','02 Aug'],['2026-08-09','09 Aug'],['2026-08-15','15 Aug'],['2026-08-22','22 Aug']])text('price-axes',px(d),824,label,18,'#62766a',{'text-anchor':'middle'});
const ox=px(K.origin);add('price-axes','rect',{x:ox,y:P.t,width:P.r-ox,height:P.b-P.t,fill:BLUE,opacity:.025});line('price-axes',ox,P.t,ox,P.b,'#97a699',{'stroke-dasharray':'5 7'});text('price-axes',ox-10,346,'15 AUG · ORIGIN',14,'#718175',{'text-anchor':'end'});
const hparts=[];let hp=[];K.history.forEach((p,i)=>{if(i&&Date.parse(p.date)-Date.parse(K.history[i-1].date)>86400000){hparts.push(hp);hp=[]}hp.push(p)});if(hp.length)hparts.push(hp);
hparts.forEach(ps=>{add('history','path',{d:path(ps,'value'),stroke:'#425e54','stroke-width':2.7,class:'guide','data-dates':ps.map(p=>p.date).join(',')});if(ps.length===1)add('history','circle',{cx:px(ps[0].date),cy:py(ps[0].value),r:3,fill:'#425e54'})});
const priceNodes=[];
K.states.forEach((s,i)=>{
 const gr=add('forecast-layers','g',{id:'fc-'+i,opacity:i===0?1:0,'data-update':s.update,'data-config':s.config});const ps=s.forecasts;
 const band=path(ps,'q10')+' '+ps.slice().reverse().map(p=>'L'+px(p.date)+','+py(p.q90)).join(' ')+' Z';
 add(gr,'path',{d:band,fill:BLUE,opacity:.15,'data-band-for':s.update});
 add(gr,'path',{d:path(ps,'q50'),stroke:BLUE,'stroke-width':3.2,'stroke-dasharray':'7 6',class:'guide','data-median-for':s.update});
 ps.forEach(p=>{
 line(gr,px(p.date),py(p.q10),px(p.date),py(p.q90),BLUE,{'stroke-width':1.2,opacity:.6});
 for(const k of ['q10','q50','q90'])priceNodes.push(add(gr,'circle',{cx:px(p.date),cy:py(p[k]),r:k==='q50'?6.2:1.8,fill:k==='q50'?PAPER:BLUE,stroke:BLUE,'stroke-width':k==='q50'?2.2:0,'data-update':s.update,'data-date':p.date,'data-horizon':p.horizon,'data-quantile':k,'data-value':p[k]}));
 });
});
K.truth.forEach(p=>{const x=px(p.date),y=py(p.value),r=5.2;add('outcomes','path',{d:'M'+x+','+(y-r)+' L'+(x+r)+','+y+' L'+x+','+(y+r)+' L'+(x-r)+','+y+' Z',fill:AMBER,stroke:PAPER,'stroke-width':1.3,'data-date':p.date,'data-value':p.value})});
const legend=[{x:80,label:'History',color:'#425e54'},{x:265,label:'Median',color:BLUE},{x:445,label:'q10–q90',color:BLUE},{x:660,label:'Archived outcomes',color:AMBER}];
legend.forEach((a,i)=>{if(i===2)add('price-legend','rect',{x:a.x,y:315,width:24,height:12,fill:a.color,opacity:.18});else line('price-legend',a.x,321,a.x+24,321,a.color,{'stroke-width':i===3?4:2.5,'stroke-dasharray':i===1?'5 4':''});text('price-legend',a.x+34,327,a.label,16)});
for(const v of [.008,.012,.016,.020]){line('learning-axes',G.l,ly(v),G.r,ly(v));text('learning-axes',G.l-15,ly(v)+6,v.toFixed(3),17,'#738276',{'text-anchor':'end'})}
for(const u of [0,20,50,100]){line('learning-axes',lx(u),G.t,lx(u),G.b,'#dce0d5',{'stroke-dasharray':'2 7',opacity:.5});text('learning-axes',lx(u),824,String(u),18,'#62766a',{'text-anchor':'middle'})}
const groups=Object.fromEntries(L.groups.map(g=>[g.id,g])),dots=[],rings=[];
for(const id of ['hard','soft-17','soft-29','soft-43']){const g=groups[id];add('lc-paths','path',{d:g.points.map((p,i)=>(i?'L':'M')+lx(p.update)+','+ly(p.loss)).join(' '),stroke:C[id],'stroke-width':id==='soft-17'?3.6:id==='hard'?3.2:2.3,'stroke-dasharray':id==='soft-43'?'4 7':id==='hard'?'10 7':'',class:'guide','data-members':g.runs.join(',')});for(const p of g.points)dots.push({p,g,e:add('lc-points','circle',{cx:lx(p.update),cy:ly(p.loss),r:3.3,fill:PAPER,stroke:C[id],'stroke-width':1.7,'data-update':p.update,'data-loss':p.loss,'data-members':g.runs.join(',')})});const p=g.points.find(p=>p.update===g.selected);rings.push({g,p,e:add('lc-selected','circle',{cx:lx(p.update),cy:ly(p.loss),r:id==='soft-17'?9.3:5.2,fill:'none',stroke:C[id],'stroke-width':1.8,'data-update':p.update,'data-loss':p.loss,'data-members':g.runs.join(',')})})}
for(const a of [{id:'hard',x:1208,y:292,t:'Hard 17/29/43'},{id:'soft-17',x:1437,y:292,t:'Soft 17'},{id:'soft-29',x:1208,y:322,t:'Soft 29'},{id:'soft-43',x:1437,y:322,t:'Soft 43'}]){line('learning-key',a.x,a.y-5,a.x+24,a.y-5,C[a.id],{'stroke-width':2.3,'stroke-dasharray':a.id==='soft-43'?'4 5':a.id==='hard'?'10 5':''});text('learning-key',a.x+32,a.y,a.t,15,C[a.id])}
const labs=[{id:'hard',y:614,t:'Hard · 17/29/43',sub:'kept 20'},{id:'soft-29',y:669,t:'Soft · 29',sub:'kept 20'},{id:'soft-43',y:724,t:'Soft · 43',sub:'kept 50'},{id:'soft-17',y:779,t:'Soft · 17',sub:'kept 100'}];
labs.forEach(a=>{const gr=add('learning-labels','g',{id:'ll-'+a.id}),p=groups[a.id].points.at(-1),yy=ly(p.loss);add(gr,'path',{d:'M'+(G.r+8)+','+yy+' L1687,'+yy+' L1703,'+(a.y-6)+' L1710,'+(a.y-6),stroke:C[a.id],'stroke-width':1.2,fill:'none',opacity:.7});text(gr,1718,a.y,a.t,a.id==='hard'?17:19,C[a.id]);text(gr,1718,a.y+23,a.sub,15,'#718175')});
const notes=[
{id:'note0',text:'One checkpoint. One real forecast.',a:0,b:.8,c:5.5,d:6},
{id:'note1',text:'This case improves; aggregate development loss worsens.',a:6,b:6.5,c:11.2,d:11.7},
{id:'note2',text:'The aggregate improves. This case goes back.',a:11.7,b:12.2,c:17.3,d:17.8},
{id:'note3',text:'The final choice improves this case.',a:17.8,b:18.3,c:24.3,d:24.8},
{id:'note4',text:'Better selection. Uneven progress.',a:24.5,b:25.1,c:31,d:32}
];notes.forEach(n=>text('notes',960,918,n.text,36,BLUE,{class:'hand',id:n.id,'text-anchor':'middle'}));
const NAME={last_value_empirical:'Empirical persistence',seasonal_naive:'Seasonal naive','ewma_0.2':'EWMA · smoothing 0.2'};
const frozen=[...document.querySelectorAll('#history path,#forecast-layers path,#forecast-layers line,#forecast-layers circle,#outcomes path,#lc-paths path,#lc-points circle,#lc-selected circle')].map(e=>({e,attrs:['d','cx','cy','x1','y1','x2','y2'].filter(k=>e.hasAttribute(k)).map(k=>[k,e.getAttribute(k)])}));
function reveal(t){if(t<2.8)return 0;if(t<6)return 20*ramp(t,2.8,6);if(t<8.7)return 20;if(t<11.7)return 20+30*ramp(t,8.7,11.7);if(t<13.6)return 50;if(t<17.8)return 50+50*ramp(t,13.6,17.8);return 100}
function render(t){
 let i=0;for(let n=1;n<TS.length;n++)if(t>=TS[n]-1e-9)i=n;
 const a=i===0?1:ramp(t,TS[i],TS[i]+D.schedule.crossfade_seconds),weights=[0,0,0,0];weights[i]=a;if(i>0)weights[i-1]=1-a;
 weights.forEach((v,j)=>document.getElementById('fc-'+j).setAttribute('opacity',v));
 const s=K.states[i];document.getElementById('checkpoint').textContent=s.update;document.getElementById('case-loss').textContent=loss(s.case_pinball);document.getElementById('development-loss').textContent=loss(s.development_pinball);document.getElementById('model').textContent='Saved selection: '+NAME[s.config];
 const u=reveal(t);document.getElementById('lc-clip').setAttribute('width',lx(u)-1277+5);
 dots.forEach(a=>a.e.setAttribute('opacity',ramp(t,TS[[0,20,50,100].indexOf(a.p.update)],TS[[0,20,50,100].indexOf(a.p.update)]+.4)));
 const rt={hard:18.1,'soft-29':19,'soft-43':20,'soft-17':21};
 rings.forEach(a=>a.e.setAttribute('opacity',ramp(t,rt[a.g.id],rt[a.g.id]+.7)));
 labs.forEach((a,j)=>document.getElementById('ll-'+a.id).setAttribute('opacity',ramp(t,18+j*.45,18.8+j*.45)));
 document.getElementById('learning-key').setAttribute('opacity',1-ramp(t,17.8,18.8));
 document.getElementById('current-dot').setAttribute('cx',lx(s.update));document.getElementById('current-dot').setAttribute('cy',ly(s.development_pinball));document.getElementById('checkpoint-guide').setAttribute('x1',lx(s.update));document.getElementById('checkpoint-guide').setAttribute('x2',lx(s.update));
 notes.forEach(n=>document.getElementById(n.id).setAttribute('opacity',range(t,n.a,n.b,n.c,n.d)));
 for(const f of frozen)for(const[k,v]of f.attrs)if(f.e.getAttribute(k)!==v)throw Error('Measured plot geometry mutated');
 document.getElementById('scrub').value=t;document.getElementById('clock').textContent=t.toFixed(2)+'s';
 return {time:t,index:i,update:s.update,config:s.config,case_label:document.getElementById('case-loss').textContent,development_label:document.getElementById('development-loss').textContent,weights,learning_reveal:u,marker:{x:lx(s.update),y:ly(s.development_pinball)},measured_geometry_immutable:true};
}
window.renderFrame=render;window.prepareCapture=()=>{document.getElementById('player').style.display='none';playing=false;render(0)};
let playing=false,start=0,current=0;function loop(ts){if(!playing)return;current=Math.min(30,(ts-start)/1000);render(current);if(current<30)requestAnimationFrame(loop);else playing=false}
document.getElementById('play').onclick=()=>{playing=!playing;if(playing){if(current>=30)current=0;start=performance.now()-current*1000;requestAnimationFrame(loop)}};
document.getElementById('scrub').oninput=e=>{playing=false;current=Number(e.target.value);render(current)};
render(0);window.READY=true;
</script></body></html>'''

def verify_frame(r,t,payload):
    i=max(i for i,v in enumerate(TIMES) if t>=v-1e-9);s=payload["case"]["states"][i]
    f=1 if i==0 else max(0,min(1,(t-TIMES[i])/.45));a=f*f*(3-2*f);w=[0.0]*4;w[i]=a
    if i:w[i-1]=1-a
    if r["index"]!=i or r["update"]!=s["update"] or r["config"]!=s["config"]:raise ValueError("Frame checkpoint/model synchronization")
    if r["case_label"]!=f'{s["case_pinball"]:.6f}' or r["development_label"]!=f'{s["development_pinball"]:.6f}':raise ValueError("Frame metric scope")
    if any(abs(x-y)>1e-8 for x,y in zip(w,r["weights"])) or abs(sum(r["weights"])-1)>1e-9:raise ValueError("Crossfade weights")
    if not math.isclose(r["marker"]["x"],1285+s["update"]/100*380,abs_tol=1e-9) or not math.isclose(r["marker"]["y"],790-(s["development_pinball"]-.008)/.012*430,abs_tol=1e-9):raise ValueError("Current learning checkpoint")
    if r["measured_geometry_immutable"] is not True:raise ValueError("Geometry mutation")

def validate(page,d):
    page.evaluate("prepareCapture()")
    rows=page.locator("#forecast-layers circle").evaluate_all("(es)=>es.map(e=>({update:+e.dataset.update,date:e.dataset.date,h:+e.dataset.horizon,q:e.dataset.quantile,v:+e.dataset.value,x:+e.getAttribute('cx'),y:+e.getAttribute('cy')}))")
    expected={(s["update"],p["horizon"],k):(p[k],p["date"]) for s in d["case"]["states"] for p in s["forecasts"] for k in ("q10","q50","q90")}
    if len(rows)!=36:raise ValueError("36 actual quantile values required")
    a=date(2026,8,2);span=20
    for r in rows:
        v,day=expected[r["update"],r["h"],r["q"]]
        x=145+(date.fromisoformat(day)-a).days/span*965;y=790-(v-1.72)/.28*430
        if r["v"]!=v or r["date"]!=day or abs(r["x"]-x)>1e-8 or abs(r["y"]-y)>1e-8:raise ValueError("Price geometry/source")
    lr=page.locator("#lc-points circle").evaluate_all("(es)=>es.map(e=>({update:+e.dataset.update,v:+e.dataset.loss,x:+e.getAttribute('cx'),y:+e.getAttribute('cy'),members:e.dataset.members.split(',')}))")
    expanded={}
    for r in lr:
        if abs(r["x"]-(1285+r["update"]/100*380))>1e-8 or abs(r["y"]-(790-(r["v"]-.008)/.012*430))>1e-8:raise ValueError("Learning geometry")
        for rid in r["members"]:expanded[rid,r["update"]]=r["v"]
    if expanded!={(r["id"],p["update"]):p["loss"] for r in d["learning"]["runs"] for p in r["points"]}:raise ValueError("All six learning runs")
    markers=page.locator("#lc-selected circle").evaluate_all("(es)=>es.map(e=>({u:+e.dataset.update,m:e.dataset.members.split(',')}))")
    if {rid:r["u"] for r in markers for rid in r["m"]}!={r["id"]:r["selected"] for r in d["learning"]["runs"]}:raise ValueError("Original selected checkpoints")
    segments=page.locator("#history path").evaluate_all("(es)=>es.map(e=>e.dataset.dates.split(','))")
    if [day for s in segments for day in s]!=[p["date"] for p in d["case"]["history"]]:raise ValueError("Missing/changed history")
    if any((date.fromisoformat(b)-date.fromisoformat(a)).days!=1 for seg in segments for a,b in zip(seg,seg[1:])):raise ValueError("Historical gap joined")
    for t in (0,1,5.999,6,6.15,6.45,7,11.699,11.7,11.85,12.15,12.6,17.799,17.8,17.95,18.25,23,28):
        verify_frame(page.evaluate("(t)=>renderFrame(t)",t),t,d)
    for t in (1,7,12.6,18.5,23,28):
        page.evaluate("(t)=>renderFrame(t)",t)
        clipped=page.locator("svg text").evaluate_all("""es=>es.filter(e=>{for(let p=e;p&&p.tagName.toLowerCase()!=='svg';p=p.parentElement)if(p.hasAttribute('opacity')&&+p.getAttribute('opacity')<.05)return false;return true}).map(e=>({text:e.textContent,b:e.getBoundingClientRect().toJSON()})).filter(v=>v.b.left<0||v.b.top<0||v.b.right>1920||v.b.bottom>1080)""")
        if clipped:raise ValueError(("Clipped text",clipped))
    labels=page.locator("#learning-labels text").evaluate_all("(es)=>es.map(e=>({text:e.textContent,b:e.getBoundingClientRect().toJSON()}))")
    for i,a in enumerate(labels):
        for b in labels[i+1:]:
            if min(a["b"]["right"],b["b"]["right"])>max(a["b"]["left"],b["b"]["left"]) and min(a["b"]["bottom"],b["b"]["bottom"])>max(a["b"]["top"],b["b"]["top"]):raise ValueError("Run label collision")
    if not page.evaluate("document.fonts.check('32px Fieldnote')"):raise ValueError("Embedded font")
    return {"status":"passed","learning_source_checkpoints":24,"represented_sft_runs":6,"original_selection_markers":6,"price_quantile_values":36,"case_score_reconstructions":12,"matched_origin":"2026-08-15","history_observations_plotted":len(d["case"]["history"]),"history_gap_bridging":False,"fixed_price_axes":True,"fixed_learning_axes":True,"intermediate_forecast_morphing":False,"frame_sync_checks":0,"all_measured_geometry_immutable":True,"page_clipping":[],"run_label_collisions":[]}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--no-publish",action="store_true");args=parser.parse_args()
    from playwright.sync_api import sync_playwright
    from PIL import Image,ImageDraw
    out=Path("artifacts/checkpoint-forecast-video");out.mkdir(parents=True,exist_ok=True)
    d,font=load_inputs(out);html=HTML.replace("__FONT__",base64.b64encode(font).decode()).replace("__DATA__",json.dumps(d,allow_nan=False).replace("</","<\\/"))
    (out/"replay.html").write_text(html);errors=[];started=time.perf_counter();movie=out/"terminal-30s.mp4";times=(1,7,12.6,18.5,23,28)
    with sync_playwright() as pw:
        browser=pw.chromium.launch();page=browser.new_page(viewport={"width":1920,"height":1080},device_scale_factor=1)
        page.on("pageerror",lambda e:errors.append(str(e)));page.set_content(html,wait_until="load");page.evaluate("document.fonts.ready");page.wait_for_function("window.READY===true")
        report=validate(page,d);write(out/"validation.json",report)
        for t in times:page.evaluate("(t)=>renderFrame(t)",t);page.screenshot(path=str(out/f"stage-{t}.png"))
        with (out/"encoder.log").open("wb") as log:
            enc=subprocess.Popen(["ffmpeg","-y","-f","image2pipe","-vcodec","png","-framerate","30","-i","pipe:0","-an","-c:v","libx264","-preset","medium","-crf","17","-pix_fmt","yuv420p","-movflags","+faststart","-frames:v","900",str(movie)],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
            try:
                for i in range(900):
                    t=i/30;r=page.evaluate("(t)=>renderFrame(t)",t);verify_frame(r,t,d);report["frame_sync_checks"]+=1
                    enc.stdin.write(page.screenshot(type="png",animations="disabled",caret="hide"))
                    if i%150==0:print("SYNC_FRAME:"+json.dumps({"frame":i,"seconds":t,"checkpoint":r["update"]}),flush=True)
                enc.stdin.close()
                if enc.wait(timeout=180):raise ValueError("Encoding failed")
            except BaseException:enc.kill();enc.wait();raise
        browser.close()
    if errors:raise ValueError(errors)
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(movie)]))
    stream=next(s for s in probe["streams"] if s["codec_type"]=="video");duration=float(probe["format"]["duration"])
    if stream["codec_name"]!="h264" or (stream["width"],stream["height"])!=(1920,1080) or stream["r_frame_rate"]!="30/1" or int(stream["nb_frames"])!=900 or abs(duration-30)>.001:raise ValueError("Encoded video format")
    if movie.stat().st_size>50_000_000:raise ValueError("Media size")
    head=movie.read_bytes()[:200000]
    if b"moov" not in head or b"mdat" in head and head.index(b"moov")>head.index(b"mdat"):raise ValueError("Fast-start atom order")
    sheet=Image.new("RGB",(1920,768),"#f7f3e9");draw=ImageDraw.Draw(sheet)
    for i,sec in enumerate(times):
        f=out/f"encoded-{sec}.png";subprocess.run(["ffmpeg","-y","-ss",str(sec),"-i",str(movie),"-frames:v","1",str(f)],check=True,capture_output=True)
        im=Image.open(f).convert("RGB")
        if sec==28:im.save(out/"poster.png")
        im.thumbnail((640,360));x=i%3*640;y=i//3*384;sheet.paste(im,(x,y));draw.text((x+12,y+364),f"{sec}s / synchronized actual checkpoints",fill="#263d3e")
    sheet.save(out/"contact-sheet.png")
    motion=Image.new("RGB",(1920,882),"#f7f3e9");md=ImageDraw.Draw(motion)
    for i,sec in enumerate((6,6.15,6.30,6.45,11.7,11.85,12.0,12.15,17.8,17.95,18.10,18.25)):
        f=out/f"transition-{i}.png";subprocess.run(["ffmpeg","-y","-ss",str(sec),"-i",str(movie),"-frames:v","1",str(f)],check=True,capture_output=True)
        im=Image.open(f).convert("RGB");im.thumbnail((480,270));x=i%4*480;y=i//4*294;motion.paste(im,(x,y));md.text((x+12,y+274),f"Encoded crossfade / {sec:.2f}s",fill="#263d3e")
    motion.save(out/"motion-strip.png")
    caption="What changes when a trained forecasting selector changes its mind? Saved A100 price forecasts beside all six Tinker SFT learning curves. This illustrative case improves, reverses, then improves again. Case loss and aggregate development loss are separate. Retrospective replay; prospective accuracy remains unestablished."
    (out/"caption.txt").write_text(caption+"\n")
    report.update({"encoded_frames":900,"encoded_seconds":duration,"fps":30,"codec":"h264","resolution":[1920,1080],"faststart_verified":True,"browser_errors":errors,"renderer_seconds":time.perf_counter()-started});write(out/"validation.json",report)
    manifest={"schema_version":3,"kind":"synchronized_checkpoint_and_price_forecast_replay","implementation_commit":os.environ.get("GITHUB_SHA"),"run_id":os.environ.get("GITHUB_RUN_ID"),"created_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"output_seconds":duration,"fps":30,"frames":900,"resolution":[1920,1080],"live_inference":False,"new_training":False,"new_numerical_fits":False,"case_id":CASE_ID,"forecast_origin":d["case"]["origin"],"checkpoint_seconds":list(TIMES),"crossfade_seconds":.45,"case_selection":d["case"]["selection"],"scopes":{"price":"One retrospectively chosen series-origin case; three horizon cells","learning":"Six development tasks, 18 cells and three dependent dates; six training runs","separate_retrospective_evaluation":"Not plotted"},"checkpoint_mapping":[{"update":s["update"],"checkpoint_id":s["checkpoint_id"],"selected_config":s["config"],"case_pinball":s["case_pinball"],"development_pinball":s["development_pinball"]} for s in d["case"]["states"]],"visual_semantics":"Fixed axes. Price remains at the last measured checkpoint until arrival, then crossfades between two actual saved paths. No prediction coordinates morph. Learning joins are guides between measured checkpoint scores.","provenance":d["provenance"],"attribution":d["case"]["permission"],"data_sha256":sha((out/"synchronized-data.json").read_bytes()),"files":{p.name:{"sha256":sha(p.read_bytes()),"bytes":p.stat().st_size} for p in (movie,out/"poster.png",out/"contact-sheet.png",out/"motion-strip.png",out/"validation.json")}}
    write(out/"manifest.json",manifest)
    if args.no_publish:print("SYNC_RENDER:"+json.dumps(report));return
    import modal
    volume=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2);run=os.environ["GITHUB_RUN_ID"]
    with volume.batch_upload() as upload:
        for name in ("terminal-30s.mp4","poster.png","contact-sheet.png","manifest.json"):upload.put_file(str(out/name),"/terminal-v10/media/"+run+"/"+name)
    base=URL+"/terminal/media/"+run+"/";raw=fetch(base+"terminal-30s.mp4")
    if sha(raw)!=manifest["files"]["terminal-30s.mp4"]["sha256"]:raise ValueError("Public MP4 hash")
    rr=urllib.request.urlopen(urllib.request.Request(base+"terminal-30s.mp4",headers={"Range":"bytes=0-1023"}),timeout=90)
    if rr.status!=206 or len(rr.read())!=1024:raise ValueError("Public range playback")
    receipt={"status":"passed","video_url":base+"terminal-30s.mp4","preview_url":base+"poster.png","manifest_url":base+"manifest.json","duration":duration,"width":1920,"height":1080,"fps":30,"video_sha256":sha(raw),"implementation_commit":os.environ["GITHUB_SHA"],"range_verified":True}
    write(out/"publication.json",receipt)
    from .publication_terminal_v10 import publish
    names=("manifest.json","publication.json","poster.png","contact-sheet.png","motion-strip.png","validation.json","synchronized-data.json","replay.html","caption.txt","OFL.txt")
    dest="results/terminal-v10/runs/"+run+"/checkpoint-forecast/"
    commit=publish({dest+n:(out/n).read_bytes() for n in names});print("SYNC_VIDEO_REPORT:"+json.dumps(receipt),flush=True);print("SYNC_VIDEO_PUBLICATION:"+commit,flush=True)
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write("## Synchronized checkpoint and price forecasts\n\n"+receipt["video_url"]+"\n\n30 seconds, 900 individually validated frames; 24 learning checkpoints and 36 price quantiles. Saved results only. Separate case and aggregate development scopes.\n\nEvidence commit: "+commit+"\n")
if __name__=="__main__":main()
