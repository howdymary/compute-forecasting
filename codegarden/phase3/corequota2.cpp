// Distinct conflicting-codeword-pair objective, independent of descendant multiplicity.
// Lazy bounded sparse conflict cache; no dense conflict graph. Positive objective INVALID.
#define main codegarden_original_main
#include "../kernel.cpp"
#undef main
#include <ctime>
#include <deque>
#include <array>
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



vector<vector<int>> hubProjections(PairPacking&p,const set<vector<int>>&known){
 vector<vector<int>>out;if(p.C.size()!=227||p.energy<=0)return out;
 for(int removed:p.C)if(p.field[removed]==p.energy){vector<int>C;for(int w:p.C)if(w!=removed)C.push_back(w);sort(C.begin(),C.end());if(!known.count(C)){if(p.descendantEnergy(C))throw runtime_error("hub projection invalid");out.push_back(C);}}
 return out;
}
int main(int argc,char**argv){try{
 if(argc==2&&string(argv[1])=="--hub-test"){Garden g(1430001);PairPacking p(g);int w;while(cin>>w)p.add(w);p.check();set<vector<int>>known;auto v=hubProjections(p,known);cout<<"{\"pair_conflicts\":"<<p.energy<<",\"projections\":[";for(size_t i=0;i<v.size();++i){if(i)cout<<",";outputArray(v[i]);}cout<<"]}\n";return 0;}

 if(argc<9)throw runtime_error("seconds seed mode checkpoint corefile quota target knownfile");double budget=stod(argv[1]);uint64_t seed=stoull(argv[2]);bool adaptive=string(argv[3])=="adaptive";string path=argv[4];int quota=stoi(argv[6]),target=stoi(argv[7]);if(quota<190||quota>210||(target!=226&&target!=227))throw runtime_error("quota or target");
 Garden g(seed);PairPacking p(g);mt19937_64 rng(seed);vector<unsigned char>member(N);array<int,4>counts{};ifstream file(argv[5]);for(int k=0;k<4;++k){int n,w;if(!(file>>n)||n!=216)throw runtime_error("core input");for(int j=0;j<n;++j){if(!(file>>w)||w<0||w>=N||(member[w]&(1u<<k)))throw runtime_error("core word");member[w]|=1u<<k;}}
 auto add=[&](int w){p.add(w);for(int k=0;k<4;++k)if(member[w]&(1u<<k))++counts[k];};
 auto remove=[&](int w){p.remove(w);for(int k=0;k<4;++k)if(member[w]&(1u<<k))--counts[k];};
 auto allowed=[&](int w){for(int k=0;k<4;++k)if((member[w]&(1u<<k))&&counts[k]>=quota)return false;return true;};
 auto check=[&](){p.check();array<int,4>a{};for(int w:p.C)for(int k=0;k<4;++k)if(member[w]&(1u<<k))++a[k];if(a!=counts)throw runtime_error("quota field mismatch");for(int k=0;k<4;++k)if(counts[k]>quota)throw runtime_error("quota violated");};
 string s;while(cin>>s){if(s.size()!=16||s.find_first_not_of("01")!=string::npos)throw runtime_error("word");add(stoi(s,nullptr,2));}if(p.energy||p.C.empty())throw runtime_error("invalid start");
 while(*max_element(counts.begin(),counts.end())>quota){vector<int>choices;for(int w:p.C){bool relevant=false;for(int k=0;k<4;++k)if(counts[k]>quota&&(member[w]&(1u<<k)))relevant=true;if(relevant)choices.push_back(w);}remove(choices[rng()%choices.size()]);}
 auto fillTarget=[&](){while(p.C.size()<size_t(target)){int best=-1,cost=100000,ties=0;for(int w=0;w<N;++w)if(!p.selected[w]&&allowed(w)){int q=p.field[w];if(q<cost){cost=q;best=w;ties=1;}else if(q==cost&&rng()%++ties==0)best=w;}if(best<0)throw runtime_error("empty fill");add(best);}};
 fillTarget();check();set<vector<int>>known;ifstream K(argv[8]);int n,w;while(K>>n){vector<int>C;for(int i=0;i<n;++i){K>>w;C.push_back(w);}sort(C.begin(),C.end());known.insert(C);}
 vector<vector<int>>novel;auto inspect=[&](){if(target!=227)return;auto candidates=hubProjections(p,known);if(!candidates.empty())novel.insert(novel.end(),candidates.begin(),candidates.end());};inspect();
 vector<int>best=p.C,tabu(N),penalty(N);long long bestE=p.energy,iterations=0,stale=0,updates=0;array<int,4>bestCounts=counts;double start=cpuclock(),lastsave=start;
 while(cpuclock()-start<budget&&bestE&&novel.empty()){
  ++iterations;++stale;vector<int>bad;for(int w:p.C)if(p.field[w])bad.push_back(w);if(bad.empty())throw runtime_error("no conflict");int removed=bad[rng()%bad.size()];remove(removed);tabu[removed]=int(iterations)+7+rng()%24;
  int pick=-1,score=100000,ties=0,scale=adaptive?4:1;
  for(int w=0;w<N;++w){if(p.selected[w]||!allowed(w)||(tabu[w]>iterations&&p.field[w]!=0))continue;int q=scale*p.field[w]+(adaptive?penalty[w]:0);if(q<score){score=q;pick=w;ties=1;}else if(q==score&&rng()%++ties==0)pick=w;}
  if(pick<0)throw runtime_error("empty move");add(pick);inspect();
  if(p.energy<bestE){bestE=p.energy;best=p.C;bestCounts=counts;stale=0;checkpoint(path,best);}
  if(adaptive&&stale>128&&iterations%128==0){for(int w:p.C)if(penalty[w]<64){++penalty[w];++updates;}}
  if(iterations%4096==0)for(int&w:penalty)w/=2;
  if(stale>=4096&&stale%2048==0){auto old=p.C;for(int w:old)remove(w);auto keep=best;shuffle(keep.begin(),keep.end(),rng);int ruin=min(96,16+int(stale/4096)*8);for(int i=ruin;i<int(keep.size());++i)add(keep[i]);fillTarget();fill(tabu.begin(),tabu.end(),0);inspect();}
  if(iterations%8192==0)check();if(cpuclock()-lastsave>10){checkpoint(path,best);ofstream o(path+".progress.json");o<<"{\"iterations\":"<<iterations<<",\"minimum_pair_conflicts\":"<<bestE<<",\"cpu_seconds\":"<<cpuclock()-start<<",\"raw_candidate_is_not_verified\":true}";lastsave=cpuclock();}
 }
 check();checkpoint(path,best);cout<<"{\"target\":"<<target<<",\"quota\":"<<quota<<",\"adaptive\":"<<(adaptive?"true":"false")<<",\"seed\":"<<seed<<",\"cpu_seconds\":"<<cpuclock()-start<<",\"iterations\":"<<iterations<<",\"minimum_pair_conflicts\":"<<bestE<<",\"penalty_updates\":"<<updates<<",\"best_core_counts\":[";for(int k=0;k<4;++k){if(k)cout<<",";cout<<bestCounts[k];}cout<<"],\"best\":";outputArray(best);cout<<",\"novel226_candidates\":[";for(size_t i=0;i<novel.size();++i){if(i)cout<<",";outputArray(novel[i]);}cout<<"]}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
