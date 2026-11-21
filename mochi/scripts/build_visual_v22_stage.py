"""Create additive rendering modules, leaving the reference renderer intact."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web/desk'

stage = (WEB / 'smooth-stage.js').read_text()
stage = stage.replace("import {loadG1} from './g1-stage.js';", "import {loadG1} from './g1-v22-stage.js';")
stage = stage.replace("import {photographicRenderer} from './realism.js';", "import {photographicRenderer} from './realism-v22.js';")
stage = stage.replace("wood:new THREE.MeshStandardMaterial({color:'#b29b72',roughness:.8})", "wood:new THREE.MeshPhysicalMaterial({color:'#b29b72',roughness:.72,clearcoat:.16,clearcoatRoughness:.5})")
stage = stage.replace("g.position.set(...pos);scene.add(g);bindings[name]=g", "g.name=name;g.position.set(...pos);scene.add(g);bindings[name]=g")
stage = stage.replace("const walnut=new THREE.MeshStandardMaterial({color:'#68523c',roughness:.65});", "const walnut=new THREE.MeshStandardMaterial({color:'#8e7051',roughness:.72});materials.walnut=walnut;")
stage = stage.replace("text('FIELD NOTES'", "text('NOTES'")
stage = stage.replace("position.copy(target).add(inspection==='feet'?new THREE.Vector3(.10,-.27,.055):new THREE.Vector3(0,-.52,.035))", "position.copy(target).add(inspection==='feet'?new THREE.Vector3(.10,-.27,.055):new THREE.Vector3(0,-.52,.035));if(inspection==='hands'){target.set(pelvis[0],pelvis[1],pelvis[2]+.065);position.copy(target).add(new THREE.Vector3(.10,-.28,.11))}")
stage = stage.replace("display.rotation.x=Math.PI/2;", """display.rotation.x=Math.PI/2;
 const desktop=document.createElement('canvas');desktop.width=1200;desktop.height=700;const dc=desktop.getContext('2d');dc.fillStyle='#111c27';dc.fillRect(0,0,1200,700);dc.fillStyle='#263440';dc.fillRect(0,0,1200,48);for(const [i,color]of ['#c76960','#c5a761','#6b9d87'].entries()){dc.fillStyle=color;dc.beginPath();dc.arc(26+i*24,24,6,0,Math.PI*2);dc.fill()}dc.fillStyle='#b5c8cd';dc.font='18px monospace';dc.fillText('workspace / motion.py',130,31);dc.fillStyle='#172430';dc.fillRect(0,48,200,652);dc.font='17px monospace';for(const [i,line]of ['MOCHI','  scene.xml','  motion.py','  controls.py','  results/'].entries()){dc.fillStyle=i===2?'#c5cfc0':'#728a94';dc.fillText(line,18,90+i*35)}dc.font='20px monospace';const lines=['import mujoco','import numpy as np','','def step(model, state, target):','    error = target - state.joints','    command = controller(error)','    state.apply(command)','    mujoco.mj_step(model, state)','','# Record movement and contact.','trajectory.capture(state)'];for(const [i,line]of lines.entries()){dc.fillStyle='#526875';dc.fillText(String(i+1).padStart(2,' '),222,105+i*39);dc.fillStyle=line.startsWith('#')?'#6f9693':line.startsWith('import')||line.startsWith('def')?'#a8b98c':'#a7bfcb';dc.fillText(line,280,105+i*39)}const desktopMap=new THREE.CanvasTexture(desktop);desktopMap.colorSpace=THREE.SRGBColorSpace;screenMat.map=desktopMap;screenMat.emissiveMap=desktopMap;screenMat.color.set('#ffffff');screenMat.emissive.set('#ffffff');screenMat.emissiveIntensity=.12;screenMat.roughness=.32;screenMat.needsUpdate=true;
""")
stage = stage.replace("return{ready,frame,", "return{scene,camera,renderer,bindings,ready,frame,")
(WEB / 'visual-v22-stage.js').write_text(stage)

renderer = (WEB / 'realism.js').read_text()
renderer = renderer.replace("import {OutputPass}", "import {SMAAPass} from 'three/addons/postprocessing/SMAAPass.js';\nimport {OutputPass}")
renderer = renderer.replace("renderer.toneMappingExposure=.95", "renderer.toneMappingExposure=1.02")
renderer = renderer.replace("lights[0].intensity=3.0", "lights[0].intensity=3.2")
renderer = renderer.replace("lights[0].shadow.normalBias=.00012", "lights[0].shadow.normalBias=.000055")
renderer = renderer.replace("lights[1].intensity=.30", "lights[1].intensity=.62")
renderer = renderer.replace("o.intensity=.24", "o.intensity=.30")
renderer = renderer.replace("ao.kernelRadius=.0065", "ao.kernelRadius=.0045")
renderer = renderer.replace("composer.addPass(ao);composer.addPass(new OutputPass())", "composer.addPass(ao);composer.addPass(new SMAAPass(1,1));composer.addPass(new OutputPass())")
renderer = renderer.replace("scene.environmentIntensity=.90", "scene.environmentIntensity=.80")
renderer = renderer.replace("scene.backgroundBlurriness=.5;scene.backgroundIntensity=.32", "scene.backgroundBlurriness=.35;scene.backgroundIntensity=.43")
renderer = renderer.replace("diffuseColor.rgb, 0.48)", "diffuseColor.rgb, 0.76)")
renderer = renderer.replace("materials.wood.roughness=.90;materials.wood.needsUpdate=true", "materials.wood.roughness=.76;materials.wood.needsUpdate=true;if(materials.walnut){materials.walnut.map=color;materials.walnut.normalMap=normal;materials.walnut.normalScale=new THREE.Vector2(.025,.025);materials.walnut.roughnessMap=rough;materials.walnut.needsUpdate=true}")
(WEB / 'realism-v22.js').write_text(renderer)

loader = (WEB / 'g1-stage.js').read_text()
loader = loader.replace("import {GLTFLoader}", "import {MeshoptDecoder} from './assets/visual-motion-v22/meshopt_decoder.mjs';\nimport {GLTFLoader}")
loader = loader.replace("new GLTFLoader().loadAsync('assets/g1-mini.glb?v=g1-v4')", "new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync('assets/visual-motion-v22/g1-studio.glb')")
(WEB / 'g1-v22-stage.js').write_text(loader)
tools = ROOT / '.cache/visual-motion-v22/asset-tools/node_modules/meshoptimizer'
for source, target in [('meshopt_decoder.mjs', 'meshopt_decoder.mjs'), ('LICENSE.md', 'MESHOPTIMIZER-LICENSE.md')]:
    shutil.copy2(tools / source, WEB / 'assets/visual-motion-v22' / target)
print('Built isolated V22 stage, renderer and decoder')
