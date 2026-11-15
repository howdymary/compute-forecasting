// Phase-two sparse exchange kernel. The protected verifiers are separate programs.
#define main codegarden_v1_main
#include "../kernel.cpp"
#undef main
#include <map>
#include <set>
#include <ctime>
struct Aug {
 bool found=false,complete=false;uint64_t checks=0,sets=0,scanned=0;
 vector<int> removed,added,pool;string status="TIMEOUT";
};
bool compatible(const vector<uint16_t>&a,const vector<uint16_t>&b){
 size_t i=0,j=0;while(i<a.size()&&j<b.size()){if(a[i]==b[j])return false;if(a[i]<b[j])++i;else ++j;}return true;
}
uint64_t pairkey(int a,int b){if(a>b)swap(a,b);return(uint64_t(a+1)<<32)|uint64_t(b+1);}
Aug augment(const vector<vector<uint16_t>>&desc,const vector<int>&code,const vector<int>&owner,int k,double seconds,uint64_t limit=2000000){
 Aug r;auto begin=chrono::steady_clock::now();
 auto over=[&](){return chrono::duration<double>(chrono::steady_clock::now()-begin).count()>=seconds||r.checks>=limit;};
 vector<uint8_t> selected(desc.size(),0);for(int w:code)selected[w]=1;
 map<int,vector<int>> single;map<uint64_t,vector<int>> pairs;vector<int> zero;
 for(int w=0;w<int(desc.size());++w){
  if((w&1023)==0&&over())return r;++r.scanned;if(selected[w])continue;
  int a=-1,b=-1;bool excess=false;
  for(auto d:desc[w]){int v=owner[d];if(v<0||v==a||v==b)continue;
   if(a<0)a=v;else if(b<0)b=v;else{excess=true;break;}}
  if(excess)continue;
  if(a<0)zero.push_back(w);else if(b<0)single[a].push_back(w);else if(k==2)pairs[pairkey(a,b)].push_back(w);
 }
 auto inspect=[&](vector<int> removed,vector<int> pool)->int{
  sort(pool.begin(),pool.end());pool.erase(unique(pool.begin(),pool.end()),pool.end());++r.sets;
  for(size_t a=0;a<pool.size();++a)for(size_t b=a+1;b<pool.size();++b){
   if(over())return -1;++r.checks;if(!compatible(desc[pool[a]],desc[pool[b]]))continue;
   if(k==1){r.found=true;r.removed=removed;r.added={pool[a],pool[b]};r.pool=pool;return 1;}
   for(size_t c=b+1;c<pool.size();++c){
    if(over())return -1;++r.checks;
    if(compatible(desc[pool[a]],desc[pool[c]])&&compatible(desc[pool[b]],desc[pool[c]])){
     r.found=true;r.removed=removed;r.added={pool[a],pool[b],pool[c]};r.pool=pool;return 1;
    }
   }
  }
  return 0;
 };
 for(size_t i=0;i<code.size();++i){
  if(over())return r;
  if(k==1){auto pool=zero;auto it=single.find(code[i]);if(it!=single.end())pool.insert(pool.end(),it->second.begin(),it->second.end());
   int s=inspect({code[i]},pool);if(s){r.status=s>0?"FEASIBLE":"TIMEOUT";return r;}}
  else for(size_t j=i+1;j<code.size();++j){
   if(over())return r;auto pool=zero;
   for(int w:{code[i],code[j]}){auto it=single.find(w);if(it!=single.end())pool.insert(pool.end(),it->second.begin(),it->second.end());}
   auto it=pairs.find(pairkey(code[i],code[j]));if(it!=pairs.end())pool.insert(pool.end(),it->second.begin(),it->second.end());
   int s=inspect({code[i],code[j]},pool);if(s){r.status=s>0?"FEASIBLE":"TIMEOUT";return r;}
  }
 }
 r.complete=true;r.status="EXHAUSTED_EXACT_K_NEW_WORD_EXCHANGES";return r;
}
vector<vector<uint16_t>> smalldesc(int n){
 vector<vector<uint16_t>> d(1<<n);
 for(int w=0;w<(1<<n);++w){auto&v=d[w];for(int i=0;i<n;++i)for(int j=0;j<n-1;++j)v.push_back(delbit(delbit(w,i),j));
  sort(v.begin(),v.end());v.erase(unique(v.begin(),v.end()),v.end());}
 return d;
}
void augjson(const Aug&r){
 cout<<"{\"status\":\""<<r.status<<"\",\"found\":"<<(r.found?"true":"false")<<",\"complete\":"<<(r.complete?"true":"false")
 <<",\"checks\":"<<r.checks<<",\"removal_sets_checked\":"<<r.sets<<",\"universe_scanned\":"<<r.scanned<<",\"removed\":";
 outputArray(r.removed);cout<<",\"added\":";outputArray(r.added);cout<<",\"candidate_pool\":";outputArray(r.pool);cout<<"}";
}
string exactkey(const vector<int>&code){auto v=code;sort(v.begin(),v.end());string k;for(int w:v){k.push_back(char(w>>8));k.push_back(char(w&255));}return k;}
int rev16(int w){int x=0;for(int i=0;i<16;++i){x=(x<<1)|(w&1);w>>=1;}return x;}
string orbitkey(const vector<int>&code){
 auto a=code,b=code,c=code;for(int& w:a)w^=65535;for(int&w:b)w=rev16(w);for(int&w:c)w=rev16(w)^65535;
 return min(min(exactkey(code),exactkey(a)),min(exactkey(b),exactkey(c)));
}
double cpu(){return double(clock())/CLOCKS_PER_SEC;}
int main(int argc,char**argv){
 try{
  double budget=stod(argv[1]);uint64_t seed=stoull(argv[2]);Garden g(seed);string text;vector<int> original;
  while(cin>>text){if(text.size()!=16||text.find_first_not_of("01")!=string::npos)throw runtime_error("input");
   int w=stoi(text,nullptr,2);g.add(w);original.push_back(w);}
  g.check();vector<int>best=g.code;set<string>visited{exactkey(g.code)};uint64_t steps=0,sweeps=0,cachehits=0,neutrals=0;
  set<string>exhausted1,exhausted2;double start=cpu();string end="BUDGET";vector<int>initialChoices;
  while(cpu()-start<budget&&best.size()<227){
   vector<pair<int,int>>choices;int freeword=-1;
   for(int w=0;w<N;++w){if(g.codePos[w]>=0)continue;int first=-1;bool excess=false;
    for(auto d:g.desc[w]){int v=g.owner[d];if(v<0||v==first)continue;if(first<0)first=v;else{excess=true;break;}}
    if(excess)continue;if(first<0){freeword=w;break;}choices.push_back({w,first});}
   if(steps==0)initialChoices={int(choices.size())};
   if(freeword>=0){g.add(freeword);best=g.code;end="FEASIBLE_IMPROVEMENT";break;}
   if(choices.empty()){end="NO_SINGLE_NEUTRAL_MOVE";break;}
   shuffle(choices.begin(),choices.end(),g.rng);bool moved=false;
   for(auto [w,v]:choices){
    auto trial=g.code;*find(trial.begin(),trial.end(),v)=w;auto key=exactkey(trial);
    if(visited.count(key))continue;
    g.remove(v);g.add(w);visited.insert(key);moved=true;++neutrals;break;
   }
   if(!moved){
    // Revisit a plateau state to avoid permanently excluding promising words.
    auto [w,v]=choices[g.rnd(choices.size())];g.remove(v);g.add(w);
   }
   ++steps;
   string key=exactkey(g.code);
   for(int k:{1,2}){
    auto&cache=k==1?exhausted1:exhausted2;
    if(cache.count(key)){++cachehits;continue;}
    double left=budget-(cpu()-start);if(left<=0)break;
    auto r=augment(g.desc,g.code,g.owner,k,min(.04,left),300000);++sweeps;
    if(r.complete)cache.insert(key);
    if(r.found){for(int v:r.removed)g.remove(v);for(int w:r.added)g.add(w);best=g.code;end="FEASIBLE_IMPROVEMENT";break;}
   }
   g.check();
  }
  g.check();cout<<"{\"seed\":"<<seed<<",\"cpu_seconds\":"<<cpu()-start<<",\"steps\":"<<steps<<",\"new_neutral_states\":"<<neutrals
   <<",\"distinct_plateau_states\":"<<visited.size()<<",\"exact_sweeps\":"<<sweeps<<",\"cache_hits\":"<<cachehits<<",\"initial_neutral_moves\":";
  outputArray(initialChoices);cout<<",\"end\":\""<<end<<"\",\"best\":";outputArray(best);
  cout<<",\"scope\":\"Budgeted one-for-one plateau walk and complete-or-timeout one/two removal augmentations; no global bound\"}\n";
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}
}
