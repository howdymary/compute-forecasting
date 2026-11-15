// Algorithm-only abstract compatibility fixtures; not binary-code witnesses.
#define main codegarden_bundle_main
#include "bundle_novel.cpp"
#undef main
Search fixture(){
 Search q(3,1,10,1000000,0);q.code={0};q.BW=1;q.W=1;q.words={200,201,202};q.blocks={{1},{1},{1}};q.compat={6,5,3};q.groups[{1}]={0,1,2};q.tableMask=4095;q.closedUsed.assign(4096,0);q.closedTable.assign(4096,0);q.start=cpu();return q;
}
int main(){try{
 auto q=fixture();q.knownGoalCodes.insert({200,201});q.closeFull({1});if(!q.found||q.limited||q.filteredKnownGoals<1)throw runtime_error("did not continue past known first goal");vector<int>A=q.answerAdded;sort(A.begin(),A.end());if(A==vector<int>{200,201})throw runtime_error("returned excluded code");
 auto r=fixture();for(int mask=1;mask<8;++mask)if(__builtin_popcount(unsigned(mask))>=2){vector<int>C;for(int i=0;i<3;++i)if(mask&(1<<i))C.push_back(200+i);r.knownGoalCodes.insert(C);}r.closeFull({1});if(r.found||r.limited||r.filteredKnownGoals==0)throw runtime_error("all-filtered fixture failed");
 cout<<"{\"goal_filter_tests\":2,\"passed\":true,\"larger_goal_not_pruned_after_filtered_pair\":true}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
