// Stream sparse conflict adjacency only after exact degree/memory profiling.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
unsigned drop(unsigned x,int p){return ((x>>(p+1))<<p)|(x&((1u<<p)-1));}
int main(int argc,char**argv){try{
 if(argc!=4)throw runtime_error("n pool.txt output.graph");int n=stoi(argv[1]),U=1<<n,M=1<<(n-2);vector<int>pool;vector<bool>seen(U);ifstream input(argv[2]);int x;while(input>>x){if(x<0||x>=U||seen[x])throw runtime_error("pool word/duplicate");seen[x]=true;pool.push_back(x);}int N=pool.size();if(!N)throw runtime_error("empty pool");if(n<3||n>16)throw runtime_error("n");
 vector<vector<int>>d(N),inv(M);for(int w=0;w<N;++w){for(int i=0;i<n;++i)for(int j=0;j<n-1;++j)d[w].push_back(drop(drop(pool[w],i),j));sort(d[w].begin(),d[w].end());d[w].erase(unique(d[w].begin(),d[w].end()),d[w].end());for(int a:d[w])inv[a].push_back(w);}
 vector<int>stamp(N,-1),neighbors,degree(N);uint64_t directed=0,incidences=0;
 auto collect=[&](int w){neighbors.clear();for(int a:d[w])for(int v:inv[a])if(v!=w&&stamp[v]!=w){stamp[v]=w;neighbors.push_back(v);}sort(neighbors.begin(),neighbors.end());};
 for(int w=0;w<N;++w){collect(w);degree[w]=neighbors.size();directed+=degree[w];incidences+=d[w].size();}
 uint64_t csr=directed*4+uint64_t(N+1)*8;bool allowed=csr*32<5000ull*1024*1024;
 cerr<<"GRAPH_PROFILE {\"n\":"<<n<<",\"vertices\":"<<N<<",\"edges\":"<<directed/2<<",\"incidences\":"<<incidences<<",\"csr_bytes\":"<<csr<<",\"conservative_solver_bytes\":"<<csr*32<<",\"allowed\":"<<(allowed?"true":"false")<<"}\n";
 if(!allowed)return 3;
 fill(stamp.begin(),stamp.end(),-1);ofstream out(argv[3]);out<<N<<" "<<directed/2<<"\n";
 for(int w=0;w<N;++w){collect(w);if(int(neighbors.size())!=degree[w])throw runtime_error("degree changed");for(size_t i=0;i<neighbors.size();++i){if(i)out<<" ";out<<neighbors[i]+1;}out<<"\n";}
 return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
