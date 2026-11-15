"""Independent role-process entry point; separate PID, input file and memory author."""
import argparse,hashlib,json,os,pathlib,sys,time,urllib.request
from common import ROOT,OUT,save
sys.path.insert(0,str(ROOT))
from providers import Providers
def recalled(result,required):
 chunks=[r for r in result.get("results",[]) if any(s.get("sourceId")==required for s in r.get("sources",[]))]
 if not chunks:raise ValueError("Required other-role source missing")
 for r in chunks:
  body=r.get("content")
  if isinstance(body,str):
   try:
    record=json.loads(body)
    if record.get("project")=="codegarden":return {"source_id":required,"actual_content":record["content"],
      "content_sha256":hashlib.sha256(body.encode()).hexdigest(),"representation":"actual recalled source record"}
   except (ValueError,TypeError):pass
 text=[r.get("content",r) for r in chunks]
 return {"source_id":required,"actual_content":text,"content_sha256":hashlib.sha256(json.dumps(text,sort_keys=True).encode()).hexdigest(),"representation":"actual recalled claims"}
def main():
 a=argparse.ArgumentParser();a.add_argument("--role",required=True);a.add_argument("--input",required=True);a.add_argument("--output",required=True);args=a.parse_args()
 data=json.loads(pathlib.Path(args.input).read_text());events=[]
 def log(kind,value):
  events.append({"kind":kind,"value":value,"pid":os.getpid(),"role":args.role,"time":time.time()})
 p=Providers(OUT,log);p.setup_memory();result={"role":args.role,"pid":os.getpid(),"input_sha256":hashlib.sha256(pathlib.Path(args.input).read_bytes()).hexdigest()}
 if args.role=="analyst":
  result["source_id"]=p.write("analyst",data["kind"],data["content"],data["experiment_id"],data.get("parents",[]))
 elif args.role=="researcher":
  evidence=recalled(p.read("researcher",data["query"],data["required_source"]),data["required_source"])
  exa=p.exa("binary deletion code maximum independent set escape two exchange local optimum large neighborhood exact set packing","phase2-larger-repairs")
  reads=[]
  for source in exa["sources"]:
   if not any(host in source["url"] for host in ["arxiv.org","pmc.ncbi.nlm.nih.gov","mdpi.com"]):continue
   try:
    request=urllib.request.Request(source["url"],headers={"User-Agent":"CodeGarden research provenance"})
    with urllib.request.urlopen(request,timeout=25) as response:raw=response.read()
    text=raw.decode("utf-8","replace")
    import re
    text=re.sub("<[^>]+>"," ",text);text=" ".join(text.split());lower=text.lower()
    at=next((lower.find(term) for term in ["maximum independent set","local search","integer programming","independent set"] if lower.find(term)>=0),0)
    reads.append({"url":source["url"],"response_sha256":hashlib.sha256(raw).hexdigest(),
     "method_excerpt":" ".join(text[at:at+700].split()[:25]),
     "extracted_representation":"Independent-set / packing optimization for deletion codes; applicability to larger repair neighborhoods is our proposed adaptation."})
   except Exception as e:reads.append({"url":source["url"],"error_type":type(e).__name__})
   if len(reads)>=2:break
  method={"recalled_analyst_evidence":evidence,"sources":exa,"primary_reads":reads,
    "method_hypothesis":"After a scoped radius-two exchange optimum, test larger sparse set-packing repairs, three-parent fusion, and population restarts.",
    "candidate_methods":["ejection3","weight_band","ruin64"],
    "attribution":"Conflict-graph/set-packing representation is adapted from retrieved literature; these bounded experiments and implementation are CodeGarden's proposals."}
  result["source_id"]=p.write("researcher","larger_repair_method",method,"phase2-larger-repairs",[data["required_source"]])
  result["method"]=method
 elif args.role=="strategist":
  evidence=recalled(p.read("strategist",data["query"],data["required_source"]),data["required_source"])
  plan={"actual_recalled_research":evidence,"long_worker_policies":["fixed","adaptive"],
   "long_worker_starts":"four distinct arena lineages, later exchanged archived populations",
   "larger_exact_repairs":[16,24,48],"evaluation":"four matched policy conditions, eight held-out cases, four 30-CPU-second chunks",
   "why":"Use the researcher's recalled response to the analyst's exact local failure, rather than repeat the same exhaustive root scan."}
  result["source_id"]=p.write("strategist","phase2_plan",plan,"phase2-campaign",[data["required_source"]]);result["plan"]=plan
 elif args.role=="recall":
  identity=data["identity"];result["evidence"]=recalled(p.read(identity,data["query"],data["required_source"]),data["required_source"])
 else:raise ValueError("Unknown bounded role")
 result["events"]=events;result["budget"]=p.ledger.summary();pathlib.Path(args.output).write_text(json.dumps(result,indent=2))
 print("ROLE_COMPLETED "+json.dumps({"role":args.role,"pid":os.getpid(),"source":result.get("source_id")}),flush=True)
if __name__=="__main__":main()
