// Goal-filtered exact clique repair in explicit three-parent unions.
// Adapted from the pinned CodeGarden fusion3_bridge kernel; no global bound.
#define main codegarden_old_main
#include "../kernel.cpp"
#undef main
#include <set>
#include <ctime>
#include <sstream>
double cputime(){return double(clock())/CLOCKS_PER_SEC;}
struct CliqueRepair{
 int m,W,target;double start,budget;uint64_t nodes=0,limit;bool found=false,limited=false;
 vector<int>words,chosen,best,fixed;vector<uint64_t>adj;set<vector<int>>known;uint64_t rejectedKnown=0;
 bool acceptable(const vector<int>&ids){vector<int>C=fixed;for(int i:ids)C.push_back(words[i]);sort(C.begin(),C.end());if(known.count(C)){++rejectedKnown;return false;}return true;}
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
  if(int(chosen.size())>=target&&acceptable(chosen)){best=chosen;found=true;return true;}
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
  if(int(best.size())>=target&&acceptable(best)){found=true;return;}expand(P);
 }
 vector<int>result(){vector<int>out;for(int i:best)out.push_back(words[i]);return out;}
};


#ifndef CODEGARDEN_TRIPLE_TEST
int main(){try{
 Garden g(1523001);int queries,K;if(!(cin>>queries>>K)||queries<0||queries>1000||K<0||K>1000)throw runtime_error("batch counts");set<vector<int>>known;
 for(int row=0;row<K;++row){int n,w;cin>>n;if(n!=226)throw runtime_error("known length");vector<int>C;for(int i=0;i<n;++i){if(!(cin>>w)||w<0||w>=N)throw runtime_error("known word");C.push_back(w);}sort(C.begin(),C.end());if(set<int>(C.begin(),C.end()).size()!=C.size())throw runtime_error("known duplicate");known.insert(C);}
 for(int q=0;q<queries;++q){int id,nf,np;double sec;if(!(cin>>id>>sec>>nf>>np)||sec<=0||sec>10||nf<0||nf>225||np<1||np>768)throw runtime_error("query header");vector<int>F(nf),P(np);for(int&w:F)cin>>w;for(int&w:P)cin>>w;
  vector<int>occ(M);set<int>unique;
  for(int w:F){if(w<0||w>=N||!unique.insert(w).second)throw runtime_error("fixed word");for(int d:g.desc[w])if(occ[d]++)throw runtime_error("invalid fixed code");}
  for(int w:P){if(w<0||w>=N||!unique.insert(w).second)throw runtime_error("pool word");for(int d:g.desc[w])if(occ[d])throw runtime_error("pool incompatible with fixed");}
  CliqueRepair r(P,g.desc,226-nf,sec,1000000000);r.fixed=F;r.known=known;r.run();
  cout<<"{\"query\":"<<id<<",\"found\":"<<(r.found?"true":"false")<<",\"complete\":"<<(!r.found&&!r.limited?"true":"false")<<",\"limited\":"<<(r.limited?"true":"false")<<",\"nodes\":"<<r.nodes<<",\"cpu_seconds\":"<<cputime()-r.start<<",\"filtered_known_goals\":"<<r.rejectedKnown<<",\"added\":";outputArray(r.result());cout<<"}"<<endl;
  if(r.found)break;
 }
 return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
#endif
