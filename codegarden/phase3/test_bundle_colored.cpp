// Independent exhaustive arbitrary-graph tests; not deletion-code witnesses.
#define main codegarden_colored_main
#include "bundle_colored.cpp"
#undef main
int main(){try{
 mt19937 rng(151121);int tested=0;
 for(int m=0;m<=11;++m)for(int trial=0;trial<100;++trial){
  int k=1+rng()%5;Search q(3,k,10,10000000,0);q.code.resize(k);for(int i=0;i<k;++i)q.code[i]=i;q.BW=1;q.W=m?1:0;q.compat.assign(m*q.W,0);q.tableMask=4095;q.closedUsed.assign(4096,0);q.closedTable.assign(4096,0);q.start=cpu();uint64_t block=(1ull<<k)-1;
  for(int i=0;i<m;++i){q.words.push_back(200+i);q.blocks.push_back({block});q.groups[{block}].push_back(i);}
  for(int i=0;i<m;++i)for(int j=0;j<i;++j)if(rng()%2){q.compat[i]|=1ull<<j;q.compat[j]|=1ull<<i;}
  vector<vector<int>>feasible;
  for(unsigned mask=0;mask<(1u<<m);++mask){if(__builtin_popcount(mask)<k+1)continue;bool ok=true;vector<int>C;for(int i=0;i<m&&ok;++i)if(mask&(1u<<i)){C.push_back(200+i);for(int j=0;j<i;++j)if((mask&(1u<<j))&&!(q.compat[i]&(1ull<<j)))ok=false;}if(ok)feasible.push_back(C);}
  for(auto&C:feasible)if(int(C.size())==k+1&&(trial%3==0||rng()%2))q.knownGoalCodes.insert(C);
  bool expected=false;for(auto&C:feasible)if(!q.knownGoalCodes.count(C))expected=true;
  q.closeFull({block});if(q.limited||q.found!=expected)throw runtime_error("colored full repair brute mismatch");
  if(q.found){auto A=q.answerAdded;sort(A.begin(),A.end());if(q.knownGoalCodes.count(A)||int(A.size())<k+1)throw runtime_error("invalid goal");for(int a:A)for(int b:A)if(a!=b&&!(q.compat[a-200]&(1ull<<(b-200))))throw runtime_error("invalid clique");}
  ++tested;
 }
 cout<<"{\"colored_arbitrary_graph_fixtures\":"<<tested<<",\"includes_filtered_targets_with_larger_extensions\":true,\"passed\":true}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
