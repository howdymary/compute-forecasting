import * as THREE from 'three';

// Native-metre task geometry matches mochi.desk.tasks. Decorative markings do
// not actuate objects. Their transforms are supplied by recorded MuJoCo poses.
export function createTaskObjects({scene,mesh,box,cyl,bar,text,materials}){
 const brass=new THREE.MeshStandardMaterial({color:'#a38c58',metalness:.78,roughness:.34});
 const laptop=new THREE.Group();laptop.position.set(-.12,-.024,.007);scene.add(laptop);
 box([.29,.195,.014],[0,0,0],'metal',laptop,.003);box([.075,.042,.0007],[0,-.053,.0075],'frame',laptop,.002);
 for(let i=0;i<48;i++)box([.017,.015,.0018],[-.119+(i%12)*.0215,.006+Math.floor(i/12)*.022,.0078],'frame',laptop,.001);
 const screen=new THREE.Group();screen.position.set(-.12,.070,.014);screen.rotation.x=Math.PI/9;scene.add(screen);
 box([.29,.007,.175],[0,0,.0925],'frame',screen,.002);box([.270,.0008,.150],[0,-.00395,.094],'visor',screen,.0004);
 text('MOCHI / CONTROL STUDIO',[0,-.0045,.149],.232,screen,'#b9c9ae',.011);text('DESK TASKS  /  01 + 02',[0,-.0045,.129],.205,screen,'#78977e',.008);
 for(let i=0;i<12;i++)box([.008,.0005,.009+(i%6)*.003],[-.105+i*.019,-.0046,.055+(i%6)*.0015],'led',screen,.0003);
 const ghost=new THREE.Group();scene.add(ghost);const corners=[[-.265,.070,.019],[.025,.070,.019],[.025,.070,.194],[-.265,.070,.194],[-.265,.070,.019]];
 let ghostGeo=new THREE.BufferGeometry().setFromPoints(corners.map(p=>new THREE.Vector3(...p)));let goal=new THREE.Line(ghostGeo,new THREE.LineDashedMaterial({color:'#6e8b58',transparent:true,opacity:.65,dashSize:.006,gapSize:.004}));goal.computeLineDistances();ghost.add(goal);
 text('90° TARGET',[.027,.067,.204],.048,ghost,'#4f714b',.005);
 // Original stylized cartography. No external raster assets or textures.
 let map=document.createElement('canvas');map.width=1536;map.height=768;let c=map.getContext('2d');c.fillStyle='#7a9690';c.fillRect(0,0,map.width,map.height);
 const continents=[
 [[-168,68],[-142,72],[-124,61],[-111,60],[-97,72],[-65,58],[-55,48],[-70,43],[-80,26],[-95,18],[-103,23],[-118,31],[-128,49],[-150,58]],
 [[-82,12],[-66,10],[-50,1],[-36,-8],[-47,-24],[-58,-36],[-70,-54],[-76,-43],[-73,-19]],
 [[-55,82],[-26,80],[-20,66],[-43,59],[-60,68]],
 [[-12,36],[-7,54],[9,59],[27,71],[47,69],[61,58],[88,73],[116,69],[147,61],[177,56],[165,45],[142,35],[128,22],[113,8],[100,4],[91,23],[79,6],[69,24],[49,30],[37,41],[28,38],[20,46],[6,43]],
 [[-17,35],[6,37],[26,30],[33,15],[43,12],[50,-13],[35,-33],[18,-35],[10,-19],[-2,1],[-15,13]],
 [[113,-22],[128,-12],[142,-12],[153,-28],[145,-39],[127,-36],[115,-32]],
 [[130,32],[143,44],[145,38],[139,32]],[[47,-13],[50,-16],[46,-26],[43,-20]],[[166,-35],[178,-39],[171,-47],[165,-44]]
 ];
 const xy=([lon,lat])=>[(lon+180)/360*map.width,(90-lat)/180*map.height];
 for(const poly of continents){c.beginPath();poly.forEach((p,i)=>{const[x,y]=xy(p);i?c.lineTo(x,y):c.moveTo(x,y)});c.closePath();c.fillStyle='#c6c9a9';c.fill();c.strokeStyle='#a9b694';c.lineWidth=2;c.stroke()}
 c.strokeStyle='#e0e4cc66';c.lineWidth=1;for(let lon=-180;lon<=180;lon+=30){const[x]=xy([lon,0]);c.beginPath();c.moveTo(x,0);c.lineTo(x,map.height);c.stroke()}for(let lat=-60;lat<=60;lat+=30){const[,y]=xy([0,lat]);c.beginPath();c.moveTo(0,y);c.lineTo(map.width,y);c.stroke()}
 let texture=new THREE.CanvasTexture(map);texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=4;
 const globe=new THREE.Group();globe.position.set(.20,.040,.123);scene.add(globe);mesh(new THREE.SphereGeometry(.058,64,40).rotateX(Math.PI/2),new THREE.MeshStandardMaterial({map:texture,roughness:.6,metalness:.08}),globe);
 const marker=mesh(new THREE.CircleGeometry(.0037,32),new THREE.MeshBasicMaterial({color:'#c77850',side:THREE.DoubleSide}),globe,[0,-.0583,0]);marker.rotation.x=Math.PI/2;
 const halo=mesh(new THREE.RingGeometry(.0042,.0048,32),new THREE.MeshBasicMaterial({color:'#f2e8cb',side:THREE.DoubleSide}),globe,[0,-.0584,0]);halo.rotation.x=Math.PI/2;
 let base=new THREE.Group();base.position.set(.20,.040,0);scene.add(base);cyl(.039,.012,[0,0,.006],'frame',base);cyl(.035,.0018,[0,0,.0128],brass,base);cyl(.004,.052,[0,0,.038],brass,base);
 let meridian=[];for(let i=0;i<=60;i++){let a=i/60*Math.PI;meridian.push(new THREE.Vector3(0,.064*Math.sin(a),.123+.064*Math.cos(a)))}let curve=new THREE.CatmullRomCurve3(meridian);mesh(new THREE.TubeGeometry(curve,60,.0015,8,false),brass,base);cyl(.003,.010,[0,0,.185],brass,base);cyl(.003,.012,[0,0,.062],brass,base);
 const pointer=new THREE.Group();base.add(pointer);bar([0,-.078,.012],[0,-.078,.123],.0016,brass,pointer);let arrow=mesh(new THREE.ConeGeometry(.0038,.012,16),brass,pointer,[0,-.071,.123]);arrow.rotation.x=0; // Cone's +Y tip points toward the globe.
 text('ALIGN',[0,-.087,.014],.027,base,'#667052',.004,true);
 return{bindings:{'laptop-screen':screen,globe},setTask(task){ghost.visible=task==='laptop';pointer.visible=task==='globe'}};
}
