import * as THREE from 'three';
import {RIG} from './rig-spec.js';
import {createTaskObjects} from './task-objects.js';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';

export function createTaskStudy(element){
 const scene=new THREE.Scene();scene.background=new THREE.Color('#dce0d4');scene.fog=new THREE.Fog('#dce0d4',.9,2.4);
 const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.08;element.append(renderer.domElement);
 const pmrem=new THREE.PMREMGenerator(renderer),env=new RoomEnvironment();scene.environment=pmrem.fromScene(env,.04).texture;env.dispose();pmrem.dispose();
 const camera=new THREE.PerspectiveCamera(34,1,.001,5);camera.up.set(0,0,1);camera.position.set(.22,-.30,.21);
 const orbit=new OrbitControls(camera,renderer.domElement);orbit.target.set(.002,.021,.058);orbit.enablePan=false;orbit.enableDamping=true;orbit.minDistance=.16;orbit.maxDistance=.85;orbit.maxPolarAngle=Math.PI*.485;orbit.update();
 const key=new THREE.DirectionalLight('#fff0d0',4.4);key.position.set(-.25,-.22,.8);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-.5,right:.5,top:.5,bottom:-.5,near:.01,far:2});key.shadow.bias=-.00006;key.shadow.normalBias=.0003;key.shadow.radius=5;scene.add(key);scene.add(new THREE.HemisphereLight('#f7f8f3','#878c70',2.1));const fill=new THREE.DirectionalLight('#d4e6ee',1.7);fill.position.set(.3,.25,.5);scene.add(fill);
 const materials={shell:new THREE.MeshStandardMaterial({color:'#e5e4d9',roughness:.28,metalness:.35}),frame:new THREE.MeshStandardMaterial({color:'#25332f',roughness:.35,metalness:.6}),metal:new THREE.MeshStandardMaterial({color:'#a0aaa3',roughness:.24,metalness:.85}),rubber:new THREE.MeshStandardMaterial({color:'#25302a',roughness:.95}),accent:new THREE.MeshStandardMaterial({color:'#be7854',roughness:.5,metalness:.2}),visor:new THREE.MeshPhysicalMaterial({color:'#172c2b',roughness:.17,metalness:.6,clearcoat:1}),led:new THREE.MeshStandardMaterial({color:'#bad1ba',emissive:'#91b292',emissiveIntensity:1.2,roughness:.4}),wood:new THREE.MeshStandardMaterial({color:'#b29b72',roughness:.8}),paper:new THREE.MeshStandardMaterial({color:'#e2e3cf',roughness:.9}),felt:new THREE.MeshStandardMaterial({color:'#748271',roughness:1})};
 function mesh(g,mat,parent=scene,pos=[0,0,0]){let m=new THREE.Mesh(g,typeof mat==='string'?materials[mat]:mat);m.position.set(...pos);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m}
 function box(size,pos,mat,parent=scene,r=.001){return mesh(new RoundedBoxGeometry(...size,2,Math.min(r,...size.map(x=>x*.45))),mat,parent,pos)}
 function ball(r,pos,mat,parent){return mesh(new THREE.SphereGeometry(r,20,14),mat,parent,pos)}
 function cyl(r,h,pos,mat,parent=scene,axis='z'){const c=mesh(new THREE.CylinderGeometry(r,r,h,32),mat,parent,pos);if(axis==='z')c.rotation.x=Math.PI/2;if(axis==='x')c.rotation.z=Math.PI/2;return c}
 function bar(a,b,r,mat,parent){const va=new THREE.Vector3(...a),vb=new THREE.Vector3(...b),delta=vb.clone().sub(va);const c=mesh(new THREE.CylinderGeometry(r,r,delta.length(),18),mat,parent,va.add(vb).multiplyScalar(.5).toArray());c.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.normalize());ball(r,a,mat,parent);ball(r,b,mat,parent);return c}
 function text(label,pos,width,parent=scene,color='#4b5947',height=.006,flat=false){const c=document.createElement('canvas');c.width=1024;c.height=160;let ctx=c.getContext('2d');ctx.fillStyle=color;ctx.font='500 75px monospace';ctx.textAlign='center';ctx.fillText(label,512,105);let t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;let p=mesh(new THREE.PlaneGeometry(width,height),new THREE.MeshBasicMaterial({map:t,transparent:true,depthWrite:false}),parent,pos);if(!flat)p.rotation.x=Math.PI/2;return p}
 function motor(parent,pos,r=.007){cyl(r,.012,pos,'frame',parent,'x');for(const s of [-1,1]){cyl(r*.77,.001,[pos[0]+s*.0067,pos[1],pos[2]],'metal',parent,'x');cyl(r*.22,.0013,[pos[0]+s*.0073,pos[1],pos[2]],'accent',parent,'x')}}
 function limb(parent,end,r){bar([0,0,0],end,r,'frame',parent);let d=new THREE.Vector3(...end);let shell=box([r*2.0,d.length()*.64,r*.90],d.clone().multiplyScalar(.48).toArray(),'shell',parent,r*.38);shell.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),d.normalize());shell.position.y-=r*.60;}
 // The one actual desk: its upper surface is z=0, exactly as in MuJoCo.
 box([1.2,.8,.04],[0,0,-.02],'wood',scene,.004);
 let grain=document.createElement('canvas');grain.width=1024;grain.height=512;let gc=grain.getContext('2d');gc.fillStyle='#b59d74';gc.fillRect(0,0,1024,512);let rnd=413;function rand(){rnd=(rnd*1664525+1013904223)>>>0;return rnd/4294967296}
 for(let i=0;i<1500;i++){let y=rand()*512;gc.strokeStyle=`rgba(83,62,33,${rand()*.10})`;gc.lineWidth=.3+rand();gc.beginPath();gc.moveTo(0,y);gc.bezierCurveTo(300,y+rand()*5,700,y-3,1024,y+rand()*6);gc.stroke()}let gt=new THREE.CanvasTexture(grain);gt.colorSpace=THREE.SRGBColorSpace;gt.wrapS=gt.wrapT=THREE.RepeatWrapping;gt.repeat.set(2,2);materials.wood.map=gt;
 const felt=box([1.198,.798,.0007],[0,0,-.0001],'felt',scene,.0001);felt.visible=false;
 const root=new THREE.Group();scene.add(root);const joints={};
 function joint(name,parent,pos){let g=new THREE.Group();g.name=name;g.position.set(...pos);parent.add(g);joints[name]=g;return g}
 box(RIG.pelvis,[0,0,0],'frame',root,.003);box([.036,.003,.014],[0,-.014,0],'shell',root,.002);
 const waist=joint('waist',root,[0,0,.014]);
 box(RIG.torso,[0,0,RIG.torso[2]/2],'frame',waist,.004);
 for(const s of[-1,1]){box([.020,.005,.039],[s*.011,-.0145,.034],'shell',waist,.003);cyl(.001,.0008,[s*.018,-.0175,.045],'metal',waist,'y')}
 box([.002,.0007,.018],[-.015,-.0175,.034],'accent',waist,.0003);text('M O C H I',[0,-.0175,.012],.030,waist,'#b3c3b0',.0038);cyl(.007,.007,[0,0,.060],'metal',waist);
 for(let i=-2;i<=2;i++)box([.002,.003,.027],[i*.006,.0145,.031],'metal',waist,.0003);
 const head=joint('head',waist,[0,0,.078]);box(RIG.head,[0,0,0],'shell',head,.0035);box([.031,.002,.016],[0,-.0158,-.001],'visor',head,.002);box([.020,.0005,.001],[0,-.017,.0005],'led',head,.0003);
 for(const s of[-1,1]){cyl(.0035,.0016,[s*.018,0,0],'metal',head,'x');cyl(.0017,.0007,[s*.009,-.017,-.005],'frame',head,'y')}
 box([.0006,.020,.0005],[0,0,.0172],'frame',head,.0001);
 for(const side of[-1,1]){
  const name=side<0?'left':'right',hip=joint(name+'-hip',root,[side*.018,0,0]);motor(hip,[0,0,0],.0078);limb(hip,[0,0,-RIG.thigh],.007);const knee=joint(name+'-knee',hip,[0,0,-RIG.thigh]);motor(knee,[0,0,0],.007);limb(knee,[0,0,-RIG.shin],.006);const ankle=joint(name+'-ankle',knee,[0,0,-RIG.shin]);motor(ankle,[0,0,0],.005);
  box([.024,.040,.010],[0,-.008,-.005],'shell',ankle,.002);box([.024,.040,.002],[0,-.008,-.011],'rubber',ankle,.0006);box([.016,.010,.0008],[0,-.020,.0005],'metal',ankle,.0004);
  const shoulder=joint(name+'-shoulder',waist,[side*RIG.shoulder_span/2,0,.047]);motor(shoulder,[0,0,0],.0078);limb(shoulder,[0,0,-RIG.upper_arm],.0058);const elbow=joint(name+'-elbow',shoulder,[0,0,-RIG.upper_arm]);motor(elbow,[0,0,0],.0058);limb(elbow,[0,0,-RIG.forearm],.0048);const wrist=joint(name+'-wrist',elbow,[0,0,-RIG.forearm]);box([.011,.008,.010],[0,0,-.005],'frame',wrist,.001);for(const s of[-1,1]){box([.0024,.004,.008],[s*.0042,-.0005,-.010],'metal',wrist,.0005);box([.0028,.004,.0025],[s*.004,-.0005,-.014],'rubber',wrist,.0004)}
 }
 const objects=createTaskObjects({scene,mesh,box,cyl,bar,text,materials});
 ball(.0045,[0,0,-.014],'rubber',joints['right-wrist']);
 let mug=new THREE.Group();mug.position.set(.33,.11,0);scene.add(mug);mesh(new THREE.CylinderGeometry(.036,.0345,.088,64,1,true),'shell',mug,[0,0,.045]).rotation.x=Math.PI/2;let innerCup=new THREE.MeshStandardMaterial({color:'#dfdfd1',roughness:.35,side:THREE.BackSide});mesh(new THREE.CylinderGeometry(.0328,.0314,.083,64,1,true),innerCup,mug,[0,0,.0465]).rotation.x=Math.PI/2;cyl(.0345,.003,[0,0,.003],'shell',mug);mesh(new THREE.TorusGeometry(.0344,.0021,12,64),'shell',mug,[0,0,.089]);cyl(.032,.0008,[0,0,.083],new THREE.MeshPhysicalMaterial({color:'#28180f',roughness:.18}),mug);let h=mesh(new THREE.TorusGeometry(.019,.004,12,32),'shell',mug,[.044,0,.052]);h.rotation.x=Math.PI/2;text('HUMAN',[0,-.0365,.054],.047,mug,'#65735d',.008);text('IN THE LOOP',[0,-.0365,.040],.052,mug,'#65735d',.006);
 let note=new THREE.Group();note.position.set(-.17,-.23,.001);note.rotation.z=-.12;scene.add(note);box([.14,.09,.0008],[0,0,0],'paper',note,.0006);text('MOCHI / CONTACT STUDY',[0,.022,.0007],.118,note,'#667454',.006,true);for(let i=0;i<4;i++){let l=mesh(new THREE.PlaneGeometry(.10,.0003),'felt',note,[0,.007-i*.012,.0008]);l.rotation.z=.02}bar([-.25,-.11,.0035],[-.10,-.10,.0035],.0035,'accent',scene);
 const bindings={pelvis:root,...joints,...objects.bindings};
 let episode=null,playhead=0;const worldA=new THREE.Vector3(),worldB=new THREE.Vector3(),qA=new THREE.Quaternion(),qB=new THREE.Quaternion(),parentQ=new THREE.Quaternion();
 function applyFrame(time){if(!episode)return null;let frames=episode.trajectory.frames,x=Math.min(Math.max(time,0)*episode.trajectory.sample_hz,frames.length-1),i=Math.floor(x),a=frames[i],b=frames[Math.min(i+1,frames.length-1)],mix=x-i;
  episode.trajectory.body_names.forEach((name,k)=>{let obj=bindings[name];if(!obj)return;worldA.fromArray(a.positions[k]);worldB.fromArray(b.positions[k]);worldA.lerp(worldB,mix);let qa=a.quaternions[k],qb=b.quaternions[k];qA.set(qa[1],qa[2],qa[3],qa[0]);qB.set(qb[1],qb[2],qb[3],qb[0]);qA.slerp(qB,mix);obj.parent.updateWorldMatrix(true,false);obj.position.copy(obj.parent.worldToLocal(worldA));parentQ.copy(obj.parent.getWorldQuaternion(parentQ)).invert();obj.quaternion.copy(parentQ.multiply(qA));obj.updateMatrixWorld(true)});
  return{angle:a.angle+(b.angle-a.angle)*mix,phase:a.phase,contact:a.hand_contact,time:a.t+(b.t-a.t)*mix};
 }
 function view(which){const views={laptop:{p:[-.25,-.34,.28],t:[-.025,.025,.115]},globe:{p:[.02,-.39,.28],t:[.135,.025,.115]},wide:{p:[.39,-.58,.37],t:[.015,.015,.10]},front:{p:[.02,-.56,.25],t:[.015,.015,.10]}};let v=views[which]||views[episode?.task]||views.wide;camera.position.set(...v.p);orbit.target.set(...v.t);orbit.update()}
 function frame(time){playhead=time;let state=applyFrame(time);orbit.update();renderer.render(scene,camera);return state}
 function resize(){let{width,height}=element.getBoundingClientRect();if(!width||!height)return;camera.aspect=width/height;camera.fov=width<600?43:34;camera.updateProjectionMatrix();renderer.setSize(width,height,false);frame(playhead)}new ResizeObserver(resize).observe(element);resize();view('wide');
 return{frame,camera:view,setEpisode(data){episode=data;objects.setTask(data.task);view(data.task);frame(0)}};
}
