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
using namespace std;
double cpu(){return double(clock())/CLOCKS_PER_SEC;}
uint32_t dropbit(uint32_t x,int p){return ((x>>(p+1))<<p)|(x&((1u<<p)-1));}
void arr(const vector<int>&a){cout<<"[";for(size_t i=0;i<a.size();++i){if(i)cout<<",";cout<<a[i];}cout<<"]";}
int pop(const vector<uint64_t>&b){int n=0;for(auto x:b)n+=__builtin_popcountll(x);return n;}
struct Search{
 int n,K,N,M,BW,W=0,neutralCap,depthLimit;uint64_t nodeLimit,nodes=0;double budget,start;bool found=false,limited=false,memoryLimited=false,neighborLimited=false;
 vector<vector<uint16_t>>desc;vector<int>code,owner,words,chosen,answerAdded,answerRemoved;vector<vector<uint64_t>>blocks;
 vector<uint64_t>compat;vector<vector<int>>neighbors;set<vector<int>>neighborKeys;
 Search(int nn,int kk,double sec,uint64_t lim,int cap):n(nn),K(kk),N(1<<nn),M(1<<(nn-2)),neutralCap(cap),nodeLimit(lim),budget(sec),desc(N),owner(M,-1){
  for(int w=0;w<N;++w){auto&d=desc[w];for(int i=0;i<n;++i)for(int j=0;j<n-1;++j)d.push_back(dropbit(dropbit(w,i),j));
   sort(d.begin(),d.end());d.erase(unique(d.begin(),d.end()),d.end());}
 }
 bool over(){return cpu()-start>=budget||nodes>=nodeLimit;}
 vector<int> changed(const vector<uint64_t>&b,const vector<int>&add){
  vector<int>out;for(size_t i=0;i<code.size();++i)if(!(b[i/64]&(1ull<<(i%64))))out.push_back(code[i]);
  for(int i:add)out.push_back(words[i]);sort(out.begin(),out.end());return out;
 }
 bool dfs(vector<uint64_t>p,const vector<uint64_t>&b){
  for(int block=0;block<W;++block)while(p[block]){
   if(nodes>=nodeLimit||((nodes&1023)==0&&cpu()-start>=budget)){limited=true;return true;}
   int bit=__builtin_ctzll(p[block]),v=block*64+bit;p[block]&=p[block]-1;++nodes;
   vector<uint64_t>nb(BW);for(int j=0;j<BW;++j)nb[j]=b[j]|blocks[v][j];int removed=pop(nb);if(removed>K)continue;
   chosen.push_back(v);
   if(int(chosen.size())>removed){
    found=true;for(int i:chosen)answerAdded.push_back(words[i]);
    for(size_t i=0;i<code.size();++i)if(nb[i/64]&(1ull<<(i%64)))answerRemoved.push_back(code[i]);
    return true;
   }
   if(neutralCap>0&&int(chosen.size())==depthLimit&&int(chosen.size())==removed){
    auto next=changed(nb,chosen);if(neighborKeys.insert(next).second){neighbors.push_back(next);
     if(int(neighbors.size())>=neutralCap){neighborLimited=true;return true;}}
   }
   if(int(chosen.size())<depthLimit){
    vector<uint64_t>q(W);int remaining=0;for(int j=0;j<W;++j){q[j]=p[j]&compat[size_t(v)*W+j];remaining+=__builtin_popcountll(q[j]);}
    if((int(chosen.size())+remaining>removed||(neutralCap>0&&int(chosen.size())+remaining==removed))&&remaining)if(dfs(q,nb))return true;
   }
   chosen.pop_back();
  }
  return false;
 }
 void run(){
  start=cpu();BW=(code.size()+63)/64;vector<uint8_t>selected(N,0);for(int w:code)selected[w]=1;
  for(int w=0;w<N;++w){
   if((w&1023)==0&&over()){limited=true;return;}
   if(selected[w])continue;vector<uint64_t>b(BW,0);int count=0;
   for(int d:desc[w]){int v=owner[d];if(v>=0&&!(b[v/64]&(1ull<<(v%64)))){b[v/64]|=1ull<<(v%64);if(++count>K)break;}}
   if(count<=K){words.push_back(w);blocks.push_back(b);}
  }
  W=(words.size()+63)/64;
  uint64_t bytes=(uint64_t(M)+words.size())*W*8;if(bytes>256ull*1024*1024){memoryLimited=true;return;}
  vector<uint64_t>at(size_t(M)*W,0);compat.assign(words.size()*W,0);
  for(size_t i=0;i<words.size();++i)for(int d:desc[words[i]])at[size_t(d)*W+i/64]|=1ull<<(i%64);
  for(size_t i=0;i<words.size();++i){
   if((i&255)==0&&over()){limited=true;return;}
   auto row=&compat[i*W];for(int j=0;j<W;++j)row[j]=~0ull;
   for(int d:desc[words[i]])for(int j=0;j<W;++j)row[j]&=~at[size_t(d)*W+j];
   if(W&&words.size()%64)row[W-1]&=(1ull<<(words.size()%64))-1;
  }
  vector<uint64_t>p(W,~0ull),b(BW,0);if(W&&words.size()%64)p[W-1]&=(1ull<<(words.size()%64))-1;
  for(depthLimit=1;depthLimit<=K+1;++depthLimit)if(dfs(p,b))break;
 }
};
int main(int argc,char**argv){
 try{
  if(argc!=6)throw runtime_error("usage: n k seconds nodes neutral_cap");int n=stoi(argv[1]),K=stoi(argv[2]);double seconds=stod(argv[3]);uint64_t nodes=stoull(argv[4]);int cap=stoi(argv[5]);
  if(n<3||n>16||K<1||K>12)throw runtime_error("parameters");Search s(n,K,seconds,nodes,cap);string text;set<int>seen;
  while(cin>>text){if(int(text.size())!=n||text.find_first_not_of("01")!=string::npos)throw runtime_error("word");
   int w=stoi(text,nullptr,2);if(!seen.insert(w).second)throw runtime_error("duplicate");int id=s.code.size();s.code.push_back(w);
   for(int d:s.desc[w]){if(s.owner[d]>=0)throw runtime_error("invalid input");s.owner[d]=id;}}
  if(s.code.empty())throw runtime_error("empty");s.run();bool complete=!s.found&&!s.limited&&!s.memoryLimited&&!s.neighborLimited;
  cout<<"{\"found\":"<<(s.found?"true":"false")<<",\"complete\":"<<(complete?"true":"false")<<",\"cpu_seconds\":"<<cpu()-s.start
   <<",\"nodes\":"<<s.nodes<<",\"k\":"<<K<<",\"n\":"<<n<<",\"memory_limited\":"<<(s.memoryLimited?"true":"false")
   <<",\"budget_limited\":"<<(s.limited?"true":"false")<<",\"neutral_cap_reached\":"<<(s.neighborLimited?"true":"false")
   <<",\"candidate_count\":"<<s.words.size()<<",\"profiled_bitset_bytes\":"<<(uint64_t(s.M)+s.words.size())*s.W*8
   <<",\"candidate_pool\":";arr(s.words);cout<<",\"removed\":";arr(s.answerRemoved);cout<<",\"added\":";arr(s.answerAdded);
  cout<<",\"neighbors\":[";for(size_t i=0;i<s.neighbors.size();++i){if(i)cout<<",";arr(s.neighbors[i]);}
  cout<<"],\"scope\":\"All outside words with at most k incumbent blockers; cliques up to k+1 new words. Complete is false on every time/node/memory/neighbor cap.\"}\n";
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}return 0;
}
