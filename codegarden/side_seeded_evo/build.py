"""Build pinned, attributed KaMIS with generic ISA and static runtime."""
import hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];V=ROOT/"vendor/global-KaMIS";B=ROOT/".build/global-KaMIS";OUT=ROOT/"artifacts/side_research/seeded_evo_001";OUT.mkdir(parents=True,exist_ok=True);V.parent.mkdir(parents=True,exist_ok=True)
def run(args,**kwargs):return subprocess.run(args,check=True,**kwargs)
run(["git","clone","--no-checkout","https://github.com/KarlsruheMIS/KaMIS.git",str(V)])
run(["git","-C",str(V),"checkout","--detach","2e4b3861b8063f05e8520434b97ce59e21ca49e7"])
run(["git","-C",str(V),"submodule","update","--init","--recursive"])
p=V/"lib/mis/ils/ils.cpp";before=p.read_bytes();text=before.decode();old="        plateau--;\n        if (plateau < 0) plateau = 0;"
assert text.count(old)==1
p.write_text(text.replace(old,"        // CodeGarden adaptation: saturating unsigned plateau decrement.\n        if (plateau > 0) --plateau;"))
patch={"upstream_revision":"2e4b3861b8063f05e8520434b97ce59e21ca49e7","file":"lib/mis/ils/ils.cpp","before_sha256":hashlib.sha256(before).hexdigest(),"after_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"change":"Replace unsigned underflow with saturating decrement; previously documented CodeGarden adaptation, not an upstream method claim.","arithmetic_cases":[{"x":x,"after":max(0,x-1)} for x in [0,1,2,226,4294967295]]}
(OUT/"patch_provenance.json").write_text(json.dumps(patch,indent=2))

# Only the ReduMIS launcher reads this experiment's bounded startup enum.
p=V/"app/reduction_evomis.cpp";before=p.read_bytes();s=before.decode()
needle="    mis_config.graph_filename = graph_filepath.substr"
assert s.count(needle)==1
insert=r'''
    if (const char *policy = std::getenv("CODEGARDEN_STARTUP")) {
        std::string action(policy);
        if (action == "thin" || action == "balanced") {
            bool thin = action == "thin";
            mis_config.number_of_partitions = thin ? 1 : 2;
            mis_config.number_of_separators = thin ? 1 : 2;
            mis_config.number_of_k_separators = 1;
            mis_config.number_of_k_partitions = 1;
            mis_config.multiway_blocks = 2;
            mis_config.population_size = thin ? 4 : 8;
            mis_config.repetitions = thin ? 1 : 2;
            mis_config.ils_iterations = 1000;
            std::cout << "CODEGARDEN_STARTUP_CONFIG {\"policy\":\"" << action
                << "\",\"partitions\":" << mis_config.number_of_partitions
                << ",\"separators\":" << mis_config.number_of_separators
                << ",\"k_separators\":" << mis_config.number_of_k_separators
                << ",\"multiway_blocks\":" << mis_config.multiway_blocks
                << ",\"population_size\":" << mis_config.population_size
                << ",\"repetitions\":" << mis_config.repetitions
                << ",\"ils_iterations\":" << mis_config.ils_iterations << "}" << std::endl;
        } else { std::cerr << "Unknown CodeGarden startup policy" << std::endl; return 2; }
    }
'''
s=s.replace("#include <stdio.h>","#include <stdio.h>\n#include <cstdlib>")
s=s.replace(needle,insert+needle);p.write_text(s)
(OUT/"startup_patch_provenance.json").write_text(json.dumps({"file":"app/reduction_evomis.cpp","before_sha256":hashlib.sha256(before).hexdigest(),"after_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"adaptation":"Environment-selected bounded heuristic startup; graph and validity unchanged.","allowed_actions":["thin","balanced"]},indent=2))


# A full-graph root path keeps vertex IDs equal to original binary words.
# This avoids assuming that an arbitrary kernel preserves word identities.
p=V/"lib/mis/evolutionary/reduction_evolution.cpp";before=p.read_bytes();s=before.decode()
s=s.replace('#include <limits.h>','#include <limits.h>\n#include <cstdlib>\n#include <fstream>\n#include <sstream>\n#include <stdexcept>')
needle="    // Reduce the graph "
assert s.count(needle)==1
block=r'''
    if (!recursive && std::getenv("CODEGARDEN_SEED_FILE")) {
        is_base = 0;
        coarser_max = 0;
        // This experiment stays on the identity-labelled full graph.
        mis_config.reduction_threshold = 1000000000;
        std::cout << "CODEGARDEN_SEEDED_ROOT_IDENTITY " << G.number_of_nodes() << std::endl;
        std::cout << "CODEGARDEN_SEEDED_POLICY " << (std::getenv("CODEGARDEN_NEUTRAL") ? std::getenv("CODEGARDEN_NEUTRAL") : "strict") << std::endl;
        perform_evolutionary(mis_config, G, independent_set);
        individuum_mis chosen;
        island.get_best_individuum(chosen);
        forall_nodes(G, node) { independent_set[node] = chosen.solution[node]; } endfor
        build_final_solution(mis_config, G, independent_set);
        unsigned int result_size = 0;
        for (bool selected : independent_set) result_size += selected;
        return result_size;
    }
'''
s=s.replace(needle,block+needle)
needle="    while (!island.is_full()) {"
assert s.count(needle)==1
seed=r'''
    if (const char *path = std::getenv("CODEGARDEN_SEED_FILE")) {
        std::ifstream stream(path);
        if (!stream) throw std::runtime_error("CodeGarden parent file unavailable");
        std::string line;
        unsigned int inserted = 0;
        while (!island.is_full() && std::getline(stream,line)) {
            std::istringstream input(line);unsigned int count;
            if (!(input >> count)) continue;
            std::vector<NodeID> nodes;NodeID node;
            while (input >> node) nodes.push_back(node);
            if (nodes.size()!=count) throw std::runtime_error("Parent count mismatch");
            individuum_mis ind;
            ind.solution = new NodeID[G.number_of_nodes()]();
            ind.solution_size = count;
            for (NodeID v : nodes) {
                if(v>=G.number_of_nodes() || ind.solution[v]) throw std::runtime_error("Bad/duplicate parent vertex");
                ind.solution[v] = 1;
            }
            // Check only selected vertices' adjacency; no search score is trusted.
            forall_nodes(G,v) {
                if(!ind.solution[v]) continue;
                forall_out_edges(G,e,v) {
                    if(ind.solution[G.getEdgeTarget(e)]) throw std::runtime_error("Conflicting parent");
                } endfor
            } endfor
            island.insert(mis_config,G,ind);++inserted;
            individuum_mis best;unsigned int best_after=collect_best_mis(mis_config,G,best);
            mis_log::instance()->set_operator("CodeGarden seeded");
            mis_log::instance()->set_best_size(mis_config,best_after);
            std::cout << "CODEGARDEN_PARENT_INSERTED " << inserted << " " << count << std::endl;
        }
        if (inserted < 2) throw std::runtime_error("Need at least two seeded parents");
    }
'''
s=s.replace(needle,seed+needle)
p.write_text(s)
(OUT/"seeded_root_patch_provenance.json").write_text(json.dumps({"file":"lib/mis/evolutionary/reduction_evolution.cpp","before_sha256":hashlib.sha256(before).hexdigest(),"after_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"adaptation":"Full-graph identity root without kernelization or recursion; seed population from explicitly checked parent index lists."},indent=2))
# Permit a distinct equal-size offspring in the treatment; original strict policy is the control.
p=V/"lib/mis/evolutionary/population_mis.cpp";before=p.read_bytes();s=before.decode()
s=s.replace('#include <limits.h>','#include <limits.h>\n#include <cstdlib>\n#include <string>')
needle="        if (ind.solution_size <= worst_solution) {"
assert s.count(needle)==1
s=s.replace(needle,"        bool cg_neutral = std::getenv(\"CODEGARDEN_NEUTRAL\") && std::string(std::getenv(\"CODEGARDEN_NEUTRAL\")) == \"neutral\";\n        if (cg_neutral && ind.solution_size == worst_solution) {\n            static unsigned long long considered = 0; ++considered;\n            if (considered <= 16 || (considered & (considered-1)) == 0) std::cout << \"CODEGARDEN_NEUTRAL_CONSIDERED \" << considered << std::endl;\n        }\n        if (ind.solution_size < worst_solution || (ind.solution_size == worst_solution && !cg_neutral)) {")
needle="    double min_ratio = 0.0;"
assert s.count(needle)==1
guard=r'''
    if (std::getenv("CODEGARDEN_NEUTRAL") && std::string(std::getenv("CODEGARDEN_NEUTRAL")) == "neutral") {
        for (const auto &existing : internal_population) {
            if(existing.solution_size != ind.solution_size) continue;
            bool identical = true;
            forall_nodes(G,node) { if(existing.solution[node] != ind.solution[node]) { identical=false;break; } } endfor
            if(identical) return false;
        }
    }
'''
s=s.replace(needle,guard+needle);p.write_text(s)
(OUT/"neutral_population_patch_provenance.json").write_text(json.dumps({"file":"lib/mis/evolutionary/population_mis.cpp","before_sha256":hashlib.sha256(before).hexdigest(),"after_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"adaptation":"Optional equal-cardinality insertion path with duplicate rejection; retains upstream ILS mutation and closest eligible non-best replacement. Control keeps original strict gate."},indent=2))

d=chr(36)
with (V/"CMakeLists.txt").open("a") as s:s.write("\nadd_executable(codegarden_pool_warm "+d+"{CMAKE_SOURCE_DIR}/../../side_global/warm.cpp "+d+"<TARGET_OBJECTS:libkaffpa> "+d+"<TARGET_OBJECTS:libfiles>)\ntarget_link_libraries(codegarden_pool_warm "+d+"{OpenMP_CXX_LIBRARIES})\n")
gomp=run(["g++","-print-file-name=libgomp.a"],text=True,capture_output=True).stdout.strip()
pthread=run(["g++","-print-file-name=libpthread.a"],text=True,capture_output=True).stdout.strip()
assert pathlib.Path(gomp).is_file() and pathlib.Path(pthread).is_file()
args=["cmake","-S",str(V),"-B",str(B),"-DCMAKE_BUILD_TYPE=Release","-DCOMPILER_SUPPORTS_MARCH_NATIVE=FALSE","-DCMAKE_CXX_FLAGS=-march=x86-64 -mtune=generic","-DCMAKE_C_FLAGS=-march=x86-64 -mtune=generic","-DCMAKE_EXE_LINKER_FLAGS=-static","-DOpenMP_gomp_LIBRARY:FILEPATH="+gomp,"-DOpenMP_pthread_LIBRARY:FILEPATH="+pthread]
run(args);run(["cmake","--build",str(B),"--target","redumis","codegarden_pool_warm","-j","2"])
commands=json.loads((B/"compile_commands.json").read_text())
assert commands and not any("-march=native" in r["command"] or "-mtune=native" in r["command"] for r in commands)
binaries=[]
for name in ["redumis","codegarden_pool_warm"]:
 binary=B/name;headers=run(["readelf","-l",str(binary)],text=True,capture_output=True).stdout
 assert "INTERP" not in headers,"Dynamic interpreter remains"
 binaries.append({"name":name,"sha256":hashlib.sha256(binary.read_bytes()).hexdigest(),"bytes":binary.stat().st_size,"dynamic_interpreter":False})
submodules=run(["git","-C",str(V),"submodule","status","--recursive"],text=True,capture_output=True).stdout
(OUT/"build.json").write_text(json.dumps({"upstream":"KarlsruheMIS/KaMIS","revision":"2e4b3861b8063f05e8520434b97ce59e21ca49e7","cmake_arguments":args,"compile_commands_sha256":hashlib.sha256((B/"compile_commands.json").read_bytes()).hexdigest(),"native_flags_found":False,"binaries":binaries,"submodules":submodules,"attribution":"KaMIS ILS and evolutionary methods are upstream; CodeGarden supplies isolation, portable build, warm-start adapter and the documented plateau correction."},indent=2))
print("GLOBAL_KAMIS_PORTABLE_BUILD",json.dumps(binaries),flush=True)
