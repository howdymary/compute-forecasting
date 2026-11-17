"""Flatten artifact download directories without replacing conflicting files."""
import pathlib,shutil
root=pathlib.Path("artifacts/market-state-v19-models")
for sub in sorted(root.glob("market-state-v19-model-*")):
    for file in sub.rglob("*"):
        if not file.is_file():continue
        dest=root/file.relative_to(sub);dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert dest.read_bytes()==file.read_bytes(),"Conflicting retained model artifact"
        else:shutil.copyfile(file,dest)
