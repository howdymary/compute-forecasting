// Exact maximum independent set of the union of TWO valid deletion codes.
// The noncommon conflict graph is bipartite. Matching gives a minimum cover.
// No negative conclusion outside the explicitly processed parent pairs.
#define main codegarden_old_main
#include "../kernel.cpp"
#undef main
#include <ctime>
#include <set>
#include <queue>
double cpuTime(){return double(clock())/CLOCKS_PER_SEC;}
struct Bipartite{
 int l,r;vector<vector<int>>a;vector<int>mr,ml,visited;int stamp=0,matching=0;
 Bipartite(int L,int R):l(L),r(R),a(L),mr(R,-1),ml(L,-1),visited(R){}
 bool aug(int v){for(int u:a[v]){if(visited[u]==stamp)continue;visited[u]=stamp;if(mr[u]<0||aug(mr[u])){mr[u]=v;ml[v]=u;return true;}}return false;}
 void solve(){for(int v=0;v<l;++v){++stamp;if(aug(v))++matching;}}
 pair<vector<int>,vector<int>>independent(){
  vector<bool>zl(l),zr(r);queue<int>q;for(int v=0;v<l;++v)if(ml[v]<0){zl[v]=true;q.push(v);}
  while(!q.empty()){int v=q.front();q.pop();for(int u:a[v])if(ml[v]!=u&&!zr[u]){zr[u]=true;int w=mr[u];if(w>=0&&!zl[w]){zl[w]=true;q.push(w);}}}
  vector<int>L,R;for(int v=0;v<l;++v)if(zl[v])L.push_back(v);for(int u=0;u<r;++u)if(!zr[u])R.push_back(u);return {L,R};
 }
};
int main(int argc,char**argv){
 try{
  if(argc>1&&string(argv[1])=="--graph"){int l,r,m;cin>>l>>r>>m;Bipartite b(l,r);for(int i=0;i<m;++i){int v,u;cin>>v>>u;if(v<0||v>=l||u<0||u>=r)throw runtime_error("edge");b.a[v].push_back(u);}b.solve();auto ind=b.independent();cout<<"{\"matching\":"<<b.matching<<",\"independent_left\":";outputArray(ind.first);cout<<",\"independent_right\":";outputArray(ind.second);cout<<"}\n";return 0;}
  if(argc<4)throw runtime_error("seconds archive_cap checkpoint");double budget=stod(argv[1]);int archiveCap=stoi(argv[2]);string path=argv[3];Garden g(1320001);vector<vector<int>>parents;set<vector<int>>seen;int size,w;
  while(cin>>size){if(size<1||size>227)throw runtime_error("parent size");vector<int>C;vector<int>occ(M,-1);for(int i=0;i<size;++i){if(!(cin>>w)||w<0||w>=N)throw runtime_error("parent input");C.push_back(w);for(int d:g.desc[w]){if(occ[d]>=0)throw runtime_error("invalid parent descendant collision");occ[d]=w;}}sort(C.begin(),C.end());if(seen.insert(C).second)parents.push_back(C);}
  if(parents.size()<2)throw runtime_error("need parents");int original=parents.size(),best=0;vector<int>winner;for(auto&C:parents)if(int(C.size())>best){best=C.size();winner=C;}
  vector<int>inpool(N),pool;for(auto&C:parents)for(int v:C)if(!inpool[v]){inpool[v]=1;pool.push_back(v);}sort(pool.begin(),pool.end());vector<vector<uint16_t>>conflicts(N);vector<int>marks(N);int token=0;
  for(int v:pool){++token;for(int d:g.desc[v])for(int u:g.inc[d])if(inpool[u]&&u!=v&&marks[u]!=token){marks[u]=token;conflicts[v].push_back(u);}}
  vector<int>rightIndex(N,-1);vector<vector<int>>novel;long long pairs=0,augmentations=0;int activeI=-1,activeJ=-1;double start=cpuTime();bool limited=false,cap=false;vector<string>sample;
  for(size_t i=0;i<parents.size()&&!limited&&best<227;++i)for(size_t j=0;j<i&&best<227;++j){
   activeI=i;activeJ=j;if(cpuTime()-start>=budget){limited=true;break;}++pairs;vector<int>L,R,common;
   set_difference(parents[i].begin(),parents[i].end(),parents[j].begin(),parents[j].end(),back_inserter(L));set_difference(parents[j].begin(),parents[j].end(),parents[i].begin(),parents[i].end(),back_inserter(R));set_intersection(parents[i].begin(),parents[i].end(),parents[j].begin(),parents[j].end(),back_inserter(common));
   for(size_t u=0;u<R.size();++u)rightIndex[R[u]]=u;Bipartite b(L.size(),R.size());
   for(size_t v=0;v<L.size();++v)for(int u:conflicts[L[v]])if(rightIndex[u]>=0)b.a[v].push_back(rightIndex[u]);b.solve();auto ind=b.independent();vector<int>C=common;for(int v:ind.first)C.push_back(L[v]);for(int u:ind.second)C.push_back(R[u]);sort(C.begin(),C.end());
   if(C.size()!=L.size()+R.size()+common.size()-b.matching)throw runtime_error("cover size");for(int u:R)rightIndex[u]=-1;
   if(C.size()>max(parents[i].size(),parents[j].size()))++augmentations;
   if(int(C.size())>best){best=C.size();winner=C;checkpoint(path,winner);}
   if(C.size()>=226&&seen.insert(C).second){if(novel.size()<size_t(archiveCap)){novel.push_back(C);parents.push_back(C);}else cap=true;}
  }
  checkpoint(path,winner);cout<<"{\"original_parent_count\":"<<original<<",\"final_parent_count\":"<<parents.size()<<",\"pairs_processed\":"<<pairs<<",\"cpu_seconds\":"<<cpuTime()-start<<",\"complete\":"<<(!limited&&!cap&&best<227?"true":"false")<<",\"time_limited\":"<<(limited?"true":"false")<<",\"new_parent_cap_reached\":"<<(cap?"true":"false")<<",\"active_i\":"<<activeI<<",\"active_j\":"<<activeJ<<",\"strict_pair_augmentations\":"<<augmentations<<",\"best_size_unverified\":"<<best<<",\"winner\":";outputArray(winner);cout<<",\"novel226_candidates\":[";for(size_t i=0;i<novel.size();++i){if(i)cout<<",";outputArray(novel[i]);}cout<<"]}\n";return 0;
 }catch(const exception&e){cerr<<e.what()<<"\n";return 2;}
}
