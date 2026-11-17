"""Read only hash-verified, permitted publication snapshots from the public volume."""
import hashlib,json,pathlib,re
NAMES={"direct-probability-v18":"probability-v18","direct-evidence-v14":"evidence-v14","market-state-v19":"market-state-v19","market-state-v19-prospective":"market-state-v19-future"}
def read_public_snapshot(study,root="/public"):
    directory=pathlib.Path(root)/"forecast-serving"/NAMES[study]
    pointer=json.loads((directory/"index.json").read_bytes());identity=pointer["report_sha256"]
    if not re.fullmatch("[0-9a-f]{64}",identity):raise ValueError("Invalid snapshot identity")
    path=directory/(identity+".json")
    if path.stat().st_size>20000000:raise ValueError("Snapshot exceeds serving budget")
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=identity:raise ValueError("Snapshot hash mismatch")
    value=json.loads(raw)
    if value.get("study_id")!=study:raise ValueError("Wrong publication snapshot")
    if "tinker://" in raw.decode():raise ValueError("Private model resource in public snapshot")
    return value,pointer
