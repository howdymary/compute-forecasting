"""Generate a self-contained offline replay from ACTUAL completed run artifacts."""
import json,pathlib,html
ROOT=pathlib.Path(__file__).resolve().parent
def build():
    out=ROOT/"results"
    report=json.loads((out/"report.json").read_text())
    cert=json.loads((out/"best.json").read_text())
    events=[json.loads(l) for l in (out/"trace.jsonl").read_text().splitlines() if l.strip()]
    sources=json.loads((out/"sources.json").read_text())
    def portable(value):
        if type(value) is int and abs(value)>2**53-1:return str(value)
        if isinstance(value,list):return [portable(x) for x in value]
        if isinstance(value,dict):return {k:portable(v) for k,v in value.items()}
        return value
    data=json.dumps({"report":report,"certificate":portable(cert),"certificate_json":json.dumps(cert,indent=2),"events":portable(events),"sources":sources}).replace("</","<\\/")
    page=HTML.replace("__DATA__",data)
    (out/"demo.html").write_text(page)
    print("BOUNDFORGE_DEMO "+json.dumps({"bytes":len(page.encode()),"events":len(events),"artifact":"demo.html"}))
HTML=r"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BoundForge · Certified research replay</title>
<style>
:root{font:16px/1.5 system-ui,sans-serif;color:#18322a;background:#f4f6ef}
body{max-width:1240px;margin:auto;padding:28px}header{display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid #c5d1c7;padding-bottom:18px}
h1{font-size:32px;letter-spacing:-1px;margin:0}h2{font-size:19px;margin:0 0 14px}.eyebrow{font:12px ui-monospace,monospace;letter-spacing:2px;color:#5a6d63}
p{margin:8px 0}main{display:grid;grid-template-columns:1.2fr 1fr;gap:20px;margin-top:24px}.card{background:white;border:1px solid #d8e0d4;border-radius:12px;padding:22px;min-width:0}
.full{grid-column:1/-1}#bound{font:20px/1.5 ui-monospace,monospace;overflow-wrap:anywhere;color:#126a49}.muted{color:#607067;font-size:14px;overflow-wrap:anywhere}
button,select{font:inherit;border:1px solid #c4d3c7;border-radius:7px;background:white;padding:7px 12px;cursor:pointer}button:hover{background:#e8f3e9}button.primary{background:#165b42;color:white;border-color:#165b42}
svg{width:100%;height:320px;background:#f8faf5;border-radius:8px}pre{white-space:pre-wrap;word-break:break-word;font:12px/1.6 ui-monospace,monospace;max-height:380px;overflow:auto;background:#f6f8f3;padding:14px;border-radius:8px}
#status{border:1px solid #a6c7b2;background:#eaf5ee;padding:5px 10px;border-radius:30px;font-size:13px;align-self:start}
table{width:100%;border-collapse:collapse;font-size:14px;table-layout:fixed}td,th{overflow-wrap:anywhere;text-align:left;border-bottom:1px solid #e3e9df;padding:9px}
a{color:#116245}#events{max-height:420px;overflow:auto}input[type=range]{width:100%}.tag{font:12px ui-monospace,monospace;color:#496957}
footer{margin-top:20px;font-size:12px;color:#607067}@media(max-width:760px){main{grid-template-columns:1fr}body{padding:16px}header{display:block}#status{display:inline-block;margin-top:12px}}
</style>
<header><div><div class="eyebrow">AUTONOMOUS MATHEMATICS / C3c</div><h1>BoundForge</h1><p class="muted">Find a construction. Challenge the result. Keep the certificate.</p></div><div id="status"></div></header>
<main>
<section class="card full"><h2>Strongest verified witness</h2><p id="bound"></p><p id="scope" class="muted"></p><p class="muted">H(X−Y) / max{H(X), H(Y), H(X+Y), H(X+2Y)}. Lower bounds only; the sharp constant is unknown.</p></section>
<section class="card"><h2>Inspect the construction</h2><select id="law" aria-label="Digit law"></select> <select id="projection" aria-label="Projection"><option value="0">X−Y</option><option value="1">X</option><option value="2">Y</option><option value="3">X+Y</option><option value="4">X+2Y</option></select>
<svg id="plot" viewBox="0 0 520 320" role="img" aria-label="Integer support of selected digit law"></svg><p id="lawdata" class="muted"></p><button id="check" class="primary">Check exact structural conditions</button><p id="checks" class="muted"></p><p class="muted">Browser check: exact rational mass, integer supports, digit base. Rigorous entropy verification uses the two Python checkers.</p><button id="download">Download exact witness</button></section>
<section class="card"><h2>Replay the actual research log</h2><p class="muted">Recorded execution. This replay launches no API calls.</p><input id="step" type="range" min="0" value="0" aria-label="Research event"><p id="eventTitle" class="tag"></p><pre id="event"></pre></section>
<section class="card"><h2>Independent certification</h2><pre id="verification"></pre><p class="muted">Repeat in a remote runner:</p><pre>python boundforge/verify.py best.json --baseline boundforge/certificates/incumbent.json
python boundforge/verify_independent.py best.json boundforge/certificates/incumbent.json</pre></section>
<section class="card"><h2>Provider accounting</h2><table><thead><tr><th>Provider</th><th>Initial cap</th><th>Usage / held reserve</th></tr></thead><tbody id="costs"></tbody></table><p class="muted">Unknown costs remain reserved. Reservations and token estimates are not invoices. Credits are never pooled.</p></section>
<section class="card full"><h2>What Exa found</h2><div id="sources"></div><p class="muted">Sources are evidence for hypotheses, not mathematical certificates. Original two-law construction and stationary free-energy method: Manvir Jaswal, Zenodo 23289305.</p></section>
</main><footer id="provenance"></footer>
<script id="data" type="application/json">__DATA__</script>
<script>
"use strict";
const data=JSON.parse(document.getElementById("data").textContent), cert=data.certificate, report=data.report;
const $=id=>document.getElementById(id), put=(id,value)=>$(id).textContent=value;
put("status",report.strict_improvement?"Certified witness improvement":"Incumbent reproduced");
put("bound",(report.best.ratio_interval_arb||[]).join("\n"));
put("scope",report.strict_improvement?"A strictly stronger exact certificate. Inspect the experiment log to distinguish refined proportions from new support.":"No new record: the strongest retained result is the attributed incumbent.");
put("verification",JSON.stringify(report.independent||report.best,null,2));
put("provenance","Source "+report.source_commit+" · Actions run "+report.workflow_run+" · No live provider credentials in this file");
cert.laws.forEach((l,i)=>{let o=document.createElement("option");o.value=i;o.textContent="Law "+(i+1)+" · "+l.points.length+" points";$("law").append(o)});
const ns="http://www.w3.org/2000/svg", forms=[(x,y)=>x-y,(x,y)=>x,(x,y)=>y,(x,y)=>x+y,(x,y)=>x+2*y];
function draw(){let law=cert.laws[+$("law").value],j=+$("projection").value;let pts=law.points,ps=law.weights.map(w=>Number(BigInt(w[0]))/Number(BigInt(w[1]))),xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]),xmin=Math.min(...xs)-2,xmax=Math.max(...xs)+2,ymin=Math.min(...ys)-2,ymax=Math.max(...ys)+2;
$("plot").replaceChildren();
pts.forEach(([x,y],i)=>{let node=document.createElementNS(ns,"circle");node.setAttribute("cx",30+460*(x-xmin)/(xmax-xmin));node.setAttribute("cy",290-260*(y-ymin)/(ymax-ymin));node.setAttribute("r",Math.max(3,25*Math.sqrt(ps[i])));node.setAttribute("fill",`hsl(${((forms[j](x,y)%17+17)%17)*21} 48% 42%)`);let t=document.createElementNS(ns,"title");t.textContent=JSON.stringify({point:[x,y],projection:forms[j](x,y),weight:law.weights[i]});node.append(t);$("plot").append(node)});
put("lawdata","Base "+cert.base+" · digit counts "+cert.counts.map(String).join(" / ")+" · colour groups equal projected values; circle area approximates probability.");}
$("law").onchange=draw;$("projection").onchange=draw;draw();
let steps=data.events;$("step").max=Math.max(0,steps.length-1);function replay(){let row=steps[+$("step").value];put("eventTitle",(+$("step").value+1)+" / "+steps.length+" · "+row.kind);put("event",JSON.stringify(row,null,2))}$("step").oninput=replay;replay();
Object.entries(report.providers).forEach(([name,p])=>{let tr=document.createElement("tr");[name,p.initial_cap+" "+(p.units||""),String(p.reserved_or_actual)].forEach(v=>{let td=document.createElement("td");td.textContent=v;tr.append(td)});$("costs").append(tr)});
data.sources.forEach(ev=>{let h=document.createElement("h3");h.textContent=ev.query;$("sources").append(h);(ev.results||[]).forEach(r=>{if(!/^https?:\/\//.test(r.url||""))return;let p=document.createElement("p"),a=document.createElement("a");a.href=r.url;a.textContent=r.title||r.url;a.rel="noopener noreferrer";a.target="_blank";p.append(a);$("sources").append(p)})});
function gcd(a,b){while(b){let t=a%b;a=b;b=t}return a}
$("check").onclick=()=>{try{if(!Number.isSafeInteger(cert.base)||cert.base<2)throw Error("invalid base");
for(let [k,l]of cert.laws.entries()){let n=0n,d=1n,seen=new Set();if(l.points.length!==l.weights.length)throw Error("length mismatch");l.points.forEach(([x,y],i)=>{if(!Number.isSafeInteger(x)||!Number.isSafeInteger(y))throw Error("invalid coordinates");let key=x+","+y;if(seen.has(key))throw Error("duplicate support");seen.add(key);if(forms.some(fn=>2*Math.abs(fn(x,y))>=cert.base))throw Error("insufficient digit base");let a=BigInt(l.weights[i][0]),b=BigInt(l.weights[i][1]);if(a<=0n||b<=0n)throw Error("nonpositive probability");n=n*b+a*d;d*=b;let g=gcd(n,d);n/=g;d/=g});if(n!==d)throw Error("mass not exactly one");if(BigInt(cert.counts[k])<=0n)throw Error("invalid count");}
put("checks","PASS · exact mass = 1 for each law; integer supports distinct; all five digit projections fit the base; counts positive.");}catch(e){put("checks","FAIL · "+e.message)}};
$("download").onclick=()=>{let blob=new Blob([data.certificate_json],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="boundforge-witness.json";a.click();URL.revokeObjectURL(a.href)};
</script></html>"""
if __name__=="__main__":build()
