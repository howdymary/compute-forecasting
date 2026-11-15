#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <vector>
using namespace std; using U=uint64_t; using Bits=vector<U>;
struct Solver {
 vector<Bits> adj; int n,blocks,target; double budget; unsigned long long nodes=0; int root_bound=0;
 vector<int> chosen,solution; bool timed=false; chrono::steady_clock::time_point start;
 Solver(vector<Bits> a,int t,double s):adj(std::move(a)),n(adj.size()),blocks((n+63)/64),target(t),budget(s){}
 double elapsed(){return chrono::duration<double>(chrono::steady_clock::now()-start).count();}
 pair<vector<int>,vector<int>> color(Bits remaining){
  vector<int> order,bounds;int c=0;
  while(true){
   bool any=false;for(U w:remaining)if(w){any=true;break;}if(!any)break;
   c++;Bits q=remaining;
   while(true){
    int j=0;while(j<blocks&&!q[j])j++;if(j==blocks)break;
    int v=64*j+__builtin_ctzll(q[j]);U bit=U(1)<<(v%64);
    order.push_back(v);bounds.push_back(c);remaining[j]&=~bit;q[j]&=~bit;
    for(int k=0;k<blocks;k++)q[k]&=~adj[v][k];
   }
  }
  return {order,bounds};
 }
 bool expand(Bits p,int depth){
  nodes++;if((nodes&1023)==1&&elapsed()>budget){timed=true;throw runtime_error("timeout");}
  if(depth>=target){solution=chosen;return true;}
  auto cb=color(p);auto &o=cb.first,&b=cb.second;if(depth==0)root_bound=b.empty()?0:b.back();
  for(int i=int(o.size())-1;i>=0;i--){
   if(depth+b[i]<target)return false;
   int v=o[i];Bits q(blocks);for(int k=0;k<blocks;k++)q[k]=p[k]&adj[v][k];
   chosen.push_back(v);if(expand(std::move(q),depth+1))return true;chosen.pop_back();
   p[v/64]&=~(U(1)<<(v%64));
  }
  return false;
 }
 bool run(){start=chrono::steady_clock::now();Bits p(blocks,~U(0));if(n%64)p.back()=(U(1)<<(n%64))-1;
  try{return expand(std::move(p),0);}catch(const runtime_error &e){if(!timed)throw;return false;}
 }
};
vector<int> descendants(int x,int n=16){
 vector<int>d;for(int i=0;i<n;i++){int y=(x&((1<<i)-1))|((x>>(i+1))<<i);
  for(int j=i;j<n-1;j++)d.push_back((y&((1<<j)-1))|((y>>(j+1))<<j));}
 sort(d.begin(),d.end());d.erase(unique(d.begin(),d.end()),d.end());return d;
}
void tests(){
 mt19937 rng(2271132);int count=0;
 for(int n=2;n<=12;n++)for(int rep=0;rep<32;rep++){
  vector<Bits>a(n,Bits(1));for(int i=0;i<n;i++)for(int j=0;j<i;j++)if(rng()%2){a[i][0]|=U(1)<<j;a[j][0]|=U(1)<<i;}
  int opt=0;for(int mask=0;mask<(1<<n);mask++){bool ok=true;for(int v=0;v<n;v++)if((mask>>v)&1)
   if(U(mask)&~(a[v][0]|(U(1)<<v))){ok=false;break;}if(ok)opt=max(opt,__builtin_popcount(unsigned(mask)));}
  Solver yes(a,opt,10),no(a,opt+1,10);if(!yes.run()||yes.timed||no.run()||no.timed)throw runtime_error("graph fixture");count++;
 }
 for(int x=0;x<64;x++){auto got=descendants(x,6);vector<int> want;
  for(int i=0;i<6;i++)for(int j=i+1;j<6;j++){int y=0;for(int k=5;k>=0;k--)if(k!=i&&k!=j)y=(y<<1)|((x>>k)&1);want.push_back(y);}
  sort(want.begin(),want.end());want.erase(unique(want.begin(),want.end()),want.end());if(got!=want)throw runtime_error("deletion fixture");
 }
 cout<<"{\"graph_fixtures\":"<<count<<",\"deletion_fixtures\":64,\"status\":\"passed\"}\n";
}
void ints(const vector<int>&v){cout<<"[";for(size_t i=0;i<v.size();i++){if(i)cout<<",";cout<<v[i];}cout<<"]";}
int main(int argc,char**argv){try{
 if(argc>1&&string(argv[1])=="--self-test"){tests();return 0;}
 int c;cin>>c;if(c!=226)throw runtime_error("seed cardinality");vector<int>base(c);for(int &w:base)cin>>w;
 int r;cin>>r;vector<int>removed(r);vector<bool>cut(c);for(int &i:removed){cin>>i;if(i<0||i>=c||cut[i])throw runtime_error("removed index");cut[i]=true;}
 int forced,mode;double seconds;cin>>forced>>mode>>seconds;
 if(!cin||forced<0||forced>=65536||r<1||r>96||mode<0||mode>2||seconds<=0||seconds>120)throw runtime_error("bounds");
 vector<vector<int>>D(65536);for(int w=0;w<65536;w++)D[w]=descendants(w);
 vector<int>owner(16384,-1);for(int i=0;i<c;i++)for(int d:D[base[i]]){if(owner[d]>=0)throw runtime_error("seed collision");owner[d]=i;}
 vector<bool>fd(16384);for(int d:D[forced])fd[d]=true;
 for(int d:D[forced])if(owner[d]>=0&&!cut[owner[d]])throw runtime_error("forced incompatible with fixed code");
 vector<int>pool;for(int w=0;w<65536;w++){bool ok=true;for(int d:D[w])if(fd[d]||(owner[d]>=0&&!cut[owner[d]])){ok=false;break;}if(ok)pool.push_back(w);}
 int n=pool.size(),blocks=(n+63)/64;if(n>6000)throw runtime_error("explicit pool resource gate");
 vector<Bits>a(n,Bits(blocks,~U(0)));if(n%64)for(auto &row:a)row.back()=(U(1)<<(n%64))-1;
 vector<vector<int>>inc(16384);for(int i=0;i<n;i++)for(int d:D[pool[i]])inc[d].push_back(i);
 for(int i=0;i<n;i++){a[i][i/64]&=~(U(1)<<(i%64));for(int d:D[pool[i]])for(int j:inc[d])a[i][j/64]&=~(U(1)<<(j%64));}
 vector<int>order(n),degree(n);iota(order.begin(),order.end(),0);unsigned long long edges=0;
 for(int i=0;i<n;i++){for(U w:a[i])degree[i]+=__builtin_popcountll(w);edges+=degree[i];}
 if(mode)stable_sort(order.begin(),order.end(),[&](int x,int y){if(degree[x]!=degree[y])return mode==1?degree[x]>degree[y]:degree[x]<degree[y];return pool[x]<pool[y];});
 vector<Bits>b(n,Bits(blocks));for(int i=0;i<n;i++)for(int j=0;j<n;j++)if((a[order[i]][order[j]/64]>>(order[j]%64))&1)b[i][j/64]|=U(1)<<(j%64);
 Solver solver(std::move(b),r,seconds);bool feasible=solver.run();vector<int>selected;
 if(feasible)for(int i:solver.solution)selected.push_back(pool[order[i]]);
 cout<<"{\"status\":\""<<(feasible?"FEASIBLE":solver.timed?"TIMEOUT":"INFEASIBLE_ENCODED_NEIGHBORHOOD")
  <<"\",\"nodes\":"<<solver.nodes<<",\"seconds\":"<<solver.elapsed()<<",\"root_coloring_bound\":"<<solver.root_bound
  <<",\"pool_count\":"<<n<<",\"compatibility_edges\":"<<edges/2<<",\"ordering\":"<<mode<<",\"required_repair\":"<<r<<",\"pool_words\":";
 ints(pool);cout<<",\"selected_words\":";ints(selected);cout<<"}\n";
 }catch(const exception &e){cerr<<e.what()<<"\n";return 2;}}
