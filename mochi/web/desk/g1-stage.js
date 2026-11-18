import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

// GLB uses glTF's Y-up convention. Each animated body gets a native Z-up
// wrapper so the recorded MuJoCo body transform can be used without retargeting.
export async function loadG1(scene){
 const file=await new GLTFLoader().loadAsync('assets/g1-mini.glb?v=g1-v4'),bindings={};
 for(const body of [...file.scene.children]){
  const name=body.userData.mujoco_body||body.name,wrapper=new THREE.Group();wrapper.name='physics:'+name;scene.add(wrapper);wrapper.add(body);body.rotation.set(Math.PI/2,0,0);bindings[name]=wrapper;
 }
 // A visible stand indicates the experiment's fixed-pelvis constraint.
 const stand=bindings.pelvis,steel=new THREE.MeshStandardMaterial({color:'#222a2c',metalness:.7,roughness:.4});
 const column=new THREE.Mesh(new THREE.CylinderGeometry(.0018,.0018,.130,20),steel);column.rotation.x=Math.PI/2;column.position.set(-.027,0,-.065);stand.add(column);
 const clamp=new THREE.Mesh(new THREE.CylinderGeometry(.0018,.0018,.027,20),steel);clamp.rotation.z=Math.PI/2;clamp.position.set(-.0135,0,0);stand.add(clamp);
 for(const object of Object.values(bindings))object.traverse(child=>{if(child.isMesh){child.castShadow=child.receiveShadow=true;if(child.material){child.material.envMapIntensity=1.0;child.material.needsUpdate=true}}});
 return bindings;
}
