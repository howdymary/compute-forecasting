// Sparse blocker-union clique search. No acceptance rule is defined here.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <ctime>
#include <iostream>
#include <random>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <functional>
#include <cstdlib>
using namespace std;
double cpu(){return double(clock())/CLOCKS_PER_SEC;}
uint32_t dropbit(uint32_t x,int p){return ((x>>(p+1))<<p)|(x&((1u<<p)-1));}
void arr(const vector<int>&a){cout<<"[";for(size_t i=0;i<a.size();++i){if(i)cout<<",";cout<<a[i];}cout<<"]";}
int pop(const vector<uint64_t>&b){int n=0;for(auto x:b)n+=__builtin_popcountll(x);return n;}
struct VHash{size_t operator()(const vector<uint64_t>&v)const{size_t h=0;for(auto x:v)h^=hash<uint64_t>{}(x)+0x9e3779b9+(h<<6)+(h>>2);return h;}};
struct Search{
 int n,K,N,M,BW,W=0,neutralCap,depthLimit;uint64_t nodeLimit,nodes=0;double budget,start;bool found=false,limited=false,memoryLimited=false,neighborLimited=false;
 vector<vector<uint16_t>>desc;vector<int>code,owner,words,chosen,answerAdded,answerRemoved;vector<vector<uint64_t>>blocks;
 vector<uint64_t>closedTable;vector<uint8_t>closedUsed;size_t tableMask=0;uint64_t cacheHits=0,closedChecks=0,cacheOccupied=0,cacheEvictions=0;vector<vector<int>>anchorBuckets;vector<int>zeroBlockers;unordered_map<vector<uint64_t>,vector<int>,VHash>groups;vector<uint64_t>blockerMasks;vector<uint64_t>compat;vector<vector<int>>neighbors;set<vector<int>>neighborKeys;
 Search(int nn,int kk,double sec,uint64_t lim,int cap):n(nn),K(kk),N(1<<nn),M(1<<(nn-2)),neutralCap(cap),nodeLimit(lim),budget(sec),desc(N),owner(M,-1){
  for(int w=0;w<N;++w){auto&d=desc[w];for(int i=0;i<n;++i)for(int j=0;j<n-1;++j)d.push_back(dropbit(dropbit(w,i),j));
   sort(d.begin(),d.end());d.erase(unique(d.begin(),d.end()),d.end());}
 }
 bool over(){return cpu()-start>=budget||nodes>=nodeLimit;}
 vector<int> changed(const vector<uint64_t>&b,const vector<int>&add){
  vector<int>out;for(size_t i=0;i<code.size();++i)if(!(b[i/64]&(1ull<<(i%64))))out.push_back(code[i]);
  for(int i:add)out.push_back(words[i]);sort(out.begin(),out.end());return out;
 }
 vector<int> permitted(const vector<uint64_t>&b){
  vector<int>ids,out=zeroBlockers;for(int j=0;j<BW;++j){uint64_t x=b[j];while(x){int z=__builtin_ctzll(x);x&=x-1;ids.push_back(j*64+z);}}
  if(!anchorBuckets.empty()){
   auto visit=[&](int a,int z){for(int v:anchorBuckets[size_t(a)*code.size()+z]){bool ok=true;for(int j=0;j<BW;++j)if(blocks[v][j]&~b[j]){ok=false;break;}if(ok)out.push_back(v);}};
   for(size_t i=0;i<ids.size();++i){visit(ids[i],ids[i]);for(size_t j=i+1;j<ids.size();++j)visit(ids[i],ids[j]);}
  }else{
   out.clear();vector<uint64_t>key(BW,0);function<void(int)>go=[&](int i){
    if(i==int(ids.size())){auto it=groups.find(key);if(it!=groups.end())out.insert(out.end(),it->second.begin(),it->second.end());return;}
    go(i+1);int id=ids[i];key[id/64]|=1ull<<(id%64);go(i+1);key[id/64]&=~(1ull<<(id%64));
   };go(0);
  }
  sort(out.begin(),out.end());return out;
 }
 bool closeFull(const vector<uint64_t>&b){
  size_t slot=VHash{}(b)&tableMask;bool cached=closedUsed[slot];if(cached)for(int j=0;j<BW;++j)if(closedTable[slot*BW+j]!=b[j]){cached=false;break;}
  if(cached){++cacheHits;return false;}
  ++closedChecks;auto pool=permitted(b);vector<int>picked;
  function<bool(const vector<int>&)>go=[&](const vector<int>&p){
   if(nodes>=nodeLimit||((nodes&1023)==0&&cpu()-start>=budget)){limited=true;return true;}
   int threshold=neutralCap>0?K:K+1;
   if(int(picked.size())+int(p.size())<threshold)return false;
   for(size_t i=0;i<p.size();++i){
    if(int(picked.size())+int(p.size()-i)<threshold)break;
    ++nodes;int v=p[i];picked.push_back(v);
    if(int(picked.size())>K){found=true;for(int u:picked)answerAdded.push_back(words[u]);
     for(size_t j=0;j<code.size();++j)if(b[j/64]&(1ull<<(j%64)))answerRemoved.push_back(code[j]);return true;}
    if(neutralCap>0&&int(picked.size())==K){
     auto next=changed(b,picked);if(neighborKeys.insert(next).second){neighbors.push_back(next);
      if(int(neighbors.size())>=neutralCap){neighborLimited=true;return true;}}
    }
    vector<int>q;for(size_t j=i+1;j<p.size();++j){int u=p[j];if(compat[size_t(v)*W+u/64]&(1ull<<(u%64)))q.push_back(u);}
    if(go(q))return true;picked.pop_back();
   }
   return false;
  };
  if(go(pool))return true;
  if(closedUsed[slot])++cacheEvictions;else{++cacheOccupied;closedUsed[slot]=1;}
  for(int j=0;j<BW;++j)closedTable[slot*BW+j]=b[j];
  return false;
 }
 bool linked(int a,int b)const{for(int j=0;j<BW;++j)if(blocks[a][j]&blocks[b][j])return true;return false;}
 bool connectedWithout(const vector<int>&t,int omit)const{
  int first=0;while(first<int(t.size())&&first==omit)++first;
  if(first==int(t.size()))return false;
  uint32_t seen=1u<<first,wanted=((1u<<t.size())-1)&~(omit<0?0u:1u<<omit);
  bool change=true;while(change){change=false;
   for(size_t i=0;i<t.size();++i)if(seen&(1u<<i))for(size_t j=0;j<t.size();++j)
    if(int(j)!=omit&&!(seen&(1u<<j))&&linked(t[i],t[j])){seen|=1u<<j;change=true;}
  }
  return (seen&wanted)==wanted;
 }
 bool canonicalAddition(int v)const{
  vector<int>t=chosen;t.push_back(v);sort(t.begin(),t.end());
  // The minimum index is the root. Delete the largest non-root
  // non-articulation vertex to define one unique connected parent.
  for(int i=int(t.size())-1;i>=1;--i)if(connectedWithout(t,i))return t[i]==v;
  return false;
 }
 bool connectedDFS(const vector<uint64_t>&allowed,const vector<uint64_t>&b){
  vector<uint64_t>choices(W,0);
  for(int j=0;j<BW;++j){uint64_t ids=b[j];while(ids){int z=__builtin_ctzll(ids);ids&=ids-1;int id=j*64+z;
   for(int k=0;k<W;++k)choices[k]|=blockerMasks[size_t(id)*W+k];}}
  for(int j=0;j<W;++j)choices[j]&=allowed[j];
  for(int block=0;block<W;++block)while(choices[block]){
   if(nodes>=nodeLimit||((nodes&1023)==0&&cpu()-start>=budget)){limited=true;return true;}
   int bit=__builtin_ctzll(choices[block]),v=block*64+bit;choices[block]&=choices[block]-1;++nodes;
   vector<uint64_t>nb(BW);for(int j=0;j<BW;++j)nb[j]=b[j]|blocks[v][j];int removed=pop(nb);if(removed>K)continue;
   if(!canonicalAddition(v))continue;chosen.push_back(v);
   if(int(chosen.size())>removed){found=true;for(int u:chosen)answerAdded.push_back(words[u]);for(size_t j=0;j<code.size();++j)if(nb[j/64]&(1ull<<(j%64)))answerRemoved.push_back(code[j]);return true;}
   if(removed==K){bool halt=closeFull(nb);chosen.pop_back();if(halt)return true;continue;}
   if(int(chosen.size())<K+1){
    vector<uint64_t>q(W);int possible=0;for(int j=0;j<W;++j){q[j]=allowed[j]&compat[size_t(v)*W+j];possible+=__builtin_popcountll(q[j]);}
    // Keep all compatible candidates, including currently disconnected ones:
    // later additions can connect them. Only choices are frontier-filtered.
    if(int(chosen.size())+possible>removed&&connectedDFS(q,nb))return true;
   }
   chosen.pop_back();
  }
  return false;
 }
 void connectedRun(){
  blockerMasks.assign(code.size()*W,0);
  for(size_t v=0;v<words.size();++v)for(int j=0;j<BW;++j){uint64_t ids=blocks[v][j];while(ids){int z=__builtin_ctzll(ids);ids&=ids-1;blockerMasks[size_t(j*64+z)*W+v/64]|=1ull<<(v%64);}}
  for(size_t r=0;r<words.size();++r){
   if(over()){limited=true;return;}
   chosen.assign(1,r);auto b=blocks[r];int removed=pop(b);
   if(removed==0){found=true;answerAdded={words[r]};return;}
   if(removed==K){if(closeFull(b))return;continue;}
   vector<uint64_t>p(W,0);int possible=0;
   for(size_t v=r+1;v<words.size();++v)if(compat[r*W+v/64]&(1ull<<(v%64))){p[v/64]|=1ull<<(v%64);++possible;}
   if(1+possible>removed&&connectedDFS(p,b))return;
  }
  chosen.clear();
 }
 void run(){
  start=cpu();BW=(code.size()+63)/64;vector<uint8_t>forbidden(N,0);const char*filter=getenv("CODEGARDEN_DOMINANCE_FILTER");
  if(filter&&*filter){ifstream input(filter);if(!input)throw runtime_error("missing certified filter");int w;while(input>>w){if(w<0||w>=N)throw runtime_error("filter universe");forbidden[w]=1;}}
  vector<uint8_t>selected(N,0);for(int w:code)selected[w]=1;
  for(int w=0;w<N;++w){
   if((w&1023)==0&&over()){limited=true;return;}
   if(selected[w]||forbidden[w])continue;vector<uint64_t>b(BW,0);int count=0;
   for(int d:desc[w]){int v=owner[d];if(v>=0&&!(b[v/64]&(1ull<<(v%64)))){b[v/64]|=1ull<<(v%64);if(++count>K)break;}}
   if(count<=K){words.push_back(w);blocks.push_back(b);}
  }
  const char*order=getenv("CODEGARDEN_BLOCK_ORDER");
  if(order&&string(order)=="1"){
   vector<int>idx(words.size());for(size_t i=0;i<idx.size();++i)idx[i]=i;
   sort(idx.begin(),idx.end(),[&](int a,int b){int x=pop(blocks[a]),y=pop(blocks[b]);if(x!=y)return x>y;if(desc[words[a]].size()!=desc[words[b]].size())return desc[words[a]].size()>desc[words[b]].size();return words[a]<words[b];});
   auto oldwords=words;auto oldblocks=blocks;for(size_t i=0;i<idx.size();++i){words[i]=oldwords[idx[i]];blocks[i]=oldblocks[idx[i]];}
  }
  for(size_t i=0;i<blocks.size();++i)groups[blocks[i]].push_back(i);
  size_t slots=size_t(1)<<(n==16?20:12);tableMask=slots-1;closedUsed.assign(slots,0);closedTable.assign(slots*BW,0);
  if(uint64_t(code.size())*code.size()*sizeof(vector<int>)<=32ull*1024*1024){
   anchorBuckets.resize(code.size()*code.size());
   for(size_t v=0;v<words.size();++v){
    vector<int>ids;for(int j=0;j<BW;++j){uint64_t x=blocks[v][j];while(x){int z=__builtin_ctzll(x);x&=x-1;ids.push_back(j*64+z);}}
    if(ids.empty()){zeroBlockers.push_back(v);continue;}
    int a=ids[0],z=ids[0];if(ids.size()>1){z=ids[1];size_t best=anchorBuckets[size_t(a)*code.size()+z].size();
     for(size_t i=0;i<ids.size();++i)for(size_t j=i+1;j<ids.size();++j){size_t size=anchorBuckets[size_t(ids[i])*code.size()+ids[j]].size();if(size<best){best=size;a=ids[i];z=ids[j];}}}
    anchorBuckets[size_t(a)*code.size()+z].push_back(v);
   }
  }
  W=(words.size()+63)/64;
  uint64_t bytes=(uint64_t(M)+words.size())*W*8;if(bytes>768ull*1024*1024){memoryLimited=true;return;}
  vector<uint64_t>at(size_t(M)*W,0);compat.assign(words.size()*W,0);
  for(size_t i=0;i<words.size();++i)for(int d:desc[words[i]])at[size_t(d)*W+i/64]|=1ull<<(i%64);
  for(size_t i=0;i<words.size();++i){
   if((i&255)==0&&over()){limited=true;return;}
   auto row=&compat[i*W];for(int j=0;j<W;++j)row[j]=~0ull;
   for(int d:desc[words[i]])for(int j=0;j<W;++j)row[j]&=~at[size_t(d)*W+j];
   if(W&&words.size()%64)row[W-1]&=(1ull<<(words.size()%64))-1;
  }
  vector<uint64_t>p(W,~0ull),b(BW,0);if(W&&words.size()%64)p[W-1]&=(1ull<<(words.size()%64))-1;
  connectedRun();
 }
};
int syntheticTests(){
 mt19937_64 rng(832047);int tests=0;
 for(int caseId=0;caseId<160;++caseId){
  int m=caseId<20?8:8+int(rng()%7),k=caseId<20?7:1+int(rng()%7);vector<uint64_t>B(m);
  if(caseId<20){
   vector<uint64_t>chain{1,3,6,12,24,48,96,64};shuffle(chain.begin(),chain.end(),rng);B=chain;
  }else for(int i=0;i<m;++i){int size=1+rng()%3;while(__builtin_popcountll(B[i])<size)B[i]|=1ull<<(rng()%7);}
  vector<vector<bool>>compatible(m,vector<bool>(m,false));
  for(int i=0;i<m;++i)for(int j=0;j<i;++j)compatible[i][j]=compatible[j][i]=caseId<10?true:caseId<20?!(i==0&&j==1):rng()%100<60;
  bool expected=false;
  for(unsigned mask=1;mask<(1u<<m)&&!expected;++mask){
   uint64_t used=0;bool ok=true;int count=__builtin_popcount(mask);
   for(int i=0;i<m&&ok;++i)if(mask&(1u<<i)){used|=B[i];for(int j=0;j<i;++j)if((mask&(1u<<j))&&!compatible[i][j]){ok=false;break;}}
   if(ok&&__builtin_popcountll(used)<=k&&count>__builtin_popcountll(used))expected=true;
  }
  Search q(3,k,10,100000000,0);q.code={0,1,2,3,4,5,6};q.BW=1;q.start=cpu();vector<int>original;
  for(int i=0;i<m;++i)if(__builtin_popcountll(B[i])<=k){q.words.push_back(200+i);q.blocks.push_back({B[i]});original.push_back(i);}
  q.W=(q.words.size()+63)/64;q.compat.assign(q.words.size()*q.W,0);
  for(size_t i=0;i<q.words.size();++i){q.groups[q.blocks[i]].push_back(i);for(size_t j=0;j<q.words.size();++j)if(compatible[original[i]][original[j]])q.compat[i*q.W+j/64]|=1ull<<(j%64);}
  q.tableMask=4095;q.closedUsed.assign(4096,0);q.closedTable.assign(4096,0);
  q.connectedRun();if(q.limited||q.found!=expected)throw runtime_error("synthetic connected-search mismatch case "+to_string(caseId));
  if(q.found){uint64_t unionB=0;vector<int>ids;for(int w:q.answerAdded){ids.push_back(w-200);unionB|=B[w-200];}
   if(ids.size()<=size_t(__builtin_popcountll(unionB))||__builtin_popcountll(unionB)>k)throw runtime_error("synthetic deficient witness");
   for(size_t i=0;i<ids.size();++i)for(size_t j=0;j<i;++j)if(!compatible[ids[i]][ids[j]])throw runtime_error("synthetic pair collision");}
  ++tests;
 }
 cout<<"{\"synthetic_cases\":"<<tests<<",\"passed\":true,\"includes_eight_vertex_path_circuits\":true,\"meaning\":\"Algorithm-only arbitrary blocker/compatibility tests, not deletion-code witnesses.\"}\n";return 0;
}
int main(int argc,char**argv){
 try{
  if(argc==2&&string(argv[1])=="--synthetic-tests")return syntheticTests();
  if(argc!=6)throw runtime_error("usage: n k seconds nodes neutral_cap");int n=stoi(argv[1]),K=stoi(argv[2]);double seconds=stod(argv[3]);uint64_t nodes=stoull(argv[4]);int cap=stoi(argv[5]);
  if(n<3||n>16||K<1||K>12||cap!=0)throw runtime_error("parameters: strict exchanges only");Search s(n,K,seconds,nodes,cap);string text;set<int>seen;
  while(cin>>text){if(int(text.size())!=n||text.find_first_not_of("01")!=string::npos)throw runtime_error("word");
   int w=stoi(text,nullptr,2);if(!seen.insert(w).second)throw runtime_error("duplicate");int id=s.code.size();s.code.push_back(w);
   for(int d:s.desc[w]){if(s.owner[d]>=0)throw runtime_error("invalid input");s.owner[d]=id;}}
  if(s.code.empty())throw runtime_error("empty");s.run();bool complete=!s.found&&!s.limited&&!s.memoryLimited&&!s.neighborLimited;
  cout<<"{\"found\":"<<(s.found?"true":"false")<<",\"complete\":"<<(complete?"true":"false")<<",\"cpu_seconds\":"<<cpu()-s.start
   <<",\"nodes\":"<<s.nodes<<",\"closed_blocker_sets\":"<<s.closedChecks<<",\"cache_hits\":"<<s.cacheHits<<",\"retained_closed_keys\":"<<s.cacheOccupied<<",\"cache_evictions\":"<<s.cacheEvictions<<",\"k\":"<<K<<",\"n\":"<<n<<",\"memory_limited\":"<<(s.memoryLimited?"true":"false")
   <<",\"budget_limited\":"<<(s.limited?"true":"false")<<",\"neutral_cap_reached\":"<<(s.neighborLimited?"true":"false")
   <<",\"candidate_count\":"<<s.words.size()<<",\"profiled_bitset_bytes\":"<<(uint64_t(s.M)+s.words.size())*s.W*8
   <<",\"candidate_pool\":";arr(s.words);cout<<",\"removed\":";arr(s.answerRemoved);cout<<",\"added\":";arr(s.answerAdded);
  cout<<",\"neighbors\":[";for(size_t i=0;i<s.neighbors.size();++i){if(i)cout<<",";arr(s.neighbors[i]);}
  cout<<"],\"scope\":\"All outside words with at most k incumbent blockers; connected improving bundles suffice by the disjoint-blocker-component lemma. Complete is false on every time/node/memory/neighbor cap.\"}\n";
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}return 0;
}
