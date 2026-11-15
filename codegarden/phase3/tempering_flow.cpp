// Fixed-cardinality symmetric-proposal Metropolis and replica exchange.
// Energies are diagnostics; only external protected verification accepts codes.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <fstream>
#include <iostream>
#include <memory>
#include <random>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
double cpu(){return double(clock())/CLOCKS_PER_SEC;}
unsigned drop(unsigned x,int p){return ((x>>(p+1))<<p)|(x&((1u<<p)-1));}
void arr(const vector<int>&v){cout<<"[";for(size_t i=0;i<v.size();++i){if(i)cout<<",";cout<<v[i];}cout<<"]";}
struct Geometry{
 int n,N,M;vector<vector<uint16_t>>d,inc;
 Geometry(int nn):n(nn),N(1<<nn),M(1<<(nn-2)),d(N),inc(M){
 for(int w=0;w<N;++w){for(int i=0;i<n;++i)for(int j=0;j<n-1;++j)d[w].push_back(drop(drop(w,i),j));sort(d[w].begin(),d[w].end());d[w].erase(unique(d[w].begin(),d[w].end()),d[w].end());for(int a:d[w])inc[a].push_back(w);}}
 int overlap(int a,int b)const{auto&x=d[a];auto&y=d[b];int i=0,j=0,c=0;while(i<int(x.size())&&j<int(y.size())){if(x[i]==y[j]){++c;++i;++j;}else if(x[i]<y[j])++i;else++j;}return c;}
};
struct State{
 const Geometry&g;vector<int>count,score,pos,code;int energy=0,id=-1;
 State(const Geometry&gg):g(gg),count(g.M,0),score(g.N,0),pos(g.N,-1){}
 void add(int w){if(pos[w]>=0)throw runtime_error("duplicate");energy+=score[w];pos[w]=code.size();code.push_back(w);for(int d:g.d[w]){++count[d];for(int v:g.inc[d])++score[v];}}
 void remove(int w){int p=pos[w];if(p<0)throw runtime_error("missing");int last=code.back();code[p]=last;pos[last]=p;code.pop_back();pos[w]=-1;for(int d:g.d[w]){--count[d];energy-=count[d];for(int v:g.inc[d])--score[v];}}
 int delta(int old,int w)const{return score[w]-g.overlap(old,w)-(score[old]-int(g.d[old].size()));}
 void check()const{vector<int>c(g.M,0);set<int>seen;for(int w:code){if(!seen.insert(w).second)throw runtime_error("duplicate state");for(int d:g.d[w])++c[d];}
  if(c!=count)throw runtime_error("counts");int E=0;for(int v:c)E+=v*(v-1)/2;if(E!=energy)throw runtime_error("energy");
  for(int w=0;w<g.N;++w){int sc=0;for(int d:g.d[w])sc+=c[d];if(sc!=score[w])throw runtime_error("scores");}}
};
vector<int> read(int n){vector<int>C;set<int>seen;string w;while(cin>>w){if(int(w.size())!=n||w.find_first_not_of("01")!=string::npos)throw runtime_error("word");int v=stoi(w,nullptr,2);if(!seen.insert(v).second)throw runtime_error("duplicate");C.push_back(v);}if(C.empty())throw runtime_error("empty");return C;}
int main(int argc,char**argv){try{
 bool inspect=argc>1&&string(argv[1])=="--inspect";int n=inspect?stoi(argv[2]):16;Geometry g(n);auto original=read(n);
 uint64_t seed=stoull(argv[2+(inspect?1:0)]);mt19937_64 rng(seed);auto rnd=[&](int k){return int(rng()%k);};auto u=[&](){return (double(rng()>>11)+.5)/9007199254740992.;};
 if(inspect){State s(g);for(int w:original)s.add(w);int initial=s.energy;for(int t=0;t<stoi(argv[4]);++t){int old=s.code[rnd(s.code.size())],w;do{w=rnd(g.N);}while(w==old||s.pos[w]>=0);int delta=s.delta(old,w),before=s.energy;s.remove(old);s.add(w);if(s.energy-before!=delta)throw runtime_error("delta");s.check();}
 cout<<"{\"initial_pair_energy\":"<<initial<<",\"final_pair_energy\":"<<s.energy<<",\"weighted_energy\":"<<s.energy<<",\"state\":";arr(s.code);cout<<",\"weights\":[";for(int i=0;i<g.M;++i){if(i)cout<<",";cout<<1;}cout<<"],\"incremental_check\":true}\n";return 0;}
 double budget=stod(argv[1]);string mode=argv[3],cp=argv[4];if(mode!="dense"&&mode!="flow_quench")throw runtime_error("mode");int R=32,target=227;
 vector<unique_ptr<State>>states;vector<double>temperatures(R);for(int i=0;i<R;++i)temperatures[i]=.08*pow(12.5,double(i)/(R-1));
 vector<int>labels(R,-1),crossings(R,0);vector<double>coldVisits(R,0),hotVisits(R,0);vector<vector<double>>ladderHistory,quenchHistory;uint64_t quenches=0;vector<uint64_t>accepted(R,0),attempted(R,0),swapTried(max(0,R-1),0),swapAccepted(max(0,R-1),0);
 for(int r=0;r<R;++r){auto s=make_unique<State>(g);s->id=r;for(int w:original)s->add(w);if(s->energy)throw runtime_error("invalid baseline");
  while(int(s->code.size())<target){int best=-1,cost=100000,ties=0;for(int w=0;w<g.N;++w)if(s->pos[w]<0){if(s->score[w]<cost){best=w;cost=s->score[w];ties=1;}else if(s->score[w]==cost&&rnd(++ties)==0)best=w;}s->add(best);}states.push_back(move(s));}
 int bestE=states[0]->energy;vector<int>closest=states[0]->code;vector<vector<int>>near;set<vector<int>>nearKeys;vector<vector<double>>progress;vector<int>initialE;for(auto&s:states)initialE.push_back(s->energy);
 double start=cpu(),lastReport=0,lastFeedback=0;auto wall=chrono::steady_clock::now();uint64_t steps=0,exchanges=0;bool winner=false;
 auto save=[&](){ofstream out(cp+".tmp");out<<"{\"state_kind\":\"possibly_infeasible\",\"minimum_pair_energy\":"<<bestE<<",\"closest\":[";for(size_t i=0;i<closest.size();++i){if(i)out<<",";out<<closest[i];}out<<"],\"iterations\":"<<steps<<"}\n";out.close();rename((cp+".tmp").c_str(),cp.c_str());};
 while(cpu()-start<budget&&chrono::duration<double>(chrono::steady_clock::now()-wall).count()<budget*1.8+15){
  int r=steps%R;State&s=*states[r];++attempted[r];int old=s.code[rnd(s.code.size())],mask;int kind=rnd(10);
  if(kind<2)mask=1+rnd(g.N-1);else if(kind<7)mask=1<<rnd(n);else{int i=rnd(n),j=rnd(n-1);if(j>=i)++j;mask=(1<<i)|(1<<j);}int w=old^mask;
  double T=R==1?.06+3.94*(1.-fmod((cpu()-start),30.)/30.):temperatures[r];
  if(s.pos[w]<0){int delta=s.delta(old,w);if(delta<=0||log(u())<-double(delta)/T){int before=s.energy;s.remove(old);s.add(w);if(s.energy-before!=delta)throw runtime_error("delta drift");++accepted[r];}}
  if(s.energy<=bestE){if(s.energy<bestE){bestE=s.energy;closest=s.code;near.clear();nearKeys.clear();save();}
   if(steps%16==0||s.energy==0){auto v=s.code;sort(v.begin(),v.end());if(nearKeys.insert(v).second){if(near.size()<64)near.push_back(v);else near[rnd(64)]=v;closest=v;}}}
  if(s.energy==0){winner=true;closest=s.code;break;}
  ++steps;
  if(R>1&&steps%4096==0){int parity=exchanges++%2;for(int i=parity;i<R-1;i+=2){++swapTried[i];double logRatio=(1./temperatures[i]-1./temperatures[i+1])*(states[i]->energy-states[i+1]->energy);
   if(log(u())<min(0.,logRatio)){swap(states[i],states[i+1]);++swapAccepted[i];}}
   for(int i=0;i<R;++i){int id=states[i]->id;
    if(i==0||i==R-1){int endpoint=i==0?0:1;if(labels[id]>=0&&labels[id]!=endpoint)++crossings[id];labels[id]=endpoint;}
    if(labels[id]==0)++coldVisits[i];else if(labels[id]==1)++hotVisits[i];
   }
  }
  if(steps%1048576==0){for(auto&s:states)s->check();}
  if(mode=="flow_quench"&&cpu()-start-lastFeedback>5){
   lastFeedback=cpu()-start;vector<double>fraction(R),mass(R-1),nextT(R);fraction[0]=1;fraction[R-1]=0;
   for(int i=1;i<R-1;++i)fraction[i]=(coldVisits[i]+2.*(1.-double(i)/(R-1)))/(coldVisits[i]+hotVisits[i]+2.);
   for(int i=1;i<R-1;++i)fraction[i]=min(fraction[i],fraction[i-1]);
   double total=0;for(int i=0;i<R-1;++i){mass[i]=sqrt(max(1.e-5,fraction[i]-fraction[i+1]));total+=mass[i];}
   nextT[0]=temperatures[0];nextT[R-1]=temperatures[R-1];
   for(int j=1;j<R-1;++j){double targetMass=total*j/(R-1),running=0;int i=0;while(i<R-2&&running+mass[i]<targetMass){running+=mass[i];++i;}
    double proposed=temperatures[i]+(temperatures[i+1]-temperatures[i])*(targetMass-running)/mass[i];nextT[j]=.5*temperatures[j]+.5*proposed;}
   temperatures=nextT;vector<double>ladder{lastFeedback};ladder.insert(ladder.end(),temperatures.begin(),temperatures.end());ladderHistory.push_back(ladder);
   fill(coldVisits.begin(),coldVisits.end(),0);fill(hotVisits.begin(),hotVisits.end(),0);
   int hot=R/4+rnd(3*R/4);auto q=make_unique<State>(g);q->id=states[0]->id;for(int w:states[hot]->code)q->add(w);int before=q->energy,stale=0;
   for(int step=0;step<256&&q->energy>0&&stale<48;++step){
    vector<int>bad;for(int w:q->code)if(q->score[w]>int(g.d[w].size()))bad.push_back(w);if(bad.empty())throw runtime_error("quench conflict");
    int old=bad[rnd(bad.size())],E=q->energy;q->remove(old);int best=-1,cost=100000,ties=0;
    for(int w=0;w<g.N;++w)if(q->pos[w]<0){if(q->score[w]<cost){cost=q->score[w];best=w;ties=1;}else if(q->score[w]==cost&&rnd(++ties)==0)best=w;}
    q->add(best);stale=q->energy<E?0:stale+1;
   }
   ++quenches;q->check();quenchHistory.push_back({lastFeedback,double(hot),double(before),double(q->energy)});
   if(q->energy<=bestE){if(q->energy<bestE){bestE=q->energy;near.clear();nearKeys.clear();}auto v=q->code;sort(v.begin(),v.end());closest=v;
    if(nearKeys.insert(v).second){if(near.size()<64)near.push_back(v);else near[rnd(64)]=v;}}
   if(q->energy==0){winner=true;closest=q->code;break;}
   // This injection and the quench make the feedback condition an optimization
   // heuristic, not an equilibrium-sampling reproduction of the cited paper.
   if(q->energy<=states[0]->energy)states[0]=move(q);
  }
  if(cpu()-start-lastReport>5){lastReport=cpu()-start;vector<double>row{lastReport,double(bestE)};for(auto&s:states)row.push_back(s->energy);progress.push_back(row);save();}
 }
 for(auto&s:states)s->check();save();
 cout<<"{\"mode\":\""<<mode<<"\",\"seed\":"<<seed<<",\"target_cardinality\":"<<target<<",\"proposed_zero_conflict\":"<<(winner?"true":"false")<<",\"minimum_pair_energy\":"<<bestE<<",\"search_cpu_seconds\":"<<cpu()-start
 <<",\"wall_seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-wall).count()<<",\"iterations\":"<<steps<<",\"closest_state\":";arr(closest);cout<<",\"initial_energies\":";arr(initialE);cout<<",\"accepted\":[";for(int i=0;i<R;++i){if(i)cout<<",";cout<<accepted[i];}cout<<"],\"attempted\":[";for(int i=0;i<R;++i){if(i)cout<<",";cout<<attempted[i];}cout<<"],\"swap_attempted\":[";for(int i=0;i<R-1;++i){if(i)cout<<",";cout<<swapTried[i];}cout<<"],\"swap_accepted\":[";for(int i=0;i<R-1;++i){if(i)cout<<",";cout<<swapAccepted[i];}cout<<"],\"near_states\":[";for(size_t i=0;i<near.size();++i){if(i)cout<<",";arr(near[i]);}cout<<"],\"energy_by_temperature\":[";for(size_t i=0;i<progress.size();++i){if(i)cout<<",";cout<<"[";for(size_t j=0;j<progress[i].size();++j){if(j)cout<<",";cout<<progress[i][j];}cout<<"]";}cout<<"],\"final_temperatures\":[";for(int i=0;i<R;++i){if(i)cout<<",";cout<<temperatures[i];}
 cout<<"],\"round_trips_by_replica\":";vector<int>roundtrips;for(int x:crossings)roundtrips.push_back(x/2);arr(roundtrips);
 cout<<",\"quench_count\":"<<quenches<<",\"quench_history\":[";for(size_t i=0;i<quenchHistory.size();++i){if(i)cout<<",";cout<<"[";for(size_t j=0;j<quenchHistory[i].size();++j){if(j)cout<<",";cout<<quenchHistory[i][j];}cout<<"]";}
 cout<<"],\"ladder_history\":[";for(size_t i=0;i<ladderHistory.size();++i){if(i)cout<<",";cout<<"[";for(size_t j=0;j<ladderHistory[i].size();++j){if(j)cout<<",";cout<<ladderHistory[i][j];}cout<<"]";}cout<<"],\"warning\":\"Positive energy target states are invalid; symmetric proposals and temperature swaps are search mechanisms, not a success certificate.\"}\n";
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}return 0;}
