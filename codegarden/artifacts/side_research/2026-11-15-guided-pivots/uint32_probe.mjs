import {createHash} from "node:crypto";
const seedURL="https://raw.githubusercontent.com/howdymary/compute-forecasting/635d085cc08145c55fad58821678e86d02c3fe93/codegarden/artifacts/best_code.txt";
const seedText=await(await fetch(seedURL)).text();
const sha=s=>createHash("sha256").update(s).digest("hex");
if(sha(seedText)!=="417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa")throw Error("seed hash");
const base=seedText.trim().split("\n").map(s=>parseInt(s,2));
const definitions=[{"pivot_id":0,"method":"closure_guided","forced":"0001110000101111","forced_blockers":4,"removed_indices":[2,3,4,6,7,16,18,21,29,31,36,39,46,52,53,55,63,67,73,74,78,110,112,114,117,119,120,129,130,152,161,162],"pool_size":662,"pool_sha256":"4fa2dca9e717cfe3c92ce1bc4eb06a767cb1df13ff42b96236e343c2416988da","required_repair":32,"status":"TIMEOUT","nodes":6241,"search_seconds":0.250699},{"pivot_id":1,"method":"closure_guided","forced":"1110000100100001","forced_blockers":3,"removed_indices":[56,57,94,95,98,102,113,133,136,137,144,149,156,177,178,183,185,187,188,192,193,196,197,200,205,209,211,213,214,216,219,220],"pool_size":779,"pool_sha256":"7773735df4bb2ebca676aa7ccab76540077d21a08c2e35928fbb82b14859712a","required_repair":32,"status":"TIMEOUT","nodes":7201,"search_seconds":0.25015}];
function solveGraph(adj,target,seconds){
 const n=adj.length,blocks=Math.ceil(n/32), all=new Uint32Array(blocks).fill(0xffffffff);
 if(n%32)all[blocks-1]=(2**(n%32)-1)>>>0;
 let nodes=0,rootBound=null,found=null;const stack=[],start=performance.now(),deadline=start+1000*seconds;
 function colors(P){
  const rem=P.slice(),order=[],bounds=[];let color=0;
  while(true){
   let any=false;for(let k=0;k<blocks;k++)if(rem[k]){any=true;break;}if(!any)break;
   color++;const Q=rem.slice();
   while(true){
    let k=0;while(k<blocks&&!Q[k])k++;if(k===blocks)break;
    const off=31-Math.clz32(Q[k]&-Q[k]),v=32*k+off,bit=1<<off;
    order.push(v);bounds.push(color);rem[k]&=~bit;Q[k]&=~bit;
    for(let j=0;j<blocks;j++)Q[j]&=~adj[v][j];
   }
  }
  return {order,bounds};
 }
 function expand(P,depth){
  nodes++;if((nodes&255)===1&&performance.now()>deadline)throw Error("TIMEOUT");
  if(depth>=target){found=stack.slice(0,depth);return true;}
  const {order,bounds}=colors(P);if(depth===0)rootBound=bounds.at(-1)??0;
  for(let i=order.length-1;i>=0;i--){
   if(depth+bounds[i]<target)return false;
   const v=order[i],Q=new Uint32Array(blocks);
   for(let k=0;k<blocks;k++)Q[k]=P[k]&adj[v][k];
   stack[depth]=v;if(expand(Q,depth+1))return true;
   P[v>>>5]&=~(1<<(v&31));
  }
  return false;
 }
 let status;
 try{status=expand(all,0)?"FEASIBLE":"INFEASIBLE_ENCODED_NEIGHBORHOOD";}catch(e){if(e.message!=="TIMEOUT")throw e;status="TIMEOUT";}
 return {status,nodes,root_coloring_bound:rootBound,seconds:(performance.now()-start)/1000,selection:found};
}
let prng=2271131;function rand(){prng^=prng<<13;prng^=prng>>>17;prng^=prng<<5;return(prng>>>0)/4294967296;}
let fixtures=0;
for(let n=2;n<=12;n++)for(let rep=0;rep<4;rep++){
 const adj=Array.from({length:n},()=>new Uint32Array(1));
 for(let i=0;i<n;i++)for(let j=0;j<i;j++)if(rand()<.5){adj[i][0]|=1<<j;adj[j][0]|=1<<i;}
 let opt=0;
 for(let mask=0;mask<(1<<n);mask++){
  let valid=true,count=0;for(let v=0;v<n;v++)if(mask&(1<<v)){count++;if(mask&~(adj[v][0]|(1<<v))){valid=false;break;}}
  if(valid)opt=Math.max(opt,count);
 }
 if(solveGraph(adj,opt,1).status!=="FEASIBLE"||solveGraph(adj,opt+1,1).status!=="INFEASIBLE_ENCODED_NEIGHBORHOOD")throw Error("fixture");
 fixtures++;
}
const started=performance.now(),D=[];
function descendants(x){
 const S=new Set();
 for(let i=0;i<16;i++){
  const y=(x&((1<<i)-1))|((x>>>(i+1))<<i);
  for(let j=i;j<15;j++)S.add((y&((1<<j)-1))|((y>>>(j+1))<<j));
 }
 return [...S].sort((a,b)=>a-b);
}
for(let w=0;w<65536;w++)D.push(descendants(w));
const owner=new Int16Array(16384).fill(-1);
for(let i=0;i<base.length;i++)for(const d of D[base[i]]){if(owner[d]>=0)throw Error("baseline collision");owner[d]=i;}
const rows=[];let witness=null;
for(const def of definitions){
 const forced=parseInt(def.forced,2),removed=new Set(def.removed_indices),blockedDesc=new Set(D[forced]),pool=[];
 for(let w=0;w<65536;w++){
  let okay=true;
  for(const d of D[w])if(blockedDesc.has(d)||(owner[d]>=0&&!removed.has(owner[d]))){okay=false;break;}
  if(okay)pool.push(w);
 }
 const poolHash=sha(pool.map(w=>w.toString(2).padStart(16,"0")).join("\n")+"\n");
 if(poolHash!==def.pool_sha256||pool.length!==def.pool_size)throw Error("pool mismatch");
 const n=pool.length,blocks=Math.ceil(n/32),adj=Array.from({length:n},()=>new Uint32Array(blocks).fill(0xffffffff));
 if(n%32)for(const row of adj)row[blocks-1]=(2**(n%32)-1)>>>0;
 const inc=Array.from({length:16384},()=>[]);
 for(let i=0;i<n;i++)for(const d of D[pool[i]])inc[d].push(i);
 for(let i=0;i<n;i++){
  adj[i][i>>>5]&=~(1<<(i&31));
  for(const d of D[pool[i]])for(const j of inc[d])adj[i][j>>>5]&=~(1<<(j&31));
 }
 const result=solveGraph(adj,removed.size,5);
 rows.push({...def,previous_python_status:def.status,previous_python_nodes:def.nodes,requested_kernel_seconds:5,kernel_result:result});
 if(result.selection){witness=base.filter((w,i)=>!removed.has(i)).concat([forced],result.selection.map(i=>pool[i])).map(w=>w.toString(2).padStart(16,"0"));break;}
}
const finalWords=witness??base.map(w=>w.toString(2).padStart(16,"0")),seen=new Map();
for(const s of finalWords){
 const ds=new Set();for(let i=0;i<16;i++)for(let j=i+1;j<16;j++)ds.add(s.slice(0,i)+s.slice(i+1,j)+s.slice(j+1));
 for(const d of ds){if(seen.has(d))throw Error("cross-word collision");seen.set(d,s);}
}
function lcs(a,b){let p=new Uint8Array(17);for(const aa of a){const q=new Uint8Array(17);for(let j=1;j<=16;j++)q[j]=aa===b[j-1]?p[j-1]+1:Math.max(p[j],q[j-1]);p=q;}return p[16];}
let maxLcs=0;for(let i=0;i<finalWords.length;i++)for(let j=i+1;j<finalWords.length;j++)maxLcs=Math.max(maxLcs,lcs(finalWords[i],finalWords[j]));
if(maxLcs>13||new Set(finalWords).size!==finalWords.length)throw Error("LCS or uniqueness");
console.log(JSON.stringify({method:"Uint32 bitset exact clique on two previously open guided-pivot packing pools",runtime:process.version,fixture_graphs:fixtures,queries:rows,best:finalWords.length,max_lcs:maxLcs,distinct_descendants:seen.size,seconds:(performance.now()-started)/1000,new_witness:witness,scope:"Time budgets are open on timeout; original fixed-outside and forced-pivot restrictions preserved. Exploratory checks do not replace protected independent acceptance."}));
