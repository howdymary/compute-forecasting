// CodeGarden sparse-incidence ruin/recreate kernel. No dense conflict graph.
// All exported witnesses require the two protected external verifiers.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>
using namespace std;
constexpr int N=65536,M=16384;
uint32_t delbit(uint32_t x,int p){return ((x>>(p+1))<<p)|(x&((1u<<p)-1));}
string bits(int w){string s(16,'0');for(int i=15;i>=0;--i){s[i]='0'+(w&1);w>>=1;}return s;}
struct Garden{
 vector<uint8_t> eligible;vector<int> candidateWords;
 vector<vector<uint16_t>> desc,inc;
 vector<uint16_t> blocked;
 vector<int> owner,freeWords,freePos,code,codePos;
 mt19937_64 rng;
 Garden(uint64_t seed):eligible(N,1),desc(N),inc(M),blocked(N,0),owner(M,-1),freePos(N),codePos(N,-1),rng(seed){
  const char*p=getenv("CODEGARDEN_POOL");if(p&&*p){std::fill(eligible.begin(),eligible.end(),0);ifstream in(p);if(!in)throw runtime_error("missing candidate pool");int w;while(in>>w){if(w<0||w>=N)throw runtime_error("pool word");eligible[w]=1;}}
  for(int w=0;w<N;++w)if(eligible[w])candidateWords.push_back(w);if(candidateWords.empty())throw runtime_error("empty pool");
  vector<uint16_t> temp;temp.reserve(120);
  for(int w=0;w<N;++w){
   temp.clear();
   for(int p=0;p<16;++p){auto a=delbit(w,p);for(int q=0;q<15;++q)temp.push_back(delbit(a,q));}
   sort(temp.begin(),temp.end());temp.erase(unique(temp.begin(),temp.end()),temp.end());
   desc[w]=temp;if(eligible[w])for(auto d:temp)inc[d].push_back(uint16_t(w));
  }
  std::fill(freePos.begin(),freePos.end(),-1);for(int w:candidateWords){freePos[w]=freeWords.size();freeWords.push_back(w);}
 }
 int rnd(int size){return int(rng()%uint64_t(size));}
 double unit(){return double(rng()>>11)*(1.0/9007199254740992.0);}
 void eraseFree(int w){
  int p=freePos[w];if(p<0)return;int last=freeWords.back();freeWords[p]=last;freePos[last]=p;freeWords.pop_back();freePos[w]=-1;
 }
 void insertFree(int w){if(!eligible[w]||freePos[w]>=0)return;freePos[w]=int(freeWords.size());freeWords.push_back(w);}
 void add(int w){
  if(!eligible[w]||blocked[w]||codePos[w]>=0)throw runtime_error("incompatible insertion");
  codePos[w]=int(code.size());code.push_back(w);
  for(auto d:desc[w]){
   if(owner[d]!=-1)throw runtime_error("descendant collision");
   owner[d]=w;
   for(auto v:inc[d])if(blocked[v]++==0)eraseFree(v);
  }
 }
 void remove(int w){
  int p=codePos[w];if(p<0)return;int last=code.back();code[p]=last;codePos[last]=p;code.pop_back();codePos[w]=-1;
  for(auto d:desc[w]){
   if(owner[d]!=w)throw runtime_error("ownership mismatch");
   owner[d]=-1;
   for(auto v:inc[d])if(--blocked[v]==0)insertFree(v);
  }
 }
 void restore(const vector<int>& target){
  vector<uint8_t> keep(N,0);for(int w:target)keep[w]=1;
  auto current=code;for(int w:current)if(!keep[w])remove(w);
  for(int w:target)if(codePos[w]<0)add(w);
 }
 vector<int> blockers(int w){
  vector<int> b;for(auto d:desc[w])if(owner[d]>=0)b.push_back(owner[d]);
  sort(b.begin(),b.end());b.erase(unique(b.begin(),b.end()),b.end());return b;
 }
 void fill(double noise){
  while(!freeWords.empty()){
   int chosen=freeWords[rnd(int(freeWords.size()))];
   if(unit()>.15){
    double score=double(desc[chosen].size())+unit()*noise;
    for(int j=0;j<24;++j){
     int w=freeWords[rnd(int(freeWords.size()))];
     double q=double(desc[w].size())+unit()*noise;
     if(q<score){score=q;chosen=w;}
    }
   }
   add(chosen);
  }
 }
 void check(){
  vector<int> owners(M,-1);
  for(int w:code)for(auto d:desc[w]){if(owners[d]>=0)throw runtime_error("self-check collision");owners[d]=w;}
  if(owners!=owner)throw runtime_error("self-check owner state");
  for(int w=0;w<N;++w){
   if(!eligible[w]){if(freePos[w]>=0||codePos[w]>=0)throw runtime_error("ineligible state");continue;}
   int count=0;for(auto d:desc[w])count+=owners[d]>=0;
   if(count!=blocked[w]||((freePos[w]>=0)!=(count==0)))throw runtime_error("incremental state mismatch");
  }
 }
 uint64_t fingerprint(const vector<int>& c){
  auto v=c;sort(v.begin(),v.end());uint64_t h=1469598103934665603ULL;
  for(int w:v){h^=uint64_t(w);h*=1099511628211ULL;}return h;
 }
};
void outputArray(const vector<int>& a){cout<<"[";for(size_t i=0;i<a.size();++i){if(i)cout<<",";cout<<a[i];}cout<<"]";}
void checkpoint(const string& path,const vector<int>& code){
 if(path.empty())return;auto v=code;sort(v.begin(),v.end());
 ofstream f(path+".tmp");for(int w:v)f<<bits(w)<<"\n";f.close();
 if(rename((path+".tmp").c_str(),path.c_str()))throw runtime_error("checkpoint rename failed");
}
int main(int argc,char**argv){
 try{
  if(argc>1&&string(argv[1])=="--descendants"){
   Garden g(0);string s;bool first=true;cout<<"{";
   while(cin>>s){
    if(s.size()!=16||s.find_first_not_of("01")!=string::npos)throw runtime_error("invalid dump input");
    int w=stoi(s,nullptr,2);if(!first)cout<<",";first=false;cout<<"\""<<w<<"\":[";
    for(size_t i=0;i<g.desc[w].size();++i){if(i)cout<<",";cout<<g.desc[w][i];}cout<<"]";
   }
   cout<<"}\n";return 0;
  }
  double seconds=argc>1?stod(argv[1]):60;uint64_t seed=argc>2?stoull(argv[2]):17;
  string policy=argc>3?argv[3]:"adaptive";string checkpointPath=argc>4?argv[4]:"";
  int target=argc>5?stoi(argv[5]):227;
  auto origin=chrono::steady_clock::now();Garden g(seed);vector<int> initial;
  string word;while(cin>>word){
   if(word.size()!=16||word.find_first_not_of("01")!=string::npos)throw runtime_error("invalid input word");
   int w=stoi(word,nullptr,2);g.add(w);initial.push_back(w);
  }
  if(initial.empty())throw runtime_error("empty start");g.check();
  vector<int> best=g.code;array<uint64_t,6> count{};array<double,6> reward{};
  vector<vector<int>> archive{best};unordered_set<uint64_t> fingerprints{g.fingerprint(best)};
  uint64_t steps=0,stale=0,accepted=0;int lastArm=-1;uint64_t switches=0;
  checkpoint(checkpointPath,best);
  auto start=chrono::steady_clock::now();double lastCheckpoint=0;
  while(chrono::duration<double>(chrono::steady_clock::now()-start).count()<seconds&&int(best.size())<target){
   int arm=1;
   if(policy=="adaptive"){
    bool chosen=false;
    for(int i=0;i<6;++i)if(count[i]==0){arm=i;chosen=true;break;}
    if(!chosen){
     double q=-1;for(int i=0;i<6;++i){
      double x=reward[i]/double(count[i])+sqrt(2*log(double(steps+1))/double(count[i]));
      if(x>q){q=x;arm=i;}
     }
    }
   }
   ++steps;++count[arm];if(arm!=lastArm){++switches;lastArm=arm;}
   auto old=g.code;
   int r=policy=="adaptive"?min(80,4+int(stale/12000)*4):16;
   double temperature=policy=="adaptive"?.35+min(2.0,double(stale)/30000.):.35;
   if(arm==0||arm==1||arm==5){
    if(arm==1)r+=16;if(arm==5)r+=40;
    r=min(r,int(g.code.size()));auto removed=g.code;
    shuffle(removed.begin(),removed.end(),g.rng);for(int i=0;i<r;++i)g.remove(removed[i]);
   }else if(arm==2){
    int center=__builtin_popcount(unsigned(g.code[g.rnd(int(g.code.size()))]));
    int radius=stale>50000?2:1;auto removed=g.code;
    for(int w:removed)if(abs(__builtin_popcount(unsigned(w))-center)<=radius)g.remove(w);
   }else{
    int pivot=-1;vector<int> removal;int bestCost=1000;
    for(int j=0;j<180;++j){
     int w=g.candidateWords[g.rnd(g.candidateWords.size())];if(g.codePos[w]>=0)continue;auto b=g.blockers(w);
     if(b.empty())continue;
     if(int(b.size())<bestCost||(int(b.size())==bestCost&&g.unit()<.15)){pivot=w;removal=b;bestCost=int(b.size());}
    }
    if(pivot>=0){for(int w:removal)g.remove(w);g.add(pivot);}
    if(arm==4){
     auto removed=g.code;shuffle(removed.begin(),removed.end(),g.rng);
     for(int i=0;i<min(12,int(removed.size()));++i)if(g.codePos[removed[i]]>=0)g.remove(removed[i]);
    }
   }
   g.fill(policy=="adaptive"?4+g.unit()*18:6);
   int beforeBest=int(best.size());int delta=int(g.code.size())-int(old.size());
   bool keep=delta>=0||(int(g.code.size())>=beforeBest-10&&g.unit()<exp(double(delta)/temperature));
   if(keep)++accepted;else g.restore(old);
   if(g.code.size()>best.size()){
    best=g.code;stale=0;reward[arm]+=double(best.size()-beforeBest);
    checkpoint(checkpointPath,best);
   }else ++stale;
   auto h=g.fingerprint(g.code);
   if(int(g.code.size())>=int(best.size())-2&&fingerprints.insert(h).second){
    archive.push_back(g.code);if(archive.size()>16)archive.erase(archive.begin()+1);
   }
   if(policy=="adaptive"&&stale&&stale%15000==0){
    auto restart=archive[g.rnd(archive.size())];
    g.restore(restart);
   }
   if(steps%10000==0)g.check();
   double elapsed=chrono::duration<double>(chrono::steady_clock::now()-start).count();
   if(elapsed-lastCheckpoint>=5){checkpoint(checkpointPath,best);lastCheckpoint=elapsed;}
  }
  g.check();checkpoint(checkpointPath,best);
  double elapsed=chrono::duration<double>(chrono::steady_clock::now()-start).count();
  cout<<"{\"seed\":"<<seed<<",\"policy\":\""<<policy<<"\",\"seconds\":"<<elapsed
      <<",\"precompute_seconds\":"<<chrono::duration<double>(start-origin).count()
      <<",\"iterations\":"<<steps<<",\"accepted\":"<<accepted<<",\"neighborhood_switches\":"<<switches
      <<",\"best_size_unverified\":"<<best.size()<<",\"best\":";
  outputArray(best);cout<<",\"arm_counts\":[";
  for(int i=0;i<6;++i){if(i)cout<<",";cout<<count[i];}
  cout<<"],\"archive\":[";
  for(size_t i=0;i<archive.size();++i){if(i)cout<<",";outputArray(archive[i]);}
  cout<<"],\"global_optimality_claim\":false}\n";
  return 0;
 }catch(const exception&e){cerr<<"CodeGarden kernel rejected state: "<<e.what()<<"\n";return 2;}
}
