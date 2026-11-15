// Target-cardinality infeasible-space search. A zero energy is only a proposal.
// External protected D2 and LCS checks alone can accept a witness.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
double cpu(){return double(clock())/CLOCKS_PER_SEC;}
uint32_t dropbit(uint32_t x,int p){return ((x>>(p+1))<<p)|(x&((1u<<p)-1));}
string bits(int w,int n){string s(n,'0');for(int i=n-1;i>=0;--i){s[i]='0'+(w&1);w>>=1;}return s;}
void arrayjson(const vector<int>&v){cout<<"[";for(size_t i=0;i<v.size();++i){if(i)cout<<",";cout<<v[i];}cout<<"]";}
struct Packing{
 int n,N,M;vector<vector<uint16_t>>d,inc;vector<int>count,weight,position,code;
 vector<int64_t>score,weighted;int64_t energy=0,weightedEnergy=0;
 Packing(int nn):n(nn),N(1<<n),M(1<<(n-2)),d(N),inc(M),count(M,0),weight(M,1),position(N,-1),score(N,0),weighted(N,0){
  if(n<3||n>16)throw runtime_error("length");
  for(int w=0;w<N;++w){auto&v=d[w];for(int i=0;i<n;++i)for(int j=0;j<n-1;++j)v.push_back(dropbit(dropbit(w,i),j));
   sort(v.begin(),v.end());v.erase(unique(v.begin(),v.end()),v.end());for(int x:v)inc[x].push_back(w);}
 }
 void add(int w){
  if(w<0||w>=N||position[w]>=0)throw runtime_error("duplicate/outside word");
  energy+=score[w];weightedEnergy+=weighted[w];position[w]=code.size();code.push_back(w);
  for(int x:d[w]){++count[x];for(int v:inc[x]){++score[v];weighted[v]+=weight[x];}}
 }
 void remove(int w){
  if(position[w]<0)throw runtime_error("missing word");int p=position[w],last=code.back();code[p]=last;position[last]=p;code.pop_back();position[w]=-1;
  for(int x:d[w]){--count[x];energy-=count[x];weightedEnergy-=int64_t(count[x])*weight[x];for(int v:inc[x]){--score[v];weighted[v]-=weight[x];}}
 }
 void penalize(){
  for(int x=0;x<M;++x)if(count[x]>1&&weight[x]<1000){
   ++weight[x];weightedEnergy+=int64_t(count[x])*(count[x]-1)/2;
   for(int v:inc[x])weighted[v]+=count[x];
  }
 }
 void reset(const vector<int>&words,bool resetWeights=true){
  fill(count.begin(),count.end(),0);fill(position.begin(),position.end(),-1);fill(score.begin(),score.end(),0);fill(weighted.begin(),weighted.end(),0);
  if(resetWeights)fill(weight.begin(),weight.end(),1);energy=weightedEnergy=0;code.clear();for(int w:words)add(w);
 }
 void check(){
  vector<int>c(M,0);set<int>seen;
  for(int w:code){if(!seen.insert(w).second)throw runtime_error("state duplicate");for(int x:d[w])++c[x];}
  if(c!=count)throw runtime_error("occupancy drift");
  int64_t e=0,ew=0;for(int x=0;x<M;++x){e+=int64_t(c[x])*(c[x]-1)/2;ew+=int64_t(c[x])*(c[x]-1)/2*weight[x];}
  if(e!=energy||ew!=weightedEnergy)throw runtime_error("energy drift");
  for(int w=0;w<N;++w){int64_t s=0,sw=0;for(int x:d[w]){s+=c[x];sw+=int64_t(c[x])*weight[x];}
   if(s!=score[w]||sw!=weighted[w])throw runtime_error("incremental score drift");}
 }
};
vector<int> readwords(int n){vector<int>v;string s;set<int>seen;while(cin>>s){
 if(int(s.size())!=n||s.find_first_not_of("01")!=string::npos)throw runtime_error("invalid word");
 int w=stoi(s,nullptr,2);if(!seen.insert(w).second)throw runtime_error("duplicate");v.push_back(w);}return v;}
void checkpoint(const string&path,const Packing&s,const vector<int>&closest,int best,uint64_t iter,uint64_t seed,const string&mode){
 if(path.empty())return;ofstream f(path+".tmp");f<<"{\"state_kind\":\"possibly_infeasible_target_cardinality\",\"seed\":"<<seed<<",\"mode\":\""<<mode<<"\",\"iterations\":"<<iter<<",\"current_pair_energy\":"<<s.energy<<",\"minimum_pair_energy\":"<<best<<",\"current\":[";
 for(size_t i=0;i<s.code.size();++i){if(i)f<<",";f<<s.code[i];}f<<"],\"closest\":[";
 for(size_t i=0;i<closest.size();++i){if(i)f<<",";f<<closest[i];}f<<"]}\n";f.close();rename((path+".tmp").c_str(),path.c_str());
}
int main(int argc,char**argv){
 try{
  bool inspect=argc>1&&string(argv[1])=="--inspect";int n=inspect?stoi(argv[2]):16;Packing s(n);auto original=readwords(n);if(original.empty())throw runtime_error("empty input");
  uint64_t seed=inspect?stoull(argv[3]):stoull(argv[2]);mt19937_64 rng(seed);
  auto rnd=[&](int k){return int(rng()%uint64_t(k));};auto unit=[&](){return double(rng()>>11)*(1.0/9007199254740992.0);};
  for(int w:original)s.add(w);int initial=s.energy;
  if(inspect){
   int steps=stoi(argv[4]);if(int(s.code.size())>=s.N)throw runtime_error("inspect requires an excluded word");
   for(int t=0;t<steps;++t){int old=s.code[rnd(s.code.size())];s.remove(old);int w;do{w=rnd(s.N);}while(w==old||s.position[w]>=0);s.add(w);if(t%4==0)s.penalize();s.check();}
   cout<<"{\"initial_pair_energy\":"<<initial<<",\"final_pair_energy\":"<<s.energy<<",\"weighted_energy\":"<<s.weightedEnergy<<",\"state\":";arrayjson(s.code);
   cout<<",\"weights\":";arrayjson(s.weight);cout<<",\"incremental_check\":true}\n";return 0;
  }
  if(s.energy)throw runtime_error("baseline must be independently valid");double budget=stod(argv[1]);string mode=argc>3?argv[3]:"tabu",cp=argc>4?argv[4]:"";
  if(mode!="tabu"&&mode!="breakout"&&mode!="anneal"&&mode!="hybrid")throw runtime_error("mode");
  int extra=-1;int64_t minimum=INT64_MAX;uint64_t ties=0;
  for(int w=0;w<s.N;++w)if(s.position[w]<0){if(s.score[w]<minimum){minimum=s.score[w];extra=w;ties=1;}else if(s.score[w]==minimum&&rng()%++ties==0)extra=w;}
  s.add(extra);int target=s.code.size(),bestEnergy=s.energy;vector<int>closest=s.code;vector<vector<int>>archive{closest};vector<uint64_t>tabu(s.N,0);
  uint64_t steps=0,penalties=0,restarts=0,checks=0;double start=cpu(),lastGain=0,lastCheckpoint=0,lastRestart=0;vector<pair<double,int>>progress{{0,bestEnergy}};
  auto wall=chrono::steady_clock::now();checkpoint(cp,s,closest,bestEnergy,steps,seed,mode);
  while(s.energy>0&&cpu()-start<budget&&chrono::duration<double>(chrono::steady_clock::now()-wall).count()<budget*1.8+20){
   double stale=cpu()-start-lastGain;int old=-1;int64_t worst=-1;int sampled=rnd(100);
   if(sampled<8)old=s.code[rnd(s.code.size())];
   else{
    vector<int>conflicted;
    for(int w:s.code)if(s.score[w]>int64_t(s.d[w].size())){
     conflicted.push_back(w);int64_t value=0;for(int d:s.d[w])value+=int64_t(s.count[d]-1)*s.weight[d];
     if(value>worst){worst=value;old=w;}else if(value==worst&&rnd(2))old=w;
    }
    if(conflicted.empty())throw runtime_error("positive energy but no conflict");
    if(sampled>=65)old=conflicted[rnd(conflicted.size())];
   }
   s.remove(old);int chosen=-1;int64_t value=INT64_MAX;uint64_t equal=0;
   double noise=(mode=="anneal"||mode=="hybrid")?min(8.,.25+stale/2):0;
   for(int w=0;w<s.N;++w)if(w!=old&&s.position[w]<0){
    if(tabu[w]>steps&&s.energy+s.score[w]>=bestEnergy)continue;
    int64_t cost=s.weighted[w];
    if(noise>0)cost=cost*1024+int64_t(unit()*noise*1024);
    if(cost<value){value=cost;chosen=w;equal=1;}
    else if(cost==value&&rng()%++equal==0)chosen=w;
   }
   if(chosen<0){chosen=old;}s.add(chosen);++steps;tabu[old]=steps+7+rnd(20)+uint64_t(min(100.,stale*2));
   if(s.energy<bestEnergy){bestEnergy=s.energy;closest=s.code;lastGain=cpu()-start;progress.push_back({lastGain,bestEnergy});checkpoint(cp,s,closest,bestEnergy,steps,seed,mode);}
   if((mode=="breakout"||mode=="hybrid")&&steps%257==0){s.penalize();++penalties;}
   if(steps%2048==0){s.check();++checks;}
   if(steps%4096==0&&s.energy<=bestEnergy+3){archive.push_back(s.code);if(archive.size()>24)archive.erase(archive.begin()+1);}
   if(stale>4&&cpu()-start-lastRestart>5){
    auto restart=mode=="tabu"?closest:archive[rnd(archive.size())];s.reset(restart);fill(tabu.begin(),tabu.end(),0);
    int destroy=2+rnd(mode=="hybrid"?17:6);
    for(int i=0;i<destroy;++i){int a=s.code[rnd(s.code.size())];s.remove(a);int b;do{b=rnd(s.N);}while(s.position[b]>=0);s.add(b);}
    ++restarts;lastRestart=cpu()-start;
   }
   if(cpu()-start-lastCheckpoint>5){checkpoint(cp,s,closest,bestEnergy,steps,seed,mode);lastCheckpoint=cpu()-start;}
  }
  if(s.energy==0){bestEnergy=0;closest=s.code;}s.check();checkpoint(cp,s,closest,bestEnergy,steps,seed,mode);
  cout<<"{\"mode\":\""<<mode<<"\",\"seed\":"<<seed<<",\"target_cardinality\":"<<target<<",\"proposed_zero_conflict\":"<<(bestEnergy==0?"true":"false")
   <<",\"minimum_pair_energy\":"<<bestEnergy<<",\"initial_pair_energy\":"<<initial+minimum<<",\"search_cpu_seconds\":"<<cpu()-start
   <<",\"wall_seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-wall).count()<<",\"iterations\":"<<steps<<",\"penalty_updates\":"<<penalties<<",\"restarts\":"<<restarts
   <<",\"incremental_checks\":"<<checks<<",\"closest_state\":";arrayjson(closest);cout<<",\"baseline_valid_words\":";arrayjson(original);cout<<",\"energy_progress\":[";
  for(size_t i=0;i<progress.size();++i){if(i)cout<<",";cout<<"["<<progress[i].first<<","<<progress[i].second<<"]";}cout<<"],\"warning\":\"Closest state is not an accepted code unless independently verified; energy improvements alone are not cardinality gains.\"}\n";
  return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}
}
