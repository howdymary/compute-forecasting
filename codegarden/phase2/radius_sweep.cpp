// General exact k -> k+1 NEW-word exchange. No dense conflict graph.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <string>
#include <unordered_map>
#include <vector>
using namespace std;
uint32_t drop(uint32_t x,int p){return ((x>>(p+1))<<p)|(x&((1u<<p)-1));}
bool compat(const vector<uint16_t>&a,const vector<uint16_t>&b){
 size_t i=0,j=0;while(i<a.size()&&j<b.size()){if(a[i]==b[j])return false;if(a[i]<b[j])++i;else ++j;}return true;
}
uint64_t key(vector<int> values){sort(values.begin(),values.end());uint64_t k=0;for(int w:values)k=(k<<16)|uint16_t(w);return k;}
void arr(const vector<int>&v){cout<<"[";for(size_t i=0;i<v.size();++i){if(i)cout<<",";cout<<v[i];}cout<<"]";}
struct Sweep{
 int n,k;double seconds;vector<vector<uint16_t>>desc;vector<int>code,owner;vector<uint8_t>selected;
 vector<unordered_map<uint64_t,vector<int>>>groups;vector<int>zero,removed,added,pool,answerR,answerA,answerPool;
 uint64_t states=0,checks=0,scanned=0;bool found=false,timed=false;
 chrono::steady_clock::time_point start;
 Sweep(int bits,int radius,double limit):n(bits),k(radius),seconds(limit),desc(1<<n),owner(1<<(n-2),-1),selected(1<<n,0),groups(k+1){
  for(int w=0;w<(1<<n);++w){auto&d=desc[w];for(int i=0;i<n;++i)for(int j=0;j<n-1;++j)d.push_back(drop(drop(w,i),j));
   sort(d.begin(),d.end());d.erase(unique(d.begin(),d.end()),d.end());}
 }
 bool over(){return chrono::duration<double>(chrono::steady_clock::now()-start).count()>=seconds;}
 bool clique(size_t at){
  if(added.size()==size_t(k+1)){found=true;answerR=removed;answerA=added;answerPool=pool;return true;}
  if(added.size()+pool.size()-at<size_t(k+1))return false;
  for(size_t i=at;i<pool.size();++i){
   if((checks&4095)==0&&over()){timed=true;return true;}++checks;bool ok=true;
   for(int w:added)if(!compat(desc[w],desc[pool[i]])){ok=false;break;}
   if(ok){added.push_back(pool[i]);if(clique(i+1))return true;added.pop_back();}
  }
  return false;
 }
 bool examine(){
  ++states;if((states&1023)==0&&over()){timed=true;return true;}
  pool=zero;
  for(int mask=1;mask<(1<<k);++mask){
   vector<int>sub;for(int j=0;j<k;++j)if(mask&(1<<j))sub.push_back(removed[j]);
   auto it=groups[sub.size()].find(key(sub));
   if(it!=groups[sub.size()].end())pool.insert(pool.end(),it->second.begin(),it->second.end());
  }
  if(pool.size()<size_t(k+1))return false;
  sort(pool.begin(),pool.end());pool.erase(unique(pool.begin(),pool.end()),pool.end());added.clear();
  return clique(0);
 }
 bool removals(size_t at){
  if(removed.size()==size_t(k))return examine();
  if(removed.size()+code.size()-at<size_t(k))return false;
  for(size_t i=at;i<code.size();++i){removed.push_back(code[i]);if(removals(i+1))return true;removed.pop_back();}
  return false;
 }
 void run(){
  start=chrono::steady_clock::now();
  for(int w=0;w<(1<<n);++w){
   if((w&1023)==0&&over()){timed=true;return;}++scanned;if(selected[w])continue;
   vector<int>b;
   for(auto d:desc[w]){int v=owner[d];if(v<0||find(b.begin(),b.end(),v)!=b.end())continue;b.push_back(v);if(b.size()>size_t(k))break;}
   if(b.size()>size_t(k))continue;
   if(b.empty())zero.push_back(w);else groups[b.size()][key(b)].push_back(w);
  }
  removals(0);
 }
};
int main(int argc,char**argv){
 try{
  int n=stoi(argv[1]),k=stoi(argv[2]);double sec=stod(argv[3]);if(n<3||n>16||k<1||k>4)throw runtime_error("parameters");
  Sweep s(n,k,sec);string word;
  while(cin>>word){if(word.size()!=size_t(n)||word.find_first_not_of("01")!=string::npos)throw runtime_error("invalid word");
   int w=stoi(word,nullptr,2);if(s.selected[w])throw runtime_error("duplicate");s.selected[w]=1;s.code.push_back(w);
   for(auto d:s.desc[w]){if(s.owner[d]>=0)throw runtime_error("invalid collision");s.owner[d]=w;}}
  s.run();bool complete=!s.timed&&!s.found;
  cout<<"{\"k\":"<<k<<",\"found\":"<<(s.found?"true":"false")<<",\"complete\":"<<(complete?"true":"false")
   <<",\"status\":\""<<(s.found?"FEASIBLE":complete?"EXHAUSTED_EXACT_K_NEW_WORD_EXCHANGES":"TIMEOUT")<<"\",\"removal_sets_checked\":"
   <<s.states<<",\"candidate_checks\":"<<s.checks<<",\"universe_scanned\":"<<s.scanned<<",\"seconds\":"
   <<chrono::duration<double>(chrono::steady_clock::now()-s.start).count()<<",\"removed\":";arr(s.answerR);
  cout<<",\"added\":";arr(s.answerA);cout<<",\"candidate_pool\":";arr(s.answerPool);cout<<"}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}
}
