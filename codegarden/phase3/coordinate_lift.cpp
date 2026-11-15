// Exact two-choice coordinate lift plus one arbitrary word; positive output is untrusted.
#define main codegarden_existing_kernel_main
#include "../kernel.cpp"
#undef main
#include <ctime>
#include <set>
#include <iomanip>
using Mask=array<uint64_t,8>;
Mask zeroMask(){Mask a{};return a;}
bool has(const Mask&a,int k){return (a[k/64]>>(k%64))&1;}
void put(Mask&a,int k){a[k/64]|=1ull<<(k%64);}
void unite(Mask&a,const Mask&b){for(int j=0;j<8;++j)a[j]|=b[j];}
bool bad(const Mask&a){for(auto x:a)if(x&(x>>1)&0x5555555555555555ull)return true;return false;}
struct TwoSAT{
 int m,V;vector<Mask>direct,reach;bool feasible=false;
 TwoSAT(int mm):m(mm),V(2*mm),direct(V){}
 void conflict(int u,int v){put(direct[u],v^1);put(direct[v],u^1);}
 void finish(){reach=direct;for(int u=0;u<V;++u)put(reach[u],u);
  for(int k=0;k<V;++k)for(int u=0;u<V;++u)if(has(reach[u],k))unite(reach[u],reach[k]);
  feasible=true;for(int i=0;i<m;++i)if(has(reach[2*i],2*i+1)&&has(reach[2*i+1],2*i))feasible=false;
 }
 bool force(const Mask&forbidden,Mask&truth)const{
  if(!feasible||bad(forbidden))return false;truth=zeroMask();
  for(int j=0;j<8;++j){auto x=forbidden[j];while(x){int k=j*64+__builtin_ctzll(x);x&=x-1;unite(truth,reach[k^1]);if(bad(truth))return false;}}
  return true;
 }
 vector<int> assignment(Mask truth)const{
  vector<int>chosen;
  for(int i=0;i<m;++i){
   if(!has(truth,2*i)&&!has(truth,2*i+1)){
    auto next=truth;unite(next,reach[2*i]);
    if(!bad(next))truth=next;else{unite(truth,reach[2*i+1]);if(bad(truth))throw runtime_error("2SAT extension contradiction");}
   }
   chosen.push_back(has(truth,2*i+1)?1:0);
  }
  for(int u=0;u<V;++u)if(has(truth,u))for(int v=0;v<V;++v)if(has(direct[u],v)&&!has(truth,v))throw runtime_error("2SAT output violates implication");
  return chosen;
 }
};
int lift(int w,int a,int b,int bit){uint32_t z=delbit(w,15-a),low=15-b;return int(((z>>low)<<(low+1))|(uint32_t(bit)<<low)|(z&((1u<<low)-1)));}
bool explicitValid(const Garden&g,const vector<int>&C){vector<int>own(M,-1);set<int>unique(C.begin(),C.end());if(unique.size()!=C.size())return false;for(int w:C)for(auto d:g.desc[w]){if(own[d]>=0)return false;own[d]=w;}return true;}
void selftest(){
 mt19937 rng(723102);uint64_t tested=0;
 for(int m=1;m<=7;++m)for(int trial=0;trial<160;++trial){
  TwoSAT s(m);vector<pair<int,int>>clauses;int n=rng()%(m*5+1);
  for(int j=0;j<n;++j){int u=rng()%(2*m),v=rng()%(2*m);s.conflict(u,v);clauses.push_back({u,v});}
  s.finish();
  for(int t=0;t<10;++t){Mask forbidden{};for(int j=0;j<2*m;++j)if(rng()%6==0)put(forbidden,j);
   bool expected=false;for(int val=0;val<(1<<m);++val){
    bool ok=true;for(int i=0;i<m;++i)if(has(forbidden,2*i+((val>>i)&1)))ok=false;
    for(auto [u,v]:clauses)if(((val>>(u/2))&1)==(u&1)&&((val>>(v/2))&1)==(v&1))ok=false;
    if(ok){expected=true;break;}
   }
   Mask truth{};bool got=s.force(forbidden,truth);if(got!=expected)throw runtime_error("brute force disagreement");
   if(got){auto A=s.assignment(truth);for(int i=0;i<m;++i)if(has(forbidden,2*i+A[i]))throw runtime_error("unit failure");}
   ++tested;
  }
 }
 cout<<"{\"brute_force_unit_instances\":"<<tested<<",\"passed\":true}\n";
}
int main(int argc,char**argv){try{
 if(argc>1&&string(argv[1])=="--test"){selftest();return 0;}
 int a=stoi(argv[1]);double budget=argc>2?stod(argv[2]):600;int addBegin=argc>3?stoi(argv[3]):0,addEnd=argc>4?stoi(argv[4]):65536;
 if(a<0||a>=16||addBegin<0||addEnd>65536||addBegin>addEnd)throw runtime_error("bad range");
 auto start=clock();Garden g(0);vector<int>C;string word;while(cin>>word){if(word.size()!=16||word.find_first_not_of("01")!=string::npos)throw runtime_error("invalid input");C.push_back(stoi(word,nullptr,2));}
 if(C.size()!=226||!explicitValid(g,C))throw runtime_error("requires valid226");
 uint64_t total=0;bool found=false,limited=false;cout<<"{\"puncture\":"<<a<<",\"contexts\":[";
 for(int b=0;b<16&&!found;++b){
  if(b)cout<<",";vector<int>words;for(int w:C)for(int v=0;v<2;++v)words.push_back(lift(w,a,b,v));if(set<int>(words.begin(),words.end()).size()!=452)throw runtime_error("variant domains overlap");
  TwoSAT s(226);vector<vector<int>>owners(M);vector<Mask>occ(M);
  for(int u=0;u<452;++u)for(auto d:g.desc[words[u]]){
   for(int v:owners[d])if(u/2!=v/2)s.conflict(u,v);owners[d].push_back(u);put(occ[d],u);
  }
  s.finish();uint64_t queries=0,directPruned=0,closurePruned=0;bool complete=true;vector<int>answer,neutral;int extra=-1;
  if(s.feasible){
   Mask noUnits{},empty{};if(!s.force(noUnits,empty))throw runtime_error("base feasibility mismatch");auto choices=s.assignment(empty);for(int i=0;i<226;++i)neutral.push_back(words[2*i+choices[i]]);if(!explicitValid(g,neutral))throw runtime_error("invalid base226");
   for(int w=addBegin;w<addEnd;++w){
    if((w&255)==0&&double(clock()-start)/CLOCKS_PER_SEC>=budget){complete=false;limited=true;break;}
    ++queries;Mask forbidden{};
    for(auto d:g.desc[w]){unite(forbidden,occ[d]);if(bad(forbidden))break;}
    if(bad(forbidden)){++directPruned;continue;}
    Mask truth{};if(!s.force(forbidden,truth)){++closurePruned;continue;}
    auto A=s.assignment(truth);for(int i=0;i<226;++i)answer.push_back(words[2*i+A[i]]);answer.push_back(w);if(!explicitValid(g,answer))throw runtime_error("invalid lifted227");extra=w;found=true;break;
   }
  }
  total+=queries;cout<<"{\"insert\":"<<b<<",\"base_satisfiable\":"<<(s.feasible?"true":"false")<<",\"complete\":"<<((complete&&!found)?"true":"false")<<",\"queries\":"<<queries<<",\"direct_pruned\":"<<directPruned<<",\"closure_pruned\":"<<closurePruned<<",\"variants\":";outputArray(words);
  cout<<",\"implication_rows_hex\":[";for(int u=0;u<452;++u){if(u)cout<<",";cout<<"\"";for(auto x:s.direct[u])cout<<hex<<setw(16)<<setfill('0')<<x;cout<<dec<<"\"";}cout<<"],\"neutral226\":";outputArray(neutral);cout<<",\"extra\":"<<extra<<",\"candidate227\":";outputArray(answer);cout<<"}";
  if(limited)break;
 }
 cout<<"],\"candidate_range\":["<<addBegin<<","<<addEnd<<"],\"total_queries\":"<<total<<",\"found_unverified\":"<<(found?"true":"false")<<",\"complete\":"<<((!found&&!limited)?"true":"false")<<",\"cpu_seconds\":"<<double(clock()-start)/CLOCKS_PER_SEC<<",\"scope\":\"All two-choice lifts for each completed coordinate context, plus one word in explicit candidate range; base-unsat contexts reject every extra word. No global bound.\"}\n";return 0;
}catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
