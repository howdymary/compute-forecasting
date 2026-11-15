// Full-universe exact repairs around the shared216 core. Sparse ownership first.
#define main codegarden_old_main
#include "../kernel.cpp"
#undef main
#include <set>
#include <ctime>
#include <sstream>
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
 Garden g(1360001);int n,w;cin>>n;vector<int>root;for(int i=0;i<n;++i){cin>>w;root.push_back(w);g.add(w);}cin>>n;vector<int>core;for(int i=0;i<n;++i){cin>>w;core.push_back(w);}sort(root.begin(),root.end());sort(core.begin(),core.end());if(root.size()!=226||core.size()!=216||!includes(root.begin(),root.end(),core.begin(),core.end()))throw runtime_error("root/core");g.restore(core);g.check();
 if(argc>1&&string(argv[1])=="--pool"){auto P=g.freeWords;sort(P.begin(),P.end());cout<<"{\"core\":";outputArray(core);cout<<",\"pool\":";outputArray(P);cout<<"}\n";return 0;}
 if(argc<5)throw runtime_error("case seconds seed checkpoint");int part=stoi(argv[1]);if(part<0||part>=4)throw runtime_error("partition");double budget=stod(argv[2]);uint64_t seed=stoull(argv[3]);string checkpointPath=argv[4];mt19937_64 rng(seed);
 vector<vector<int>>removals;for(int i=0;i<216;++i)for(int j=i+1;j<216;++j)for(int k=j+1;k<216;++k)removals.push_back({core[i],core[j],core[k]});
 vector<string>rows;string primaryCodes,secondaryCodes;vector<vector<int>>novel;set<vector<int>>novelSeen;vector<int>winner=root;int best=226,planned=0,processed=0;long long complete227=0,timeout227=0,complete226=0,timeout226=0,cap=0;double start=cputime();
 for(size_t index=0;index<removals.size();++index)if(int(index%4)==part)++planned;
 for(size_t index=part;index<removals.size()&&best<227;index+=4){
  if(cputime()-start>=budget)break;auto removed=removals[index];g.restore(core);for(int v:removed)g.remove(v);auto fixed=g.code;auto P=g.freeWords;sort(P.begin(),P.end());++processed;
  string primaryStatus="POOL_CAP_SKIP",secondaryStatus="NOT_RUN";uint64_t nodesP=0,nodesS=0;vector<int>P2;
  auto accept=[&](const vector<int>&extra){auto C=fixed;C.insert(C.end(),extra.begin(),extra.end());sort(C.begin(),C.end());if(C.size()>=226&&novelSeen.insert(C).second&&novel.size()<64)novel.push_back(C);if(int(C.size())>best){best=C.size();winner=C;checkpoint(checkpointPath,winner);}};
  if(P.size()<=512){
   auto order=P;shuffle(order.begin(),order.end(),rng);CliqueRepair r(order,g.desc,227-fixed.size(),.02,100000);
   for(size_t i=0;i<order.size();++i)if(binary_search(root.begin(),root.end(),order[i]))r.best.push_back(i);
   r.run();nodesP=r.nodes;primaryStatus=r.found?"FEASIBLE_227":r.limited?"TIMEOUT":"INFEASIBLE_227";if(!r.found&&!r.limited)++complete227;else if(r.limited)++timeout227;if(r.found)accept(r.result());
   if(best<227){
    for(int v:P)if(!binary_search(removed.begin(),removed.end(),v))P2.push_back(v);
    auto order2=P2;shuffle(order2.begin(),order2.end(),rng);CliqueRepair q(order2,g.desc,226-fixed.size(),.03,100000);
    for(size_t i=0;i<order2.size();++i)if(binary_search(root.begin(),root.end(),order2[i]))q.best.push_back(i);
    q.run();nodesS=q.nodes;secondaryStatus=q.found?"FEASIBLE_NEW226_CANDIDATE":q.limited?"TIMEOUT":"INFEASIBLE_EXCLUDING_REMOVED";if(!q.found&&!q.limited)++complete226;else if(q.limited)++timeout226;if(q.found)accept(q.result());
   }
  }else ++cap;
  primaryCodes.push_back(primaryStatus=="INFEASIBLE_227"?'I':primaryStatus=="TIMEOUT"?'T':primaryStatus=="POOL_CAP_SKIP"?'C':'F');secondaryCodes.push_back(secondaryStatus=="INFEASIBLE_EXCLUDING_REMOVED"?'I':secondaryStatus=="TIMEOUT"?'T':secondaryStatus=="NOT_RUN"?'N':'F');
  if(rows.size()<64){ostringstream z;z<<"{\"index\":"<<index<<",\"removed_core\":[";for(size_t i=0;i<removed.size();++i){if(i)z<<",";z<<removed[i];}z<<"],\"primary_status\":\""<<primaryStatus<<"\",\"secondary_status\":\""<<secondaryStatus<<"\",\"primary_nodes\":"<<nodesP<<",\"secondary_nodes\":"<<nodesS<<",\"primary_pool\":[";for(size_t i=0;i<P.size();++i){if(i)z<<",";z<<P[i];}z<<"],\"secondary_pool\":[";for(size_t i=0;i<P2.size();++i){if(i)z<<",";z<<P2[i];}z<<"]}";rows.push_back(z.str());}
  if(index%1000<4)g.check();
 }
 g.check();checkpoint(checkpointPath,winner);cout<<"{\"case\":"<<part<<",\"seed\":"<<seed<<",\"planned\":"<<planned<<",\"processed\":"<<processed<<",\"primary_complete_no227\":"<<complete227<<",\"primary_timeouts\":"<<timeout227<<",\"secondary_complete_no226_excluding_removed\":"<<complete226<<",\"secondary_timeouts\":"<<timeout226<<",\"pool_cap_skips\":"<<cap<<",\"all_planned_neighborhoods_processed\":"<<(processed==planned?"true":"false")<<",\"cpu_seconds\":"<<cputime()-start<<",\"best_size_unverified\":"<<best<<",\"winner\":";outputArray(winner);cout<<",\"new226_candidates\":[";for(size_t i=0;i<novel.size();++i){if(i)cout<<",";outputArray(novel[i]);}cout<<"],\"primary_status_codes\":\""<<primaryCodes<<"\",\"secondary_status_codes\":\""<<secondaryCodes<<"\",\"rows\":[";for(size_t i=0;i<rows.size();++i){if(i)cout<<",";cout<<rows[i];}cout<<"]}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
