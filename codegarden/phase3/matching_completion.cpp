// Bipartite-union MIS plus bounded arbitrary outside words. Search output is untrusted.
#define main codegarden_existing_kernel_main
#include "../kernel.cpp"
#undef main
#include <ctime>
#include <set>
#include <functional>
#include <unordered_map>
using Mask=array<uint64_t,8>;
int countBits(const Mask&a){int k=0;for(auto x:a)k+=__builtin_popcountll(x);return k;}
bool bit(const Mask&a,int i){return (a[i/64]>>(i%64))&1;}
void setBit(Mask&a,int i){a[i/64]|=1ull<<(i%64);}
Mask join(Mask a,const Mask&b){for(int j=0;j<8;++j)a[j]|=b[j];return a;}
struct MaskHash{size_t operator()(const Mask&a)const{size_t h=0;for(auto x:a)h^=hash<uint64_t>{}(x)+0x9e3779b97f4a7c15ull+(h<<6)+(h>>2);return h;}};
struct Bipartite{
 int l,r;vector<vector<int>>adj;
 Bipartite(int a,int b):l(a),r(b),adj(a){}
 struct Result{int matching;vector<int>left,right;vector<pair<int,int>>pairs;};
 Result solve(const vector<char>&offL,const vector<char>&offR)const{
  vector<int>ml(l,-1),mr(r,-1);int k=0;
  for(int root=0;root<l;++root)if(!offL[root]){
   vector<char>seen(r,0);
   function<bool(int)>dfs=[&](int u){for(int v:adj[u])if(!offR[v]&&!seen[v]){seen[v]=1;if(mr[v]<0||dfs(mr[v])){ml[u]=v;mr[v]=u;return true;}}return false;};
   if(dfs(root))++k;
  }
  vector<char>zl(l,0),zr(r,0);vector<int>q;
  for(int i=0;i<l;++i)if(!offL[i]&&ml[i]<0){zl[i]=1;q.push_back(i);}
  for(size_t it=0;it<q.size();++it){int u=q[it];for(int v:adj[u])if(!offR[v]&&ml[u]!=v&&!zr[v]){zr[v]=1;if(mr[v]>=0&&!zl[mr[v]]){zl[mr[v]]=1;q.push_back(mr[v]);}}}
  Result out{k,{},{},{}};for(int i=0;i<l;++i)if(ml[i]>=0)out.pairs.push_back({i,ml[i]});for(int i=0;i<l;++i)if(!offL[i]&&zl[i])out.left.push_back(i);
  for(int j=0;j<r;++j)if(!offR[j]&&!zr[j])out.right.push_back(j);
  vector<char>selectedR(r,0);for(int v:out.right)selectedR[v]=1;for(int u:out.left)for(int v:adj[u])if(selectedR[v])throw runtime_error("MIS cover extraction failed");
  int active=0;for(auto x:offL)active+=!x;for(auto x:offR)active+=!x;if(int(out.left.size()+out.right.size())!=active-k)throw runtime_error("Konig cardinality failed");return out;
 }
};
void testMatching(){
 mt19937 rng(149113);int tested=0;
 for(int l=0;l<=5;++l)for(int r=0;r<=5;++r)for(int t=0;t<40;++t){
  Bipartite g(l,r);for(int i=0;i<l;++i)for(int j=0;j<r;++j)if(rng()%2)g.adj[i].push_back(j);
  vector<char>a(l),b(r);for(auto&x:a)x=rng()%4==0;for(auto&x:b)x=rng()%4==0;
  auto q=g.solve(a,b);int expected=0;
  for(int mask=0;mask<(1<<(l+r));++mask){bool ok=true;for(int i=0;i<l;++i)if(a[i]&&(mask&(1<<i)))ok=false;for(int j=0;j<r;++j)if(b[j]&&(mask&(1<<(l+j))))ok=false;
   for(int i=0;i<l;++i)if(mask&(1<<i))for(int j:g.adj[i])if(mask&(1<<(l+j)))ok=false;if(ok)expected=max(expected,__builtin_popcount(unsigned(mask)));}
  if(int(q.left.size()+q.right.size())!=expected)throw runtime_error("brute MIS disagreement");
  vector<char>noneL(l,0),noneR(r,0);auto base=g.solve(noneL,noneR);int removed=0,touched=0;for(auto x:a)removed+=x;for(auto x:b)removed+=x;for(auto [u,v]:base.pairs)touched+=(a[u]||b[v]);int upper=l+r-removed-base.matching+touched;if(upper<expected)throw runtime_error("matching deletion upper bound invalid");++tested;
 }
 cout<<"{\"brute_force_bipartite_deletion_cases\":"<<tested<<",\"passed\":true}\n";
}
bool valid(const Garden&g,const vector<int>&C){set<int>s(C.begin(),C.end());if(s.size()!=C.size())return false;vector<int>o(M,-1);for(int w:C)for(auto d:g.desc[w]){if(o[d]>=0)return false;o[d]=w;}return true;}

template<class Conflict>bool insufficientColors(const vector<int>&P,int need,Conflict conflict){
 if(need<=0)return false;vector<vector<int>>classes;
 for(int v:P){bool placed=false;for(auto&group:classes){bool ok=true;for(int u:group)if(!conflict(v,u)){ok=false;break;}if(ok){group.push_back(v);placed=true;break;}}
  if(!placed){classes.push_back({v});if(int(classes.size())>=need)return false;}}
 return int(classes.size())<need;
}
void testOutsideColor(){
 mt19937 rng(154101);int tested=0;
 for(int n=0;n<=11;++n)for(int t=0;t<60;++t){
  vector<vector<bool>>conflict(n,vector<bool>(n));for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)conflict[i][j]=conflict[j][i]=rng()%2;
  int maximum=0;for(int mask=0;mask<(1<<n);++mask){bool ok=true;for(int i=0;i<n;++i)if(mask&(1<<i))for(int j=i+1;j<n;++j)if((mask&(1<<j))&&conflict[i][j])ok=false;if(ok)maximum=max(maximum,__builtin_popcount(unsigned(mask)));}
  vector<int>P(n);iota(P.begin(),P.end(),0);
  for(int need=1;need<=7;++need){bool pruned=insufficientColors(P,need,[&](int a,int b){return conflict[a][b];});if(pruned&&maximum>=need)throw runtime_error("unsafe outside color bound");++tested;}
 }
 cout<<"{\"outside_color_bruteforce_targets\":"<<tested<<",\"passed\":true}\n";
}
struct Research{
 Garden g;vector<int>A,B,U,L,R,common;vector<int>ui,li,ri;vector<Mask>blocked,hitPairs;Bipartite graph;int baseAlpha=0;vector<pair<int,int>>basePairs;uint64_t cheapPrunes=0,memoClears=0,colorPrunes=0,candidateFilters=0;
 unordered_map<Mask,int,MaskHash>memo;set<vector<int>>known,exported;vector<vector<int>>solutions;double start,budget;uint64_t matchingCalls=0,memoHits=0,nodes=0;bool found=false,limited=false;vector<int>occupied,picked;int K=0,threshold=0;vector<int>pool;uint64_t rootsComplete=0;int activeRoot=-1;
 Research(vector<int>a,vector<int>b,double sec):g(0),A(a),B(b),ui(N,-1),li(N,-1),ri(N,-1),blocked(N),hitPairs(N),graph(0,0),start(double(clock())/CLOCKS_PER_SEC),budget(sec),occupied(M,0){
  if(A.size()!=225||B.size()!=225||!valid(g,A)||!valid(g,B))throw runtime_error("requires two valid225 parents");
  set<int>sa(A.begin(),A.end()),sb(B.begin(),B.end());for(int w=0;w<N;++w)if(sa.count(w)||sb.count(w)){ui[w]=U.size();U.push_back(w);if(sa.count(w)&&sb.count(w))common.push_back(w);else if(sa.count(w)){li[w]=L.size();L.push_back(w);}else{ri[w]=R.size();R.push_back(w);}}
  graph=Bipartite(L.size(),R.size());vector<vector<int>>owners(M);for(int w:U)for(auto d:g.desc[w])owners[d].push_back(w);
  vector<set<int>>edges(L.size());
  for(int u=0;u<int(L.size());++u)for(auto d:g.desc[L[u]])for(int v:owners[d])if(ri[v]>=0)edges[u].insert(ri[v]);
  for(int u=0;u<int(L.size());++u)graph.adj[u]=vector<int>(edges[u].begin(),edges[u].end());
  for(int w:common)for(auto d:g.desc[w])for(int v:owners[d])if(v!=w)throw runtime_error("common union vertex not isolated");
  vector<char>noneL(L.size(),0),noneR(R.size(),0);auto base=graph.solve(noneL,noneR);baseAlpha=U.size()-base.matching;vector<int>pairIndex(U.size(),-1);
  for(auto [a,b]:base.pairs){int id=basePairs.size();basePairs.push_back({L[a],R[b]});pairIndex[ui[L[a]]]=id;pairIndex[ui[R[b]]]=id;}
  for(int w=0;w<N;++w){
   for(auto d:g.desc[w])for(int v:owners[d])setBit(blocked[w],ui[v]);
   for(int chunk=0;chunk<8;++chunk){auto x=blocked[w][chunk];while(x){int v=chunk*64+__builtin_ctzll(x);x&=x-1;if(pairIndex[v]>=0)setBit(hitPairs[w],pairIndex[v]);}}
  }
 }
 bool over(){if(double(clock())/CLOCKS_PER_SEC-start>=budget){limited=true;return true;}return false;}
 int alpha(const Mask&mask,vector<int>*witness=nullptr){
  if(!witness){auto it=memo.find(mask);if(it!=memo.end()){++memoHits;return it->second;}}
  vector<char>a(L.size()),b(R.size());for(size_t i=0;i<L.size();++i)a[i]=bit(mask,ui[L[i]]);for(size_t i=0;i<R.size();++i)b[i]=bit(mask,ui[R[i]]);
  auto q=graph.solve(a,b);++matchingCalls;int commonLeft=0;for(int w:common)commonLeft+=!bit(mask,ui[w]);int value=commonLeft+q.left.size()+q.right.size();
  if(memo.size()>=500000){memo.clear();++memoClears;}memo[mask]=value;
  if(witness){witness->clear();for(int w:common)if(!bit(mask,ui[w]))witness->push_back(w);for(int i:q.left)witness->push_back(L[i]);for(int i:q.right)witness->push_back(R[i]);sort(witness->begin(),witness->end());if(!valid(g,*witness))throw runtime_error("invalid bipartite MIS");}
  return value;
 }
 void inspect(const Mask&mask,int size){
  if(size+int(picked.size())<226)return;if(size+int(picked.size())<227&&(solutions.size()>=16||nodes%17!=0))return;
  vector<int>C;alpha(mask,&C);C.insert(C.end(),picked.begin(),picked.end());sort(C.begin(),C.end());
  if(!valid(g,C))throw runtime_error("invalid augmentation output");
  if(C.size()>=227){solutions.push_back(C);found=true;}
  else if(!known.count(C)&&exported.insert(C).second&&solutions.size()<16)solutions.push_back(C);
 }
 bool compatible(int w){for(auto d:g.desc[w])if(occupied[d])return false;return true;}
 bool outsideConflict(int a,int b)const{
  const auto&A=g.desc[a];const auto&B=g.desc[b];size_t i=0,j=0;while(i<A.size()&&j<B.size()){if(A[i]==B[j])return true;if(A[i]<B[j])++i;else ++j;}return false;
 }
 vector<int>filterCandidates(const vector<int>&P,int begin,const Mask&mask,const Mask&hits){
  vector<int>next;
  for(int j=begin;j<int(P.size());++j){
   if((j&1023)==0&&over())break;int id=P[j],w=pool[id];++candidateFilters;if(!compatible(w))continue;
   if(baseAlpha-countBits(join(mask,blocked[w]))+countBits(join(hits,hitPairs[w]))<threshold){++cheapPrunes;continue;}next.push_back(id);
  }
  return next;
 }
 void dfs(const vector<int>&P,const Mask&mask,const Mask&hits,int currentAlpha){
  ++nodes;if((nodes&255)==0&&over())return;inspect(mask,currentAlpha);if(found||int(picked.size())==K)return;
  int need=max(0,227-currentAlpha-int(picked.size()));if(currentAlpha+K<227||int(P.size())<need)return;
  if(P.size()<=64&&need>1&&insufficientColors(P,need,[&](int a,int b){return outsideConflict(pool[a],pool[b]);})){++colorPrunes;return;}
  for(int j=0;j<int(P.size());++j){
   if(int(P.size())-j<need)break;if((j&1023)==0&&over())return;int w=pool[P[j]];
   Mask next=join(mask,blocked[w]),nextHits=join(hits,hitPairs[w]);int a=alpha(next);if(a+K<227)continue;
   picked.push_back(w);for(auto d:g.desc[w])++occupied[d];if(a+int(picked.size())>=227)inspect(next,a);auto child=found?vector<int>{}:filterCandidates(P,j+1,next,nextHits);
   if(!limited&&!found)dfs(child,next,nextHits,a);
   for(auto d:g.desc[w])--occupied[d];picked.pop_back();if(found||limited)return;
  }
 }
 void run(int firstK,int lastK,int resumeRoot,const string&expectedPoolPath){
  Mask empty{};int base=alpha(empty);inspect(empty,base);cout<<"{\"union_size\":"<<U.size()<<",\"left\":"<<L.size()<<",\"right\":"<<R.size()<<",\"common\":"<<common.size()<<",\"union_alpha\":"<<base<<",\"levels\":[";bool first=true;
  for(K=firstK;K<=lastK&&!found;++K){
   if(over())break;threshold=227-K;pool.clear();rootsComplete=0;activeRoot=-1;uint64_t filterQueries=0;bool filterComplete=true;
   for(int w=0;w<N;++w)if(ui[w]<0){
    if((w&255)==0&&over()){filterComplete=false;break;}
    if(baseAlpha-countBits(blocked[w])+countBits(hitPairs[w])<threshold){++cheapPrunes;continue;}
    ++filterQueries;if(alpha(blocked[w])>=threshold)pool.push_back(w);
   }
   vector<int>originalPool=pool;
   if(filterComplete){
    // Ordering changes traversal only, never the candidate set.
    stable_sort(pool.begin(),pool.end(),[&](int a,int b){int aa=alpha(blocked[a]),bb=alpha(blocked[b]);return aa!=bb?aa>bb:a<b;});
    if(K==firstK&&expectedPoolPath!="-"){ifstream expected(expectedPoolPath);int n;if(!(expected>>n)||n!=int(pool.size()))throw runtime_error("resumed pool size differs");for(int w:pool){int v;if(!(expected>>v)||v!=w)throw runtime_error("resumed pool order differs");}if(resumeRoot<0||resumeRoot>int(pool.size()))throw runtime_error("invalid resume prefix");}
    for(int root=(K==firstK?resumeRoot:0);root<int(pool.size())&&!found&&!limited;++root){
     activeRoot=root;int w=pool[root];picked={w};for(auto d:g.desc[w])++occupied[d];if(alpha(blocked[w])+1>=227)inspect(blocked[w],alpha(blocked[w]));vector<int>tail(pool.size()-root-1);iota(tail.begin(),tail.end(),root+1);auto candidates=found?vector<int>{}:filterCandidates(tail,0,blocked[w],hitPairs[w]);if(!limited&&!found)dfs(candidates,blocked[w],hitPairs[w],alpha(blocked[w]));for(auto d:g.desc[w])--occupied[d];picked.clear();
     if(!found&&!limited)++rootsComplete;
    }
   }
   if(!first)cout<<",";first=false;cout<<"{\"outside_limit\":"<<K<<",\"required_union_size\":"<<threshold<<",\"filter_complete\":"<<(filterComplete?"true":"false")<<",\"filter_matching_queries\":"<<filterQueries<<",\"candidate_pool\":";outputArray(originalPool);cout<<",\"search_order\":";outputArray(pool);cout<<",\"prior_completed_roots\":"<<(K==firstK?resumeRoot:0)<<",\"new_completed_roots\":"<<rootsComplete<<",\"completed_roots\":"<<rootsComplete+(K==firstK?resumeRoot:0)<<",\"active_root\":"<<activeRoot<<",\"complete\":"<<((filterComplete&&!limited&&!found)?"true":"false")<<",\"cpu_seconds_cumulative\":"<<double(clock())/CLOCKS_PER_SEC-start<<"}";
   if(limited)break;
  }
  cout<<"],\"solutions_unverified\":[";for(size_t i=0;i<solutions.size();++i){if(i)cout<<",";outputArray(solutions[i]);}cout<<"],\"outside_color_prunes\":"<<colorPrunes<<",\"candidate_filter_tests\":"<<candidateFilters<<",\"cheap_matching_bound_prunes\":"<<cheapPrunes<<",\"memo_clears\":"<<memoClears<<",\"base_matching_words\":[";for(size_t i=0;i<basePairs.size();++i){if(i)cout<<",";cout<<"["<<basePairs[i].first<<","<<basePairs[i].second<<"]";}cout<<"],\"matching_calls\":"<<matchingCalls<<",\"memo_hits\":"<<memoHits<<",\"nodes\":"<<nodes<<",\"found227_unverified\":"<<(found?"true":"false")<<",\"timed_out\":"<<(limited?"true":"false")<<",\"cpu_seconds\":"<<double(clock())/CLOCKS_PER_SEC-start<<",\"scope\":\"Full two-parent union with the explicitly reported outside-word limit, continuing previously closed smaller limits for each completed level; exact bipartite matching after outside conflicts. Interrupted roots/filters remain open. Not all codes or global optimality.\"}\n";
 }
};

#include <climits>

double nowCPU(){return double(clock())/CLOCKS_PER_SEC;}
int main(int argc,char**argv){try{
 if(argc>1&&string(argv[1])=="--test"){testMatching();return 0;}
 if(argc<7)throw runtime_error("seconds seed adaptive checkpoint knownfile corefile");
 double seconds=stod(argv[1]);uint64_t seed=stoull(argv[2]);bool adaptive=stoi(argv[3]);string path=argv[4];vector<int>A,B;string x;
 for(int i=0;i<450;++i){if(!(cin>>x)||x.size()!=16||x.find_first_not_of("01")!=string::npos)throw runtime_error("parent input");(i<225?A:B).push_back(stoi(x,nullptr,2));}
 double actualStart=nowCPU();Research r(A,B,seconds);mt19937_64 rng(seed);ifstream known(argv[5]);int n,w;while(known>>n){vector<int>C(n);for(auto&v:C)known>>v;sort(C.begin(),C.end());r.known.insert(C);}
 vector<unsigned char>coreMember(N);array<Mask,4>coreMasks{};array<int,4>coreU{};ifstream cores(argv[6]);for(int k=0;k<4;++k){int size;if(!(cores>>size)||size!=216)throw runtime_error("core file");for(int j=0;j<size;++j){cores>>w;if(w<0||w>=N)throw runtime_error("core word");coreMember[w]|=1u<<k;if(r.ui[w]>=0){setBit(coreMasks[k],r.ui[w]);++coreU[k];}}}
 vector<int>outside,low;for(int w=0;w<N;++w)if(r.ui[w]<0)outside.push_back(w);low=outside;sort(low.begin(),low.end(),[&](int a,int b){return r.g.desc[a].size()!=r.g.desc[b].size()?r.g.desc[a].size()<r.g.desc[b].size():a<b;});if(low.size()>8192)low.resize(8192);
 vector<int>T,bestT,bestC;Mask blocked{},hits{};array<int,4>outsideCore{};int bestSize=0,activeK=8,stale=0;long long bestUtility=LLONG_MIN;uint64_t cycles=0,evaluations=0,prunes=0,samples=0,duplicates=0;vector<int>stamp(N);int tag=0;vector<vector<int>>reservoir,bank;set<vector<int>>seenT;vector<string>events;
 auto rebuild=[&](){blocked={};hits={};outsideCore={};fill(r.occupied.begin(),r.occupied.end(),0);for(int u:T){blocked=join(blocked,r.blocked[u]);hits=join(hits,r.hitPairs[u]);for(int d:r.g.desc[u])++r.occupied[d];for(int k=0;k<4;++k)if(coreMember[u]&(1u<<k))++outsideCore[k];}};
 auto excess=[&](const Mask&m,const array<int,4>&oc){int e=0;for(int k=0;k<4;++k){Mask overlap{};for(int j=0;j<8;++j)overlap[j]=m[j]&coreMasks[k][j];e=max(e,coreU[k]-countBits(overlap)+oc[k]-210);}return max(0,e);};
 auto observe=[&](){
  vector<int>C;int alpha=r.alpha(blocked,&C);C.insert(C.end(),T.begin(),T.end());sort(C.begin(),C.end());if(!valid(r.g,C)||int(C.size())!=alpha+int(T.size()))throw runtime_error("invalid matching completion");
  int score=C.size();long long util=100ll*score-110*excess(blocked,outsideCore);
  if(score>bestSize||(score==bestSize&&util>bestUtility)){bestSize=score;bestUtility=util;bestC=C;bestT=T;checkpoint(path,C);}
  auto key=T;sort(key.begin(),key.end());if(score>=223&&seenT.insert(key).second){if(reservoir.size()<64)reservoir.push_back(T);else reservoir[rng()%reservoir.size()]=T;}
  if(score==225&&bank.size()<16){bool diverse=true;for(auto&D:bank){vector<int>I;set_intersection(C.begin(),C.end(),D.begin(),D.end(),back_inserter(I));if(I.size()>220){diverse=false;break;}}if(diverse)bank.push_back(C);}
  r.picked=T;r.nodes+=17;r.inspect(blocked,alpha);return score;
 };
 observe();double lastSave=nowCPU();ofstream changes(path+".events.jsonl");
 while(!r.over()&&!r.found){
  ++cycles;int priorBest=bestSize;int penalty=(cycles/64)%2?0:110;
  if(!T.empty()){shuffle(T.begin(),T.end(),rng);int ruin=1+rng()%min(6,int(T.size()));T.resize(T.size()-ruin);}
  if(stale>=64){if(adaptive){int old=activeK;activeK=activeK<16?activeK+2:8;changes<<"{\"cycle\":"<<cycles<<",\"from\":"<<old<<",\"to\":"<<activeK<<",\"reason\":\"empirical_stagnation_not_exhaustion\",\"cpu_seconds\":"<<nowCPU()-r.start<<"}\n";changes.flush();}if(!reservoir.empty())T=reservoir[rng()%reservoir.size()];if(int(T.size())>activeK)T.resize(activeK);stale=0;}
  rebuild();
  while(int(T.size())<activeK&&!r.over()&&!r.found){
   ++tag;int pick=-1;long long score=LLONG_MIN;int ties=0;Mask pickB{},pickH{};array<int,4>pickCore{};
   for(int attempt=0;attempt<512&&!r.over();++attempt){
    ++samples;int v=(rng()%4==0?low[rng()%low.size()]:outside[rng()%outside.size()]);if(stamp[v]==tag){++duplicates;continue;}stamp[v]=tag;if(!r.compatible(v))continue;
    auto mb=join(blocked,r.blocked[v]),mh=join(hits,r.hitPairs[v]);auto oc=outsideCore;for(int k=0;k<4;++k)if(coreMember[v]&(1u<<k))++oc[k];
    int upper=r.baseAlpha-countBits(mb)+countBits(mh)+T.size()+1;long long bound=100ll*upper-penalty*excess(mb,oc);
    if(upper<227&&bound<score){++prunes;continue;}
    int value=r.alpha(mb)+T.size()+1;++evaluations;long long utility=100ll*value-penalty*excess(mb,oc);
    if(value>=227){pick=v;pickB=mb;pickH=mh;pickCore=oc;break;}
    if(utility>score){score=utility;pick=v;pickB=mb;pickH=mh;pickCore=oc;ties=1;}else if(utility==score&&rng()%++ties==0){pick=v;pickB=mb;pickH=mh;pickCore=oc;}
   }
   if(pick<0)break;T.push_back(pick);blocked=pickB;hits=pickH;outsideCore=pickCore;for(int d:r.g.desc[pick])++r.occupied[d];observe();
  }
  observe();if(bestSize>priorBest)stale=0;else ++stale;
  if(nowCPU()-lastSave>=10){checkpoint(path,bestC);lastSave=nowCPU();}
 }
 checkpoint(path,bestC);cout<<"{\"seed\":"<<seed<<",\"adaptive\":"<<(adaptive?"true":"false")<<",\"nominal_cpu_seconds\":"<<seconds<<",\"native_cpu_including_initialization\":"<<nowCPU()-actualStart<<",\"search_cpu_seconds\":"<<nowCPU()-r.start<<",\"cycles\":"<<cycles<<",\"matching_evaluations\":"<<evaluations<<",\"matching_calls\":"<<r.matchingCalls<<",\"memo_hits\":"<<r.memoHits<<",\"memo_clears\":"<<r.memoClears<<",\"sample_occurrences\":"<<samples<<",\"duplicate_sample_occurrences\":"<<duplicates<<",\"utility_prunes\":"<<prunes<<",\"active_outside_limit\":"<<activeK<<",\"best_size_unverified\":"<<bestSize<<",\"best\":";outputArray(bestC);cout<<",\"best_outside\":";outputArray(bestT);cout<<",\"novel226_candidates\":[";for(size_t i=0;i<r.solutions.size();++i){if(i)cout<<",";outputArray(r.solutions[i]);}cout<<"],\"bank225_unverified\":[";for(size_t i=0;i<bank.size();++i){if(i)cout<<",";outputArray(bank[i]);}cout<<"],\"scope\":\"Heuristic outside-set ruin/recreate with exact bipartite completion. No exhaustion or global absence claim. The alternating core-upper-count penalty is a heuristic, not a necessary cut. Every exported positive still requires independent verification.\"}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
