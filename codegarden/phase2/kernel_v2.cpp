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
  if(argc>1&&string(argv[1])=="--augment"){
   int n=stoi(argv[2]),k=stoi(argv[3]);double sec=stod(argv[4]);
   if(n<3||n>16||(k!=1&&k!=2))throw runtime_error("invalid exchange parameters");
   auto d=smalldesc(n);vector<int> owner(1<<(n-2),-1),code;string s;
   while(cin>>s){if(int(s.size())!=n||s.find_first_not_of("01")!=string::npos)throw runtime_error("invalid input");
    int w=stoi(s,nullptr,2);for(auto child:d[w]){if(owner[child]>=0)throw runtime_error("invalid input collision");owner[child]=w;}code.push_back(w);}
   Aug r=augment(d,code,owner,k,sec);augjson(r);cout<<"\n";return 0;
  }
  double budget=argc>1?stod(argv[1]):30;uint64_t seed=argc>2?stoull(argv[2]):1;
  string policy=argc>3?argv[3]:"adaptive",cp=argc>4?argv[4]:"";int target=argc>5?stoi(argv[5]):227;
  int preferred=argc>6?stoi(argv[6]):0;if(preferred<0||preferred>5||budget<0)throw runtime_error("invalid budget/action");
  double pre=cpu();Garden g(seed);string s;vector<int> original;
  while(cin>>s){if(s.size()!=16||s.find_first_not_of("01")!=string::npos)throw runtime_error("invalid input");
   int w=stoi(s,nullptr,2);g.add(w);original.push_back(w);}
  if(original.empty())throw runtime_error("empty input");g.check();
  vector<int>best=g.code;vector<vector<int>>archive{best};set<string> diversity{orbitkey(best)},exhausted1,exhausted2;
  array<uint64_t,6>counts{};array<double,6>rewards{},times{};
  uint64_t iterations=0,accepted=0,cachehits=0,sweeps=0,exactgains=0,chains=0;
  double start=cpu(),lastGain=0,lastCp=0;auto wall=chrono::steady_clock::now();
  checkpoint(cp,best);vector<pair<double,int>>progress{{0,int(best.size())}};
  while(cpu()-start<budget&&chrono::duration<double>(chrono::steady_clock::now()-wall).count()<budget*1.6+10&&int(best.size())<target){
   int arm=preferred;
   if(policy=="adaptive"){
    bool initial=false;for(int i=0;i<6;++i)if(!counts[i]){arm=i;initial=true;break;}
    if(!initial){double mx=-1e100;for(int i=0;i<6;++i){
      double score=rewards[i]/max(.001,times[i])+sqrt(2*log(double(iterations+1))/double(counts[i]));
      if(score>mx){mx=score;arm=i;}}}
   double stepStart=cpu();auto old=g.code;int priorBest=best.size();double stale=cpu()-start-lastGain;
   if(arm==4){
    string key=exactkey(g.code);bool changed=false;
    for(int k:{1,2}){
     auto&cache=k==1?exhausted1:exhausted2;
     if(cache.count(key)){++cachehits;continue;}
     auto r=augment(g.desc,g.code,g.owner,k,min(.06,max(.002,budget-(cpu()-start))),250000);++sweeps;
     if(r.complete){if(cache.size()>4000)cache.clear();cache.insert(key);}
     if(r.found){for(int w:r.removed)g.remove(w);for(int w:r.added)g.add(w);++exactgains;changed=true;break;}
    }
    if(!changed){auto v=g.code;shuffle(v.begin(),v.end(),g.rng);for(int i=0;i<min(8,int(v.size()));++i)g.remove(v[i]);}
   }else if(arm==2){
    for(int depth=0;depth<3;++depth){
     int pivot=-1,cost=1000;vector<int> removal;
     for(int j=0;j<120;++j){int w=g.rnd(N);if(g.codePos[w]>=0)continue;auto b=g.blockers(w);
      if(!b.empty()&&int(b.size())<cost){pivot=w;cost=b.size();removal=b;}}
     if(pivot>=0&&cost<=5){for(int w:removal)g.remove(w);g.add(pivot);++chains;}
    }
   }else if(arm==3){
    int center=__builtin_popcount(unsigned(g.code[g.rnd(g.code.size())]));auto v=g.code;
    for(int w:v)if(abs(__builtin_popcount(unsigned(w))-center)<=1)g.remove(w);
   }else{
    int remove=arm==0?32:arm==1?8:64;
    if(policy=="adaptive"&&stale>budget/3)remove+=min(32,int(stale));
    auto v=g.code;shuffle(v.begin(),v.end(),g.rng);for(int i=0;i<min(remove,int(v.size()));++i)g.remove(v[i]);
   }
   g.fill(arm==5?18:arm==1?3:7);
   int delta=int(g.code.size())-int(old.size());double temperature=.45+min(2.0,stale/30);
   bool keep=delta>=0||(int(g.code.size())>=priorBest-8&&g.unit()<exp(double(delta)/temperature));
   if(keep)++accepted;else g.restore(old);
   ++iterations;++counts[arm];times[arm]+=cpu()-stepStart;
   if(g.code.size()>best.size()){best=g.code;lastGain=cpu()-start;rewards[arm]+=double(best.size()-priorBest);
    progress.push_back({lastGain,int(best.size())});checkpoint(cp,best);}
   auto key=orbitkey(g.code);
   if(int(g.code.size())>=int(best.size())-4&&diversity.insert(key).second){archive.push_back(g.code);if(archive.size()>40)archive.erase(archive.begin()+1);}
   if(iterations%12000==0&&policy=="adaptive"){auto v=archive[g.rnd(archive.size())];if(g.unit()<.5)for(int&w:v)w^=65535;g.restore(v);}
   if(iterations%15000==0)g.check();
   if(cpu()-start-lastCp>5){checkpoint(cp,best);lastCp=cpu()-start;}
  }
  g.check();checkpoint(cp,best);double consumed=cpu()-start,elapsed=chrono::duration<double>(chrono::steady_clock::now()-wall).count();
  vector<int>blockHist(9,0);for(int i=0;i<512;++i){auto b=g.blockers(g.rnd(N));++blockHist[min(8,int(b.size()))];}
  cout<<"{\"seed\":"<<seed<<",\"policy\":\""<<policy<<"\",\"preferred_arm\":"<<preferred
   <<",\"cpu_seconds\":"<<consumed<<",\"wall_seconds\":"<<elapsed<<",\"precompute_cpu_seconds\":"<<start-pre
   <<",\"iterations\":"<<iterations<<",\"accepted\":"<<accepted<<",\"cache_hits\":"<<cachehits<<",\"exact_sweeps\":"<<sweeps
   <<",\"exact_augmentations\":"<<exactgains<<",\"ejection_steps\":"<<chains<<",\"stagnation_cpu_seconds\":"<<max(0.,consumed-lastGain)
   <<",\"best_size_unverified\":"<<best.size()<<",\"best\":";outputArray(best);cout<<",\"current\":";outputArray(g.code);
  cout<<",\"archive\":[";for(size_t i=0;i<archive.size();++i){if(i)cout<<",";outputArray(archive[i]);}
  cout<<"],\"arm_counts\":[";for(int i=0;i<6;++i){if(i)cout<<",";cout<<counts[i];}
  cout<<"],\"blocker_histogram_sample\":";outputArray(blockHist);cout<<",\"progress\":[";
  for(size_t i=0;i<progress.size();++i){if(i)cout<<",";cout<<"["<<progress[i].first<<","<<progress[i].second<<"]";}
  cout<<"],\"global_optimality_claim\":false}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}
}
