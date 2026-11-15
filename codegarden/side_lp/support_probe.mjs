import {createHash} from "node:crypto";
const sha=s=>createHash("sha256").update(s).digest("hex");
const root="https://raw.githubusercontent.com/howdymary/compute-forecasting/f134115893bde7150b5ab74456597e7d132d5c00/codegarden/";
const seedText=await(await fetch(root+"artifacts/best_code.txt")).text();
if(sha(seedText)!=="417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa")throw Error("seed hash");
const base=seedText.trim().split("\n").map(s=>parseInt(s,2));
const vectorText=await(await fetch(root+"artifacts/side_research/lp_001/lp_vectors/unforced3176.json")).text();
const V=JSON.parse(vectorText);
const defs=await(await fetch(root+"side_services/models.json")).json();
const removed=new Set(defs[2].removed_indices),fixed=base.filter((w,i)=>!removed.has(i)),repairSeed=base.filter((w,i)=>removed.has(i));
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

const started=performance.now();
function descendants(x){
 const S=new Set();for(let i=0;i<16;i++){const y=(x&((1<<i)-1))|((x>>>(i+1))<<i);for(let j=i;j<15;j++)S.add((y&((1<<j)-1))|((y>>>(j+1))<<j));}return [...S].sort((a,b)=>a-b);
}
const cache=new Map();function ds(w){if(!cache.has(w))cache.set(w,descendants(w));return cache.get(w);}
const occupied=new Set();for(const w of fixed)for(const d of ds(w)){if(occupied.has(d))throw Error("fixed collision");occupied.add(d);}
for(const w of V.pool_words)for(const d of ds(w))if(occupied.has(d))throw Error("candidate incompatible with fixed code");
const fmt=w=>w.toString(2).padStart(16,"0"),hashPool=p=>sha(p.map(fmt).join("\n")+"\n");
if(hashPool(V.pool_words)!=="6fb37782459eeccb5100dab6fde2b1aa88958e96fb69573622d12306c046e7fb")throw Error("complete pool hash");
prng=2271135;
const models=[],seenPools=new Map();
for(const threshold of [1e-7,0.1,0.2]){
 const keep=new Set(repairSeed);
 for(let i=0;i<V.pool_words.length;i++)if(V.fractional_values[i]>threshold)keep.add(V.pool_words[i]);
 const support=[...keep].sort((a,b)=>a-b);
 const alternatives=V.pool_words.filter(w=>!new Set(repairSeed).has(w));
 for(let i=alternatives.length-1;i>0;i--){const j=Math.floor(rand()*(i+1));[alternatives[i],alternatives[j]]=[alternatives[j],alternatives[i]];}
 const random=[...repairSeed,...alternatives.slice(0,support.length-repairSeed.length)].sort((a,b)=>a-b);
 models.push({method:"lp_support_plus_seed",threshold,pool:support},{method:"size_matched_random_plus_seed",threshold,pool:random});
}
const results=[];let witness=null;
for(const spec of models){
 if(performance.now()-started>38000)break;
 const pool=spec.pool,n=pool.length,poolHash=hashPool(pool);
 if(seenPools.has(poolHash)){results.push({...spec,pool_sha256:poolHash,status:"DUPLICATE_NOT_REPEATED",duplicate_of:seenPools.get(poolHash)});continue;}
 seenPools.set(poolHash,results.length);
 const blocks=Math.ceil(n/32),adj=Array.from({length:n},()=>new Uint32Array(blocks).fill(0xffffffff));
 if(n%32)for(const row of adj)row[blocks-1]=(2**(n%32)-1)>>>0;
 const inc=Array.from({length:16384},()=>[]);
 for(let i=0;i<n;i++)for(const d of ds(pool[i]))inc[d].push(i);
 for(let i=0;i<n;i++){adj[i][i>>>5]&=~(1<<(i&31));for(const d of ds(pool[i]))for(const j of inc[d])adj[i][j>>>5]&=~(1<<(j&31));}
 function popc(x){x=x-((x>>>1)&0x55555555);x=(x&0x33333333)+((x>>>2)&0x33333333);return (((x+(x>>>4))&0x0f0f0f0f)*0x01010101)>>>24;}
 const degree=adj.map(row=>row.reduce((s,w)=>s+popc(w),0)),order=Array.from({length:n},(_,i)=>i).sort((i,j)=>degree[j]-degree[i]||pool[i]-pool[j]);
 const sorted=Array.from({length:n},()=>new Uint32Array(blocks));
 for(let i=0;i<n;i++)for(let j=0;j<n;j++)if(adj[order[i]][order[j]>>>5]&(1<<(order[j]&31)))sorted[i][j>>>5]|=1<<(j&31);
 const exact=solveGraph(sorted,227-fixed.length,4);
 results.push({...spec,pool_count:n,pool_sha256:poolHash,required_repair:227-fixed.length,ordering:"static decreasing compatibility degree",budget_seconds:4,result:exact});
 if(exact.selection){witness=fixed.concat(exact.selection.map(i=>pool[order[i]])).sort((a,b)=>a-b).map(fmt);break;}
}
const words=witness??base.map(fmt),owners=new Map();
for(const s of words){const dd=new Set();for(let i=0;i<16;i++)for(let j=i+1;j<16;j++)dd.add(s.slice(0,i)+s.slice(i+1,j)+s.slice(j+1));for(const d of dd){if(owners.has(d))throw Error("cross-codeword descendant");owners.set(d,s);}}
function lcs(a,b){let p=new Uint8Array(17);for(const aa of a){const q=new Uint8Array(17);for(let j=1;j<=16;j++)q[j]=aa===b[j-1]?p[j-1]+1:Math.max(p[j],q[j-1]);p=q;}return p[16];}
let maxLcs=0;for(let i=0;i<words.length;i++)for(let j=i+1;j<words.length;j++)maxLcs=Math.max(maxLcs,lcs(words[i],words[j]));
if(maxLcs>13||new Set(words).size!==words.length)throw Error("invalid result");
console.log(JSON.stringify({method:"LP-support restricted repair versus size-matched random repair",seed:2271135,runtime:process.version,fixture_graphs:fixtures,source_commit:"f134115893bde7150b5ab74456597e7d132d5c00",lp_vectors_sha256:sha(vectorText),fixed_words:fixed.map(fmt),removed_indices:[...removed],full_pool_sha256:hashPool(V.pool_words),models:results,best:words.length,max_lcs:maxLcs,new_witness:witness,seconds:(performance.now()-started)/1000,scope:"Temporary restricted candidate pools only. Full3176-word pool remains open. Timeout is unresolved; completed restricted negatives are not full-neighborhood or global impossibility proofs."}));
