"""Inspect original BLS workbook cells remotely; never fabricate historical vintages."""
import hashlib,io,json,os,pathlib,urllib.request,zipfile,xml.etree.ElementTree as ET
from datetime import datetime,timezone
N={"s":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
def workbook(raw):
    z=zipfile.ZipFile(io.BytesIO(raw));strings=[]
    if "xl/sharedStrings.xml" in z.namelist():
        strings=["".join(n.itertext()) for n in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("s:si",N)]
    rels={r.attrib["Id"]:r.attrib["Target"] for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    outputs=[]
    for sheet in ET.fromstring(z.read("xl/workbook.xml")).findall("s:sheets/s:sheet",N):
        rid=sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"];target=rels[rid]
        path=target.lstrip("/") if target.startswith("/") else "xl/"+target
        rows=[]
        for row in ET.fromstring(z.read(path)).findall(".//s:row",N):
            cells={}
            for c in row.findall("s:c",N):
                if c.attrib.get("t")=="inlineStr":value="".join(c.find("s:is",N).itertext())
                else:
                    v=c.find("s:v",N);value=v.text if v is not None else ""
                    if c.attrib.get("t")=="s" and value:value=strings[int(value)]
                if value:cells[c.attrib["r"]]=value
            if cells:rows.append(cells)
        matches=[i for i,row in enumerate(rows) if any("electric power distribution" in str(v).lower() or str(v).strip()=="221122" for v in row.values())]
        if matches:
            selected=rows[:12]+[rows[j] for i in matches for j in range(max(0,i-1),min(len(rows),i+2))]
            outputs.append({"sheet":sheet.attrib["name"],"rows":selected,"match_count":len(matches)})
    return outputs
def main():
    out=pathlib.Path("artifacts/evidence-v14-audit");out.mkdir(parents=True,exist_ok=True);records=[]
    for month in ("january","july"):
        url="https://www.bls.gov/ppi/detailed-report/ppi-detailed-report-"+month+"-2026.xlsx"
        r={"url":url,"publisher":"US Bureau of Labor Statistics","retrieved_at":datetime.now(timezone.utc).isoformat(),"archive_basis":"https://www.bls.gov/ppi/detailed-report/","source_period":month+" 2026"}
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"ComputeForecastResearch/1.0"}),timeout=25) as response:
                raw=response.read(10000001)
                if len(raw)>10000000:raise ValueError("Archive size budget exceeded")
                r.update(http_status=response.status,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
            r["matches"]=workbook(raw);r["status"]="inspected"
        except Exception as e:r.update(status="unavailable",error_type=type(e).__name__,error_message=str(e)[:180])
        records.append(r);print(json.dumps(r),flush=True)
    result={"study_id":"direct-evidence-v14","created_at":datetime.now(timezone.utc).isoformat(),"source_sha":os.environ["GITHUB_SHA"],"records":records,"qualified_for_training":False,"reason":"Cell mappings and release dates require confirmation; workbook retrieval alone is not historical-availability verification"}
    (out/"bls-archive-inspection.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":main()
