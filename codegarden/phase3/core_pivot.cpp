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

 if(argc==3&&string(argv[1])=="--forced-pool"){
  Garden g(1400001);int n,v;cin>>n;vector<int>root;for(int i=0;i<n;++i){cin>>v;root.push_back(v);g.add(v);}cin>>n;vector<int>core;for(int i=0;i<n;++i){cin>>v;core.push_back(v);}g.restore(core);int w=stoi(argv[2]);auto B=g.blockers(w);for(int u:B)g.remove(u);g.add(w);auto P=g.freeWords;sort(P.begin(),P.end());cout<<"{\"blockers\":";outputArray(B);cout<<",\"fixed\":";outputArray(g.code);cout<<",\"pool\":";outputArray(P);cout<<"}\n";return 0;
 }
 if(argc<5)throw runtime_error("part seconds seed checkpoint");
 int part=stoi(argv[1]);double budget=stod(argv[2]);uint64_t seed=stoull(argv[3]);string cp=argv[4];if(part<0||part>=16)throw runtime_error("partition");
 Garden g(seed);int n,w;cin>>n;vector<int>root;for(int i=0;i<n;++i){cin>>w;root.push_back(w);g.add(w);}cin>>n;vector<int>core;for(int i=0;i<n;++i){cin>>w;core.push_back(w);}sort(root.begin(),root.end());sort(core.begin(),core.end());if(root.size()!=226||core.size()!=216||!includes(root.begin(),root.end(),core.begin(),core.end()))throw runtime_error("root/core");g.restore(core);g.check();mt19937_64 rng(seed);
 vector<pair<vector<int>,int>>pivots;
 for(int v=0;v<N;++v)if(!binary_search(core.begin(),core.end(),v)){auto B=g.blockers(v);if(B.size()>=6&&B.size()<=18)pivots.push_back({B,v});}
 sort(pivots.begin(),pivots.end(),[](const auto&a,const auto&b){return a.first.size()!=b.first.size()?a.first.size()<b.first.size():a.second<b.second;});
 int planned=0,processed=0,cap=0,found226=0,complete227=0,timeout227=0,complete226=0,timeout226=0;for(int i=part;i<int(pivots.size());i+=16)++planned;
 vector<int>winner=root;vector<vector<int>>novel;vector<string>rows;string pcodes,scodes;double start=cputime();map<int,int>hist;bool win=false;
 for(size_t index=part;index<pivots.size()&&!win;index+=16){
  if(cputime()-start>=budget)break;
  auto removed=pivots[index].first;int pivot=pivots[index].second;g.restore(core);for(int u:removed)g.remove(u);g.add(pivot);g.check();auto fixed=g.code;auto P=g.freeWords;sort(P.begin(),P.end());++processed;++hist[removed.size()];int target227=227-fixed.size(),target226=226-fixed.size();string primary="C",secondary="N";uint64_t nodesP=0,nodesS=0;
  auto accept=[&](vector<int>extra){auto C=fixed;C.insert(C.end(),extra.begin(),extra.end());sort(C.begin(),C.end());if(C.size()>=226){novel.push_back(C);if(C.size()>=227){winner=C;win=true;}checkpoint(cp,C);}};
  if(P.size()<=768){
   auto order=P;shuffle(order.begin(),order.end(),rng);CliqueRepair r(order,g.desc,target227,.04,300000);
   for(size_t i=0;i<order.size();++i)if(binary_search(root.begin(),root.end(),order[i]))r.best.push_back(i);
   r.run();nodesP=r.nodes;primary=r.found?"F":r.limited?"T":"I";if(r.found)accept(r.result());else if(r.limited)++timeout227;else ++complete227;
   if(!win){
    auto order2=P;shuffle(order2.begin(),order2.end(),rng);CliqueRepair q(order2,g.desc,target226,.04,300000);
    for(size_t i=0;i<order2.size();++i)if(binary_search(root.begin(),root.end(),order2[i]))q.best.push_back(i);
    q.run();nodesS=q.nodes;secondary=q.found?"F":q.limited?"T":"I";if(q.found){++found226;accept(q.result());}else if(q.limited)++timeout226;else ++complete226;
   }
  }else ++cap;
  pcodes+=primary;scodes+=secondary;
  if(rows.size()<128){ostringstream o;o<<"{\"index\":"<<index<<",\"pivot\":"<<pivot<<",\"removed_core\":[";for(size_t i=0;i<removed.size();++i){if(i)o<<",";o<<removed[i];}o<<"],\"primary_status\":\""<<primary<<"\",\"secondary_status\":\""<<secondary<<"\",\"primary_nodes\":"<<nodesP<<",\"secondary_nodes\":"<<nodesS<<",\"pool\":[";for(size_t i=0;i<P.size();++i){if(i)o<<",";o<<P[i];}o<<"]}";rows.push_back(o.str());}
  if(!novel.empty())break;
 }
 checkpoint(cp,winner);cout<<"{\"case\":"<<part<<",\"planned\":"<<planned<<",\"processed\":"<<processed<<",\"all_pivots_processed\":"<<(processed==planned?"true":"false")<<",\"primary_complete_no227\":"<<complete227<<",\"primary_timeouts\":"<<timeout227<<",\"secondary_complete_no226\":"<<complete226<<",\"secondary_timeouts\":"<<timeout226<<",\"found226\":"<<found226<<",\"pool_cap_skips\":"<<cap<<",\"cpu_seconds\":"<<cputime()-start<<",\"winner\":";outputArray(winner);cout<<",\"new226_candidates\":[";for(size_t i=0;i<novel.size();++i){if(i)cout<<",";outputArray(novel[i]);}cout<<"],\"primary_status_codes\":\""<<pcodes<<"\",\"secondary_status_codes\":\""<<scodes<<"\",\"blocker_size_histogram\":{";bool first=true;for(auto [k,v]:hist){if(!first)cout<<",";first=false;cout<<"\""<<k<<"\":"<<v;}cout<<"},\"rows\":[";for(size_t i=0;i<rows.size();++i){if(i)cout<<",";cout<<rows[i];}cout<<"]}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
