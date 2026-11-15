"""Build pinned, attributed KaMIS with generic ISA and static runtime."""
import hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];V=ROOT/"vendor/global-KaMIS";B=ROOT/".build/global-KaMIS";OUT=ROOT/"artifacts/side_research/startup_001";OUT.mkdir(parents=True,exist_ok=True);V.parent.mkdir(parents=True,exist_ok=True)
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
