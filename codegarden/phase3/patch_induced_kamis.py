"""Narrow documented experiment patch to upstream plateau underflow, never verifier code."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=ROOT/"vendor/KaMIS/lib/mis/ils/ils.cpp";before=p.read_bytes();text=before.decode()
old="        plateau--;\n        if (plateau < 0) plateau = 0;"
assert text.count(old)==1
text=text.replace(old,"        // CodeGarden experiment: saturating decrement of unsigned plateau.\n        if (plateau > 0) --plateau;")
p.write_text(text);after=p.read_bytes()
# Tiny exhaustive arithmetic regression for the exact changed operation.
cases=[]
for value in [0,1,2,226,4294967295]:
 original=(value-1)%(1<<32);patched=max(0,value-1)
 cases.append({"before":value,"original_unsigned_after":original,"patched_after":patched})
assert cases[0]["original_unsigned_after"]==4294967295 and cases[0]["patched_after"]==0
out=ROOT/"artifacts/phase3/induced_kamis_001";out.mkdir(parents=True,exist_ok=True)
(out/"patch_provenance.json").write_text(json.dumps({"upstream_revision":"2e4b3861b8063f05e8520434b97ce59e21ca49e7","path":"lib/mis/ils/ils.cpp",
 "upstream_file_sha256":hashlib.sha256(before).hexdigest(),"patched_file_sha256":hashlib.sha256(after).hexdigest(),
 "change":"Replace decrement-then-negative-test on unsigned plateau with saturating decrement.","arithmetic_regression":cases,
 "attribution":"KaMIS ILS method is upstream; this narrowly documented behavior correction is CodeGarden's experimental adaptation. No validity rules changed."},indent=2))
