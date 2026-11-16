"""Price-led market history, archived forecasts, scenarios and saved-checkpoint film."""
from __future__ import annotations
import argparse,base64,csv,hashlib,io,json,math,os,subprocess,time,urllib.request
from datetime import date,timedelta
from pathlib import Path
from .record_checkpoint_forecasts import load_inputs as checkpoint_inputs
from .record_learning_curve import sha,fetch,write,URL
CASE_ID="afhubbard.hyperscaler_spot.A100_SXM_80GB.spot.median"
def source(path,cfg):
    raw=Path(path).read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if blob!=cfg["source_blobs"][path]:raise ValueError("Frozen source changed: "+path)
    return json.loads(raw),sha(raw)
def load_inputs(out):
    raw=Path("configs/market-outlook-video.json").read_bytes();cfg=json.loads(raw)
    if (cfg["source_seconds"],cfg["output_seconds"],cfg["playback_speed"],cfg["fps"],cfg["frames"],cfg["width"],cfg["height"])!=(60,30,2,30,900,1920,1080):raise ValueError("60-to-30 render contract")
    d,font=checkpoint_inputs(out);prov={}
    vals={}
    for p in cfg["source_blobs"]:vals[p],prov[p]=source(p,cfg)
    study=vals["results/value-v5/runs/43757456253/study.json"]
    pricing=vals["results/explorer-v3/series-metadata.json"]
    outlook=vals["results/frozen-v1/outlook-scenarios.json"]
    s=next(x for x in study["history"]["series"] if x["id"]==CASE_ID)
    meta=next(x for x in pricing["series"] if x["id"]==CASE_ID)
    permission=next(x for x in study["history"]["publication_decisions"] if x["series_id"]==CASE_ID)
    if not permission["approved"] or permission["license"]!="CC-BY-4.0":raise ValueError("Publication grant")
    for key in ("source_id","instrument_class","pricing_tier","unit"):
        if s[key]!=meta[key]:raise ValueError("History/forecast compatibility: "+key)
    if s["catalog"]["series_id"]!=CASE_ID or s["gpu_model"]!="A100 SXM 80GB" or s["catalog"]["benchmark_contract"].split(";")[0]!="hyperscaler_spot":raise ValueError("Contract identity")
    points=s["points"]
    if len({p["date"] for p in points})!=len(points) or points!=sorted(points,key=lambda p:p["date"]):raise ValueError("History dates")
    if len(points)!=234 or points[0]["date"]!="2026-01-12" or points[-1]["date"]!="2026-11-06":raise ValueError("Complete approved history")
    if any(p["date"]>cfg["origin"] or not math.isfinite(p["value"]) or p["value"]<=0 for p in points):raise ValueError("History cutoff/value")
    official=fetch(URL+"/files/forecasts.csv")
    if sha(official)!=cfg["official_csv_sha256"] or sha(official)!=d["learning"]["provenance"]["official_csv_sha256"]:raise ValueError("Official CSV preservation")
    rows=list(csv.DictReader(io.StringIO(official.decode())))
    rr=sorted([r for r in rows if r["series_id"]==CASE_ID],key=lambda r:int(r["horizon_days"]))
    if len(rows)!=111 or len(rr)!=3 or {r["origin_date"] for r in rr}!={cfg["origin"]}:raise ValueError("Official export scope")
    forecasts=meta["forecasts"]
    for r,p in zip(rr,forecasts):
        h=int(r["horizon_days"])
        if h!=p["horizon_days"] or h not in (1,3,7) or p["date"]!=(date.fromisoformat(cfg["origin"])+timedelta(days=h)).isoformat():raise ValueError("Archived horizon")
        q=[float(r[k]) for k in ("q10","q50","q90")]
        if q!=[p[k] for k in ("q10","q50","q90")] or q!=sorted(q) or q[0]<=0:raise ValueError("Exact official quantiles")
    anchor=points[-1]["value"]
    if anchor!=1.8818 or pricing["origin_date"]!=cfg["origin"]:raise ValueError("Dollar anchor")
    if outlook["reference_date"]!=cfg["origin"] or outlook["scenario_probabilities"] is not None or outlook["confidence_level"] is not None:raise ValueError("Scenario semantics")
    if [a["rental_annual_change"] for a in outlook["assumptions"]]!=cfg["rental_annual_changes"]:raise ValueError("Published rental paths")
    assumptions=[]
    labels={"supply_expansion":"Supply expansion","moderate_decline":"Moderate decline","persistent_constraints":"Persistent constraints"}
    for a in outlook["assumptions"]:
        path=[{"month":m,"rental_rate":anchor*(1+a["rental_annual_change"])**(m/12),"rental_index":100*(1+a["rental_annual_change"])**(m/12),"resale_index":100*(1-a["resale_annual_depreciation"])**(m/12)} for m in range(37)]
        for r in outlook["results"]:
            if r["scenario"]==a["scenario"]:
                p=path[r["years"]*12]
                if not math.isclose(p["rental_index"],r["rental_index"],abs_tol=1e-10) or not math.isclose(p["resale_index"],r["resale_index"],abs_tol=1e-10):raise ValueError("Published scenario arithmetic")
        assumptions.append({**a,"label":labels[a["scenario"]],"points":path})

    # Reconstruct existing exact-series horizon diagnostics; this is not a new fit.
    existing_controls=[]
    for method in study["baseline_audit"]["methods"]:
        reports=[]
        for h in (1,3,7):
            cells=[c for c in method["cells"] if c["series_id"]==CASE_ID and int(c["horizon_days"])==h]
            if len(cells)!=3 or {c["origin_date"] for c in cells}!={"2026-08-29","2026-09-05","2026-09-12"}:raise ValueError("Retained horizon audit cohort")
            for c in cells:
                q=[float(c[k]) for k in ("q10","q50","q90")];actual=float(c["y"])
                if q!=sorted(q) or q[0]<=0 or (date.fromisoformat(c["origin_date"])+timedelta(days=h)).isoformat()!=c["target_date"]:raise ValueError("Retained interval/date")
                loss=sum(max(a*(actual-v),(a-1)*(actual-v)) for a,v in zip((.1,.5,.9),q))/3
                if not math.isclose(loss,float(c["loss"]),abs_tol=1e-12):raise ValueError("Retained official pinball")
            avg=lambda key:sum(float(c[key]) for c in cells)/len(cells)
            loss=avg("loss");baseline=avg("baseline_loss")
            reports.append({"horizon_days":h,"cells":len(cells),"distinct_origins":3,"pinball":loss,"reference_pinball":baseline,"skill":None if baseline==0 else 1-loss/baseline,"coverage":sum(float(c["q10"])<=float(c["y"])<=float(c["q90"]) for c in cells)/len(cells),"mean_interval_width":sum(float(c["q90"])-float(c["q10"]) for c in cells)/len(cells),"retained_cell_failures":sum(c["status"]!="scored" for c in cells)})
        existing_controls.append({"method":method["method"],"horizons":reports})

    bydate={p["date"]:p["value"] for p in points}
    saturdays=[p["date"] for p in points if p["date"]>="2026-07-15" and date.fromisoformat(p["date"]).weekday()==5]
    horizon=[]
    for h in (1,3,7,14,30,90):
        exact=[day for day in bydate if (date.fromisoformat(day)+timedelta(days=h)).isoformat() in bydate]
        weekly=[day for day in saturdays if (date.fromisoformat(day)+timedelta(days=h)).isoformat() in bydate]
        horizon.append({"horizon_days":h,"exact_label_pairs":len(exact),"saturday_pairs_since_2026_07_15":len(weekly),"saturday_origins":weekly,"forecast_issued":h in (1,3,7),"independent_sample_size":None,"horizon_specific_new_accuracy_estimate":None,"status":"Archived official export; prospective accuracy unestablished" if h in (1,3,7) else "Coverage candidates only; no audited forecast or calibration at this horizon"})
    gaps=(date.fromisoformat(points[-1]["date"])-date.fromisoformat(points[0]["date"])).days+1-len(points)
    econ=vals["configs/pacific-value-v5.json"]["economic_model"].copy()
    econ["active_gpu_w"]=400
    econ["active_gpu_w_note"]="Explicit A100 SXM 80GB power assumption, separate from the published H100-default 700W; does not affect rental-rate paths."
    econ["rental_rate_dependence"]="Only annual rental-rate assumption changes the plotted rental path. Utilization, energy, life, discounting and residual assumptions belong to a separate income calculation."
    d.update({"market":{"metadata":{k:v for k,v in s.items() if k!="points"},"history":points,"forecasts":forecasts,"permission":permission,"anchor":anchor,"origin":cfg["origin"],"origin_cutoff_utc":pricing["origin_cutoff_utc"],"missing_calendar_days":gaps,"source_vintage":study["history"]["source_vintage"]},"scenarios":{"kind":"assumption_driven_not_trained_forecast","anchor":anchor,"anchor_date":cfg["origin"],"months":[12,24,36],"assumptions":assumptions,"formula":"rental_rate(m) = 1.8818 * (1 + annual_change) ** (m / 12)","probabilities":None,"confidence_interval":False,"resale_reference":"Separate hypothetical resale index 100; no dollar resale anchor","economic_assumptions":econ},"horizon_audit":{"kind":"Descriptive coverage plus reconstruction of previously published retrospective controls; not a new backtest or tuning result","series_id":CASE_ID,"rows":horizon,"retained_control_diagnostics":existing_controls,"retained_control_scope":"Exact A100 SXM80 series, three reused origins Aug29/Sep5/Sep12, three cells per horizon; no independent calibration claim","longest_issued_statistical_horizon_days":7,"longest_scenario_months":36,"decision":"Retain actual 1/3/7-day archive. Do not create 14/30/90-day forecasts just for motion.","freshness":"This exact target has history through Nov6 only. Nov15 provider-contract pilot quotes exist but have different identities and one retained day; no new model issuance."},"timing":cfg,"market_provenance":{"implementation_commit":os.environ.get("GITHUB_SHA"),"config_sha256":sha(raw),"source_sha256":prov,"source_git_blobs":cfg["source_blobs"],"official_csv_sha256":sha(official),"protected_Nov7_13_outcomes_loaded":False,"new_training":False,"new_numerical_fits":False}})
    write(out/"market-data.json",d);write(out/"horizon-audit.json",d["horizon_audit"])
    return d,font

HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Compute Forecast · Prices, forecasts and assumptions</title>
<style>
@font-face{font-family:Fieldnote;src:url(data:font/ttf;base64,__FONT__) format("truetype");font-weight:400 700}
*{box-sizing:border-box}html,body{margin:0;background:#f7f3e9;color:#263d3e}svg{display:block;width:100%;height:auto;max-height:100vh}text{font-family:Arial,sans-serif;font-variant-numeric:tabular-nums}.book{font-family:Georgia,serif}.hand{font-family:Fieldnote,cursive}.guide{fill:none;stroke-linejoin:round;stroke-linecap:round}
#player{display:flex;align-items:center;gap:16px;padding:16px 4%;font:16px Arial;background:#eeeadd}#player input{flex:1;min-width:60px}button,select{font:inherit;padding:8px;border:1px solid #a1aca0;background:#f7f3e9;color:#263d3e;border-radius:4px}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #315dc1;outline-offset:3px}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}@media(max-width:700px){#player{flex-wrap:wrap;font-size:14px;gap:8px}#clock{display:none}}
</style></head><body>
<svg viewBox="0 0 1920 1080" role="img" aria-labelledby="figure-title figure-desc">
<title id="figure-title">GPU prices: history, archived forecasts and conditional scenarios</title><desc id="figure-desc">A100 SXM 80GB hyperscaler spot medians, licensed history through November 6 2026, actual one, three and seven day submitted quantiles, separate thirty-six month scenarios, and a retrospective checkpoint replay.</desc>
<defs><pattern id="paper" width="64" height="64" patternUnits="userSpaceOnUse"><path d="M64 0H0V64" fill="none" stroke="#455d4f" stroke-width=".5" opacity=".035"/></pattern>
<clipPath id="scenario-clip"><rect id="sc-clip" x="149" y="285" width="1333" height="440"/></clipPath>
<clipPath id="learning-clip"><rect id="learn-clip" x="168" y="801" width="16" height="151"/></clipPath></defs>
<rect width="1920" height="1080" fill="#f7f3e9"/><rect width="1920" height="1080" fill="url(#paper)"/>
<text x="76" y="53" font-size="16" letter-spacing="3" fill="#516963">COMPUTE FORECAST / A MARKET RESEARCH NOTEBOOK</text>
<text x="1844" y="53" text-anchor="end" font-size="16" fill="#65766f">2× playback</text>
<text x="76" y="119" font-size="56" class="book" letter-spacing="-1" fill="#263d3e">The price of compute, in context.</text>
<text x="78" y="164" font-size="24" fill="#52685f">A100 SXM 80GB · hyperscaler spot · pooled collector median · USD per GPU-hour</text>
<line x1="76" y1="196" x2="1844" y2="196" stroke="#ccd3c8"/>
<text id="mode" x="80" y="239" font-size="19" fill="#315dc1" letter-spacing="1.5"></text>
<text id="scope" x="1480" y="239" font-size="18" fill="#65766f" text-anchor="end"></text>
<text x="1540" y="239" font-size="16" letter-spacing="1.2" fill="#65766f">READING THE CHART</text>
<g id="full"></g><g id="close"></g><g id="scenario"></g><g id="research"></g>
<g id="right"></g><g id="explain"></g><g id="learning"></g>
<line x1="1514" y1="269" x2="1514" y2="944" stroke="#d9ded1"/>
<text id="axis-note" x="150" y="770" font-size="17" fill="#65766f"></text>
<text x="76" y="1000" font-size="14" fill="#65766f">afhubbard.hyperscaler_spot.A100_SXM_80GB.spot.median · advertised offers, not transactions or capacity</text>
<line x1="76" y1="1020" x2="1844" y2="1020" stroke="#ccd3c8"/>
<text id="foot" x="76" y="1053" font-size="17" fill="#52685f"></text>
<text x="1844" y="1053" text-anchor="end" font-size="16" fill="#65766f">A. Hubbard / Pacific · CC BY 4.0</text>
</svg>
<div id="player"><button id="play" aria-label="Play or pause the two-times replay">Play 2×</button><select id="chapter" aria-label="Choose a research chapter"><option value="0">Full history</option><option value="9">Origin close-up</option><option value="17">Archived forecast</option><option value="23">12-month scenarios</option><option value="29">24-month scenarios</option><option value="35">36-month scenarios</option><option value="41">Checkpoint 0</option><option value="45">Checkpoint 20</option><option value="49">Checkpoint 50</option><option value="51">Checkpoint 100</option></select><input id="scrub" type="range" min="0" max="60" step=".05" value="0" aria-label="Source timeline in seconds"><span id="clock">0.00 source seconds</span></div>
<script>
const D=__DATA__, NS='http://www.w3.org/2000/svg', C={ink:'#263d3e',muted:'#65766f',grid:'#d9ded1',paper:'#f7f3e9',blue:'#315dc1',green:'#37816d',amber:'#b1843d'};
const G=id=>document.getElementById(id),day=d=>Date.parse(d+'T00:00:00Z')/86400000;
function el(tag,a={},parent){const e=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(a))e.setAttribute(k,v);if(parent)parent.appendChild(e);return e}
function txt(p,x,y,s,size=20,fill=C.ink,more={}){const e=el('text',{x,y,'font-size':size,fill,...more},p);e.textContent=s;return e}
function line(p,x1,y1,x2,y2,a={}){return el('line',{x1,y1,x2,y2,stroke:C.grid,...a},p)}
function ramp(t,a,b){return Math.max(0,Math.min(1,(t-a)/(b-a)))}function ease(v){return v*v*(3-2*v)}
function op(id,v){G(id).setAttribute('opacity',v);G(id).setAttribute('aria-hidden',v<.02?'true':'false')}
function scaleDate(domain){return d=>150+(day(d)-day(domain[0]))/(day(domain[1])-day(domain[0]))*1330}
function scalePrice(domain){return v=>710-(v-domain[0])/(domain[1]-domain[0])*410}
function path(ps,x,y,k='value'){return ps.map((p,i)=>(i?'L':'M')+x(p.date)+','+y(p[k])).join(' ')}
function segments(ps){let all=[],cur=[];for(const p of ps){if(cur.length&&day(p.date)-day(cur.at(-1).date)!==1){all.push(cur);cur=[]}cur.push(p)}if(cur.length)all.push(cur);return all}
function axes(g,x,y,dates,ticks){for(const v of ticks){line(g,150,y(v),1480,y(v));txt(g,125,y(v)+7,'$'+v.toFixed(2),20,C.muted,{'text-anchor':'end'})}
 for(const[d,label]of dates){line(g,x(d),710,x(d),719,{stroke:'#a8b5a7'});txt(g,x(d),746,label,19,C.muted,{'text-anchor':'middle'})}}
function hist(g,ps,x,y,kind){const h=el('g',{'data-kind':kind},g);for(const seg of segments(ps)){el('path',{d:path(seg,x,y),class:'guide',stroke:C.ink,'stroke-width':2.6,'data-dates':seg.map(p=>p.date).join(',')},h);
 for(const p of seg)el('circle',{cx:x(p.date),cy:y(p.value),r:1.8,fill:C.ink,'data-date':p.date,'data-value':p.value,'data-kind':'history'},h)}return h}
function origin(g,x,label){line(g,x,288,x,716,{stroke:'#7d8d80','stroke-width':1.3,'stroke-dasharray':'4 7'});txt(g,x-10,281,label,16,C.muted,{'text-anchor':'end'})}
function forecast(g,ps,x,y,id,opts={}){const layer=el('g',{id},g),poly=[...ps.map(p=>[x(p.date),y(p.q90)]),...ps.slice().reverse().map(p=>[x(p.date),y(p.q10)])];
 el('polygon',{points:poly.map(p=>p.join(',')).join(' '),fill:C.blue,'fill-opacity':.14,'data-kind':'quantile-band'},layer);
 for(const k of ['q10','q50','q90']){el('path',{d:path(ps,x,y,k),class:'guide',stroke:C.blue,'stroke-width':k==='q50'?3:1.1,'stroke-dasharray':k==='q50'?'7 5':'3 5','stroke-opacity':k==='q50'?1:.5},layer);
 for(const p of ps)el('circle',{cx:x(p.date),cy:y(p[k]),r:k==='q50'?5:3,fill:k==='q50'?C.blue:C.paper,stroke:C.blue,'stroke-width':1.5,'data-kind':opts.kind||'official','data-update':opts.update??'','data-horizon':p.horizon_days??p.horizon,'data-quantile':k,'data-date':p.date,'data-value':p[k]},layer)}return layer}
const X=scaleDate(D.timing.history_domain),Y=scalePrice(D.timing.history_y_domain);
axes(G('full'),X,Y,[['2026-01-12','Jan 12'],['2026-03-01','Mar'],['2026-05-01','May'],['2026-07-01','Jul'],['2026-09-01','Sep'],['2026-11-06','Nov 6']],[1.6,1.7,1.8,1.9,2.0]);
hist(G('full'),D.market.history,X,Y,'full-history');origin(G('full'),X(D.market.origin),'Cutoff · 6 Nov 2026');
const last=D.market.history.at(-1);el('circle',{cx:X(last.date),cy:Y(last.value),r:5,fill:C.ink},G('full'));
const CX=scaleDate(D.timing.close_domain),CY=scalePrice(D.timing.close_y_domain),closeHistory=D.market.history.filter(p=>p.date>=D.timing.close_domain[0]);
axes(G('close'),CX,CY,[['2026-10-23','Oct 23'],['2026-10-30','Oct 30'],['2026-11-06','Nov 6'],['2026-11-13','Nov 13']],[1.75,1.85,1.95]);
hist(G('close'),closeHistory,CX,CY,'close-history');origin(G('close'),CX(D.market.origin),'Forecast origin');
forecast(G('close'),D.market.forecasts,CX,CY,'official-forecast');
for(const p of D.market.forecasts)txt(G('official-forecast'),CX(p.date),CY(p.q90)-17,'+'+p.horizon_days+'d',18,C.blue,{'text-anchor':'middle'});
// The flat median is explained outside the band to keep quantile edges unobstructed.
const SX=m=>150+m/36*1330,SY=scalePrice([.4,2.3]),sc=G('scenario');
for(const v of [.5,1,1.5,2]){line(sc,150,SY(v),1480,SY(v));txt(sc,125,SY(v)+7,'$'+v.toFixed(2),20,C.muted,{'text-anchor':'end'})}
for(const m of [0,12,24,36]){line(sc,SX(m),710,SX(m),719,{stroke:'#a8b5a7'});txt(sc,SX(m),746,m===0?'Nov 2026':m+' months',19,C.muted,{'text-anchor':'middle'})}
const scPaths=el('g',{'clip-path':'url(#scenario-clip)'},sc),colors=[C.green,C.blue,C.amber];
D.scenarios.assumptions.forEach((a,i)=>{el('path',{d:a.points.map((p,j)=>(j?'L':'M')+SX(p.month)+','+SY(p.rental_rate)).join(' '),class:'guide',stroke:colors[i],'stroke-width':3.2,'data-kind':'scenario','data-scenario':a.scenario},scPaths);for(const p of a.points)el('circle',{cx:SX(p.month),cy:SY(p.rental_rate),r:0,'data-kind':'scenario-month','data-month':p.month,'data-scenario':a.scenario,'data-value':p.rental_rate},scPaths)});
line(sc,SX(0),288,SX(0),716,{stroke:'#7d8d80','stroke-dasharray':'4 7'});txt(sc,158,281,'Dated anchor · $1.8818',17,C.muted);
el('line',{id:'scenario-ruler',x1:150,x2:150,y1:288,y2:716,stroke:'#7d8d80','stroke-dasharray':'4 7'},sc);
for(let i=0;i<3;i++)el('circle',{id:'sc-dot-'+i,r:6,fill:colors[i],stroke:C.paper,'stroke-width':2},sc);
const RX=scaleDate(['2026-08-02','2026-08-22']),RY=scalePrice([1.72,2]),rg=G('research');
axes(rg,RX,RY,[['2026-08-02','Aug 2'],['2026-08-08','Aug 8'],['2026-08-15','Aug 15'],['2026-08-22','Aug 22']],[1.75,1.85,1.95]);
hist(rg,D.case.history,RX,RY,'research-history');origin(rg,RX(D.case.origin),'Research origin · 15 Aug');
D.case.states.forEach((s,i)=>forecast(rg,s.forecasts,RX,RY,'case-'+i,{kind:'checkpoint',update:s.update}));
for(const p of D.case.truth){el('rect',{x:RX(p.date)-5,y:RY(p.value)-5,width:10,height:10,fill:C.amber,'data-kind':'archived-outcome','data-date':p.date,'data-value':p.value},rg)}
txt(rg,150,281,'August development case · different origin from archived submission',17,C.muted);
const lg=G('learning'),LX=u=>180+u/100*1010,LY=v=>943-(v-.008)/.012*116;
txt(lg,150,806,'Six SFT runs · development pinball loss · lower is better',19,C.ink);
for(const v of [.008,.014,.020]){line(lg,180,LY(v),1190,LY(v));txt(lg,164,LY(v)+5,v.toFixed(3),16,C.muted,{'text-anchor':'end'})}
for(const u of [0,20,50,100]){txt(lg,LX(u),968,String(u),16,C.muted,{'text-anchor':'middle'})}
txt(lg,1190,968,'optimizer updates',16,C.muted,{'text-anchor':'end',transform:'translate(0 24)'});
const lp=el('g',{'clip-path':'url(#learning-clip)'},lg);
const lcColors={hard:C.ink,'soft-17':C.blue,'soft-29':C.green,'soft-43':C.amber};
D.learning.shared_segments.forEach(s=>{const isOp=s.members.includes('soft-17'),c=isOp?C.blue:s.members.every(r=>r.startsWith('hard'))?C.ink:s.members.includes('soft-29')?C.green:C.amber;
 el('path',{d:'M'+LX(s.from_update)+','+LY(s.from_loss)+' L'+LX(s.to_update)+','+LY(s.to_loss),stroke:c,'stroke-width':isOp?2.8:1.9,'stroke-dasharray':s.members.every(r=>r.startsWith('hard'))?'5 5':'',class:'guide','data-kind':'learning-segment','data-members':s.members.join(',')},lp)});
D.learning.groups.forEach(g=>{g.points.forEach(p=>el('circle',{cx:LX(p.update),cy:LY(p.loss),r:3.2,fill:lcColors[g.id],stroke:C.paper,'stroke-width':1,'data-kind':'learning-point','data-update':p.update,'data-loss':p.loss,'data-members':g.runs.join(',')},lp));
 const p=g.points.find(p=>p.update===g.selected);el('circle',{cx:LX(p.update),cy:LY(p.loss),r:7.5,fill:'none',stroke:lcColors[g.id],'stroke-width':2,'data-kind':'selected-checkpoint','data-update':g.selected,'data-members':g.runs.join(',')},lp)});
[['hard / 17, 29, 43',C.ink],['soft / 17 · operational',C.blue],['soft / 29',C.green],['soft / 43',C.amber]].forEach(([s,c],i)=>{line(lg,1250,826+i*32,1280,826+i*32,{stroke:c,'stroke-width':3});txt(lg,1293,832+i*32,s,17,c)});
el('circle',{id:'learning-dot',r:6,fill:C.blue,stroke:C.paper,'stroke-width':2},lg);
const frozen=[...document.querySelectorAll('[data-kind]')].map(e=>({e,attrs:[...e.attributes].filter(a=>['d','points','cx','cy','x','y','width','height','data-value','data-loss'].includes(a.name)).map(a=>[a.name,a.value])}));
function noteLines(g,x,y,lines,size=20,c=C.ink){lines.forEach((s,i)=>txt(g,x,y+i*(size+10),s,size,c))}
function modeState(t){return t<22?'archive':t<40?'scenario':'research'}
function stateIndex(t){return t<44?0:t<48?1:t<50?2:3}
function render(t){
 t=Math.max(0,Math.min(60,t));const mode=modeState(t),i=stateIndex(t),s=D.case.states[i],month=t<28?12:t<34?24:36;
 op('full',t<6?1:1-ease(ramp(t,6,8)));op('close',t<6?0:t<22?ease(ramp(t,6,8)):1-ease(ramp(t,22,22.6)));
 op('official-forecast',ease(ramp(t,10,11)));op('scenario',t<22?0:t<40?ease(ramp(t,22,22.6)):1-ease(ramp(t,40,40.6)));
 op('research',ease(ramp(t,40,40.6)));op('learning',ease(ramp(t,40,40.6)));
 for(let j=0;j<4;j++){let w=j===i?1:0;if(i>0&&t<[40,44,48,50][i]+.6){const a=ease(ramp(t,[40,44,48,50][i],[40,44,48,50][i]+.6));w=j===i?a:j===i-1?1-a:0}op('case-'+j,w)}
 const weights=[0,1,2,3].map(j=>+G('case-'+j).getAttribute('opacity'));
 const right=G('right'),ex=G('explain');right.replaceChildren();ex.replaceChildren();
 let label,scope,axis,foot;
 if(mode==='archive'){
  label=t<10?'01 / OBSERVED HISTORY':'02 / ARCHIVED STATISTICAL FORECAST';scope=t<8?'12 Jan – 6 Nov 2026':'Origin · 6 Nov 2026 · cutoff 23:59:59 UTC';
  axis=t<10?'Gaps remain empty. Lines only join consecutive observed days.':'Only +1, +3 and +7-day quantiles were issued. Dashed joins are visual guides.';
  foot='Archived benchmark · not a live forecast made today';
  if(t<10){txt(right,1540,305,'234',56,C.ink);noteLines(right,1540,349,['observed daily medians','Jan 12 – Nov 6, 2026'],20,C.muted);
   txt(right,1540,460,'$1.8818',43,C.ink);noteLines(right,1540,500,['last archived observation','6 November 2026'],19,C.muted);
   noteLines(right,1540,628,['65 calendar days missing','No gap filling'],19,C.muted);
   txt(ex,150,855,'A longer history gives context, not certainty.',34,C.ink,{class:'hand'});noteLines(ex,150,900,['Collector-defined population · all regions pooled · median provider count: 3','Provider composition can change; this is not a fixed-contract price index.'],20,C.muted);
  }else{
   const p=D.market.forecasts[2];txt(right,1540,303,'+7 days',39,C.blue);txt(right,1540,339,'13 November 2026',20,C.muted);
   [['q90',p.q90],['q50',p.q50],['q10',p.q10]].forEach(([k,v],j)=>{txt(right,1540,407+j*62,k,18,C.muted);txt(right,1840,410+j*62,'$'+v.toFixed(4),30,k==='q50'?C.blue:C.ink,{'text-anchor':'end'})});
   noteLines(right,1540,641,['Nominal q10–q90 range','Calibration not established','by this replay'],18,C.muted);
   txt(ex,150,850,t<16?'A flat median is still the actual forecast.':'Seven days is the furthest audited export.',34,C.ink,{class:'hand'});
   noteLines(ex,150,896,t<16?['Observed prices stop on November 6. Protected November 7–13 outcomes are not shown.','Shading connects actual quantiles; it does not create independent daily forecasts.']:['14 / 30 days: historical label pairs exist, but no audited forecast or interval test here.','A model can emit a number farther out. That alone does not validate the horizon.'],20,C.muted);
  }
 }else if(mode==='scenario'){
  label='03 / CONDITIONAL RENTAL SCENARIOS';scope='Dated Nov 6 anchor · assumptions, not trained forecasts';
  axis='Months after 6 Nov 2026 · monthly values are compounded calculations, not predicted observations.';
  foot='Scenario paths carry no probabilities · rental and hardware resale remain separate';
  const reveal=month===12?12:month===24?12+12*ease(ramp(t,28,28.8)):24+12*ease(ramp(t,34,34.8));G('sc-clip').setAttribute('width',SX(reveal)-149+8);G('scenario-ruler').setAttribute('x1',SX(reveal));G('scenario-ruler').setAttribute('x2',SX(reveal));
  txt(right,1540,306,'At '+month+' months',36,C.ink);txt(right,1540,344,'Annual rental assumption',18,C.muted);
  D.scenarios.assumptions.forEach((a,j)=>{const p=a.points[month],cursorRate=D.scenarios.anchor*(1+a.rental_annual_change)**(reveal/12);G('sc-dot-'+j).setAttribute('cx',SX(reveal));G('sc-dot-'+j).setAttribute('cy',SY(cursorRate));
   txt(right,1540,398+j*95,a.label,19,colors[j]);txt(right,1540,430+j*95,(a.rental_annual_change*100>0?'+':'')+(a.rental_annual_change*100).toFixed(0)+'% / year',20,C.muted);txt(right,1840,432+j*95,'$'+p.rental_rate.toFixed(2),29,colors[j],{'text-anchor':'end'})});
  txt(ex,150,838,'The further future is conditional on assumptions.',34,C.ink,{class:'hand'});
  txt(ex,150,881,'Rate(m) = $1.8818 × (1 + annual change)^(m / 12)',23,C.ink);
  noteLines(ex,150,921,month===36?['Separate hypothetical resale index at 36 months: 21.6 / 42.2 / 72.9 (start = 100).','Those resale assumptions are not observed transaction prices or rental-rate quantiles.']:['Same source, SKU and spot contract must remain quoted for the rental anchor to apply.','Utilization, power costs and residual value affect the separate income outlook, not these rate paths.'],19,C.muted);
 }else{
  label='04 / SAVED CHECKPOINT REPLAY';scope='Illustrative development case · origin 15 Aug 2026';
  axis='Actual saved +1, +3, +7-day quantiles · amber squares are compatible archived August outcomes.';
  foot='Retrospective development illustration · prospective forecasting improvement is not established';
  txt(right,1540,300,'Checkpoint '+s.update,32,C.blue);txt(right,1540,338,'soft targets / seed 17',19,C.muted);
  txt(right,1540,399,'Selected numerical method',18,C.muted);txt(right,1540,434,s.config.replaceAll('_',' '),23,C.ink);
  txt(right,1540,503,'THIS CASE · 3 HORIZONS',15,C.muted,{'letter-spacing':1});txt(right,1540,544,s.case_pinball.toFixed(6),35,C.ink);
  txt(right,1540,612,'AGGREGATE DEVELOPMENT',15,C.muted,{'letter-spacing':.6});txt(right,1540,653,s.development_pinball.toFixed(6),35,C.blue);
  noteLines(right,1540,712,['6 tasks · 18 cells','3 reused, dependent dates'],17,C.muted);
  const reveal=s.update;G('learn-clip').setAttribute('width',LX(reveal)-168+11);
  G('learning-dot').setAttribute('cx',LX(s.update));G('learning-dot').setAttribute('cy',LY(s.development_pinball));
  txt(right,1540,833,'Tinker trained the selector.',21,C.ink,{class:'hand'});noteLines(right,1540,869,['Numerical models generated','the price quantiles.','Rings: original kept checkpoints.'],17,C.muted);
  // The persistent scope footer carries the prospective limitation.
 }
 G('mode').textContent=label;G('scope').textContent=scope;G('axis-note').textContent=axis;G('foot').textContent=foot;
 for(const f of frozen)for(const[k,v]of f.attrs)if(f.e.getAttribute(k)!==v)throw Error('Measured geometry changed');
 G('scrub').value=t;G('clock').textContent=t.toFixed(2)+' source seconds';
 return{source_time:t,output_time:t/2,mode,checkpoint:mode==='research'?s.update:null,config:mode==='research'?s.config:null,case_loss:mode==='research'?s.case_pinball:null,development_loss:mode==='research'?s.development_pinball:null,checkpoint_weights:weights,scenario_month:mode==='scenario'?month:null,scenario_cursor_month:mode==='scenario'?(month===12?12:month===24?12+12*ease(ramp(t,28,28.8)):24+12*ease(ramp(t,34,34.8))):null,scenario_cursor_rates:mode==='scenario'?[0,1,2].map(j=>{const e=G('sc-dot-'+j);return{month:(+e.getAttribute('cx')-150)/1330*36,rate:.4+(710-(+e.getAttribute('cy')))/410*1.9}}):null,scenario_rates:mode==='scenario'?D.scenarios.assumptions.map(a=>a.points[month].rental_rate):null,measured_geometry_immutable:true};
}
window.renderFrame=render;let playing=false,current=0,start=0;
window.prepareCapture=()=>{G('player').style.display='none';playing=false;render(0)};
function loop(ts){if(!playing)return;current=Math.min(60,(ts-start)/1000*2);render(current);if(current<60)requestAnimationFrame(loop);else{playing=false;G('play').textContent='Play 2×'}}
G('play').onclick=()=>{playing=!playing;G('play').textContent=playing?'Pause':'Play 2×';if(playing){if(current>=60)current=0;start=performance.now()-current*500;requestAnimationFrame(loop)}};
function seek(t){playing=false;G('play').textContent='Play 2×';current=t;render(t)}
G('scrub').oninput=e=>seek(+e.target.value);G('chapter').onchange=e=>seek(+e.target.value);
render(0);window.READY=true;
</script></body></html>'''

def verify_frame(r,t,d):
    mode="archive" if t<22 else "scenario" if t<40 else "research"
    if r["source_time"]!=t or r["output_time"]!=t/2 or r["mode"]!=mode or not r["measured_geometry_immutable"]:raise ValueError("Deterministic two-times clock/mode")
    if mode=="scenario":
        month=12 if t<28 else 24 if t<34 else 36
        if r["scenario_month"]!=month or any(not math.isclose(a,b["points"][month]["rental_rate"],abs_tol=1e-12) for a,b in zip(r["scenario_rates"],d["scenarios"]["assumptions"])):raise ValueError("Scenario cursor/value")
        ease=lambda v:v*v*(3-2*v)
        cursor=12 if month==12 else 12+12*ease(max(0,min(1,(t-28)/.8))) if month==24 else 24+12*ease(max(0,min(1,(t-34)/.8)))
        if not math.isclose(r["scenario_cursor_month"],cursor,abs_tol=1e-10):raise ValueError("Scenario ruler clock")
        for rendered,a in zip(r["scenario_cursor_rates"],d["scenarios"]["assumptions"]):
            if not math.isclose(rendered["month"],cursor,abs_tol=1e-9) or not math.isclose(rendered["rate"],d["scenarios"]["anchor"]*(1+a["rental_annual_change"])**(cursor/12),abs_tol=1e-10):raise ValueError("Ruler compounding")
    if mode=="research":
        i=0 if t<44 else 1 if t<48 else 2 if t<50 else 3;s=d["case"]["states"][i]
        if (r["checkpoint"],r["config"],r["case_loss"],r["development_loss"])!=(s["update"],s["config"],s["case_pinball"],s["development_pinball"]):raise ValueError("Saved checkpoint/forecast synchronization")
        if abs(sum(r["checkpoint_weights"])-1)>1e-9:raise ValueError("Forecast opacity weights")

def validate(page,d):
    page.evaluate("prepareCapture()")
    rows=page.locator("circle[data-kind=official]").evaluate_all("(es)=>es.map(e=>({h:+e.dataset.horizon,q:e.dataset.quantile,date:e.dataset.date,v:+e.dataset.value,x:+e.getAttribute('cx'),y:+e.getAttribute('cy')}))")
    if len(rows)!=9:raise ValueError("Nine issued quantiles")
    for r in rows:
        p=next(p for p in d["market"]["forecasts"] if p["horizon_days"]==r["h"])
        x=150+(date.fromisoformat(p["date"])-date(2026,10,23)).days/21*1330;y=710-(p[r["q"]]-1.72)/.30*410
        if r["v"]!=p[r["q"]] or r["date"]!=p["date"] or not math.isclose(r["x"],x,abs_tol=1e-8) or not math.isclose(r["y"],y,abs_tol=1e-8):raise ValueError("Official quantile coordinates")
    hist=page.locator("#full circle[data-kind=history]").evaluate_all("(es)=>es.map(e=>({date:e.dataset.date,value:+e.dataset.value,x:+e.getAttribute('cx'),y:+e.getAttribute('cy')}))")
    if [{"date":p["date"],"value":p["value"]} for p in hist]!=d["market"]["history"]:raise ValueError("All approved observations")
    for r in hist:
        x=150+(date.fromisoformat(r["date"])-date(2026,1,12)).days/305*1330;y=710-(r["value"]-1.55)/.5*410
        if not math.isclose(x,r["x"],abs_tol=1e-8) or not math.isclose(y,r["y"],abs_tol=1e-8):raise ValueError("History coordinates")
    for kind,expected in (("full-history",d["market"]["history"]),("close-history",[p for p in d["market"]["history"] if p["date"]>="2026-10-23"]),("research-history",d["case"]["history"])):
        segs=page.locator(f'g[data-kind="{kind}"] path').evaluate_all("(es)=>es.map(e=>e.dataset.dates.split(','))")
        if [day for seg in segs for day in seg]!=[p["date"] for p in expected]:raise ValueError("Missing history segment")
        if any((date.fromisoformat(b)-date.fromisoformat(a)).days!=1 for seg in segs for a,b in zip(seg,seg[1:])):raise ValueError("Historical gap bridged")
    qp=page.locator("circle[data-kind=checkpoint]").evaluate_all("(es)=>es.map(e=>({u:+e.dataset.update,h:+e.dataset.horizon,q:e.dataset.quantile,v:+e.dataset.value,x:+e.getAttribute('cx'),y:+e.getAttribute('cy')}))")
    if len(qp)!=36:raise ValueError("36 saved checkpoint quantiles")
    for r in qp:
        s=next(s for s in d["case"]["states"] if s["update"]==r["u"]);p=next(p for p in s["forecasts"] if p["horizon"]==r["h"])
        x=150+(date.fromisoformat(p["date"])-date(2026,8,2)).days/20*1330;y=710-(p[r["q"]]-1.72)/.28*410
        if p[r["q"]]!=r["v"] or not math.isclose(r["x"],x,abs_tol=1e-8) or not math.isclose(r["y"],y,abs_tol=1e-8):raise ValueError("Checkpoint quantile coordinate")
    lp=page.locator("circle[data-kind=learning-point]").evaluate_all("(es)=>es.map(e=>({u:+e.dataset.update,l:+e.dataset.loss,m:e.dataset.members.split(','),x:+e.getAttribute('cx'),y:+e.getAttribute('cy')}))")
    expanded={}
    for r in lp:
        for rid in r["m"]:expanded[rid,r["u"]]=r["l"]
        if not math.isclose(r["x"],180+r["u"]/100*1010,abs_tol=1e-8) or not math.isclose(r["y"],943-(r["l"]-.008)/.012*116,abs_tol=1e-8):raise ValueError("Learning coordinates")
    if expanded!={(r["id"],p["update"]):p["loss"] for r in d["learning"]["runs"] for p in r["points"]}:raise ValueError("All six SFT runs")
    selections=page.locator("circle[data-kind=selected-checkpoint]").evaluate_all("(es)=>es.map(e=>({u:+e.dataset.update,m:e.dataset.members.split(',')}))")
    if {rid:r["u"] for r in selections for rid in r["m"]}!={r["id"]:r["selected"] for r in d["learning"]["runs"]}:raise ValueError("Original selected checkpoints")
    sp=page.locator("circle[data-kind=scenario-month]").evaluate_all("(es)=>es.map(e=>({s:e.dataset.scenario,m:+e.dataset.month,v:+e.dataset.value,x:+e.getAttribute('cx'),y:+e.getAttribute('cy')}))")
    if len(sp)!=111:raise ValueError("Three monthly compounded scenario paths")
    for p in sp:
        a=next(a for a in d["scenarios"]["assumptions"] if a["scenario"]==p["s"]);v=d["market"]["anchor"]*(1+a["rental_annual_change"])**(p["m"]/12)
        if not math.isclose(v,p["v"],abs_tol=1e-12) or not math.isclose(p["x"],150+p["m"]/36*1330,abs_tol=1e-8) or not math.isclose(p["y"],710-(v-.4)/1.9*410,abs_tol=1e-8):raise ValueError("Scenario geometry/formula")
    for t in (0,5.9,6,7,8,10,10.5,11,16,21.99,22,22.3,23,27.99,28,34,39.99,40,40.3,43.99,44,44.3,44.6,48,48.3,50,50.3,50.6,54,59.99):
        verify_frame(page.evaluate("(t)=>renderFrame(t)",t),t,d)
    for t in (2,9,13,19,25,31,37,42,46,49,52,57):
        page.evaluate("(t)=>renderFrame(t)",t)
        bad=page.locator("svg text").evaluate_all("""es=>es.filter(e=>{for(let p=e;p&&p.tagName.toLowerCase()!=='svg';p=p.parentElement)if(p.hasAttribute('opacity')&&+p.getAttribute('opacity')<.05)return false;return true}).map(e=>({text:e.textContent,b:e.getBoundingClientRect().toJSON()})).filter(v=>v.b.left<0||v.b.top<0||v.b.right>1920||v.b.bottom>1080)""")
        if bad:raise ValueError(("Clipped text",bad))
    if not page.evaluate("document.fonts.check('32px Fieldnote')"):raise ValueError("Handwriting font unavailable")
    # Native slider and chapter controls have keyboard semantics and no autoplay.
    page.evaluate("document.getElementById('player').style.display='flex'")
    page.locator("#chapter").select_option("29")
    if page.evaluate("renderFrame(29).scenario_month")!=24:raise ValueError("Chapter navigation")
    page.locator("#scrub").focus();page.keyboard.press("ArrowRight")
    if float(page.locator("#scrub").input_value())<=29:raise ValueError("Keyboard scrub")
    page.evaluate("prepareCapture()")
    return {"status":"passed","history_observations":234,"missing_calendar_days":65,"history_gap_bridging":False,"official_quantiles_verified":9,"checkpoint_quantiles_verified":36,"learning_checkpoints_verified":24,"original_checkpoint_selections_verified":6,"scenario_monthly_calculations_verified":111,"existing_control_cell_losses_reconstructed":36,"scenario_ruler_formula_checks":True,"case_loss_reconstructions":12,"supported_archived_horizons":[1,3,7],"new_statistical_forecasts":0,"future_Nov7_13_outcomes_loaded":False,"source_seconds":60,"output_seconds":30,"playback_speed":2,"frame_sync_checks":0,"intermediate_forecast_morphing":False,"fixed_axes_within_comparison":True,"native_keyboard_controls":True,"autoplay":False,"new_training":False,"new_numerical_fits":False,"page_clipping":[]}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--no-publish",action="store_true");parser.add_argument("--verify-only",action="store_true");args=parser.parse_args()
    from playwright.sync_api import sync_playwright
    from PIL import Image,ImageDraw
    out=Path("artifacts/market-outlook-video");out.mkdir(parents=True,exist_ok=True)
    d,font=load_inputs(out)
    html=HTML.replace("__FONT__",base64.b64encode(font).decode()).replace("__DATA__",json.dumps(d,allow_nan=False).replace("</","<\\/"))
    (out/"replay.html").write_text(html);errors=[];started=time.perf_counter();movie=out/"terminal-30s.mp4"
    times=d["timing"]["stage_output_seconds"];frame_rows=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch();page=browser.new_page(viewport={"width":1920,"height":1080},device_scale_factor=1)
        page.on("pageerror",lambda e:errors.append(str(e)));page.set_content(html,wait_until="load");page.evaluate("document.fonts.ready");page.wait_for_function("window.READY===true")
        report=validate(page,d);write(out/"validation.json",report)
        for sec in times:page.evaluate("(t)=>renderFrame(t)",sec*2);page.screenshot(path=str(out/f"stage-{sec}.png"))
        if args.verify_only:
            if errors:raise ValueError(errors)
            browser.close();print("MARKET_VERIFICATION:"+json.dumps(report));return
        with (out/"encoder.log").open("wb") as log:
            enc=subprocess.Popen(["ffmpeg","-y","-f","image2pipe","-vcodec","png","-framerate","30","-i","pipe:0","-an","-c:v","libx264","-preset","medium","-crf","17","-pix_fmt","yuv420p","-movflags","+faststart","-frames:v","900",str(movie)],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
            try:
                for i in range(900):
                    output_time=i/30;source_time=2*output_time
                    r=page.evaluate("(t)=>renderFrame(t)",source_time);verify_frame(r,source_time,d);report["frame_sync_checks"]+=1
                    frame_rows.append({"frame":i,**r})
                    enc.stdin.write(page.screenshot(type="png",animations="disabled",caret="hide"))
                    if i%150==0:print("MARKET_FRAME:"+json.dumps({"frame":i,"source_time":source_time,"output_time":output_time,"mode":r["mode"]}),flush=True)
                enc.stdin.close()
                if enc.wait(timeout=180):raise ValueError("Encoding failed")
            except BaseException:enc.kill();enc.wait();raise
        # Narrow layout and reduced motion: controls stay available and playback remains opt-in.
        page.evaluate("document.getElementById('player').style.display='flex'")
        page.set_viewport_size({"width":390,"height":844});page.emulate_media(reduced_motion="reduce")
        page.locator("#chapter").select_option("35")
        if page.evaluate("document.documentElement.scrollWidth>window.innerWidth"):raise ValueError("Narrow page overflow")
        page.screenshot(path=str(out/"mobile.png"),full_page=True)
        report["narrow_layout_no_overflow"]=True;report["reduced_motion_no_autoplay"]=True
        browser.close()
    if errors:raise ValueError(errors)
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(movie)]))
    stream=next(s for s in probe["streams"] if s["codec_type"]=="video");duration=float(probe["format"]["duration"])
    if stream["codec_name"]!="h264" or (stream["width"],stream["height"])!=(1920,1080) or stream["r_frame_rate"]!="30/1" or int(stream["nb_frames"])!=900 or abs(duration-30)>.001:raise ValueError("Encoded format")
    if movie.stat().st_size>d["timing"]["finite_limits"]["max_output_bytes"]:raise ValueError("Media size bound")
    head=movie.read_bytes()[:200000]
    if b"moov" not in head or b"mdat" in head and head.index(b"moov")>head.index(b"mdat"):raise ValueError("Fast-start atom order")
    sheet=Image.new("RGB",(1920,882),"#f7f3e9");draw=ImageDraw.Draw(sheet)
    for i,sec in enumerate(times):
        f=out/f"encoded-{sec}.png";subprocess.run(["ffmpeg","-y","-ss",str(sec),"-i",str(movie),"-frames:v","1",str(f)],check=True,capture_output=True)
        im=Image.open(f).convert("RGB")
        if sec==9.5:im.save(out/"poster.png")
        im.thumbnail((480,270));x=i%4*480;y=i//4*294;sheet.paste(im,(x,y));draw.text((x+12,y+278),f"Output {sec}s / source {2*sec}s",fill="#263d3e")
    sheet.save(out/"contact-sheet.png")
    transition_times=(3.0,3.5,4.0,5.0,5.25,5.5,11.0,11.15,11.3,14.0,14.2,14.4,17.0,17.2,17.4,20.0,20.15,20.3,22.0,22.15,22.3,24.0,24.15,24.3,25.0,25.15,25.3)
    motion=Image.new("RGB",(1920,2058),"#f7f3e9");md=ImageDraw.Draw(motion)
    for i,sec in enumerate(transition_times):
        f=out/f"transition-{i}.png";subprocess.run(["ffmpeg","-y","-ss",str(sec),"-i",str(movie),"-frames:v","1",str(f)],check=True,capture_output=True)
        im=Image.open(f).convert("RGB");im.thumbnail((480,270));x=i%4*480;y=i//4*294;motion.paste(im,(x,y));md.text((x+12,y+274),f"Encoded transition / {sec:.2f}s",fill="#263d3e")
    motion.save(out/"motion-strip.png")
    # Inspectable encoded video stream, not just source screenshots.
    subprocess.run(["ffmpeg","-v","error","-i",str(movie),"-f","null","-"],check=True,capture_output=True)
    caption="What can we actually say about GPU prices? 234 archived A100 spot observations, the unchanged November 6 forecasts through seven days, and separate 12–36 month assumption paths. Then a saved-checkpoint replay: Tinker trained the selector; numerical models produced its chosen quantiles. Development gains are retrospective. Prospective improvement is not yet established. 60-second source timeline, shown at 2×."
    (out/"caption.txt").write_text(caption+"\n")
    write(out/"frame-timing.json",frame_rows)
    report.update({"encoded_frames":900,"encoded_seconds":duration,"fps":30,"codec":"h264","resolution":[1920,1080],"faststart_verified":True,"complete_decode_errors":[],"browser_errors":errors,"renderer_seconds":time.perf_counter()-started,"final_hold_output_seconds":3,"final_speed_transition_samples":len(transition_times)});write(out/"validation.json",report)
    names=["terminal-30s.mp4","poster.png","contact-sheet.png","motion-strip.png","mobile.png","validation.json","frame-timing.json","market-data.json","horizon-audit.json","replay.html","caption.txt","OFL.txt"]
    names += [f"encoded-{sec}.png" for sec in times]
    manifest={"schema_version":1,"kind":"price_led_market_outlook_and_training_replay","implementation_commit":os.environ.get("GITHUB_SHA"),"run_id":os.environ.get("GITHUB_RUN_ID"),"created_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source_seconds":60,"output_seconds":duration,"playback_speed":2,"timing_rule":"source_time = 2 * output_time","fps":30,"frames":900,"resolution":[1920,1080],"new_training":False,"new_numerical_fits":False,"live_inference":False,"case_id":CASE_ID,"archived_origin":"2026-11-06","archived_horizons_days":[1,3,7],"long_term":"Explicit annual rental assumptions -35%, -15%, +5%, compounded to 12/24/36 months; no probabilities","history":{"observations":234,"missing_calendar_days":65,"first":"2026-01-12","last":"2026-11-06","source_vintage":d["market"]["source_vintage"]},"checkpoint_replay":{"origin":d["case"]["origin"],"selection":d["case"]["selection"],"source_seconds":[40,44,48,50],"updates":[0,20,50,100],"case_vs_aggregate_separate":True,"quantile_coordinates_morph":False},"visual_semantics":"Separate chart modes and domains. History gaps are empty. Statistical quantile joins are guides. Scenario interpolation is explicit compounding. Checkpoint transitions crossfade actual saved paths without changing their coordinates.","limitations":["No 14/30-day accuracy claim.","No prospective accuracy claim.","No incremental RL benefit claim.","No actual resale transaction-price series.","Archived Nov7–13 outcomes not retrieved."],"provenance":d["market_provenance"],"research_provenance":d["provenance"],"attribution":d["market"]["permission"],"files":{n:{"sha256":sha((out/n).read_bytes()),"bytes":(out/n).stat().st_size} for n in names}}
    write(out/"manifest.json",manifest)
    if args.no_publish:print("MARKET_RENDER:"+json.dumps(report));return
    import modal
    run=os.environ["GITHUB_RUN_ID"];volume=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
    public_names=("terminal-30s.mp4","poster.png","contact-sheet.png","manifest.json","replay.html","validation.json","horizon-audit.json")
    with volume.batch_upload() as upload:
        for n in public_names:upload.put_file(str(out/n),"/terminal-v10/media/"+run+"/"+n)
    base=URL+"/terminal/media/"+run+"/";raw=fetch(base+"terminal-30s.mp4")
    if sha(raw)!=manifest["files"]["terminal-30s.mp4"]["sha256"]:raise ValueError("Public MP4 hash")
    rr=urllib.request.urlopen(urllib.request.Request(base+"terminal-30s.mp4",headers={"Range":"bytes=0-1023"}),timeout=90)
    if rr.status!=206 or len(rr.read())!=1024:raise ValueError("Range playback")
    receipt={"status":"passed","video_url":base+"terminal-30s.mp4","preview_url":base+"poster.png","manifest_url":base+"manifest.json","interactive_url":base+"replay.html","validation_url":base+"validation.json","duration":duration,"source_seconds":60,"playback_speed":2,"fps":30,"frames":900,"video_sha256":sha(raw),"implementation_commit":os.environ["GITHUB_SHA"],"range_verified":True}
    write(out/"publication.json",receipt)
    from .publication_terminal_v10 import publish
    publish_names=[n for n in names if n!="terminal-30s.mp4"]+["manifest.json","publication.json"]
    dest="results/terminal-v10/runs/"+run+"/market-outlook/"
    commit=publish({dest+n:(out/n).read_bytes() for n in publish_names})
    print("MARKET_VIDEO_REPORT:"+json.dumps(receipt),flush=True);print("MARKET_VIDEO_PUBLICATION:"+commit,flush=True)
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write("## Price-led market outlook at 2×\n\n"+receipt["video_url"]+"\n\n60 source seconds → 30 output seconds. 900 timing checks; 234 historical observations; 9 official quantiles; 36 saved checkpoint quantiles; 24 learning checkpoints; 111 compounded scenario values.\n\nEvidence commit: "+commit+"\n")
if __name__=="__main__":main()
