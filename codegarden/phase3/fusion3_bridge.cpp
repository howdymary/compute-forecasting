// Exact repair in an explicitly sampled THREE-parent union; no global bound.
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
  int n=stoi(argv[2]),target=stoi(argv[3]);double seconds=stod(argv[4]);vector<vector<uint16_t>>desc(1<<n);
  for(int w=0;w<(1<<n);++w){set<uint16_t>d;for(int p=0;p<n;++p)for(int q=0;q<n-1;++q)d.insert(delbit(delbit(w,p),q));desc[w]=vector<uint16_t>(d.begin(),d.end());}
  vector<int>pool;int w;while(cin>>w)pool.push_back(w);CliqueRepair r(pool,desc,target,seconds,100000000);r.run();cout<<"{\"found\":"<<(r.found?"true":"false")<<",\"complete\":"<<(!r.found&&!r.limited?"true":"false")<<",\"nodes\":"<<r.nodes<<",\"best\":";outputArray(r.result());cout<<"}\n";return 0;
 }
 if(argc<5)throw runtime_error("seconds seed mode checkpoint");double seconds=stod(argv[1]);uint64_t seed=stoull(argv[2]);int mode=stoi(argv[3]);string path=argv[4];Garden g(seed);mt19937_64 rng(seed);vector<vector<int>>parents;set<vector<int>>seen;int size,w;
 while(cin>>size){vector<int>C;vector<int>occ(M);for(int i=0;i<size;++i){if(!(cin>>w)||w<0||w>=N)throw runtime_error("word");for(int d:g.desc[w])if(occ[d]++)throw runtime_error("invalid parent");C.push_back(w);}sort(C.begin(),C.end());if(seen.insert(C).second)parents.push_back(C);}
 if(parents.size()<3)throw runtime_error("parents");vector<int>large,medium,all;int best=0;vector<int>winner;for(size_t i=0;i<parents.size();++i){all.push_back(i);if(parents[i].size()==226)large.push_back(i);if(parents[i].size()==225)medium.push_back(i);if(int(parents[i].size())>best){best=parents[i].size();winner=parents[i];}}
 long long trials=0,complete=0,timeouts=0,skips=0,duplicates=0;set<array<int,3>>triples;vector<vector<int>>novel;vector<string>samples;double start=cputime();
 while(cputime()-start<seconds&&best<227){
  auto pick=[&](const vector<int>&v){return v[rng()%v.size()];};array<int,3>ids;ids[0]=pick(mode==0&&!large.empty()?large:mode==1&&!medium.empty()?medium:all);ids[1]=pick(mode<=1&&!medium.empty()?medium:all);ids[2]=pick(mode==1&&!medium.empty()?medium:all);sort(ids.begin(),ids.end());if(ids[0]==ids[1]||ids[1]==ids[2]||!triples.insert(ids).second){++duplicates;continue;}
  ++trials;auto A=parents[ids[0]],B=parents[ids[1]],C=parents[ids[2]];vector<int>ab,fixed,pool,whole;set_intersection(A.begin(),A.end(),B.begin(),B.end(),back_inserter(ab));set_intersection(ab.begin(),ab.end(),C.begin(),C.end(),back_inserter(fixed));whole=A;whole.insert(whole.end(),B.begin(),B.end());whole.insert(whole.end(),C.begin(),C.end());sort(whole.begin(),whole.end());whole.erase(unique(whole.begin(),whole.end()),whole.end());set_difference(whole.begin(),whole.end(),fixed.begin(),fixed.end(),back_inserter(pool));
  if(pool.size()>512){++skips;continue;}shuffle(pool.begin(),pool.end(),rng);auto hint=A.size()>=B.size()&&A.size()>=C.size()?A:B.size()>=C.size()?B:C;int goal=hint.size()>=226?227:226;int target=goal-fixed.size();CliqueRepair r(pool,g.desc,target,min(.025,max(.001,seconds-(cputime()-start))),100000);
  for(size_t i=0;i<pool.size();++i)if(binary_search(hint.begin(),hint.end(),pool[i]))r.best.push_back(i);
  r.run();auto out=fixed,extra=r.result();out.insert(out.end(),extra.begin(),extra.end());sort(out.begin(),out.end());
  if(!r.found&&!r.limited)++complete;else if(r.limited)++timeouts;
  if(int(out.size())>best){best=out.size();winner=out;checkpoint(path,winner);}
  if(out.size()>=226&&seen.insert(out).second&&novel.size()<64){novel.push_back(out);parents.push_back(out);all.push_back(parents.size()-1);if(out.size()==226)large.push_back(parents.size()-1);}
  if(samples.size()<64&&trials%17==0){
   ostringstream z;z<<"{\"parent_indices\":["<<ids[0]<<","<<ids[1]<<","<<ids[2]<<"],\"fixed\":[";for(size_t i=0;i<fixed.size();++i){if(i)z<<",";z<<fixed[i];}z<<"],\"pool\":[";for(size_t i=0;i<pool.size();++i){if(i)z<<",";z<<pool[i];}z<<"],\"target_added\":"<<target<<",\"complete_no_target\":"<<(!r.found&&!r.limited?"true":"false")<<",\"limited\":"<<(r.limited?"true":"false")<<",\"nodes\":"<<r.nodes<<"}";samples.push_back(z.str());
  }
 }
 checkpoint(path,winner);cout<<"{\"mode\":"<<mode<<",\"seed\":"<<seed<<",\"trials\":"<<trials<<",\"complete_scoped_negatives\":"<<complete<<",\"timeouts\":"<<timeouts<<",\"pool_cap_skips\":"<<skips<<",\"duplicate_draws_skipped\":"<<duplicates<<",\"cpu_seconds\":"<<cputime()-start<<",\"best_size_unverified\":"<<best<<",\"winner\":";outputArray(winner);cout<<",\"novel226_candidates\":[";for(size_t i=0;i<novel.size();++i){if(i)cout<<",";outputArray(novel[i]);}cout<<"],\"sampled_repairs\":[";for(size_t i=0;i<samples.size();++i){if(i)cout<<",";cout<<samples[i];}cout<<"]}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
