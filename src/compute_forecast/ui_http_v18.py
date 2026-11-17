"""Strict pooled HTTP/2 transport for public browser-facing validation only."""
import atexit,io,json,urllib.parse
import httpx
BASE="https://howdymary--compute-forecast-evidence-v14-web.us-east.modal.run"
client=httpx.Client(http2=True,timeout=90,limits=httpx.Limits(max_connections=6,max_keepalive_connections=6),headers={"Accept-Encoding":"identity"})
atexit.register(client.close)
def live_urlopen(url,timeout=90):
    if not url.startswith(BASE+"/"):raise ValueError("Validation transport only accepts the public study origin")
    response=client.get(url,timeout=timeout)
    response.raise_for_status()
    assert response.http_version=="HTTP/2","Browser-facing endpoint did not negotiate the verified transport"
    body=io.BytesIO(response.content)
    body.status=response.status_code;body.headers=response.headers;body.http_version=response.http_version
    print(json.dumps({"transport":"HTTP/2","path":urllib.parse.urlparse(url).path,"status":body.status,"bytes":body.getbuffer().nbytes,"request_id":response.headers.get("X-Compute-Request-ID")}),flush=True)
    return body
