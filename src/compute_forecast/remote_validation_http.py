"""Pooled browser-like test transport, with no retry or assertion relaxation."""
from __future__ import annotations
import atexit,threading,time
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
_client=None
_lock=threading.Lock()
_active=0
_max_active=0
_observations=[]
def client():
    global _client
    with _lock:
        if _client is None:
            import httpx
            _client=httpx.Client(http2=True,timeout=90,limits=httpx.Limits(max_connections=8,max_keepalive_connections=8,keepalive_expiry=5),verify=True,follow_redirects=False,headers={"Cache-Control":"no-cache"})
            atexit.register(_client.close)
        return _client
def get_bytes(path):
    global _active,_max_active
    connection=client();start=time.monotonic()
    with _lock:_active+=1;_max_active=max(_max_active,_active)
    try:
        response=connection.get(URL+path);response.raise_for_status()
        if response.status_code!=200:raise ValueError("Expected exact HTTP 200")
        raw=response.content
        with _lock:_observations.append({"path":path,"status":response.status_code,"http_version":response.http_version,"seconds":time.monotonic()-start,"bytes":len(raw)})
        return raw
    finally:
        with _lock:_active-=1
def snapshot():
    with _lock:return {"kind":"pooled HTTP/2 where negotiated; HTTP/1.1 fallback","automatic_retries":0,"keepalive_expiry_seconds":5,"maximum_connections":8,"maximum_observed_in_flight":_max_active,"http_versions":sorted({r["http_version"] for r in _observations}),"requests":list(_observations)}
