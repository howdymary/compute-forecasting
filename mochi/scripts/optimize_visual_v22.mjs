import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import crypto from 'node:crypto';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(root,'.cache/visual-motion-v22/asset-tools/package.json'));
const {NodeIO}=await import(require.resolve('@gltf-transform/core'));
const {ALL_EXTENSIONS}=await import(require.resolve('@gltf-transform/extensions'));
const {meshopt,weld,getBounds}=await import(require.resolve('@gltf-transform/functions'));
const {MeshoptEncoder,MeshoptDecoder}=await import(require.resolve('meshoptimizer'));
await Promise.all([MeshoptEncoder.ready,MeshoptDecoder.ready]);
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.encoder':MeshoptEncoder,'meshopt.decoder':MeshoptDecoder});
const source=path.join(root,'web/desk/assets/g1-mini.glb');
const input=path.join(root,'artifacts/visual-motion-v22/g1-studio-unpacked.glb');
const output=path.join(root,'web/desk/assets/visual-motion-v22/g1-studio.glb');
const original=await io.read(source),doc=await io.read(input);
function bodies(document){return Object.fromEntries(document.getRoot().listNodes().filter(n=>n.getExtras().mujoco_body).map(n=>[n.getExtras().mujoco_body,{matrix:n.getWorldMatrix(),bounds:getBounds(n)}]));}
const before=bodies(original),authored=bodies(doc);
assert.deepEqual(Object.keys(before).sort(),Object.keys(authored).sort());
await doc.transform(weld({tolerance:0}),meshopt({encoder:MeshoptEncoder,level:'high',quantizePosition:16,quantizeNormal:12,quantizeTexcoord:14,cleanup:false}));
await io.write(output,doc);
const decoded=await io.read(output),after=bodies(decoded);let maxMatrixError=0,maxBoundsError=0;
assert.deepEqual(Object.keys(before).sort(),Object.keys(after).sort());
for(const [name,b]of Object.entries(before)){
 const a=after[name];
 maxMatrixError=Math.max(maxMatrixError,...b.matrix.map((v,i)=>Math.abs(v-a.matrix[i])));
 for(const key of ['min','max'])for(let i=0;i<3;i++)maxBoundsError=Math.max(maxBoundsError,Math.abs(b.bounds[key][i]-a.bounds[key][i]));
}
assert(maxMatrixError<1e-6,{maxMatrixError});assert(maxBoundsError<.00002,{maxBoundsError});
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const receipt={source_bytes:fs.statSync(source).size,authored_bytes:fs.statSync(input).size,optimized_bytes:fs.statSync(output).size,
 source_sha256:hash(source),authored_sha256:hash(input),optimized_sha256:hash(output),
 preserved_body_bindings:Object.keys(after).length,max_body_matrix_error:maxMatrixError,max_world_bounds_error_m:maxBoundsError,
 node_count:decoded.getRoot().listNodes().length,mesh_count:decoded.getRoot().listMeshes().length,
 versions:{gltf_transform:'4.5.1',meshoptimizer:'1.3.0'},
 scope:'Visual materials, UVs and mesh compression. No geometry simplification, physical model or trajectory change.'};
fs.mkdirSync(path.join(root,'evidence/visual-motion-v22'),{recursive:true});
fs.writeFileSync(path.join(root,'evidence/visual-motion-v22/asset-audit.json'),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt));
