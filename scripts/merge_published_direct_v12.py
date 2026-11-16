"""Reuse already published completed seeds when adding another registered seed."""
import json,pathlib,shutil
root=pathlib.Path("inputs/publication");pointer=pathlib.Path("results/direct-v12/latest.json")
if pointer.exists():
    index=json.loads(pointer.read_text());source=pathlib.Path(index["report_path"]);report=json.loads(source.read_text())
    existing={json.loads(f.read_text()).get("seed") for f in root.rglob("result.json")}
    for run in report.get("runs",[]):
        if run["seed"] in existing:continue
        directory=source.parent/("seed-"+str(run["seed"]))
        if directory.is_dir():shutil.copytree(directory,root/"published"/directory.name,dirs_exist_ok=True)
