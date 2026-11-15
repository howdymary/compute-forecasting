#define CODEGARDEN_PAIR_NO_MAIN 1
#include "pair_events.cpp"
#undef CODEGARDEN_PAIR_NO_MAIN
int main(){try{Garden g(1290001);PairPacking p(g);mt19937_64 rng(1290001);for(int j=0;j<227;++j){int w;do{w=rng()%N;}while(p.selected[w]);p.add(w);}cout<<"[";for(int s=0;s<20;++s){int removed=p.C[rng()%p.C.size()];p.remove(removed);int added;do{added=rng()%N;}while(p.selected[added]);p.add(added);p.check();if(s)cout<<",";cout<<"{\"words\":";outputArray(p.C);cout<<",\"pair_energy\":"<<p.energy<<",\"descendant_energy\":"<<p.descendantEnergy(p.C)<<",\"sample_fields\":[";for(int q=0;q<16;++q){if(q)cout<<",";int w=rng()%N;cout<<"["<<w<<","<<p.field[w]<<"]";}cout<<"]}";}cout<<"]\n";return 0;}catch(const exception&e){cerr<<e.what()<<"\n";return 2;}}
