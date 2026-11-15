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

#include <unordered_map>
struct WeightedPacking{
 PairPacking&p;vector<long long>field;unordered_map<uint32_t,int>extra;vector<vector<int>>neighbors;long long energy=0,bumps=0,forgets=0;
 WeightedPacking(PairPacking&x):p(x),field(N),neighbors(N){}
 uint32_t key(int a,int b)const{if(a>b)swap(a,b);return (uint32_t(a)<<16)|uint32_t(b);}
 int weight(int a,int b)const{auto it=extra.find(key(a,b));return it==extra.end()?0:it->second;}
 void add(int w){energy+=field[w];p.add(w);for(int u:p.adj(w))++field[u];for(int u:neighbors[w])field[u]+=weight(w,u);}
 void remove(int w){energy-=field[w];p.remove(w);for(int u:p.adj(w))--field[u];for(int u:neighbors[w])field[u]-=weight(w,u);}
 void bump(){
  for(int a:p.C)for(int b:p.adj(a))if(a<b&&p.selected[b]){
   uint32_t k=key(a,b);auto it=extra.find(k);if(it==extra.end()){extra[k]=0;neighbors[a].push_back(b);neighbors[b].push_back(a);}
   if(extra[k]<128){++extra[k];++field[a];++field[b];++energy;++bumps;}
  }
 }
 void forget(){
  ++forgets;for(auto&item:extra)item.second/=2;for(int w=0;w<N;++w)field[w]=p.field[w];
  for(auto [k,v]:extra)if(v){int a=k>>16,b=k&65535;if(p.selected[a])field[b]+=v;if(p.selected[b])field[a]+=v;}
  energy=0;for(int w:p.C)energy+=field[w];if(energy%2)throw runtime_error("odd weighted energy");energy/=2;
 }
 void check(){
  p.check();vector<long long>expected(p.field.begin(),p.field.end());
  for(auto [k,v]:extra)if(v){int a=k>>16,b=k&65535;if(p.selected[a])expected[b]+=v;if(p.selected[b])expected[a]+=v;}
  long long e=0;for(int w:p.C)e+=expected[w];if(expected!=field||e!=2*energy)throw runtime_error("weighted incremental mismatch");
 }
 void observation(){
  cout<<"{\"selected\":";outputArray(p.C);cout<<",\"pair_energy\":"<<p.energy<<",\"weighted_energy\":"<<energy<<",\"penalties\":[";bool first=true;
  for(auto [k,v]:extra)if(v){if(!first)cout<<",";first=false;cout<<"["<<(k>>16)<<","<<(k&65535)<<","<<v<<"]";}
  cout<<"],\"field_samples\":[";vector<int>samples=p.C;for(int i=0;i<40;++i)samples.push_back((i*1371+19)%65536);first=true;for(int w:samples){if(!first)cout<<",";first=false;cout<<"["<<w<<","<<field[w]<<"]";}cout<<"]}";
 }
};
int main(int argc,char**argv){try{
 if(argc>1&&string(argv[1])=="--weighted-test"){
  Garden g(1500101);PairPacking p(g);WeightedPacking q(p);mt19937 rng(1500101);for(int w=0;w<30;++w)q.add(w);q.bump();q.check();cout<<"{\"observations\":[";q.observation();
  for(int t=1;t<=120;++t){int old=p.C[rng()%p.C.size()];q.remove(old);int w;do{w=rng()%65536;}while(p.selected[w]);q.add(w);if(t%3==0)q.bump();if(t%31==0)q.forget();q.check();if(t%30==0){cout<<",";q.observation();}}
  cout<<"],\"passed_native\":true}\n";return 0;
 }
 if(argc<8)throw runtime_error("seconds seed mode checkpoint corefile quota knownfile");double budget=stod(argv[1]);uint64_t seed=stoull(argv[2]);bool weighted=string(argv[3])=="weighted";string path=argv[4];int quota=stoi(argv[6]);if(quota!=210)throw runtime_error("only audited conditional quota210");
 Garden g(seed);PairPacking p(g);WeightedPacking q(p);mt19937_64 rng(seed);vector<unsigned char>member(N);array<int,4>counts{};ifstream corefile(argv[5]);for(int k=0;k<4;++k){int n,w;if(!(corefile>>n)||n!=216)throw runtime_error("core file");for(int j=0;j<n;++j){corefile>>w;if(w<0||w>=N)throw runtime_error("core word");member[w]|=1u<<k;}}
 auto add=[&](int w){q.add(w);for(int k=0;k<4;++k)if(member[w]&(1u<<k))++counts[k];};
 auto remove=[&](int w){q.remove(w);for(int k=0;k<4;++k)if(member[w]&(1u<<k))--counts[k];};
 auto allowed=[&](int w){for(int k=0;k<4;++k)if((member[w]&(1u<<k))&&counts[k]>=quota)return false;return true;};
 string word;while(cin>>word){if(word.size()!=16||word.find_first_not_of("01")!=string::npos)throw runtime_error("input");add(stoi(word,nullptr,2));}if(p.energy||p.C.empty())throw runtime_error("invalid start");
 while(*max_element(counts.begin(),counts.end())>quota){vector<int>choices;for(int w:p.C){bool relevant=false;for(int k=0;k<4;++k)if(counts[k]>quota&&(member[w]&(1u<<k)))relevant=true;if(relevant)choices.push_back(w);}remove(choices[rng()%choices.size()]);}
 auto fillTarget=[&](){while(p.C.size()<227){int best=-1,ties=0;long long score=1ll<<60;for(int w=0;w<N;++w)if(!p.selected[w]&&allowed(w)){long long c=q.field[w];if(c<score){score=c;best=w;ties=1;}else if(c==score&&rng()%++ties==0)best=w;}if(best<0)throw runtime_error("empty fill");add(best);}};
 fillTarget();q.check();set<vector<int>>known;ifstream kfile(argv[7]);int n,w;while(kfile>>n){vector<int>C(n);for(auto&v:C)kfile>>v;sort(C.begin(),C.end());known.insert(C);}
 vector<vector<int>>novel;auto inspect=[&](){for(auto C:hubProjections(p,known)){known.insert(C);if(novel.size()<16)novel.push_back(C);}};inspect();
 vector<int>best=p.C,tabu(N);long long bestE=p.energy,iterations=0,stale=0,restarts=0;double start=cpuclock(),lastsave=start;array<int,4>bestCounts=counts;checkpoint(path,best);
 while(cpuclock()-start<budget&&bestE>0){
  ++iterations;++stale;int removed=-1,ties=0;long long score=-1;
  for(int w:p.C)if(p.field[w]){long long cost=q.field[w];if(cost>score){score=cost;removed=w;ties=1;}else if(cost==score&&rng()%++ties==0)removed=w;}
  if(removed<0)throw runtime_error("no conflict");remove(removed);tabu[removed]=int(iterations)+7+rng()%24;
  int pick=-1;ties=0;score=1ll<<60;
  for(int w=0;w<N;++w){if(p.selected[w]||!allowed(w)||(tabu[w]>iterations&&p.field[w]!=0))continue;long long cost=q.field[w];if(cost<score){score=cost;pick=w;ties=1;}else if(cost==score&&rng()%++ties==0)pick=w;}
  if(pick<0)throw runtime_error("empty move");add(pick);inspect();
  if(p.energy<bestE){bestE=p.energy;best=p.C;bestCounts=counts;stale=0;checkpoint(path,best);}
  if(weighted&&stale>=32&&iterations%32==0)q.bump();
  if(weighted&&iterations%4096==0)q.forget();
  if(stale>=4096&&stale%2048==0){++restarts;auto old=p.C;for(int w:old)remove(w);auto keep=best;shuffle(keep.begin(),keep.end(),rng);int ruin=min(96,16+int(stale/4096)*8);for(int i=ruin;i<int(keep.size());++i)add(keep[i]);fillTarget();fill(tabu.begin(),tabu.end(),0);inspect();if(p.energy<bestE){bestE=p.energy;best=p.C;bestCounts=counts;stale=0;checkpoint(path,best);}}
  if(iterations%8192==0)q.check();
  if(cpuclock()-lastsave>=10){checkpoint(path,best);ofstream o(path+".progress.json");o<<"{\"iterations\":"<<iterations<<",\"minimum_pair_conflicts\":"<<bestE<<",\"cpu_seconds\":"<<cpuclock()-start<<",\"invalid_unless_zero\":true}";lastsave=cpuclock();}
 }
 q.check();checkpoint(path,best);cout<<"{\"seed\":"<<seed<<",\"weighted\":"<<(weighted?"true":"false")<<",\"target\":227,\"quota\":210,\"cpu_seconds\":"<<cpuclock()-start<<",\"iterations\":"<<iterations<<",\"minimum_pair_conflicts\":"<<bestE<<",\"edge_weight_updates\":"<<q.bumps<<",\"stored_weighted_edges\":"<<q.extra.size()<<",\"forgettings\":"<<q.forgets<<",\"restarts\":"<<restarts<<",\"best\":";outputArray(best);cout<<",\"novel226_candidates\":[";for(size_t i=0;i<novel.size();++i){if(i)cout<<",";outputArray(novel[i]);}cout<<"]}\n";return 0;
}catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
