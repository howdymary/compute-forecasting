// Distinct conflicting-codeword-pair objective, independent of descendant multiplicity.
// Lazy bounded sparse conflict cache; no dense conflict graph. Positive objective INVALID.
#define main codegarden_original_main
#include "../kernel.cpp"
#undef main
#include <ctime>
#include <deque>
#include <set>
double cpuclock(){return double(clock())/CLOCKS_PER_SEC;}
struct PairPacking{
 Garden&g;vector<int>field,selected,C,stamp;int tag=0;long long energy=0,builds=0,hits=0,nnz=0,peak=0;vector<vector<uint16_t>>cache;vector<bool>cached;deque<int>fifo;
 PairPacking(Garden&x):g(x),field(N),selected(N),stamp(N),cache(N),cached(N){}
 const vector<uint16_t>&adj(int w){
  if(cached[w]){++hits;return cache[w];}
  if(fifo.size()>=512){int old=fifo.front();fifo.pop_front();nnz-=cache[old].size();vector<uint16_t>().swap(cache[old]);cached[old]=false;}
  ++tag;auto&v=cache[w];for(int d:g.desc[w])for(int u:g.inc[d])if(u!=w&&stamp[u]!=tag){stamp[u]=tag;v.push_back(u);}cached[w]=true;fifo.push_back(w);++builds;nnz+=v.size();peak=max(peak,nnz);return v;
 }
 void add(int w){if(selected[w])throw runtime_error("duplicate");energy+=field[w];selected[w]=1;C.push_back(w);for(int u:adj(w))++field[u];}
 void remove(int w){if(!selected[w])throw runtime_error("missing");energy-=field[w];selected[w]=0;C.erase(find(C.begin(),C.end(),w));for(int u:adj(w))--field[u];}
 long long descendantEnergy(const vector<int>&a){vector<int>occ(M);long long e=0;for(int w:a)for(int d:g.desc[w])e+=occ[d]++;return e;}
 void check(){vector<int>expected(N);long long e=0;for(int w:C)for(int u:adj(w))++expected[u];for(int w:C)e+=expected[w];if(expected!=field||e!=energy*2)throw runtime_error("pair incremental mismatch");}
};

#ifndef CODEGARDEN_PAIR_NO_MAIN
int main(int argc,char**argv){
 try{
  if(argc<5)throw runtime_error("seconds seed mode checkpoint");double budget=stod(argv[1]);uint64_t seed=stoull(argv[2]);string mode=argv[3],path=argv[4];Garden g(seed);PairPacking p(g);string s;while(cin>>s){if(s.size()!=16||s.find_first_not_of("01")!=string::npos)throw runtime_error("word");int w=stoi(s,nullptr,2);p.add(w);}if(p.energy||p.C.empty())throw runtime_error("invalid initial code");mt19937_64 rng(seed);
  while(p.C.size()<227){int best=-1,cost=100000,t=0;for(int w=0;w<N;++w)if(!p.selected[w]){if(p.field[w]<cost){cost=p.field[w];best=w;t=1;}else if(p.field[w]==cost&&rng()%++t==0)best=w;}p.add(best);}
  set<vector<int>>known226;vector<vector<int>>novel226;
  if(argc>5){ifstream known(argv[5]);int count,w;while(known>>count){if(count!=226)throw runtime_error("known code length");vector<int>v;for(int i=0;i<count;++i){if(!(known>>w)||w<0||w>=N)throw runtime_error("known code input");v.push_back(w);}sort(v.begin(),v.end());known226.insert(v);}}
  auto inspect226=[&](){if(p.energy!=1)return;for(int removed:p.C)if(p.field[removed]){vector<int>C;for(int w:p.C)if(w!=removed)C.push_back(w);sort(C.begin(),C.end());if(!known226.count(C)){if(p.descendantEnergy(C))throw runtime_error("pair projection not valid");novel226.push_back(C);return;}}};
  inspect226();
  vector<int>best=p.C,tabu(N),penalty(N);long long bestE=p.energy,iterations=0,stale=0,updates=0;vector<vector<int>>archive{best};unordered_set<uint64_t>seen;double start=cpuclock(),lastsave=start;bool adaptive=mode=="adaptive";
  while(cpuclock()-start<budget&&bestE&&novel226.empty()){
   ++iterations;++stale;vector<int>bad;for(int w:p.C)if(p.field[w])bad.push_back(w);if(bad.empty())throw runtime_error("no conflicts");int remove=bad[rng()%bad.size()];p.remove(remove);tabu[remove]=int(iterations)+7+rng()%24;int pick=-1,score=100000,ties=0;
   int scale=adaptive?4:1;
   for(int w=0;w<N;++w){if(p.selected[w]||(tabu[w]>iterations&&p.field[w]!=0))continue;int q=scale*p.field[w]+(adaptive?penalty[w]:0);if(q<score){score=q;pick=w;ties=1;}else if(q==score&&rng()%++ties==0)pick=w;}
   if(pick<0)throw runtime_error("empty candidate");p.add(pick);inspect226();
   if(p.energy<bestE){bestE=p.energy;best=p.C;stale=0;archive.clear();seen.clear();checkpoint(path,best);}
   if(p.energy<=bestE+1&&iterations%128==0&&seen.insert(g.fingerprint(p.C)).second){archive.push_back(p.C);if(archive.size()>32)archive.erase(archive.begin());}
   if(adaptive&&stale>128&&iterations%128==0){for(int w:p.C)if(penalty[w]<64){++penalty[w];++updates;}}
   if(iterations%4096==0)for(int&w:penalty)w/=2;
   if(stale>=8192&&stale%4096==0){auto old=p.C;for(int w:old)p.remove(w);auto keep=best;shuffle(keep.begin(),keep.end(),rng);int ruin=min(100,16+int(stale/8192)*8);for(int i=ruin;i<int(keep.size());++i)p.add(keep[i]);while(p.C.size()<227){int w;do{w=rng()%N;}while(p.selected[w]);p.add(w);}fill(tabu.begin(),tabu.end(),0);}
   if(iterations%8192==0)p.check();if(cpuclock()-lastsave>10){checkpoint(path,best);lastsave=cpuclock();}
  }
  p.check();checkpoint(path,best);archive.push_back(best);cout<<"{\"mode\":\""<<mode<<"\",\"seed\":"<<seed<<",\"cpu_seconds\":"<<cpuclock()-start<<",\"iterations\":"<<iterations<<",\"minimum_pair_conflicts\":"<<bestE<<",\"raw_energy_at_best_pair_state\":"<<p.descendantEnergy(best)<<",\"penalty_updates\":"<<updates<<",\"adjacency_builds\":"<<p.builds<<",\"cache_hits\":"<<p.hits<<",\"peak_cached_edges\":"<<p.peak<<",\"cache_limit\":512,\"best\":";outputArray(best);cout<<",\"archive\":[";
  for(size_t i=0;i<archive.size();++i){if(i)cout<<",";cout<<"{\"words\":";outputArray(archive[i]);cout<<",\"raw_energy\":"<<p.descendantEnergy(archive[i])<<"}";}cout<<"],\"novel226_candidates\":[";for(size_t i=0;i<novel226.size();++i){if(i)cout<<",";outputArray(novel226[i]);}cout<<"],\"stopped_on_novel226_candidate\":"<<(!novel226.empty()?"true":"false")<<"}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}
}

#endif
