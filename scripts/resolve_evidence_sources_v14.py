"""Resolve the newest fully qualified source audit without using forecast performance."""
import base64,json,os,pathlib,subprocess,time
def api(path):
    return json.loads(subprocess.check_output(["gh","api","repos/"+os.environ["GITHUB_REPOSITORY"]+"/"+path],text=True))
out=pathlib.Path("inputs/source");out.mkdir(parents=True,exist_ok=True)
for attempt in range(60):
    dirs=api("contents/results/evidence-v14/audits?ref=compute-observatory")
    selected=None
    for directory in sorted(dirs,key=lambda d:int(d["name"]),reverse=True):
        result=subprocess.run(["gh","api","repos/"+os.environ["GITHUB_REPOSITORY"]+"/contents/"+directory["path"]+"/bls-vintages.json?ref=compute-observatory"],capture_output=True,text=True)
        if result.returncode:continue
        value=json.loads(base64.b64decode(json.loads(result.stdout)["content"]))
        if value.get("ready"):selected=(directory,value);break
    if selected:break
    time.sleep(5)
else:raise RuntimeError("No qualified original BLS release audit; training remains gated")
directory,value=selected
(out/"bls-vintages.json").write_text(json.dumps(value,indent=2)+"\n")
print("BLS_SOURCE_AUDIT "+directory["path"])
