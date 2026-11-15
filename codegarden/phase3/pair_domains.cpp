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
 vector<int> assignment(Mask truth,bool preferAlternative=false)const{
  vector<int>chosen;
  for(int i=0;i<m;++i){
   if(!has(truth,2*i)&&!has(truth,2*i+1)){
    auto next=truth;unite(next,reach[2*i+(preferAlternative?1:0)]);
    if(!bad(next))truth=next;else{unite(truth,reach[2*i+(preferAlternative?0:1)]);if(bad(truth))throw runtime_error("2SAT extension contradiction");}
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
 int mode=stoi(argv[1]),caseId=stoi(argv[2]),maxContexts=stoi(argv[3]);double budget=stod(argv[4]);string knownPath=argv[5];uint64_t seed=1470011+caseId;
 mt19937_64 rng(seed);auto t0=clock();Garden g(seed);vector<int>C;string word;while(cin>>word){if(word.size()!=16||word.find_first_not_of("01")!=string::npos)throw runtime_error("invalid input");C.push_back(stoi(word,nullptr,2));}
 if(C.size()!=226||!explicitValid(g,C))throw runtime_error("requires valid226");for(int w:C)g.add(w);
 set<vector<int>>known,exported;ifstream kin(knownPath);int m;while(kin>>m){vector<int>A(m);for(auto&w:A)kin>>w;sort(A.begin(),A.end());known.insert(A);}
 vector<vector<int>>banks(226);vector<int>bc(N),oldIndex(N,-1);for(int i=0;i<226;++i)oldIndex[C[i]]=i;
 for(int w=0;w<N;++w)if(oldIndex[w]<0){auto B=g.blockers(w);bc[w]=B.size();if(B.size()>=1&&B.size()<=12)for(int v:B)banks[oldIndex[v]].push_back(w);}
 for(auto&bank:banks)sort(bank.begin(),bank.end(),[&](int a,int b){return bc[a]!=bc[b]?bc[a]<bc[b]:a<b;});
 uint64_t allQueries=0,allDirect=0,allClosure=0;bool found=false,timed=false;int contextsDone=0,novelCount=0;
 cout<<"{\"seed\":"<<seed<<",\"mode\":"<<mode<<",\"contexts\":[";
 for(int iter=0;iter<maxContexts&&!found;++iter){
  if(double(clock()-t0)/CLOCKS_PER_SEC>=budget){timed=true;break;}
  vector<int>alt(226);uint32_t mask=rng()%65536;vector<int>perm(16);iota(perm.begin(),perm.end(),0);
  if(mode==1){int type=iter%3;if(type==0)rotate(perm.begin(),perm.begin()+1+rng()%15,perm.end());else if(type==1){int a=rng()%15,b=a+2+rng()%(15-a);reverse(perm.begin()+a,perm.begin()+b);}else for(int j=0;j<2+iter%7;++j){int a=rng()%15;swap(perm[a],perm[a+1]);}}
  for(int i=0;i<226;++i){
   if(mode==0)alt[i]=C[i]^mask;
   else if(mode==1){int x=0;for(int j:perm)x=(x<<1)|((C[i]>>(15-j))&1);alt[i]=x;}
   else if(banks[i].empty())alt[i]=C[i];
   else{
    auto&bank=banks[i];size_t begin=0;
    if(mode==2&&rng()%5!=0)while(begin<bank.size()&&bc[bank[begin]]<2)++begin;
    if(begin==bank.size())begin=0;
    size_t width=mode==2?min(bank.size()-begin,size_t(8+iter%121)):bank.size()-begin;
    alt[i]=bank[begin+rng()%width];
   }
  }
  vector<int>words;for(int i=0;i<226;++i){words.push_back(C[i]);words.push_back(alt[i]);}
  TwoSAT s(226);vector<vector<int>>owners(M);vector<Mask>occ(M);
  for(int u=0;u<452;++u)for(auto d:g.desc[words[u]]){for(int v:owners[d])if(u/2!=v/2)s.conflict(u,v);owners[d].push_back(u);put(occ[d],u);}
  s.finish();if(!s.feasible)throw runtime_error("original assignment must be feasible");
  int usable=0;for(int i=0;i<226;++i)if(alt[i]!=C[i]&&!bad(s.reach[2*i+1]))++usable;
  vector<int>novel,answer;uint64_t queries=0,direct=0,closure=0;bool complete=true;
  Mask none{},truth{};if(!s.force(none,truth))throw runtime_error("base failure");auto A=s.assignment(truth,true);vector<int>neutral;for(int i=0;i<226;++i)neutral.push_back(words[2*i+A[i]]);sort(neutral.begin(),neutral.end());if(!explicitValid(g,neutral))throw runtime_error("bad neutral");
  if(!known.count(neutral)&&exported.insert(neutral).second&&novelCount<16){novel=neutral;++novelCount;}
  if(usable==0){if(!g.freeWords.empty())throw runtime_error("base not maximal");}
  else for(int w=0;w<N;++w){
   if((w&255)==0&&double(clock()-t0)/CLOCKS_PER_SEC>=budget){complete=false;timed=true;break;}
   ++queries;Mask forbidden{};for(auto d:g.desc[w]){unite(forbidden,occ[d]);if(bad(forbidden))break;}
   if(bad(forbidden)){++direct;continue;}Mask forced{};if(!s.force(forbidden,forced)){++closure;continue;}
   auto values=s.assignment(forced,true);for(int i=0;i<226;++i)answer.push_back(words[2*i+values[i]]);answer.push_back(w);if(!explicitValid(g,answer))throw runtime_error("bad227");found=true;break;
  }
  if(iter)cout<<",";cout<<"{\"iteration\":"<<iter<<",\"alternative_words\":";outputArray(alt);cout<<",\"usable_alternatives\":"<<usable<<",\"complete\":"<<((complete&&!found)?"true":"false")<<",\"queries\":"<<queries<<",\"direct_pruned\":"<<direct<<",\"closure_pruned\":"<<closure<<",\"zero_usable_maximal_base_shortcut\":"<<((usable==0)?"true":"false")<<",\"novel226_unverified\":";outputArray(novel);cout<<",\"candidate227_unverified\":";outputArray(answer);cout<<"}";++contextsDone;allQueries+=queries;allDirect+=direct;allClosure+=closure;
  if(timed)break;
 }
 cout<<"],\"contexts_processed\":"<<contextsDone<<",\"requested_contexts\":"<<maxContexts<<",\"total_queries\":"<<allQueries<<",\"direct_pruned\":"<<allDirect<<",\"closure_pruned\":"<<allClosure<<",\"found_unverified\":"<<(found?"true":"false")<<",\"timed_out\":"<<(timed?"true":"false")<<",\"cpu_seconds\":"<<double(clock()-t0)/CLOCKS_PER_SEC<<",\"scope\":\"Each complete context exactly tests one variant per original group plus any one arbitrary extra word. Finite sampled domains only, never all possible replacement choices or global optimality.\"}\n";return 0;
}catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
