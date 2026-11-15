#define CODEGARDEN_TRIPLE_TEST
#include "triple_goal.cpp"
int main(){try{
 mt19937 rng(1523001);int cases=0;
 for(int m=0;m<=12;++m)for(int trial=0;trial<100;++trial){
  int target=1+rng()%9;vector<int>P;for(int i=0;i<m;++i)P.push_back(i);
  vector<vector<uint16_t>>dummy(m);CliqueRepair r(P,dummy,target,10,10000000);r.adj.assign(m*r.W,0);r.fixed={100};
  for(int i=0;i<m;++i)for(int j=0;j<i;++j)if(trial%5==0||rng()%2){r.adj[size_t(i)*r.W+j/64]|=1ull<<(j%64);r.adj[size_t(j)*r.W+i/64]|=1ull<<(i%64);}
  vector<vector<int>>eligible;
  for(unsigned mask=0;mask<(1u<<m);++mask){if(__builtin_popcount(mask)<target)continue;bool ok=true;vector<int>C;for(int i=0;i<m&&ok;++i)if(mask&(1u<<i)){C.push_back(i);for(int j=0;j<i;++j)if((mask&(1u<<j))&&!(r.adj[size_t(i)*r.W+j/64]&(1ull<<(j%64))))ok=false;}C.push_back(100);if(ok){eligible.push_back(C);if(int(C.size())==target+1&&(trial%3==0||rng()%2))r.known.insert(C);}}
  bool expected=false;for(auto C:eligible)if(!r.known.count(C))expected=true;
  r.run();if(r.limited||r.found!=expected)throw runtime_error("triple filtered clique brute mismatch");
  if(r.found){auto C=r.result();C.push_back(100);sort(C.begin(),C.end());if(r.known.count(C)||int(C.size())<target+1)throw runtime_error("triple bad accepted goal");for(int a:r.result())for(int b:r.result())if(a!=b&&!(r.adj[size_t(a)*r.W+b/64]&(1ull<<(b%64))))throw runtime_error("triple bad clique");}
  ++cases;
 }
 cout<<"{\"exhaustive_arbitrary_graph_fixtures\":"<<cases<<",\"filtered_exact_goals_and_eligible_larger_supersets\":true,\"passed\":true}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
