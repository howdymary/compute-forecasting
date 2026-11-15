// CodeGarden adapter to pinned KaMIS ILS; upstream solver library is unchanged.
#include <cstdio>
#include <cstring>
#include <iostream>
#include <fstream>
#include <cstdlib>
#include <limits>
#include <argtable3.h>
#include "timer.h"
#include "ils/ils.h"
#include "ils/local_search.h"
#include "mis_log.h"
#include "graph_io.h"
#include "reduction_evolution.h"
#include "mis_config.h"
#include "greedy_mis.h"
#include "parse_parameters.h"
#include "data_structure/graph_access.h"
int main(int argc,char**argv){
 mis_log::instance()->restart_total_timer();MISConfig cfg;std::string path;
 if(parse_parameters(argc,argv,cfg,path))return 2;
 graph_access G;graph_io::readGraphWeighted(G,path);mis_log::instance()->set_config(cfg);mis_log::instance()->set_graph(G);
 for(NodeID v=0;v<G.number_of_nodes();++v)G.setPartitionIndex(v,0);
 const char*start=getenv("CODEGARDEN_START_CODES");if(!start)return 2;
 std::ifstream input(start);std::string word;unsigned count=0;
 while(input>>word){if(word.size()!=16||word.find_first_not_of("01")!=std::string::npos)return 2;unsigned v=std::stoul(word,nullptr,2);if(v>=G.number_of_nodes()||G.getPartitionIndex(v))return 2;G.setPartitionIndex(v,1);++count;}
 for(NodeID v=0;v<G.number_of_nodes();++v)if(G.getPartitionIndex(v))for(EdgeID e=G.get_first_edge(v);e<G.get_first_invalid_edge(v);++e)if(G.getPartitionIndex(G.getEdgeTarget(e)))return 2;
 std::cout<<"CODEGARDEN_WARM_START "<<count<<std::endl;
 ils search;search.perform_ils(cfg,G,std::numeric_limits<unsigned>::max());
 graph_io::writeIndependentSet(G,cfg.output_filename);return 0;
}
