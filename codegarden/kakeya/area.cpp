// Floating proposal kernel. Exact independent checkers alone certify witnesses.
#include <algorithm>
#include <cmath>
#include <numeric>
#include <vector>
struct Line{int m,owner;long double b;bool left;};
extern "C" int cg_area_grad(int n,const double*x,double*area,double*g,int*slabs){
 if(n<2||n>128)return 1;
 std::vector<Line>L;L.reserve(2*n);
 for(int j=0;j<n;++j){
  if(!std::isfinite(x[j]))return 2;
  L.push_back({j+1,j,n*(long double)x[j],true});
  L.push_back({j,j,n*(long double)x[j]+1,false});
 }
 std::vector<long double>events{0,1};
 for(int a=0;a<2*n;++a)for(int b=a+1;b<2*n;++b)if(L[a].m!=L[b].m){
  long double y=(L[b].b-L[a].b)/(L[a].m-L[b].m);
  if(y>0&&y<1)events.push_back(y);
 }
 std::sort(events.begin(),events.end());events.erase(std::unique(events.begin(),events.end()),events.end());
 std::vector<int>order(2*n);std::iota(order.begin(),order.end(),0);
 std::vector<long double>v(2*n),grad(n,0);long double A=0,comp=0;
 for(size_t t=1;t<events.size();++t){
  long double dy=events[t]-events[t-1],mid=(events[t]+events[t-1])/2;
  for(int a=0;a<2*n;++a)v[a]=L[a].b+L[a].m*mid;
  auto less=[&](int a,int b){if(v[a]!=v[b])return v[a]<v[b];if(L[a].left!=L[b].left)return L[a].left;return a<b;};
  // Consecutive slabs differ by line crossings: insertion sort reuses the previous order.
  for(int k=1;k<2*n;++k){int a=order[k],p=k;while(p&&less(a,order[p-1])){order[p]=order[p-1];--p;}order[p]=a;}
  int cover=0;long double u=0;
  for(int a:order){
   if(L[a].left){if(!cover){u-=v[a];grad[L[a].owner]-=dy;}++cover;}
   else{--cover;if(!cover){u+=v[a];grad[L[a].owner]+=dy;}}
  }
  if(cover!=0)return 3;
  long double term=u*dy/n-comp,next=A+term;comp=(next-A)-term;A=next;
 }
 *area=(double)A;for(int j=0;j<n;++j)g[j]=(double)grad[j];*slabs=(int)events.size()-1;
 return std::isfinite(*area)?0:4;
}
