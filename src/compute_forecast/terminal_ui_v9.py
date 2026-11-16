"""Institutional market-dashboard presentation. Forecast and research artifacts stay unchanged."""
CSS=r"""
:root{--paper:#f2f5f9;--white:#ffffff;--ink:#17283e;--muted:#63738a;--line:#dce3ed;--blue:#285fe4;--green:#087e8b;--amber:#ab7928;--light:#edf3ff;--q9-shell:#101d31;--q9-font:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
html{background:var(--paper)}body{background:var(--paper);background-image:none;color:var(--ink);font-family:var(--q9-font);font-size:13px;font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1,"lnum" 1}
header{max-width:none;background:var(--q9-shell);color:#eef4ff;border:0;padding:15px 3vw;min-height:66px}
.brand{gap:11px}.brand b{font:650 18px/1.2 var(--q9-font);letter-spacing:-.4px;color:#f4f7fd}.brand small{font:9px/1.5 ui-monospace,SFMono-Regular,monospace;color:#9dafc8;letter-spacing:1.7px;margin-top:4px}.mark{border:0;border-radius:5px;transform:none;width:30px;height:30px;background:#285fe4;color:#fff;font:700 13px ui-monospace,monospace}
header>a{font-size:11px;color:#b7c7df;border:1px solid #35445c;padding:8px 12px;border-radius:4px}
nav{max-width:none;background:#17263d;border-bottom:1px solid #2c3a50;padding:0 3vw;gap:7px;justify-content:flex-start}
nav button,nav>a{font:500 12px var(--q9-font);color:#b4c3d7;min-height:42px;padding:0 14px;border-radius:0}
nav button[aria-current=true]{color:#fff;background:#233753;box-shadow:inset 0 -2px #5e91ff}
nav button[aria-current=true]:after{display:none}nav>a{margin-left:auto;display:flex;align-items:center;text-decoration:none}
main{max-width:1680px;padding:22px 3vw 56px}.leadrow{margin:0 0 18px;align-items:center}.leadrow .eyebrow{font:10px/1.5 ui-monospace,monospace;letter-spacing:1.5px;color:#63738a;text-transform:uppercase}.leadrow h1{font:650 clamp(25px,2.4vw,36px)/1.14 var(--q9-font);letter-spacing:-1.05px;margin:7px 0 6px;max-width:none}.leadrow p{font-size:12px;line-height:1.5;max-width:780px;color:#63738a}
h1,h2,h3{font-family:var(--q9-font)!important;transform:none!important}h2{font-size:22px}h3{font-size:15px}.eyebrow{font-family:ui-monospace,monospace;letter-spacing:1.3px;font-size:10px}.tiny,.sub,.fine{color:#63738a}.edition:before{display:none}.edition{border:0;background:none;transform:none}
.q9-edition{text-align:right;font:10px/1.7 ui-monospace,monospace;color:#60728c;white-space:nowrap}.q9-edition b{display:inline-block;background:#e8edf5;border:1px solid #d3ddeb;border-radius:3px;padding:3px 8px;color:#435772;font-weight:600;letter-spacing:1px;margin-bottom:4px}
.modebar{margin:0 0 14px;align-items:center}.modebar>.tiny{font:10px ui-monospace,monospace;color:#5f7188}.seg{border-radius:4px;padding:3px;background:#e6ecf4;gap:2px}.seg button{font:500 11px var(--q9-font);border-radius:3px;min-height:32px;padding:7px 12px;white-space:nowrap;color:#596c85}.seg button[aria-pressed=true]{background:#fff;box-shadow:0 1px 3px #12284512;color:#244f9f}.modes button[aria-pressed=true]{background:#172e50;color:#fff;box-shadow:none}
.timeline-sheet,.workspace{border:1px solid #d8e0ec;border-radius:7px;background:#fff;box-shadow:0 2px 9px #18315105}
.timeline-tools{padding:13px 22px;background:#f8fafd;border-bottom:1px solid #e0e7f0;gap:24px}.timeline-series{max-width:660px}.timeline-series label{font-size:9px;letter-spacing:1.2px;margin-bottom:5px;color:#6a7c95}.timeline-series select{font-size:13px;font-weight:600;border:0;padding:4px 24px 4px 0;background:transparent;letter-spacing:-.1px;color:#172d4a}
.timeline-range{gap:10px}.timeline-range>span{font-size:10px;color:#5f7188}.timeline-range .seg button{font-size:10px;min-height:29px;padding:6px 10px}
.plotpanel{background:#fff;padding:20px 24px}.plotpanel:before{display:none}.timeline-sheet .plotpanel{padding:0 22px 18px}
.timeline-summary.q9-quote-strip{display:grid;grid-template-columns:1.35fr 1fr 1.1fr .95fr;align-items:center;gap:0;margin:0 -22px;padding:17px 22px;border-bottom:1px solid #e4eaf2;background:#fff}
.q9-quote-strip>div{min-width:0;padding:0 22px;border-left:1px solid #e3e9f1}.q9-quote-strip>div:first-child{padding-left:0;border-left:0}.timeline-summary .eyebrow,.q9-quote-label{font:9px/1.5 ui-monospace,monospace;letter-spacing:1px;color:#5f7188}
.timeline-summary .timeline-price{font:600 clamp(26px,2.7vw,36px)/1.16 var(--q9-font);letter-spacing:-1.2px;margin:4px 0}.timeline-summary .timeline-price small{display:inline;font:10px var(--q9-font);margin-left:9px;color:#66788e;letter-spacing:0}.q9-quote-value{font:550 21px/1.3 var(--q9-font);letter-spacing:-.55px;color:#1e3c61;white-space:nowrap;margin:5px 0 3px}.q9-quote-meta,#timeline-point-date{font:10px/1.5 var(--q9-font);color:#5f7188;margin:0}.q9-quote-value.q9-interval{font-size:18px;letter-spacing:-.4px;color:#285fe4}.q9-quote-value.q9-unavailable{font-size:14px;color:#5f7188}
.timeline-sheet .plot-toolbar{margin:14px 0 5px;align-items:center;justify-content:space-between;gap:15px}.timeline-sheet .legend{font-size:10px;gap:17px;color:#586b83}.timeline-sheet .legend i{height:2px;border-radius:0;width:18px}.timeline-sheet .legend .band-key{background:#dce7ff!important}.q9-toolset{display:flex;gap:12px;align-items:center}.q9-toolset .seg{background:#f1f5fa}.q9-toolset .seg button{font-size:10px;min-height:28px;padding:5px 9px}.q9-toolset .seg button[aria-pressed=true]{border:1px solid #c7d5eb;background:#fff}
#plot{background:none;min-height:0;margin-top:8px}#price-chart{min-height:0;border-radius:0}.timeline-sheet #plot{margin-top:5px}
.timeline-sheet svg text{font-family:ui-monospace,SFMono-Regular,monospace;fill:#5f7188}.timeline-sheet .timeline-forecast-label{fill:#285fe4}.timeline-cutoff-label{font-size:9px;letter-spacing:.5px}.timeline-history-state{font-size:10px;color:#5f7188;margin:6px 0}.timeline-overview{border-top:1px solid #edf1f6;padding-top:7px;margin:6px 0}.timeline-overview-labels{font-size:9px;color:#5f7188}
.q9-axis-note{font:9px/1.5 ui-monospace,monospace;color:#5f7188;letter-spacing:.3px}.timeline-sheet .cursorbar,.cursorbar{padding:8px 0 3px;margin-top:7px;border-color:#e3eaf3}.cursorbar label{font:500 10px var(--q9-font);color:#627690;min-width:68px}.cursorbar input{accent-color:#285fe4;min-height:24px}
.timeline-sheet .chart-note,.chart-note{font-size:10px;line-height:1.6;color:#5f7188}.timeline-sheet .plotfoot{font:9px/1.5 ui-monospace,monospace;margin-top:8px;color:#5f7188}
.timeline-readout{background:#f8fafd;border-color:#e0e7f0;padding:17px 22px;gap:24px}.timeline-readout .margin-note{border-left-color:#dce4ef;padding-left:24px}.margin-note:before{display:none}.margin-note,.timeline-readout .margin-note{transform:none;background:none;box-shadow:none}.margin-note h3,.timeline-readout .margin-note h3{font:600 12px var(--q9-font);color:#2b4565;padding-left:0;margin-bottom:8px}.margin-note p,.timeline-readout .margin-note p{font-size:12px;color:#4e627d}.margin-note small,.timeline-readout .margin-note small{font-size:10px;color:#5f7188}
.pointvalues{font-variant-numeric:tabular-nums}.timeline-readout .pointvalue .value,.pointvalue .value{font-size:23px;font-weight:550;letter-spacing:-.7px;color:#1d3d64}.pointvalue .label{font-size:9px;letter-spacing:.3px;color:#6e7d91}.pointvalue .end{font-size:9px}.readoutdate{font:11px ui-monospace,monospace;color:#526984}.pin-action{border-color:#d8e2ee}.action,.pin-action .action,.d8-action{font:500 11px var(--q9-font);min-height:32px;border:1px solid #c7d4e5;background:#fff;color:#2f568b;border-radius:4px}
.timeline-meta{padding:0 22px 15px;background:#f8fafd;color:#65778f}.timeline-meta details{border-color:#e0e7f0}.timeline-meta summary{font-size:11px}.timeline-meta pre,.mono{font-size:10px;line-height:1.7;overflow-wrap:anywhere}.timeline-meta details p{font-size:11px}.timeline-meta details:first-child{padding-top:10px}
.contextrow{gap:28px;margin-top:24px}.contextrow h3{font:600 12px var(--q9-font);color:#435c7e;letter-spacing:0}.contextrow p{font-size:11px;line-height:1.7;color:#5f7188}
.settings{background:#f8fafd;border-color:#dde5f0;padding:22px}.settings h2{font:600 13px/1.5 var(--q9-font);color:#2f4d74}.settings label{font-size:11px;color:#526b8a}.settings select{background:#fff;border-color:#d4dfec;border-radius:4px;color:#223d60}.rate{border-color:#e1e8f1}.rate label{font-size:10px}.rate input{accent-color:#285fe4}.source-note{color:#5f7188}.plothead h2{font:600 23px/1.3 var(--q9-font);letter-spacing:-.5px}.plothead .tag,.tag{border-radius:3px;background:#f7f1e4;color:#826522;font:10px/1.5 var(--q9-font)}
.card,.research-figure,.d8-sheet,.tracecard,.textpage,.callout,.pinned-note,.sig-panel,.sig-sheet{background:#fff;border-color:#dce4ef;border-radius:6px;box-shadow:none}.research-figure h3,.atlas-lead h2{font-family:var(--q9-font);font-size:21px;letter-spacing:-.5px}.researchtabs{gap:4px}.researchtabs button{font:500 11px var(--q9-font);border:1px solid #dce4ef;border-radius:4px;background:#fff;color:#586d88;padding:8px 11px}.researchtabs button[aria-pressed=true]{color:#285fe4;background:#eaf1ff;border-color:#b9cdf5}
.d8-header{margin:22px 0 16px}.d8-header h2{font-size:28px;letter-spacing:-.8px}.d8-note{display:none}.d8-controls{border-color:#dce4ef;padding:13px 0}.d8-controls label{color:#61758f;font-size:10px}.d8-controls select{font-size:11px;border-color:#d3deed;background:#fff}.d8-grid{gap:20px;margin-top:20px}.d8-sheet{padding:21px}.d8-sheet h3{font:600 15px/1.4 var(--q9-font);color:#2b4464}.d8-small{color:#586c84;font-size:11px;line-height:1.7}.d8-sheet svg text{fill:#5c718c}.d8-banner{background:#eef3fb;border:1px solid #dbe5f5;border-left:3px solid #285fe4;border-radius:3px;padding:12px 17px}.d8-banner b{font-size:12px}.d8-full{margin-top:20px}.d8-table th{font-size:9px;color:#5f7188}.d8-table td{border-color:#e9eef5;font-size:11px}.d8-pin{background:#eef3fa;border-color:#285fe4}.d8-sheet [role=button]:focus-visible{outline-color:#285fe4}
.pin-shelf>h2{font:600 17px var(--q9-font)}.pinned-note:before{display:none}.pinned-note h3{font:600 13px var(--q9-font)}.pinned-note{background:#f8fafd;border-color:#cdd9e9}.margin-observation{font:500 15px/1.6 var(--q9-font);color:#345479}.edition{display:none}
footer{max-width:1680px;margin:auto;border-color:#dce4ef;background:transparent;color:#5f7188;font:9px/1.7 var(--q9-font);padding:20px 3vw 28px}footer>span{overflow-wrap:anywhere}
@media(min-width:1500px){.timeline-sheet .plotpanel{padding-inline:28px}.timeline-summary.q9-quote-strip{margin-inline:-28px;padding-inline:28px}.timeline-readout{padding-inline:28px}.timeline-meta{padding-inline:28px}}
@media(max-width:1100px){.q9-quote-strip>div{padding-inline:14px}.q9-quote-value{font-size:19px}.q9-quote-value.q9-interval{font-size:16px}.q9-quote-strip{grid-template-columns:1.3fr 1fr 1fr!important}.q9-quote-strip>div:last-child{display:none}.q9-edition{font-size:9px}nav{gap:0}nav button,nav>a{padding-inline:11px;font-size:11px}}
@media(max-width:760px){header{padding:12px 4vw;min-height:60px}.brand b{font-size:17px}.brand small{font-size:8px;letter-spacing:1.1px}.mark{width:27px;height:27px;font-size:11px}header>a{border:0;padding:0;font-size:10px;max-width:90px}nav{padding:0 2vw;gap:0;overflow-x:auto}nav button,nav>a{min-height:38px;padding:0 11px;font-size:10px;flex-shrink:0}nav>a{margin-left:0}
main{padding:17px 3vw 36px}.leadrow{margin:0 0 14px}.leadrow .eyebrow{font:9px ui-monospace,monospace;letter-spacing:1.1px}.leadrow h1{font:650 25px/1.14 var(--q9-font);letter-spacing:-.8px;margin:6px 0 0;max-width:340px}.leadrow p,.q9-edition{display:none}.modebar{display:block;margin-bottom:12px}.modes{display:flex;flex-wrap:nowrap;overflow-x:auto;max-width:100%;width:max-content}.modes button{font-size:10px;min-height:31px;padding:7px 9px;flex-shrink:0}.modebar>.tiny{display:none}
.timeline-tools{padding:11px 13px;display:block}.timeline-series select{font-size:12px;padding:3px 22px 4px 0}.timeline-series label{font-size:8px;margin-bottom:4px}.timeline-range{margin-top:8px;justify-content:flex-start}.timeline-range .seg{width:100%;justify-content:space-between}.timeline-range .seg button{padding:5px 8px;font-size:10px;min-height:27px}.timeline-range>span{display:none}
.timeline-sheet .plotpanel{padding:0 12px 13px}.timeline-summary.q9-quote-strip{grid-template-columns:1fr 1fr!important;margin:0 -12px;padding:12px}.q9-quote-strip>div{padding:0 0 0 14px}.q9-quote-strip>div:first-child{padding:0}.q9-quote-strip>div:nth-child(n+3){display:none}.timeline-summary .timeline-price{font-size:27px;letter-spacing:-.8px;margin-top:4px}.timeline-summary .timeline-price small{font-size:8px;margin-left:4px}.q9-quote-label,.timeline-summary .eyebrow{font-size:8px;letter-spacing:.6px}.q9-quote-value{font-size:22px}.q9-quote-meta,#timeline-point-date{font-size:9px;line-height:1.45;max-width:165px}.timeline-summary .timeline-price small{display:none}
.timeline-sheet .plot-toolbar{display:flex;margin:10px 0 4px;gap:8px;align-items:center}.timeline-sheet .legend{display:grid;grid-template-columns:1fr;gap:4px;font-size:9px}.q9-toolset{display:grid;gap:4px}.q9-toolset .seg{justify-content:space-between}.q9-toolset .seg button{font-size:9px;min-height:24px;padding:4px 7px}.timeline-sheet .plot-toolbar .seg button{min-height:24px}.q9-axis-note{font-size:8px}#price-chart{min-height:0}.timeline-sheet #unit-caption{display:none}.timeline-history-state{font-size:9px}
.timeline-readout{padding:14px 13px;grid-template-columns:1fr;gap:15px}.timeline-readout .margin-note{border-left:0;border-top:1px solid #dce5f0;padding:12px 0 0}.timeline-meta{padding:0 13px 13px}.timeline-readout .pointvalue .value{font-size:22px}.timeline-readout .pointvalues{gap:14px}.timeline-sheet .chart-note{font-size:9px}.timeline-sheet .plotfoot{font-size:8px}.timeline-overview-labels{font-size:8px}.contextrow{gap:15px}.contextrow h3{font-size:12px}.contextrow p{font-size:10px}.settings{padding:18px}.plotpanel{padding:18px 13px}.plothead h2{font-size:21px}.cursorbar label{font:500 10px var(--q9-font)}
.d8-header h2{font-size:25px}.d8-sheet{padding:16px}.d8-grid{gap:15px}.d8-controls{gap:10px}.d8-small{font-size:11px}.d8-sheet h3{font-size:15px}
}
@media(max-width:360px){main{padding-top:13px}.timeline-tools{padding-block:9px}.timeline-summary.q9-quote-strip{grid-template-columns:1.2fr .8fr!important;padding-block:10px}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}.timeline-sheet *,nav *{transition:none!important;animation:none!important}}
"""
JS=r"""
const Q9={scale:'fit'};
function q9AxisMoney(value,span){const digits=Math.max(2,Math.min(6,Math.ceil(-Math.log10(Math.max(span/4,1e-8)))+1));return '$'+new Intl.NumberFormat('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(value)}
function q9Heading(){const detail=S.mode==='scenario'?'ASSUMPTION ANALYSIS':S.mode==='history'?'INDEPENDENT MARKET CONTEXT':'GPU RENTAL MARKETS',badge=S.mode==='scenario'?'SCENARIO WORKSPACE':S.mode==='history'?'INDEPENDENT ARCHIVE':'ARCHIVED BENCHMARK',meta=S.mode==='scenario'?'12 / 24 / 36 MONTHS<br>ASSUMPTIONS / NO PROBABILITIES':S.mode==='history'?'LICENSED SOURCE HISTORY<br>SEPARATE FROM THE BENCHMARK':'06 NOV 2026 · UTC<br>'+P.series.length+' SERIES / '+P.series.reduce((n,s)=>n+s.forecasts.length,0)+' FORECAST POINTS';return '<div class="leadrow q9-heading"><div><div class="eyebrow">'+detail+' / COMPUTE FORECAST</div><h1>See what compute could cost.</h1><p>Source-level rental history, archived quantile forecasts and transparent pricing scenarios.</p></div><div class="q9-edition"><b>'+badge+'</b><br>'+meta+'</div></div>'}
atlasHeading=q9Heading;
function q9Quote(label,value,meta,cls='',raw=null){return '<div class="q9-quote"><div class="q9-quote-label">'+label+'</div><div class="q9-quote-value '+cls+'"'+(raw===null?'':' data-q9-value="'+raw+'"')+'>'+value+'</div><div class="q9-quote-meta">'+meta+'</div></div>'}
function q9ScaleButtons(){return '<div class="seg q9-scale" aria-label="Price axis scale"><button id="q9-scale-fit" data-q9-scale="fit" aria-pressed="'+(Q9.scale==='fit')+'">Fit range</button><button id="q9-scale-zero" data-q9-scale="zero" aria-pressed="'+(Q9.scale==='zero')+'">Zero base</button></div>'}
const q9PreviousExplore=explore;
explore=function(){
 let html=q9PreviousExplore();
 html=html.replace(/<div class="leadrow">[\s\S]*?<\/div><div class="modebar">/,q9Heading()+'<div class="modebar">');
 if(S.mode!=='benchmark')return html;
 const s=series(),h=t7History(),last=h?.points.filter(p=>p.date<=P.origin_date).at(-1),fc=s.forecasts.find(p=>p.horizon_days===S.forecastHorizon);
 const delta=last?fc.q50/last.value-1:null;
 const quotes=q9Quote('LAST OBSERVED',last?money(last.value):(!V5?(V5Error?'Unavailable':'Loading…'):'Not published'),last?esc(shortDate(last.date)+' · '+s.unit):(!V5?(V5Error?'Retry history below':'Matching history loading'):'Matching history unavailable'),last?'':'q9-unavailable',last?.value??null)+q9Quote('+'+S.forecastHorizon+'D QUANTILE INTERVAL',money(fc.q10)+' – '+money(fc.q90),'q10 / q90 · '+esc(s.unit),'q9-interval')+q9Quote('FORECAST / LAST OBSERVED',delta===null?'—':(delta>0?'+':'')+pct(delta),'Median change · not a realized return','',delta);
 html=html.replace('class="timeline-summary"','class="timeline-summary q9-quote-strip"').replace('<div class="timeline-hand">The past, then a forecast.<br>Keep the two in view.</div>',quotes);
 html=html.replace(/<div class="seg" aria-label="Forecast date range">[\s\S]*?<\/div>/,match=>'<div class="q9-toolset">'+q9ScaleButtons()+match+'</div>');
 html=html.replace('<div id="plot"></div>','<div id="plot"></div><div id="q9-axis-note" class="q9-axis-note">'+(Q9.scale==='fit'?'Y-AXIS: FITTED TO VISIBLE PRICES':'Y-AXIS: ZERO BASELINE')+' · USD / GPU-HOUR</div>');
 return html
};
const q9PreviousBind=bindExplore;
bindExplore=function(){q9PreviousBind();document.querySelectorAll('[data-q9-scale]').forEach(button=>button.onclick=()=>{Q9.scale=button.dataset.q9Scale;render()})};
const q9PreviousBuild=buildPlot;
buildPlot=function(){q9PreviousBuild();const chart=$('#price-chart');if(S.mode==='benchmark'&&chart){chart.dataset.axisMode=Q9.scale;chart.dataset.axisMinimum=String(plotGeom.low);chart.dataset.axisMaximum=String(plotGeom.top)}};
const q9PreviousRender=render;
render=function(){const focused=document.activeElement?.id;q9PreviousRender();if(focused?.startsWith('q9-scale'))$('#'+focused)?.focus({preventScroll:true})};

const q9OriginalBindAtlas=bindAtlas;
bindAtlas=function(){
 q9OriginalBindAtlas();const button=$('#refresh-atlas');if(!button)return;
 button.disabled=!!Q9.atlasLoading;button.setAttribute('aria-busy',String(!!Q9.atlasLoading));
 const status=document.createElement('span');status.id='q9-atlas-status';status.className='q9-axis-note';status.setAttribute('role','status');status.textContent=Q9.atlasStatus||'';button.after(status);
 button.onclick=async()=>{
  if(Q9.atlasLoading)return;const initiatedWithFocus=document.activeElement===button;Q9.atlasLoading=true;button.disabled=true;button.setAttribute('aria-busy','true');status.textContent='Refreshing verified artifacts…';
  const results=await Promise.allSettled([fetchJson('/api/experimental'),fetchJson('/api/notebook')]);
  if(results.every(r=>r.status==='fulfilled')){X=results[0].value;N=results[1].value;expandedError=null;notebookError=null;Q9.atlasStatus='Verified artifacts refreshed.'}
  else{Q9.atlasStatus='Refresh failed. Prior verified artifacts remain visible; retry is available.';if(results[0].status==='rejected')expandedError=results[0].reason;if(results[1].status==='rejected')notebookError=results[1].reason}
  Q9.atlasLoading=false;if(P&&view==='research'&&researchTab==='visual'){const restoreRefreshFocus=initiatedWithFocus&&(document.activeElement===button||document.activeElement===document.body);render();if(restoreRefreshFocus)$('#refresh-atlas')?.focus({preventScroll:true})}
 };
};
"""
def enhance(html):
    original='const raw=maximum*1.15,mag=Math.pow(10,Math.floor(Math.log10(raw))),top=Math.ceil(raw/mag*4)/4*mag,x=v=>L+(v-minX)/(maxX-minX)*(w-L-R),y=v=>T+(1-v/top)*(height-T-B);'
    replacement='const raw=maximum*1.15,mag=Math.pow(10,Math.floor(Math.log10(raw))),roundedTop=Math.ceil(raw/mag*4)/4*mag,visibleValues=pts.flatMap(p=>p.kind==="forecast"?[p.q10,p.q50,p.q90]:[p.value]);if(S.compare)visibleValues.push(...P.series.find(s=>s.id===S.compare).forecasts.filter(p=>p.horizon_days<=S.forecastHorizon).map(p=>p.q50));const floor=Math.min(...visibleValues),spread=Math.max(maximum-floor,maximum*.05,1e-8),q9Low=Q9.scale==="fit"?Math.max(0,floor-spread*.16):0,top=Q9.scale==="fit"?maximum+spread*.16:roundedTop,x=v=>L+(v-minX)/(maxX-minX)*(w-L-R),y=v=>T+(1-(v-q9Low)/(top-q9Low))*(height-T-B);'
    if html.count(original)!=1:raise ValueError("Timeline price-axis insertion contract changed")
    html=html.replace(original,replacement)
    marker='plotGeom={w,h:height,L,R,T,B,x,y,top,maxX,minX,is:false,timeline:true};'
    if html.count(marker)!=1:raise ValueError("Timeline geometry contract changed")
    html=html.replace(marker,'plotGeom={w,h:height,L,R,T,B,x,y,top,low:q9Low,maxX,minX,is:false,timeline:true};')
    if html.count('height=w<500?310:420')!=1:raise ValueError("Timeline dimensions contract changed")
    html=html.replace('height=w<500?310:420','height=w<500?280:350')
    for old,new in [('y(top*f)','y(q9Low+(top-q9Low)*f)'),('money(top*f)','q9AxisMoney(q9Low+(top-q9Low)*f,top-q9Low)')]:
        # Restrict replacements to the registered timeline builder, never other charts.
        before,body=html.split('buildPlot=function(){\n if(S.mode!==\'benchmark\')return t7PrevBuild();',1)
        body,after=body.split('\ndrawCursor=function(){',1)
        body=body.replace(old,new)
        html=before+'buildPlot=function(){\n if(S.mode!==\'benchmark\')return t7PrevBuild();'+body+'\ndrawCursor=function(){'+after
    tick_contract="ticks.forEach((t,i)=>{body+='<text x=\"'+x(t)"
    tick_replacement="ticks.forEach((t,i)=>{if(i>0&&i<ticks.length-1&&x(ticks[ticks.length-1])-x(t)<50)return;body+='<text class=\"q9-date-tick\" x=\"'+x(t)"
    if html.count(tick_contract)!=1:raise ValueError("Timeline date-label contract changed")
    html=html.replace(tick_contract,tick_replacement)
    html=html.replace('<small>AN OPEN COMPUTE NOTEBOOK</small>','<small>GPU MARKET RESEARCH</small>')
    html=html.replace('<span class="mark" aria-hidden="true">↗</span>','<span class="mark" aria-hidden="true">CF</span>')
    return html.replace('</style>',CSS+'</style>').replace('</script>',JS+'</script>')
