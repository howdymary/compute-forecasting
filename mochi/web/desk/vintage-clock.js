import * as THREE from 'three';

// Cosmetic shell only. The cap remains bound to MuJoCo's alarm-button body.
// The case collider, button envelope, stroke and contact location are unchanged.
export function vintageClock({clock,cap,mesh,box,ball,cyl,bar}) {
 const enamel=new THREE.MeshPhysicalMaterial({color:'#586b62',metalness:.3,roughness:.26,clearcoat:.72,clearcoatRoughness:.2});
 const brass=new THREE.MeshStandardMaterial({color:'#b6a079',metalness:.86,roughness:.28});
 const dark=new THREE.MeshStandardMaterial({color:'#333936',metalness:.65,roughness:.36});
 const rubber=new THREE.MeshStandardMaterial({color:'#252928',roughness:.84});
 const lacquer=new THREE.MeshStandardMaterial({color:'#9b4c37',metalness:.3,roughness:.35});
 cyl(.037,.041,[0,0,0],enamel,clock,'y');
 const ring=(radius,tube,pos,mat)=>{const o=mesh(new THREE.TorusGeometry(radius,tube,12,80),mat,clock,pos);o.rotation.x=Math.PI/2;return o};
 ring(.0353,.0018,[0,-.022,0],brass);ring(.0326,.0006,[0,-.0242,0],dark);
 const face=document.createElement('canvas');face.width=face.height=1024;const c=face.getContext('2d');c.fillStyle='#ece5d5';c.fillRect(0,0,1024,1024);
 let seed=731;for(let i=0;i<7000;i++){seed=(seed*1664525+1013904223)>>>0;const x=seed%1024;seed=(seed*1664525+1013904223)>>>0;const y=seed%1024;c.fillStyle='rgba(98,79,48,.035)';c.fillRect(x,y,2,2)}
 c.translate(512,512);c.strokeStyle='#454a43';for(let i=0;i<60;i++){const a=i*Math.PI/30,r=i%5?448:425;c.lineWidth=i%5?3:7;c.beginPath();c.moveTo(Math.sin(a)*r,-Math.cos(a)*r);c.lineTo(Math.sin(a)*466,-Math.cos(a)*466);c.stroke()}
 c.fillStyle='#303b35';c.font='500 119px Georgia, serif';c.textAlign='center';c.textBaseline='middle';for(let i=1;i<=12;i++){const a=i*Math.PI/6;c.fillText(String(i),Math.sin(a)*340,-Math.cos(a)*340+4)}
 c.font='29px Georgia, serif';c.fillStyle='#6c7064';c.fillText('M O C H I',0,155);c.font='22px Georgia, serif';c.fillText('MECHANICAL ALARM',0,201);
 const texture=new THREE.CanvasTexture(face);texture.colorSpace=THREE.SRGBColorSpace;
 const dial=mesh(new THREE.CircleGeometry(.0324,80),new THREE.MeshStandardMaterial({map:texture,roughness:.75}),clock,[0,-.0243,0]);dial.rotation.x=Math.PI/2;
 bar([0,-.0254,0],[-.010,-.0254,-.0173],.0013,dark,clock);bar([0,-.0262,0],[0,-.0262,.025],.00085,dark,clock);bar([-.004,-.027, .002],[.021,-.027,-.012],.00028,lacquer,clock);cyl(.0025,.0015,[0,-.0274,0],brass,clock,'y');
 // Rear-set bells leave the original front-right snooze cap unobstructed.
 for(const x of[-.024,.024]){
  bar([x*.65,.013,.028],[x,.018,.052],.0016,brass,clock);
  const bell=ball(.014,[x,.018,.055],brass,clock);bell.scale.z=.62;
  cyl(.0145,.0017,[x,.018,.050],brass,clock);
  ball(.0022,[x,.018,.064],dark,clock);
  bar([x*.85,0,-.027],[x*1.2,-.002,-.055],.0022,brass,clock);box([.014,.012,.0035],[x*1.2,-.002,-.057],rubber,clock,.0014);
 }
 bar([0,.017,.033],[0,.017,.061],.0014,dark,clock);bar([-.006,.017,.061],[.006,.017,.061],.002,dark,clock);
 cyl(.006,.007,[0,.026,-.005],brass,clock,'y');cyl(.0027,.009,[-.016,.026,-.016],dark,clock,'y');
 // The elevated plunger housing meets the exact recorded cap, not a new target.
 box([.026,.019,.016],[.025,-.010,.054],enamel,clock,.003);box([.025,.018,.004],[0,0,0],brass,cap,.0015);box([.015,.008,.0003],[0,0,.0021],lacquer,cap,.001);
 const indicator=new THREE.MeshStandardMaterial({color:'#a45439',emissive:'#a45439',emissiveIntensity:.2});ball(.0012,[.016,-.025,-.020],indicator,clock);return indicator;
}
