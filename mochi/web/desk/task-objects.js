import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

// Contact envelopes remain the native-metre MuJoCo screen box and sphere.
// Sand3D meshes supply the fitted visual shells, never object actuation.
export function createTaskObjects({scene,mesh,box,cyl,bar,text,materials}){
 const loader=new GLTFLoader(),pending=[];
 function asset(file,parent){pending.push(loader.loadAsync('assets/'+file).then(({scene:model})=>{const axes=new THREE.Group();axes.rotation.x=Math.PI/2;axes.add(model);parent.add(axes);model.traverse(o=>{if(o.isMesh){o.castShadow=o.receiveShadow=true;for(const m of Array.isArray(o.material)?o.material:[o.material]){m.envMapIntensity=.85;m.needsUpdate=true}}})}));}
 const brass=new THREE.MeshStandardMaterial({color:'#a38c58',metalness:.86,roughness:.3});
 const laptop=new THREE.Group();laptop.position.set(-.12,-.024,.007);scene.add(laptop);asset('sand-laptop-base.glb',laptop);
 const keyMaterial=new THREE.MeshStandardMaterial({color:'#20252a',roughness:.55,metalness:.12});
 const rows=['1234567890-=','QWERTYUIOP[]','ASDFGHJKL;\'↵','ZXCVBNM,./↑⌫'];
 for(let row=0;row<4;row++)for(let col=0;col<12;col++){
  const x=-.119+col*.0215,y=.053-row*.022;box([.0177,.016,.0017],[x,y,.0079],keyMaterial,laptop,.0008);
  text(rows[row][col],[x,y,.0089],.005,laptop,'#aeb7b7',.0047,true);
 }
 box([.090,.011,.0014],[0,-.041,.0078],keyMaterial,laptop,.0008);
 const screen=new THREE.Group();screen.position.set(-.12,.070,.014);screen.rotation.x=Math.PI/9;scene.add(screen);asset('sand-laptop-lid.glb',screen);
 const displayMaterial=new THREE.MeshPhysicalMaterial({roughness:.27,metalness:0,clearcoat:.6,emissive:'#ffffff',emissiveIntensity:.17});
 pending.push(new THREE.TextureLoader().loadAsync('assets/laptop-display.png?v=free-base-v5').then(t=>{t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=8;displayMaterial.map=t;displayMaterial.emissiveMap=t;displayMaterial.needsUpdate=true}));
 const display=mesh(new THREE.PlaneGeometry(.265,.149),displayMaterial,screen,[0,-.0037,.094]);display.rotation.x=Math.PI/2;
 const ghost=new THREE.Group();scene.add(ghost);const corners=[[-.265,.070,.019],[.025,.070,.019],[.025,.070,.194],[-.265,.070,.194],[-.265,.070,.019]];
 let ghostGeo=new THREE.BufferGeometry().setFromPoints(corners.map(p=>new THREE.Vector3(...p)));let goal=new THREE.Line(ghostGeo,new THREE.LineDashedMaterial({color:'#6e8b58',transparent:true,opacity:.55,dashSize:.006,gapSize:.004}));goal.computeLineDistances();ghost.add(goal);text('90° TARGET',[.027,.067,.204],.048,ghost,'#4f714b',.005);
 const globe=new THREE.Group();globe.position.set(.20,.040,.123);scene.add(globe);asset('sand-earth.glb',globe);
 const marker=mesh(new THREE.CircleGeometry(.0037,32),new THREE.MeshStandardMaterial({color:'#bd623e',roughness:.7,side:THREE.DoubleSide}),globe,[0,-.0583,0]);marker.rotation.x=Math.PI/2;
 const halo=mesh(new THREE.RingGeometry(.0042,.0048,32),new THREE.MeshStandardMaterial({color:'#f2e8cb',roughness:.7,side:THREE.DoubleSide}),globe,[0,-.0584,0]);halo.rotation.x=Math.PI/2;
 let base=new THREE.Group();base.position.set(.20,.040,0);scene.add(base);asset('sand-globe-base.glb',base);
 let meridian=[];for(let i=0;i<=60;i++){let a=i/60*Math.PI;meridian.push(new THREE.Vector3(0,.064*Math.sin(a),.123+.064*Math.cos(a)))}let curve=new THREE.CatmullRomCurve3(meridian);mesh(new THREE.TubeGeometry(curve,60,.0015,8,false),brass,base);cyl(.003,.010,[0,0,.185],brass,base);cyl(.003,.012,[0,0,.062],brass,base);
 const pointer=new THREE.Group();base.add(pointer);bar([0,-.078,.012],[0,-.078,.123],.0016,brass,pointer);mesh(new THREE.ConeGeometry(.0038,.012,16),brass,pointer,[0,-.071,.123]);text('ALIGN',[0,-.087,.014],.027,base,'#667052',.004,true);
 const lamp=new THREE.Group();lamp.position.set(-.37,.25,0);lamp.rotation.z=.45;scene.add(lamp);asset('sand-desk-lamp.glb',lamp);
 return{ready:Promise.all(pending),bindings:{'laptop-screen':screen,globe},setTask(task){ghost.visible=task==='laptop';pointer.visible=task==='globe'}};
}
