// Exact nonnegative integer autoconvolution certificate: three NTT primes + CRT.
// Search code cannot redefine the score. Output is an exact rational.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <boost/multiprecision/cpp_int.hpp>
using u128=unsigned __int128;
using u256=boost::multiprecision::uint256_t;
uint32_t power(uint64_t a,uint64_t e,uint32_t p){uint64_t z=1;while(e){if(e&1)z=z*a%p;a=a*a%p;e>>=1;}return z;}
bool prime(uint32_t p){if(p<2)return false;for(uint32_t d=2;uint64_t(d)*d<=p;++d)if(p%d==0)return false;return true;}
void ntt(std::vector<uint32_t>&a,bool inverse,uint32_t p){
 size_t n=a.size();
 for(size_t i=1,j=0;i<n;++i){size_t bit=n>>1;for(;j&bit;bit>>=1)j^=bit;j^=bit;if(i<j)std::swap(a[i],a[j]);}
 for(size_t len=2;len<=n;len<<=1){
  uint32_t root=power(3,(p-1)/len,p);if(inverse)root=power(root,p-2,p);
  for(size_t i=0;i<n;i+=len){
   uint64_t w=1;
   for(size_t j=0;j<len/2;++j){
    uint32_t u=a[i+j],v=uint64_t(a[i+j+len/2])*w%p;
    uint32_t sum=u+v;a[i+j]=sum>=p?sum-p:sum;a[i+j+len/2]=u>=v?u-v:u+p-v;w=w*root%p;
   }
  }
 }
 if(inverse){uint32_t inv=power(n%p,p-2,p);for(auto&x:a)x=uint64_t(x)*inv%p;}
}
u256 wide(u128 x){u256 y=uint64_t(x>>64);y<<=64;y+=uint64_t(x);return y;}
std::string dec(u128 x){if(!x)return "0";std::string s;while(x){s.push_back('0'+x%10);x/=10;}std::reverse(s.begin(),s.end());return s;}
int main(){
 try{
  auto start=std::chrono::steady_clock::now();size_t n;if(!(std::cin>>n)||n<1||n>2000000)throw std::runtime_error("Length outside1..2000000");
  std::vector<uint64_t>a(n);uint64_t mx=0,sum=0;u128 first=0;
  for(size_t i=0;i<n;++i){if(!(std::cin>>a[i])||a[i]>(1ull<<32))throw std::runtime_error("Need coefficients in0..2^32");mx=std::max(mx,a[i]);sum+=a[i];first+=u128(i)*a[i];}
  std::string extra;if(std::cin>>extra)throw std::runtime_error("Trailing data");if(!mx)throw std::runtime_error("Zero function");
  size_t m=2*n-1,L=1;while(L<m)L<<=1;
  const uint32_t ps[3]={998244353,469762049,167772161};
  u128 P=u128(ps[0])*ps[1]*ps[2],bound=u128(n)*mx*mx;
  if(u256(2)*(n-1)*wide(u128(sum)*sum)>((u256(1)<<128)-1))throw std::runtime_error("Moment accumulator bound exceeded");
  if(P<=bound)throw std::runtime_error("CRT product too small");
  std::vector<std::vector<uint32_t>>rs;
  for(uint32_t p:ps){
   if(!prime(p)||(p-1)%L)throw std::runtime_error("Invalid NTT modulus/length");
   uint32_t root=power(3,(p-1)/L,p);
   if(power(root,L,p)!=1||(L>1&&power(root,L/2,p)==1))throw std::runtime_error("Root order failed");
   std::vector<uint32_t>v(L);for(size_t i=0;i<n;++i)v[i]=a[i]%p;
   ntt(v,false,p);for(auto&x:v)x=uint64_t(x)*x%p;ntt(v,true,p);v.resize(m);rs.push_back(std::move(v));
  }
  uint64_t p12=uint64_t(ps[0])*ps[1];uint32_t inv1=power(ps[0]%ps[1],ps[1]-2,ps[1]),inv12=power(p12%ps[2],ps[2]-2,ps[2]);
  u128 prev=0,maxc=0,sumc=0,moment=0;u256 squares=0,adjacent=0;std::vector<u128>conv;
  if(n<=128)conv.reserve(m);
  for(size_t k=0;k<m;++k){
   uint32_t t1=uint64_t((uint64_t(rs[1][k])+ps[1]-rs[0][k]%ps[1])%ps[1])*inv1%ps[1];
   uint64_t x12=rs[0][k]+uint64_t(ps[0])*t1;
   uint32_t t2=uint64_t((uint64_t(rs[2][k])+ps[2]-x12%ps[2])%ps[2])*inv12%ps[2];
   u128 c=u128(x12)+u128(p12)*t2;
   if(c>bound)throw std::runtime_error("Reconstruction exceeds proven coefficient bound");
   if(n<=128)conv.push_back(c);
   maxc=std::max(maxc,c);sumc+=c;moment+=u128(k)*c;
   u256 v=wide(c);squares+=v*v;if(k)adjacent+=v*wide(prev);prev=c;
  }
  if(sumc!=u128(sum)*sum||moment!=u128(2)*sum*first)throw std::runtime_error("Exact moment identities failed");
  if(n<=128)for(size_t k=0;k<m;++k){u128 direct=0;for(size_t i=0;i<n;++i)if(k>=i&&k-i<n)direct+=u128(a[i])*a[k-i];if(direct!=conv[k])throw std::runtime_error("Schoolbook oracle mismatch");}
  u256 numerator=2*squares+adjacent,denominator=3*wide(sumc)*wide(maxc);u256 aa=numerator,bb=denominator;
  while(bb!=0){u256 rr=aa%bb;aa=bb;bb=rr;}numerator/=aa;denominator/=aa;
  if(numerator>denominator)throw std::runtime_error("Ratio exceeds1");
  long double score=numerator.convert_to<long double>()/denominator.convert_to<long double>();
  std::cout.precision(18);
  std::cout<<"{\"method\":\"exact_three_prime_ntt_crt\",\"n\":"<<n<<",\"transform_length\":"<<L<<",\"coefficient_bound\":\""<<dec(bound)<<"\",\"crt_product\":\""<<dec(P)<<"\",\"exact_moment_checks\":true,\"schoolbook_all_coefficients\":"<<(n<=128?"true":"false")<<",\"numerator\":\""<<numerator<<"\",\"denominator\":\""<<denominator<<"\",\"score\":"<<score<<",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 2;}
}
