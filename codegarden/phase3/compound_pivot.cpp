// Full-universe exact repairs around the shared216 core. Sparse ownership first.
#define main codegarden_old_main
#include "../kernel.cpp"
#undef main
#include <set>
#include <ctime>
#include <sstream>
#include <map>
double cputime(){return double(clock())/CLOCKS_PER_SEC;}
struct CliqueRepair{
 int m,W,target;double start,budget;uint64_t nodes=0,limit;bool found=false,limited=false;
 vector<int>words,chosen,best;vector<uint64_t>adj;
 CliqueRepair(const vector<int>&p,const vector<vector<uint16_t>>&desc,int t,double seconds,uint64_t cap):m(p.size()),W((m+63)/64),target(t),start(cputime()),budget(seconds),limit(cap),words(p),adj(size_t(m)*W,0){
  if(set<int>(p.begin(),p.end()).size()!=p.size())throw runtime_error("duplicate repair candidate");
  for(int i=0;i<m;++i)for(int j=0;j<i;++j){
   auto&a=desc[p[i]];auto&b=desc[p[j]];size_t x=0,y=0;bool ok=true;
   while(x<a.size()&&y<b.size()){if(a[x]==b[y]){ok=false;break;}if(a[x]<b[y])++x;else ++y;}
   if(ok){adj[size_t(i)*W+j/64]|=1ull<<(j%64);adj[size_t(j)*W+i/64]|=1ull<<(i%64);}
  }
 }
 bool any(const vector<uint64_t>&p){for(auto w:p)if(w)return true;return false;}
 void color(const vector<uint64_t>&P,vector<int>&order,vector<int>&bounds){
  auto left=P;int c=0;
  while(any(left)){
   ++c;auto q=left;
   for(int block=0;block<W;++block)while(q[block]){
    int bit=__builtin_ctzll(q[block]),v=block*64+bit;left[block]&=~(1ull<<bit);q[block]&=~(1ull<<bit);
    for(int j=0;j<W;++j)q[j]&=~adj[size_t(v)*W+j];
    order.push_back(v);bounds.push_back(c);
   }
  }
 }
 bool expand(vector<uint64_t>P){
  if(++nodes>=limit||((nodes&255)==0&&cputime()-start>=budget)){limited=true;return true;}
  if(chosen.size()>best.size())best=chosen;
  if(int(chosen.size())>=target){found=true;return true;}
  vector<int>order,bounds;color(P,order,bounds);
  for(int i=int(order.size())-1;i>=0;--i){
   if(int(chosen.size())+bounds[i]<target)return false;
   int v=order[i];chosen.push_back(v);vector<uint64_t>q(W);
   for(int j=0;j<W;++j)q[j]=P[j]&adj[size_t(v)*W+j];
   if(expand(q))return true;chosen.pop_back();P[v/64]&=~(1ull<<(v%64));
  }
  return false;
 }
 void run(){
  vector<uint64_t>P(W,~0ull);if(W&&m%64)P[W-1]&=(1ull<<(m%64))-1;
  // A randomized greedy seed supports feasible reconstruction even on a timeout.
  for(int i=0;i<m;++i){bool ok=true;for(int j:best)if(!(adj[size_t(i)*W+j/64]&(1ull<<(j%64)))){ok=false;break;}if(ok)best.push_back(i);}
  if(int(best.size())>=target){found=true;return;}expand(P);
 }
 vector<int>result(){vector<int>out;for(int i:best)out.push_back(words[i]);return out;}
};

int main(int argc,char**argv){try{
 if(argc>1&&string(argv[1])=="--repair"){
  int n=stoi(argv[2]),target=stoi(argv[3]);double sec=stod(argv[4]);vector<vector<uint16_t>>desc(1<<n);
  for(int w=0;w<(1<<n);++w){set<uint16_t>d;for(int i=0;i<n;++i)for(int j=0;j<n-1;++j)d.insert(delbit(delbit(w,i),j));desc[w]=vector<uint16_t>(d.begin(),d.end());}
  vector<int>pool;int w;while(cin>>w)pool.push_back(w);CliqueRepair r(pool,desc,target,sec,100000000);r.run();cout<<"{\"found\":"<<(r.found?"true":"false")<<",\"complete\":"<<(!r.found&&!r.limited?"true":"false")<<",\"nodes\":"<<r.nodes<<",\"best\":";outputArray(r.result());cout<<"}\n";return 0;
 }


 if(argc<5)throw runtime_error("case seconds seed checkpoint");int part=stoi(argv[1]);double budget=stod(argv[2]);uint64_t seed=stoull(argv[3]);string cp=argv[4];Garden g(seed);mt19937_64 rng(seed);int n,w;cin>>n;vector<int>root;for(int i=0;i<n;++i){cin>>w;root.push_back(w);g.add(w);}cin>>n;vector<int>core;for(int i=0;i<n;++i){cin>>w;core.push_back(w);}sort(root.begin(),root.end());sort(core.begin(),core.end());g.restore(core);g.check();
 using Mask=array<uint64_t,4>;vector<Mask>masks(N);vector<int>outside;for(int v=0;v<N;++v)if(!binary_search(core.begin(),core.end(),v)){for(int b:g.blockers(v)){int i=lower_bound(core.begin(),core.end(),b)-core.begin();masks[v][i/64]|=1ull<<(i%64);}outside.push_back(v);}
 auto unite=[](const Mask&a,const Mask&b){Mask c;for(int i=0;i<4;++i)c[i]=a[i]|b[i];return c;};auto count=[](const Mask&a){int k=0;for(auto x:a)k+=__builtin_popcountll(x);return k;};
 auto compatible=[&](int a,int b){auto&A=g.desc[a];auto&B=g.desc[b];size_t i=0,j=0;while(i<A.size()&&j<B.size()){if(A[i]==B[j])return false;if(A[i]<B[j])++i;else ++j;}return a!=b;};
 int goalP=part<4?2:part<8?3:part<12?4:2,rankCap=part<4?14:part<8?20:part<12?26:18;bool adaptive=part>=12;int epoch=0,stale=0;
 long long trials=0,processed=0,complete227=0,timeout227=0,complete226=0,timeout226=0,cap=0,duplicate=0,single_hull_skips=0;set<vector<int>>seen;vector<string>rows;vector<vector<int>>novel;vector<int>winner=root;double start=cputime(),lastCheckpoint=start;bool win=false;
 while(cputime()-start<budget&&!win&&novel.empty()){
  if(cputime()-lastCheckpoint>10){checkpoint(cp,winner);ofstream progress(cp+".progress.json");progress<<"{\"trials\":"<<trials<<",\"processed\":"<<processed<<",\"cpu_seconds\":"<<cputime()-start<<",\"verified_incumbent_size\":226,\"scope\":\"bounded heuristic in progress, no absence claim\"}";lastCheckpoint=cputime();}
  ++trials;++stale;if(adaptive&&stale%512==0){++epoch;goalP=2+(epoch%4);rankCap=16+4*((epoch/4)%5);}
  vector<int>forced{outside[rng()%outside.size()]};Mask B=masks[forced[0]];
  if(count(B)>rankCap)continue;
  while(int(forced.size())<goalP){
   int best=-1,score=1000,ties=0;Mask newB{};
   for(int q=0;q<96;++q){int v=outside[rng()%outside.size()];Mask U=unite(B,masks[v]);int k=count(U);if(k>rankCap||k==count(B))continue;bool ok=true;for(int u:forced)if(!compatible(v,u)){ok=false;break;}if(!ok)continue;int cost=k-count(B);if(cost<score||(cost==score&&rng()%++ties==0)){if(cost<score)ties=1;best=v;newB=U;score=cost;}}
   if(best<0)break;forced.push_back(best);B=newB;
  }
  if(int(forced.size())<goalP||count(B)<=5)continue;
  bool single=false;for(int v:forced)if(masks[v]==B)single=true;if(single){++single_hull_skips;continue;}
  sort(forced.begin(),forced.end());if(!seen.insert(forced).second){++duplicate;continue;}++processed;
  vector<int>removed;for(int i=0;i<216;++i)if(B[i/64]&(1ull<<(i%64)))removed.push_back(core[i]);
  g.restore(core);for(int v:removed)g.remove(v);for(int v:forced)g.add(v);auto fixed=g.code;auto P=g.freeWords;sort(P.begin(),P.end());string ps="C",ss="N";uint64_t np=0,ns=0;
  auto accept=[&](vector<int>extra){auto C=fixed;C.insert(C.end(),extra.begin(),extra.end());sort(C.begin(),C.end());novel.push_back(C);if(C.size()>=227){winner=C;win=true;}checkpoint(cp,C);};
  if(P.size()<=1024){
   auto order=P;shuffle(order.begin(),order.end(),rng);CliqueRepair r(order,g.desc,227-fixed.size(),.035,250000);for(size_t i=0;i<order.size();++i)if(binary_search(root.begin(),root.end(),order[i]))r.best.push_back(i);r.run();np=r.nodes;ps=r.found?"F":r.limited?"T":"I";if(r.found)accept(r.result());else if(r.limited)++timeout227;else ++complete227;
   if(!win){auto order2=P;shuffle(order2.begin(),order2.end(),rng);CliqueRepair q(order2,g.desc,226-fixed.size(),.035,250000);for(size_t i=0;i<order2.size();++i)if(binary_search(root.begin(),root.end(),order2[i]))q.best.push_back(i);q.run();ns=q.nodes;ss=q.found?"F":q.limited?"T":"I";if(q.found)accept(q.result());else if(q.limited)++timeout226;else ++complete226;}
  }else ++cap;
  if(rows.size()<128||ps=="F"||ss=="F"){ostringstream z;z<<"{\"trial\":"<<trials<<",\"forced\":[";for(size_t i=0;i<forced.size();++i){if(i)z<<",";z<<forced[i];}z<<"],\"removed_core\":[";for(size_t i=0;i<removed.size();++i){if(i)z<<",";z<<removed[i];}z<<"],\"primary_status\":\""<<ps<<"\",\"secondary_status\":\""<<ss<<"\",\"primary_nodes\":"<<np<<",\"secondary_nodes\":"<<ns<<",\"pool\":[";for(size_t i=0;i<P.size();++i){if(i)z<<",";z<<P[i];}z<<"]}";rows.push_back(z.str());}
  if(processed%1024==0)g.check();
 }
 g.check();checkpoint(cp,winner);cout<<"{\"case\":"<<part<<",\"seed\":"<<seed<<",\"adaptive\":"<<(adaptive?"true":"false")<<",\"epochs\":"<<epoch<<",\"last_pivot_count\":"<<goalP<<",\"last_rank_cap\":"<<rankCap<<",\"trials\":"<<trials<<",\"processed\":"<<processed<<",\"complete_no227\":"<<complete227<<",\"timeouts227\":"<<timeout227<<",\"complete_no226\":"<<complete226<<",\"timeouts226\":"<<timeout226<<",\"pool_cap_skips\":"<<cap<<",\"duplicate_proposals\":"<<duplicate<<",\"single_hull_skips\":"<<single_hull_skips<<",\"cpu_seconds\":"<<cputime()-start<<",\"winner\":";outputArray(winner);cout<<",\"new226_candidates\":[";for(size_t i=0;i<novel.size();++i){if(i)cout<<",";outputArray(novel[i]);}cout<<"],\"rows\":[";for(size_t i=0;i<rows.size();++i){if(i)cout<<",";cout<<rows[i];}cout<<"]}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
