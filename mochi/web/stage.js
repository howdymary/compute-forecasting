import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';

// A mechanical visual shell around recorded rigid-body frames. The contact pad,
// puck, target, and table retain the same uniform transform. Passive panels have
// no claimed collision or balancing capability. No task motion is synthesized.
export function createStage(element){
 const scene=new THREE.Scene();scene.background=new THREE.Color('#d9ddd3');scene.fog=new THREE.Fog('#d9ddd3',1.1,3);
 const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;element.append(renderer.domElement);
 const pmrem=new THREE.PMREMGenerator(renderer);const env=new RoomEnvironment();scene.environment=pmrem.fromScene(env,.04).texture;env.dispose();pmrem.dispose();
 const camera=new THREE.PerspectiveCamera(33,1,.002,8);camera.up.set(0,0,1);camera.position.set(.30,-.39,.26);
 const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,.045,.104);controls.minDistance=.24;controls.maxDistance=.82;controls.enablePan=false;controls.maxPolarAngle=Math.PI*.48;controls.enableDamping=true;controls.update();let touched=false;controls.addEventListener('start',()=>touched=true);
 const sun=new THREE.DirectionalLight('#fff2d9',4.3);sun.position.set(-.30,-.35,.8);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-.6,right:.6,top:.6,bottom:-.6,near:.01,far:2});sun.shadow.bias=-.00015;sun.shadow.normalBias=.0008;sun.shadow.radius=5;scene.add(sun);
 scene.add(new THREE.HemisphereLight('#f1f5ef','#a5aa95',1.65));const rim=new THREE.DirectionalLight('#e1effa',1.9);rim.position.set(.3,.3,.6);scene.add(rim);
 const mat={shell:new THREE.MeshStandardMaterial({color:'#e0e2dc',roughness:.29,metalness:.32}),frame:new THREE.MeshStandardMaterial({color:'#263333',roughness:.32,metalness:.65}),metal:new THREE.MeshStandardMaterial({color:'#8d9b9c',roughness:.29,metalness:.87}),rubber:new THREE.MeshStandardMaterial({color:'#1d2725',roughness:.86}),orange:new THREE.MeshStandardMaterial({color:'#bd6940',roughness:.4,metalness:.2}),visor:new THREE.MeshPhysicalMaterial({color:'#142b31',roughness:.15,metalness:.65,clearcoat:1}),light:new THREE.MeshStandardMaterial({color:'#c1e6cf',emissive:'#82c4a4',emissiveIntensity:1.4,roughness:.3}),wood:new THREE.MeshStandardMaterial({color:'#b89973',roughness:.7}),paper:new THREE.MeshStandardMaterial({color:'#eae8d6',roughness:.85}),puck:new THREE.MeshStandardMaterial({color:'#c9904a',roughness:.32,metalness:.4}),glass:new THREE.MeshPhysicalMaterial({color:'#b6c9b4',roughness:.25,metalness:.1,transparent:true,opacity:.76,depthWrite:false}),screen:new THREE.MeshStandardMaterial({color:'#294138',roughness:.6,emissive:'#122820',emissiveIntensity:.2})};
 const rig=new THREE.Group();rig.scale.setScalar(.23);rig.position.z=-.00805;scene.add(rig);
 function mesh(geometry,m,parent=rig,pos=[0,0,0]){const o=new THREE.Mesh(geometry,mat[m]);o.position.set(...pos);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o}
 function box(size,pos,m,parent=rig,r=.005){return mesh(new RoundedBoxGeometry(...size,2,r),m,parent,pos)}
 function ball(radius,pos,m,parent){return mesh(new THREE.SphereGeometry(radius,20,12),m,parent,pos)}
 function cylinder(radius,depth,pos,m,parent=rig,axis='Z'){const o=mesh(new THREE.CylinderGeometry(radius,radius,depth,24),m,parent,pos);if(axis==='Z')o.rotation.x=Math.PI/2;if(axis==='X')o.rotation.z=Math.PI/2;return o}
 function bar(a,b,r,m,parent){const v=new THREE.Vector3(...b).sub(new THREE.Vector3(...a));const o=mesh(new THREE.CylinderGeometry(r,r,v.length(),20),m,parent,new THREE.Vector3(...a).addScaledVector(v,.5).toArray());o.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),v.normalize());return o}
 function text(value,pos,width,parent=rig,color='#d6dfcf',height=.022){const c=document.createElement('canvas');c.width=1024;c.height=128;const ctx=c.getContext('2d');ctx.fillStyle=color;ctx.font='500 62px Arial';ctx.textAlign='center';ctx.fillText(value,512,86);const texture=new THREE.CanvasTexture(c);texture.colorSpace=THREE.SRGBColorSpace;const o=new THREE.Mesh(new THREE.PlaneGeometry(width,height),new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false}));o.position.set(...pos);o.rotation.x=Math.PI/2;parent.add(o);return o}
 function motor(pos,r,parent){cylinder(r,.065,pos,'frame',parent,'X');for(const sign of [-1,1]){cylinder(r*.78,.007,[pos[0]+sign*.035,pos[1],pos[2]],'metal',parent,'X');cylinder(r*.23,.009,[pos[0]+sign*.039,pos[1],pos[2]],'shell',parent,'X')}}
 function limb(parent,a,b,r){bar(a,b,r,'frame',parent);ball(r,a,'metal',parent);ball(r,b,'frame',parent);const v=new THREE.Vector3(...b).sub(new THREE.Vector3(...a));const panel=box([r*1.65,v.length()*.68,r*.92],new THREE.Vector3(...a).addScaledVector(v,.5).toArray(),'shell',parent,r*.3);panel.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),v.normalize());panel.position.z+=r*.64;return panel}
 // Raised instrument platform. Its upper surface equals MuJoCo's z=.46.
 box([.72,.58,.05],[0,0,.435],'glass',rig,.008);box([.73,.025,.025],[0,-.28,.432],'metal');
 for(const x of [-.29,.29])for(const y of [-.22,.22]){cylinder(.012,.39,[x,y,.23],'metal');cylinder(.022,.02,[x,y,.044],'rubber')}
 for(const x of [-.29,.29])for(const y of [-.22,.22])cylinder(.006,.003,[x,y,.462],'metal');
 text('MOCHI / CONTACT LAB',[0,-.296,.425],.37,rig,'#263a32',.022);
 const bodies={};for(const name of ['torso','head','left-upper','left-fore','right-yaw','right-upper','right-fore','hand','left-leg','right-leg','left-foot','right-foot','puck']){const o=new THREE.Group();bodies[name]=o;rig.add(o)}
 box([.22,.14,.24],[0,0,.012],'frame',bodies.torso,.025);
 for(const sign of [-1,1]){box([.101,.023,.17],[sign*.054,-.079,.04],'shell',bodies.torso,.014);for(const z of [-.024,.10])cylinder(.004,.004,[sign*.086,-.094,z],'metal',bodies.torso,'Y')}
 box([.012,.003,.09],[-.077,-.094,.065],'orange',bodies.torso,.002);text('M O C H I',[0,-.096,-.009],.12,bodies.torso,'#5c6f65',.017);
 for(const z of [-.125,-.15])box([.145,.12,.018],[0,0,z],'shell',bodies.torso,.006);
 cylinder(.037,.08,[0,0,.14],'metal',bodies.torso);for(let i=-2;i<=2;i++)box([.009,.018,.12],[i*.027,.078,.01],'metal',bodies.torso,.002);
 const head=bodies.head;box([.173,.143,.16],[0,0,-.014],'shell',head,.028);box([.155,.016,.085],[0,-.074,-.015],'visor',head,.013);box([.10,.003,.006],[0,-.084,.004],'light',head,.002);
 for(const sign of [-1,1]){cylinder(.011,.005,[sign*.049,-.085,-.039],'frame',head,'Y');cylinder(.005,.006,[sign*.049,-.089,-.039],'metal',head,'Y');cylinder(.021,.008,[sign*.087,0,-.014],'metal',head,'X')}
 box([.003,.09,.002],[0,0,.067],'frame',head,.0005);
 limb(bodies['left-upper'],[0,0,0],[-.045,-.035,-.16],.035);motor([0,0,0],.043,bodies['left-upper']);limb(bodies['left-fore'],[0,0,0],[.02,-.11,-.04],.030);motor([0,0,0],.032,bodies['left-fore']);box([.056,.048,.047],[.02,-.13,-.04],'frame',bodies['left-fore'],.006);
 motor([0,0,0],.043,bodies['right-yaw']);limb(bodies['right-upper'],[0,0,0],[0,-.22,0],.029);limb(bodies['right-fore'],[0,0,0],[0,-.20,0],.024);motor([0,0,0],.033,bodies['right-fore']);
 // Exact simulated sphere is the active contact pad; fingers are passive visual details.
 ball(.018,[0,0,0],'rubber',bodies.hand);box([.048,.035,.031],[0,.028,0],'frame',bodies.hand,.006);for(const sign of [-1,1]){box([.008,.032,.011],[sign*.023,.016,.009],'metal',bodies.hand,.002);box([.009,.013,.012],[sign*.023,-.002,.005],'shell',bodies.hand,.002)}
 box([.18,.13,.063],[0,.36,.418],'frame');
 for(const side of ['left','right']){const g=bodies[`${side}-leg`];bar([0,0,-.12],[0,0,.18],.022,'frame',g);box([.071,.073,.116],[0,0,.11],'shell',g,.010);motor([0,0,.025],.030,g);box([.063,.071,.092],[0,-.009,-.052],'shell',g,.009);for(const z of [-.025,-.077])cylinder(.004,.004,[0,-.046,z],'metal',g,'Y');const foot=bodies[`${side}-foot`];box([.11,.17,.02],[0,0,-.025],'rubber',foot,.008);box([.106,.16,.046],[0,0,.006],'shell',foot,.012);box([.085,.05,.007],[0,-.05,.032],'metal',foot,.003)}
 cylinder(.025,.024,[0,0,0],'puck',bodies.puck);const stamp=text('✳',[0,0,.0125],.034,bodies.puck,'#fff0d4',.025);stamp.rotation.set(0,0,0);
 const ring=mesh(new THREE.TorusGeometry(.028,.0025,12,64),'light');
 // Human-size desk objects establish scale around the miniature experiment.
 box([1.35,.88,.035],[0,.08,-.020],'wood',scene,.012);
 for(let i=0;i<20;i++)box([1.35,.0004,.0002],[0,-.32+i*.04,-.0022],'orange',scene,.0001).material=new THREE.MeshStandardMaterial({color:'#8c7354',roughness:1,transparent:true,opacity:.15});
 const laptop=new THREE.Group();laptop.position.set(-.24,.22,.009);laptop.rotation.z=-.1;scene.add(laptop);box([.30,.20,.012],[0,0,0],'metal',laptop,.006);box([.082,.045,.001],[0,-.056,.007],'frame',laptop,.003);
 const keys=new THREE.InstancedMesh(new RoundedBoxGeometry(.018,.016,.002,1,.001),mat.frame,48);const dummy=new THREE.Object3D();for(let i=0;i<48;i++){dummy.position.set(-.122+(i%12)*.022,.008+Math.floor(i/12)*.023,.008);dummy.updateMatrix();keys.setMatrixAt(i,dummy.matrix)}laptop.add(keys);
 box([.30,.010,.195],[0,.096,.101],'frame',laptop,.005);box([.277,.001,.171],[0,.090,.104],'screen',laptop,.001);text('MOCHI / POLICY LAB',[0,.088,.153],.225,laptop,'#c2dbbf',.022);text('OBSERVE  /  TEST  /  REMEMBER',[0,.088,.128],.22,laptop,'#8fac99',.010);
 for(let i=0;i<13;i++)box([.006,.001,.016+i*.004],[-.107+i*.018,.088,.065+i*.002],'light',laptop,.001);
 const mug=new THREE.Group();mug.position.set(.21,.16,0);scene.add(mug);cylinder(.037,.09,[0,0,.045],'shell',mug);const rimMesh=mesh(new THREE.TorusGeometry(.0345,.003,12,48),'shell',mug,[0,0,.092]);cylinder(.032,.001,[0,0,.089],'visor',mug);const handle=mesh(new THREE.TorusGeometry(.021,.0045,12,32),'shell',mug,[.046,0,.052]);handle.rotation.x=Math.PI/2;text('HUMAN FUEL',[0,-.0375,.047],.059,mug,'#465448',.010);
 bar([-.30,-.10,.0035],[-.125,-.09,.0035],.0035,'orange',scene);box([.16,.10,.001],[.21,-.14,0],'paper',scene,.001);const note=text('DO NOT TOUCH THE COFFEE',[.21,-.14,.001],.145,scene,'#6a715b',.010);note.rotation.set(0,0,.12);
 const trailGeometry=new THREE.BufferGeometry();const trail=new THREE.Line(trailGeometry,new THREE.LineBasicMaterial({color:'#9b6948',transparent:true,opacity:.6}));rig.add(trail);
 let data,trajectory,focusAmount=0;const qa=new THREE.Quaternion(),qb=new THREE.Quaternion(),pa=new THREE.Vector3(),pb=new THREE.Vector3();let lastTime=0;
 function setData(value){data=value;trajectory=value.trajectory;ring.position.set(value.scenario.target[0],value.scenario.target[1],.463);const pi=trajectory.body_names.indexOf('puck');trailGeometry.setFromPoints(trajectory.frames.map(f=>new THREE.Vector3(f.positions[pi][0],f.positions[pi][1],f.positions[pi][2]+.013)));trail.material.color.set(value.success?'#638653':'#b07550')}
 function frame(t,cinema=0,focus=0){lastTime=t;if(!trajectory)return;const samples=trajectory.frames;const x=Math.min(t*25,samples.length-1);const n=Math.floor(x),f=samples[n],next=samples[Math.min(n+1,samples.length-1)],blend=x-n;trajectory.body_names.forEach((name,i)=>{const o=bodies[name];if(!o)return;pa.fromArray(f.positions[i]);pb.fromArray(next.positions[i]);o.position.lerpVectors(pa,pb,blend);let q=f.quaternions[i],r=next.quaternions[i];qa.set(q[1],q[2],q[3],q[0]);qb.set(r[1],r[2],r[3],r[0]);o.quaternion.slerpQuaternions(qa,qb,blend)});trailGeometry.setDrawRange(0,n+1);
  focusAmount+=(focus-focusAmount)*.06;if(!touched){const az=.52+Math.sin(cinema*.065)*.10;pa.set(Math.sin(az)*.46,-Math.cos(az)*.46,.27+Math.sin(cinema*.035)*.012);pb.set(.11,-.19,.185);camera.position.lerpVectors(pa,pb,focusAmount);pa.set(0,.045,.104);pb.set(0,.010,.111);controls.target.lerpVectors(pa,pb,focusAmount)}controls.update();renderer.render(scene,camera);
 }
 const resize=()=>{const rect=element.getBoundingClientRect();if(!rect.width||!rect.height)return;camera.aspect=rect.width/rect.height;camera.updateProjectionMatrix();renderer.setSize(rect.width,rect.height,false);frame(lastTime)};new ResizeObserver(resize).observe(element);resize();
 return {setData,frame,resize};
}
