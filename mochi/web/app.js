import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const $=s=>document.querySelector(s), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=x=>`${Math.round(x*100)}%`, get=async name=>{let r=await fetch(`data/${name}.json`);if(!r.ok)throw Error(`Missing ${name}`);return r.json()};
let report,baseline,selected,heldout,mode='selected',scope='development',playing=!matchMedia('(prefers-reduced-motion: reduce)').matches,time=0,previous=performance.now();
const palette={ivory:0xe3dfcf,coral:0xe09a7e,dark:0x30443c,mint:0xb5dab6,gold:0xedbc60,wood:0xc4aa83,floor:0xe8e8da};
function sceneView(element){
 const scene=new THREE.Scene();scene.background=new THREE.Color(0xe9e9de);
 const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.setClearColor(0xe9e9de);renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;element.append(renderer.domElement);
 const camera=new THREE.PerspectiveCamera(35,1,.01,50);camera.up.set(0,0,1);camera.position.set(.95,-1.28,1.04);
 const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,.11,.48);controls.enablePan=false;controls.minDistance=1.1;controls.maxDistance=2.8;controls.maxPolarAngle=Math.PI*.48;controls.update();
 const light=new THREE.DirectionalLight(0xfff8e6,3.3);light.position.set(-.8,-1.4,2.4);light.castShadow=true;light.shadow.mapSize.set(2048,2048);light.shadow.camera.left=-1;light.shadow.camera.right=1;light.shadow.camera.top=1;light.shadow.camera.bottom=-1;light.shadow.bias=-.0004;light.shadow.normalBias=.008;scene.add(light);scene.add(new THREE.HemisphereLight(0xfff9eb,0xb6c0ac,3));
 const fill=new THREE.DirectionalLight(0xffffff,1.3);fill.position.set(1,.6,1.3);scene.add(fill);
 const materials={};for(const [k,c] of Object.entries(palette))materials[k]=new THREE.MeshStandardMaterial({color:c,roughness:k==='floor'?.9:.38,metalness:k==='ivory'?.12:.05});materials.mint.emissive.setHex(0x689574);materials.mint.emissiveIntensity=.5;
 function mesh(geo,material,parent=scene,pos=[0,0,0]){const o=new THREE.Mesh(geo,materials[material]);o.position.set(...pos);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o}
 function box(size,pos,mat,parent=scene,r=.01){return mesh(new RoundedBoxGeometry(...size,3,r),mat,parent,pos)}
 function sphere(size,pos,mat,parent=scene){const o=mesh(new THREE.SphereGeometry(1,24,16),mat,parent,pos);o.scale.set(...size);return o}
 function capsule(a,b,rad,mat,parent){const v=new THREE.Vector3(...b).sub(new THREE.Vector3(...a));const o=mesh(new THREE.CylinderGeometry(rad,rad,v.length,24),mat,parent,new THREE.Vector3(...a).addScaledVector(v,.5).toArray());o.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),v.normalize());sphere([rad,rad,rad],a,mat,parent);sphere([rad,rad,rad],b,mat,parent)}
 box([1.13,.98,.055],[0,.08,-.03],'floor',scene,.04);box([20,20,.02],[0,0,-.075],'floor',scene,.005);box([.72,.58,.05],[0,0,.435],'wood',scene,.012);
 for(const x of [-.29,.29])for(const y of [-.22,.22])box([.034,.034,.42],[x,y,.21],'wood');
 const bodies={};for(const name of ['torso','head','left-upper','left-fore','right-yaw','right-upper','right-fore','hand','left-leg','right-leg','left-foot','right-foot','puck']){bodies[name]=new THREE.Group();scene.add(bodies[name])}
 sphere([.12,.075,.15],[0,0,0],'ivory',bodies.torso);box([.09,.012,.052],[0,-.073,.02],'coral',bodies.torso,.012);
 box([.29,.18,.23],[0,0,0],'ivory',bodies.head,.055);box([.238,.015,.151],[0,-.092,.002],'dark',bodies.head,.03);
 for(const x of [-.052,.052])box([.027,.009,.043],[x,-.103,.013],'mint',bodies.head,.012);
 const smile=new THREE.CatmullRomCurve3([new THREE.Vector3(-.016,-.103,-.033),new THREE.Vector3(0,-.105,-.04),new THREE.Vector3(.016,-.103,-.033)]);mesh(new THREE.TubeGeometry(smile,12,.002,6,false),'mint',bodies.head);
 for(const x of [-.157,.157])sphere([.018,.04,.05],[x,0,0],'coral',bodies.head);
 capsule([0,0,0],[-.045,-.035,-.16],.035,'ivory',bodies['left-upper']);capsule([0,0,0],[.02,-.11,-.04],.03,'ivory',bodies['left-fore']);sphere([.033,.03,.028],[.02,-.11,-.04],'coral',bodies['left-fore']);
 sphere([.04,.04,.04],[0,0,0],'coral',bodies['right-yaw']);capsule([0,0,0],[0,-.22,0],.029,'ivory',bodies['right-upper']);capsule([0,0,0],[0,-.20,0],.024,'ivory',bodies['right-fore']);sphere([.032,.032,.032],[0,0,0],'coral',bodies['right-fore']);sphere([.018,.018,.018],[0,0,0],'coral',bodies.hand);
 for(const side of ['left','right']){capsule([0,0,-.12],[0,0,.18],.04,'ivory',bodies[`${side}-leg`]);box([.11,.17,.07],[0,0,0],'coral',bodies[`${side}-foot`],.02)}
 const puck=mesh(new THREE.CylinderGeometry(.025,.025,.024,48),'gold',bodies.puck);puck.rotation.x=Math.PI/2;
 const shape=new THREE.Shape();for(let i=0;i<10;i++){const r=i%2===0?.014:.006,x=r*Math.sin(i*Math.PI/5),y=r*Math.cos(i*Math.PI/5);if(i===0)shape.moveTo(x,y);else shape.lineTo(x,y)}shape.closePath();mesh(new THREE.ShapeGeometry(shape),'ivory',bodies.puck,[0,0,.0124]);
 const ring=mesh(new THREE.TorusGeometry(.028,.0025,12,48),'mint');
 let trajectory;
 function setData(data){trajectory=data.trajectory;ring.position.set(data.scenario.target[0],data.scenario.target[1],.463)}
 function frame(t){if(!trajectory)return;const f=trajectory.frames[Math.min(trajectory.frames.length-1,Math.floor(t*25))];trajectory.body_names.forEach((name,i)=>{const o=bodies[name];if(o){o.position.set(...f.positions[i]);const q=f.quaternions[i];o.quaternion.set(q[1],q[2],q[3],q[0])}});renderer.render(scene,camera)}
 const resize=()=>{const {width,height}=element.getBoundingClientRect();if(!width)return;camera.aspect=width/height;camera.updateProjectionMatrix();renderer.setSize(width,height,false);frame(time)};new ResizeObserver(resize).observe(element);resize();return {setData,frame,resize};
}
let left,right;
function updateMode(){
 $('#selected-view').classList.toggle('hidden',mode==='baseline');$('#baseline-view').classList.toggle('hidden',mode==='selected'||scope==='heldout');$('.studio').classList.toggle('compare',mode==='compare');
 document.querySelectorAll('[data-mode]').forEach(x=>{x.classList.toggle('active',x.dataset.mode===mode);x.disabled=scope==='heldout'&&x.dataset.mode!=='selected'});
 if(left){left.setData(scope==='heldout'?heldout:selected);right.setData(baseline);left.resize();right.resize()}
 $('#seed').textContent=`SEED ${(scope==='heldout'?heldout:selected).scenario.seed}`;time=0;
}
function showReport(r){
 const evals=r.evaluation.heldout;$('#baseline-score').textContent=pct(evals.baseline.success_rate);$('#selected-score').textContent=pct(evals.selected.success_rate);$('#distance').textContent=`${(evals.selected.mean_final_distance_m*100).toFixed(1)}cm`;
 for(const key of ['baseline','selected']){let v=evals[key];$(`#${key}-count`).textContent=`${v.successes}/${v.n} trials · 95% CI ${pct(v.wilson_95[0])}–${pct(v.wilson_95[1])}`}
 $('#run-status').textContent=r.mode==='live-sponsored-research'?`Live sponsor run completed · Exa, past.dev, Tinker & Modal · ${r.remote_rollouts} remote rollouts`:'Local conventional search · sponsor services were not executed in this run.';
 $('#demo-note').textContent=r.demo_scope;
 const rounds=r.rounds??[];$('#decisions').innerHTML=rounds.length?rounds.map(x=>`<div class="decision"><small>ROUND ${x.round+1}</small><span>${esc(x.design.replaceAll('_',' '))}<br><small>Research focus: ${esc(x.focus.replaceAll('_',' '))}</small></span><span class="badge ${x.accepted?'':'rejected'}">${x.accepted?'ACCEPTED':'REJECTED'}</span></div>`).join(''):`<div class="decision"><small>LOCAL</small><span>${r.candidate_count} parameter candidates · ${r.search_rollouts} search rollouts<br><small>Selected on development; held-out evaluation follows the freeze.</small></span><span class="badge">MEASURED</span></div>`;
 const sources=(r.sources??[]).flatMap(x=>x.sources??[]);const unique=[...new Map(sources.map(x=>[x.url,x])).values()];$('#sources').innerHTML=unique.length?unique.slice(0,5).map(x=>`<div class="source"><a href="${/^https?:\/\//.test(x.url)?esc(x.url):'#'}" target="_blank" rel="noreferrer">${esc(x.title)} ↗</a><small>${esc(new URL(x.url).hostname)}</small><p>${esc(x.excerpt)}</p></div>`).join(''):'<p class="empty">This local run used conventional parameter search. Source cards appear only after real Exa retrieval in the sponsor-connected run.</p>';
 const mem=r.memory?.reads?.filter(x=>x.cross_agent_use)??[];$('#memory').innerHTML=mem.length?mem.slice(0,5).map(x=>`<div class="memory">${esc(x.author.split('-').at(-1))} → ${esc(x.reader_role)}<small>Verified source: ${esc(x.record_id)}<br>Canonical payload hash: ${esc(x.sha256?.slice(0,16))}</small></div>`).join(''):'<p class="empty">No external memory reads occurred in this local run. The live workflow records actual author, reader, source ID, and consumed payload hash.</p>';
 $('#evaluations').innerHTML='<table><thead><tr><th>Scenario set</th><th>Starting</th><th>Selected</th><th>Random control</th></tr></thead><tbody>'+Object.entries(r.evaluation).map(([key,v])=>`<tr><td>${esc(key.replaceAll('_',' '))}</td><td>${v.baseline.successes}/${v.baseline.n}</td><td>${v.selected.successes}/${v.selected.n}</td><td>${v.random?`${v.random.successes}/${v.random.n}`:'Selected is random-search winner'}</td></tr>`).join('')+'</tbody></table>';
}
try{
 [report,baseline,selected,heldout]=await Promise.all(['report','baseline','selected','heldout'].map(get));showReport(report);
 left=sceneView($('#selected-view'));right=sceneView($('#baseline-view'));updateMode();
}catch(e){console.error(e);$('#fallback').hidden=false;$('#run-status').textContent='Interactive viewer unavailable. Recorded render and raw artifacts remain inspectable.'}
document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.mode;updateMode()}));$('#scope').addEventListener('change',e=>{scope=e.target.value;mode='selected';updateMode()});$('#play').onclick=()=>{playing=!playing;$('#play').textContent=playing?'Ⅱ':'▶'};$('#reset').onclick=()=>{time=0};$('#scrub').oninput=e=>{time=+e.target.value/100;playing=false;$('#play').textContent='▶'};
function tick(now){const dt=Math.min(.08,(now-previous)/1000);previous=now;if(playing)time=(time+dt)%6;left?.frame(time);if(mode!=='selected')right?.frame(time);$('#scrub').value=Math.round(time*100);$('#time').textContent=`${time.toFixed(2)} / 6.00s`;const data=scope==='heldout'?heldout:mode==='baseline'?baseline:selected;const idx=Math.min(data?.trajectory?.frames.length-1,Math.floor(time*25));if(data){const inContact=data.trajectory.contact[idx];$('#contact').textContent=inContact?'CONTACT DETECTED':data.trajectory.phases[idx]?.toUpperCase()??'RECORDED REPLAY'}requestAnimationFrame(tick)}requestAnimationFrame(tick);
