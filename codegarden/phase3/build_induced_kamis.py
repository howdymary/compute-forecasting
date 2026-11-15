"""Pinned remote-only upstream build, isolated below CodeGarden."""
import hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];vendor=ROOT/"vendor/KaMIS";build=ROOT/".build/kamis-upstream";OUT=ROOT/"artifacts/phase3/induced_kamis_001";OUT.mkdir(parents=True,exist_ok=True);vendor.parent.mkdir(parents=True,exist_ok=True)
def run(args,**kwargs):return subprocess.run(args,check=True,**kwargs)
run(["git","clone","--no-checkout","https://github.com/KarlsruheMIS/KaMIS.git",str(vendor)])
run(["git","-C",str(vendor),"checkout","--detach","2e4b3861b8063f05e8520434b97ce59e21ca49e7"])
run(["git","-C",str(vendor),"submodule","update","--init","--recursive"])
run([sys.executable,"-B",str(ROOT/"phase3/patch_induced_kamis.py")])
cm=vendor/"CMakeLists.txt";dollar=chr(36)
with cm.open("a") as stream:stream.write('\nadd_executable(codegarden_pool_warm '+dollar+'{CMAKE_SOURCE_DIR}/../../phase3/induced_kamis_warm.cpp '+dollar+'<TARGET_OBJECTS:libkaffpa> '+dollar+'<TARGET_OBJECTS:libfiles>)\ntarget_link_libraries(codegarden_pool_warm '+dollar+'{OpenMP_CXX_LIBRARIES})\n')
run(["cmake","-S",str(vendor),"-B",str(build),"-DCMAKE_BUILD_TYPE=Release"]);run(["cmake","--build",str(build),"--target","redumis","codegarden_pool_warm","-j","2"])
rows=[]
for name in ["redumis","codegarden_pool_warm"]:
 p=build/name;rows.append({"binary":name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size})
(OUT/"binary_hashes.json").write_text(json.dumps(rows,indent=2));s=run(["git","-C",str(vendor),"submodule","status","--recursive"],text=True,capture_output=True);(OUT/"submodule_revisions.txt").write_text(s.stdout)
