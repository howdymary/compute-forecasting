// Independent exhaustive arbitrary-graph tests; not deletion-code witnesses.
#define main codegarden_neutral_main
#include "bundle_neutral_goal.cpp"
#undef main
int main(){try{
 mt19937 rng(151121);int tested=0;
 for(int m=0;m<=11;++m)for(int trial=0;trial<100;++trial){
  int k=1+rng()%10;Search q(3,k,10,10000000,0);q.code.resize(k);for(int i=0;i<k;++i)q.code[i]=i;q.BW=1;q.W=m?1:0;q.compat.assign(m*q.W,0);q.tableMask=4095;q.closedUsed.assign(4096,0);q.closedTable.assign(4096,0);q.start=cpu();uint64_t block=(1ull<<k)-1;
  for(int i=0;i<m;++i){q.words.push_back(200+i);q.blocks.push_back({block});q.groups[{block}].push_back(i);}
  for(int i=0;i<m;++i)for(int j=0;j<i;++j)if(trial%5==0||rng()%2){q.compat[i]|=1ull<<j;q.compat[j]|=1ull<<i;}
  vector<vector<int>>feasible;
  for(unsigned mask=0;mask<(1u<<m);++mask){if(__builtin_popcount(mask)<k)continue;bool ok=true;vector<int>C;for(int i=0;i<m&&ok;++i)if(mask&(1u<<i)){C.push_back(200+i);for(int j=0;j<i;++j)if((mask&(1u<<j))&&!(q.compat[i]&(1ull<<j)))ok=false;}if(ok)feasible.push_back(C);}
  for(auto&C:feasible)if(int(C.size())==k&&(trial%3==0||rng()%2))q.knownGoalCodes.insert(C);
  bool expected=false;for(auto&C:feasible)if(!q.knownGoalCodes.count(C))expected=true;
  q.closeFull({block});if(q.limited||q.found!=expected)throw runtime_error("colored full repair brute mismatch");
  if(q.found){auto A=q.answerAdded;sort(A.begin(),A.end());if(q.knownGoalCodes.count(A)||int(A.size())<k)throw runtime_error("invalid goal");for(int a:A)for(int b:A)if(a!=b&&!(q.compat[a-200]&(1ull<<(b-200))))throw runtime_error("invalid clique");}
  ++tested;
 }
 
 // Independently enumerate arbitrary blocker graphs. No connected goal can be missed;
 // disconnected unsaturated goals are deliberately outside the completeness claim.
 int connectedFixtures=0,ambiguousFixtures=0,noGoalFixtures=0;
 for(int trial=0;trial<400;++trial){
  int m=1+rng()%11,k=1+rng()%7;Search q(3,k,10,10000000,0);
  q.code={0,1,2,3,4,5,6};q.BW=1;q.start=cpu();q.W=1;
  vector<uint64_t>B(m);for(int i=0;i<m;++i){int count=1+rng()%min(3,k);while(__builtin_popcountll(B[i])<count)B[i]|=1ull<<(rng()%7);q.words.push_back(200+i);q.blocks.push_back({B[i]});q.groups[{B[i]}].push_back(i);}
  q.compat.assign(m,0);for(int i=0;i<m;++i)for(int j=0;j<i;++j)if(rng()%2){q.compat[i]|=1ull<<j;q.compat[j]|=1ull<<i;}
  q.tableMask=4095;q.closedUsed.assign(4096,0);q.closedTable.assign(4096,0);
  auto candidate=[&](unsigned mask,uint64_t b){vector<int>C;for(int j=0;j<7;++j)if(!(b&(1ull<<j)))C.push_back(j);for(int i=0;i<m;++i)if(mask&(1u<<i))C.push_back(200+i);return C;};
  vector<pair<unsigned,uint64_t>>eligible;
  for(unsigned mask=1;mask<(1u<<m);++mask){uint64_t b=0;bool ok=true;for(int i=0;i<m&&ok;++i)if(mask&(1u<<i)){b|=B[i];for(int j=0;j<i;++j)if((mask&(1u<<j))&&!(q.compat[i]&(1ull<<j)))ok=false;}
   if(ok&&__builtin_popcountll(b)<=k&&__builtin_popcount(mask)>=__builtin_popcountll(b)){eligible.push_back({mask,b});if(__builtin_popcount(mask)==__builtin_popcountll(b)&&rng()%2)q.knownGoalCodes.insert(candidate(mask,b));}}
  bool any=false,connected=false;
  for(auto row:eligible){unsigned mask=row.first;if(q.knownGoalCodes.count(candidate(mask,row.second)))continue;any=true;
   unsigned seen=mask&(~mask+1);bool change=true;while(change){change=false;for(int i=0;i<m;++i)if(seen&(1u<<i))for(int j=0;j<m;++j)if((mask&(1u<<j))&&!(seen&(1u<<j))&&(B[i]&B[j])){seen|=1u<<j;change=true;}}
   if(seen==mask)connected=true;
  }
  q.connectedRun();if(q.limited||(!any&&q.found)||(connected&&!q.found))throw runtime_error("neutral connected-goal exhaustive mismatch");
  if(q.found){auto A=q.answerAdded;uint64_t b=0;for(int w:A)b|=B[w-200];unsigned mask=0;for(int w:A)mask|=1u<<(w-200);if(q.knownGoalCodes.count(candidate(mask,b))||int(A.size())<__builtin_popcountll(b)||__builtin_popcountll(b)>k)throw runtime_error("neutral invalid goal");for(int a:A)for(int b:A)if(a!=b&&!(q.compat[a-200]&(1ull<<(b-200))))throw runtime_error("neutral invalid pair");}
  if(connected)++connectedFixtures;else if(!any)++noGoalFixtures;else ++ambiguousFixtures;
 }
 cout<<"{\"connected_blocker_fixtures\":400,\"connected_goal_cases\":"<<connectedFixtures<<",\"no_eligible_goal_cases\":"<<noGoalFixtures<<",\"disconnected_only_cases_no_completeness_claim\":"<<ambiguousFixtures<<",\"passed\":true}\n";
 cout<<"{\"neutral_saturated_arbitrary_graph_fixtures\":"
<<tested<<",\"includes_filtered_targets_with_larger_extensions\":true,\"passed\":true}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
