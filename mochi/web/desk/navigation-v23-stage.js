import {createCurriculumStage} from './navigation-v23-renderer.js';
import * as THREE from 'three';

export function createNavigationStage(element, episode, row) {
 const stage=createCurriculumStage(element,{scene:row.layout.scene,fullBody:true,cameraOffset:[.32,-.46,.29]});
 const annotations=new THREE.Group();stage.scene.add(annotations);
 const plan=row.plans[row.action], radius=row.envelope.planning_radius_m;
 const material=color=>new THREE.LineBasicMaterial({color,transparent:true,opacity:.82,depthTest:true});
 const line=(points,color)=>{const o=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(p[0],p[1],.002))),material(color));o.renderOrder=7;annotations.add(o);return o};
 for(const o of row.obstacles){const a=o.minimum,b=o.maximum;line([[a[0],a[1]],[b[0],a[1]],[b[0],b[1]],[a[0],b[1]],[a[0],a[1]]],'#8b927b').material.opacity=.22}
 if(plan.feasible){
  line(plan.points,'#245f65');
  for(const p of plan.points.slice(1,-1))line(Array.from({length:65},(_,i)=>[p[0]+radius*Math.cos(i*Math.PI/32),p[1]+radius*Math.sin(i*Math.PI/32)]),'#9e8954');
 }
 const goal=row.layout.goal;
 line(Array.from({length:65},(_,i)=>[goal[0]+.012*Math.cos(i*Math.PI/32),goal[1]+.012*Math.sin(i*Math.PI/32)]),'#3e7a50');
 annotations.add(new THREE.ArrowHelper(new THREE.Vector3(Math.cos(goal[2]),Math.sin(goal[2]),0),new THREE.Vector3(goal[0],goal[1],.004),.045,'#3e7a50',.011,.006));
 const pelvis=episode.trajectory.body_names.indexOf('pelvis');
 const index=pelvis<0?1:pelvis, frames=episode.trajectory.frames;
 const executed=line(frames.map(f=>f.positions[index]),'#b46843');
 const ready=stage.ready.then(()=>{stage.setEpisode(episode);stage.showFootfalls(true);stage.frame(0)});
 return {...stage,ready,frame(time){const f=stage.frame(time);let count=0;while(count<frames.length&&frames[count].t<=time)count++;executed.geometry.setDrawRange(0,count);return f},overlays(visible){annotations.visible=visible;stage.showFootfalls(visible)},dispose(){for(const o of annotations.children){o.geometry?.dispose();o.material?.dispose()}stage.dispose();stage.renderer.forceContextLoss();element.replaceChildren()}};
}
