// CodeGarden fixed-cardinality breakout tabu search. Positive energy is INVALID.
#include <algorithm>
#include <cmath>
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
double nowcpu(){return double(clock())/CLOCKS_PER_SEC;}
unsigned del(unsigned x,int p){return ((x>>(p+1))<<p)|(x&((1u<<p)-1));}
void arrayout(const vector<int>&a){cout<<"[";for(size_t i=0;i<a.size();++i){if(i)cout<<",";cout<<a[i];}cout<<"]";}
struct SoftPacking{
 int n,N,M;vector<vector<int>> ds,inv;vector<int>occ,weight,field,selfweight,selected,C;long long energy=0,weighted=0;
 SoftPacking(int length):n(length),N(1<<n),M(1<<(n-2)),ds(N),inv(M),occ(M),weight(M,1),field(N),selfweight(N),selected(N){
  for(int w=0;w<N;++w){auto &v=ds[w];for(int p=0;p<n;++p)for(int q=0;q<n-1;++q)v.push_back(del(del(w,p),q));sort(v.begin(),v.end());v.erase(unique(v.begin(),v.end()),v.end());selfweight[w]=v.size();for(int d:v)inv[d].push_back(w);}
 }
 void add(int w){if(w<0||w>=N||selected[w])throw runtime_error("duplicate/bad insertion");selected[w]=1;C.push_back(w);for(int d:ds[w]){energy+=occ[d];weighted+=1ll*weight[d]*occ[d];++occ[d];for(int v:inv[d])field[v]+=weight[d];}}
 void remove(int w){if(!selected[w])throw runtime_error("missing removal");selected[w]=0;C.erase(find(C.begin(),C.end(),w));for(int d:ds[w]){--occ[d];energy-=occ[d];weighted-=1ll*weight[d]*occ[d];for(int v:inv[d])field[v]-=weight[d];}}
 void penalty(int d,int change){if(weight[d]+change<1)throw runtime_error("bad penalty");weight[d]+=change;weighted+=1ll*change*occ[d]*(occ[d]-1)/2;for(int v:inv[d]){field[v]+=change*occ[d];selfweight[v]+=change;}}
 int rawcost(int w){int cost=0;for(int d:ds[w])cost+=occ[d];return cost;}
 void resetweights(){for(int d=0;d<M;++d)if(weight[d]>1)penalty(d,1-weight[d]);}
 void check(){
  vector<int>count(M);long long raw=0,wt=0;for(int w:C){if(!selected[w])throw runtime_error("selection");for(int d:ds[w])++count[d];}
  if(count!=occ)throw runtime_error("occupancy");
  for(int d=0;d<M;++d){raw+=1ll*occ[d]*(occ[d]-1)/2;wt+=1ll*weight[d]*occ[d]*(occ[d]-1)/2;}
  if(raw!=energy||wt!=weighted)throw runtime_error("energy");
  for(int w=0;w<N;++w){int a=0,b=0;for(int d:ds[w]){a+=weight[d]*occ[d];b+=weight[d];}if(a!=field[w]||b!=selfweight[w])throw runtime_error("incremental field");}
 }
};
void save(const string&path,const vector<int>&C){if(path.empty())return;ofstream f(path);auto v=C;sort(v.begin(),v.end());for(int w:v){for(int p=15;p>=0;--p)f<<((w>>p)&1);f<<"\n";}}
int main(int argc,char**argv){
 try{
  if(argc>1&&string(argv[1])=="--trace"){
   int n=stoi(argv[2]),steps=stoi(argv[3]);mt19937_64 rng(stoull(argv[4]));SoftPacking g(n);int w;while(cin>>w)g.add(w);cout<<"[";
   for(int s=0;s<steps;++s){int old=g.C[rng()%g.C.size()];g.remove(old);int added;do{added=rng()%g.N;}while(g.selected[added]);g.add(added);if(s%3==0)g.penalty(rng()%g.M,1);if(s%17==16)g.resetweights();g.check();if(s)cout<<",";cout<<"{\"words\":";arrayout(g.C);cout<<",\"weights\":";arrayout(g.weight);cout<<",\"field\":";arrayout(g.field);cout<<",\"selfweight\":";arrayout(g.selfweight);cout<<",\"energy\":"<<g.energy<<",\"weighted_energy\":"<<g.weighted<<"}";}
   cout<<"]\n";return 0;
  }
  if(argc<6)throw runtime_error("seconds seed mode checkpoint quota");double budget=stod(argv[1]);uint64_t seed=stoull(argv[2]);string mode=argv[3],path=argv[4];int quota=stoi(argv[5]);mt19937_64 rng(seed);SoftPacking g(16);string bits;vector<int>initial;while(cin>>bits){if(bits.size()!=16||bits.find_first_not_of("01")!=string::npos)throw runtime_error("bad input");int w=stoi(bits,nullptr,2);g.add(w);initial.push_back(w);}if(g.energy||g.C.empty())throw runtime_error("invalid start");
  vector<int>iscore(g.N);if(argc>6){ifstream core(argv[6]);int w;while(core>>w){if(w<0||w>=g.N)throw runtime_error("bad core");iscore[w]=1;}}
  auto corecount=[&](){int c=0;for(int w:g.C)c+=iscore[w];return c;};
  // A quota is an explicit experimental restriction, not a validity criterion.
  while(corecount()>quota){for(int w:g.C)if(iscore[w]){g.remove(w);break;}}
  while(g.C.size()<227){int w=rng()%g.N;if(!g.selected[w]&&(!iscore[w]||corecount()<quota))g.add(w);}
  vector<int>tabu(g.N);long long iterations=0,stale=0,bestE=g.energy,penalties=0,restarts=0;vector<int>best=g.C;vector<vector<int>>archive{best};set<vector<int>>seen;vector<int>archE{int(bestE)};double start=nowcpu(),lastsave=start;bool adaptive=mode=="adaptive";
  while(nowcpu()-start<budget&&bestE>0){
   ++iterations;++stale;vector<int>violated;int maxloss=-1,remove=-1,ties=0;
   for(int w:g.C)if(g.field[w]>g.selfweight[w]){violated.push_back(w);int loss=g.field[w]-g.selfweight[w];if(loss>maxloss){maxloss=loss;remove=w;ties=1;}else if(loss==maxloss&&rng()%++ties==0)remove=w;}
   if(violated.empty())throw runtime_error("positive energy without conflicts");if(rng()%5)remove=violated[rng()%violated.size()];
   g.remove(remove);tabu[remove]=int(iterations)+7+int(rng()%24);int cc=corecount(),chosen=-1,mincost=2147483647,count=0;
   for(int w=0;w<g.N;++w){if(g.selected[w]||(iscore[w]&&cc>=quota))continue;if(tabu[w]>iterations&&g.field[w]!=0)continue;int cost=g.field[w];if(cost<mincost){mincost=cost;chosen=w;count=1;}else if(cost==mincost&&rng()%++count==0)chosen=w;}
   if(chosen<0)throw runtime_error("no insertion");g.add(chosen);
   if(g.energy<bestE){bestE=g.energy;best=g.C;stale=0;archive.clear();archE.clear();seen.clear();save(path,best);}
   if(g.energy<=bestE+2&&iterations%64==0){auto C=g.C;sort(C.begin(),C.end());if(seen.insert(C).second){archive.push_back(C);archE.push_back(g.energy);if(archive.size()>32){archive.erase(archive.begin());archE.erase(archE.begin());}}}
   if(adaptive&&stale>256&&iterations%64==0){for(int d=0;d<g.M;++d)if(g.occ[d]>1&&g.weight[d]<100){g.penalty(d,1);++penalties;}}
   if(iterations%8192==0)g.resetweights();
   if(stale>=4096&&stale%2048==0){++restarts;auto old=g.C;for(int w:old)g.remove(w);auto restart=best;shuffle(restart.begin(),restart.end(),rng);int ruin=min(80,8+int(stale/4096)*8);for(int i=ruin;i<int(restart.size());++i)g.add(restart[i]);while(g.C.size()<227){int cc2=corecount(),choice=-1,score=2147483647,t=0;for(int w=0;w<g.N;++w)if(!g.selected[w]&&(!iscore[w]||cc2<quota)){int c=g.field[w]+int(rng()%8);if(c<score){score=c;choice=w;t=1;}else if(c==score&&rng()%++t==0)choice=w;}if(choice<0)throw runtime_error("restart insertion");g.add(choice);}fill(tabu.begin(),tabu.end(),0);}
   if(iterations%4096==0)g.check();if(nowcpu()-lastsave>=10){save(path,best);lastsave=nowcpu();}
  }
  g.check();save(path,best);auto sorted=best;sort(sorted.begin(),sorted.end());if(seen.insert(sorted).second){archive.push_back(sorted);archE.push_back(bestE);}
  cout<<"{\"mode\":\""<<mode<<"\",\"seed\":"<<seed<<",\"cpu_seconds\":"<<nowcpu()-start<<",\"iterations\":"<<iterations<<",\"minimum_raw_energy\":"<<bestE<<",\"penalty_updates\":"<<penalties<<",\"restarts\":"<<restarts<<",\"quota\":"<<quota<<",\"best\":";arrayout(best);cout<<",\"archive\":[";
  for(size_t i=0;i<archive.size();++i){if(i)cout<<",";cout<<"{\"words\":";arrayout(archive[i]);cout<<",\"raw_energy\":"<<archE[i]<<"}";}cout<<"]}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}
}
