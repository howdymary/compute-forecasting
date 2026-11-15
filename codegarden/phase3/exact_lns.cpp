// Bounded exact large-neighborhood repair; positive scores require external verifiers.
#define main codegarden_old_main
#include "../kernel.cpp"
#undef main
#include <ctime>
#include <sstream>
#include <set>
#include <unordered_map>
#include <functional>
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
int main(int argc,char**argv){
 try{
  if(argc>1&&string(argv[1])=="--repair"){
   int n=stoi(argv[2]),target=stoi(argv[3]);double sec=stod(argv[4]);if(n<3||n>16)throw runtime_error("length");
   vector<vector<uint16_t>>desc(1<<n);for(int w=0;w<(1<<n);++w){set<uint16_t>d;for(int i=0;i<n;++i)for(int j=0;j<n-1;++j)d.insert(delbit(delbit(w,i),j));desc[w]=vector<uint16_t>(d.begin(),d.end());}
   vector<int>pool;int w;while(cin>>w){if(w<0||w>=(1<<n))throw runtime_error("word");pool.push_back(w);}CliqueRepair r(pool,desc,target,sec,100000000);r.run();
   cout<<"{\"found\":"<<(r.found?"true":"false")<<",\"complete\":"<<(!r.found&&!r.limited?"true":"false")<<",\"nodes\":"<<r.nodes<<",\"best\":";outputArray(r.result());cout<<"}\n";return 0;
  }
  if(argc<5)throw runtime_error("usage seconds seed start_mode checkpoint");double seconds=stod(argv[1]);uint64_t seed=stoull(argv[2]);string mode=argv[3],path=argv[4];Garden g(seed);string s;vector<int>initial;
  while(cin>>s){if(s.size()!=16||s.find_first_not_of("01")!=string::npos)throw runtime_error("word");int w=stoi(s,nullptr,2);g.add(w);initial.push_back(w);}if(initial.empty())throw runtime_error("empty");g.check();
  vector<int>best=g.code;vector<vector<int>>archive{best};unordered_set<uint64_t>seen{g.fingerprint(best)};uint64_t iterations=0,complete=0,timeouts=0,skipped=0,improvements=0;
  vector<string>negative;double start=cputime(),lastSave=start;int stale=0;
  while(cputime()-start<seconds&&best.size()<227){
   ++iterations;auto old=g.code;int size=min(int(old.size()),24+int(g.rng()%41));set<int>removed;vector<int>forced;
   if(mode=="opportunity"&&g.unit()<.7){
    for(int pick=0;pick<1+int(g.rng()%2);++pick){
     int chosen=-1,cost=1000;vector<int>block;
     for(int q=0;q<64;++q){int w=g.rnd(N);if(g.codePos[w]>=0)continue;bool ok=true;for(int v:forced)for(auto d:g.desc[w])if(binary_search(g.desc[v].begin(),g.desc[v].end(),d)){ok=false;break;}if(!ok)continue;
      auto b=g.blockers(w);if(b.size()<3||b.size()>16)continue;if(int(b.size())<cost){chosen=w;cost=b.size();block=b;}}
     if(chosen>=0){forced.push_back(chosen);removed.insert(block.begin(),block.end());}
    }
   }
   auto shuffled=old;shuffle(shuffled.begin(),shuffled.end(),g.rng);for(int w:shuffled){if(int(removed.size())>=size)break;removed.insert(w);}
   for(int w:removed)g.remove(w);for(int w:forced)g.add(w);auto fixed=g.code;auto pool=g.freeWords;shuffle(pool.begin(),pool.end(),g.rng);
   int target=int(old.size())+1-int(fixed.size());string status="SKIPPED_POOL_CAP";uint64_t nodes=0;bool exactComplete=false;
   if(pool.size()<=512&&target>0){
    double budget=min(.025,max(.002,seconds-(cputime()-start)));CliqueRepair r(pool,g.desc,target,budget,200000);r.run();nodes=r.nodes;
    auto add=r.result();for(int w:add)g.add(w);exactComplete=!r.found&&!r.limited;status=r.found?"FEASIBLE_AUGMENTATION":r.limited?"TIMEOUT_NO_AUGMENTATION":"INFEASIBLE_TARGET";
    if(exactComplete)++complete;else if(r.limited)++timeouts;
   }else ++skipped;
   g.fill(5+g.unit()*16);int delta=int(g.code.size())-int(old.size());double temp=.3+min(2.,stale/20000.);
   if(delta<0&&(g.code.size()+10<best.size()||g.unit()>=exp(delta/temp)))g.restore(old);
   if(g.code.size()>best.size()){best=g.code;stale=0;++improvements;checkpoint(path,best);}else ++stale;
   if(g.code.size()+1>=best.size()&&seen.insert(g.fingerprint(g.code)).second){archive.push_back(g.code);if(archive.size()>32)archive.erase(archive.begin()+1);}
   if(exactComplete&&negative.size()<64&&iterations%97==0){
    ostringstream out;out<<"{\"incumbent\":[";for(size_t i=0;i<old.size();++i){if(i)out<<",";out<<old[i];}out<<"],\"fixed\":[";for(size_t i=0;i<fixed.size();++i){if(i)out<<",";out<<fixed[i];}out<<"],\"pool\":[";
    for(size_t i=0;i<pool.size();++i){if(i)out<<",";out<<pool[i];}out<<"],\"target_added\":"<<target<<",\"nodes\":"<<nodes<<",\"status\":\"INFEASIBLE_TARGET\",\"proof_artifact\":null,\"scope\":\"This exact fixed-outside repair pool only\"}";negative.push_back(out.str());
   }
   if(iterations%2000==0)g.check();if(stale&&stale%3000==0)g.restore(archive[g.rnd(archive.size())]);
   if(cputime()-lastSave>=5){checkpoint(path,best);lastSave=cputime();}
  }
  g.check();checkpoint(path,best);cout<<"{\"seed\":"<<seed<<",\"mode\":\""<<mode<<"\",\"cpu_seconds\":"<<cputime()-start<<",\"iterations\":"<<iterations<<",\"complete_target_negatives\":"<<complete<<",\"timeouts\":"<<timeouts<<",\"pool_cap_skips\":"<<skipped<<",\"best_size_unverified\":"<<best.size()<<",\"best\":";outputArray(best);cout<<",\"archive\":[";
  for(size_t i=0;i<archive.size();++i){if(i)cout<<",";outputArray(archive[i]);}cout<<"],\"sampled_scoped_negatives\":[";for(size_t i=0;i<negative.size();++i){if(i)cout<<",";cout<<negative[i];}cout<<"]}\n";
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}return 0;
}
