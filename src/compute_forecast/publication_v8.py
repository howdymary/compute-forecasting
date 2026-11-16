"""Append-only versioned public research publication with branch-head checks."""
import base64,json,os,re
from urllib.error import HTTPError
from .public_results import github,private_guard
def publish(files):
    if os.environ.get("GITHUB_REF")!="refs/heads/compute-observatory":raise ValueError("Publication branch")
    repo=os.environ["GITHUB_REPOSITORY"];blobs={}
    for path,raw in files.items():
        if not re.fullmatch(r"results/price-dynamics-v8/runs/[0-9]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?",path) or ".." in path.split("/"):raise ValueError("Unapproved publication path")
        if path.endswith(".json"):private_guard(json.loads(raw))
        blobs[path]=github("POST","repos/"+repo+"/git/blobs",{"encoding":"base64","content":base64.b64encode(raw).decode()})["sha"]
    for attempt in range(3):
        b=github("GET","repos/"+repo+"/branches/compute-observatory");parent=b["commit"]["sha"];entries=[]
        for path,sha in blobs.items():
            try:old=github("GET","repos/"+repo+"/contents/"+path+"?ref="+parent)["sha"]
            except HTTPError as e:
                if e.code!=404:raise
                old=None
            if old and old!=sha:raise ValueError("Versioned result already exists with different bytes")
            if not old:entries.append({"path":path,"type":"blob","mode":"100644","sha":sha})
        if not entries:return parent
        t=github("POST","repos/"+repo+"/git/trees",{"base_tree":b["commit"]["commit"]["tree"]["sha"],"tree":entries})
        c=github("POST","repos/"+repo+"/git/commits",{"message":"Publish price-dynamics v8 measured results and attribution","parents":[parent],"tree":t["sha"]})
        if github("GET","repos/"+repo+"/branches/compute-observatory")["commit"]["sha"]!=parent:continue
        try:github("PATCH","repos/"+repo+"/git/refs/heads/compute-observatory",{"sha":c["sha"],"force":False});return c["sha"]
        except HTTPError as e:
            if e.code not in (409,422):raise
    raise ValueError("Repeated branch advancement")
