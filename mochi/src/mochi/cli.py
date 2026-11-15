import argparse,json,os
from pathlib import Path
from .simulation import ROOT
from .campaign import local_campaign

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('demo');d.add_argument('--out',default=str(ROOT/'artifacts/local'))
    s=sub.add_parser('serve');s.add_argument('--port',type=int,default=8765)
    sub.add_parser('capabilities')
    a=p.parse_args()
    if a.command=='demo':
        r=local_campaign(a.out);print(json.dumps({k:r[k] for k in ['run_id','selected','seconds']}));print(json.dumps(r['evaluation']['heldout']['selected']))
    elif a.command=='serve':
        import uvicorn
        uvicorn.run('mochi.api:app',host='127.0.0.1',port=a.port)
    else:
        import shutil
        print(json.dumps({'credentials':{n:bool(os.getenv(n)) for n in ['EXA_API_KEY','PAST_API_KEY','TINKER_API_KEY','MODAL_TOKEN_ID','MODAL_TOKEN_SECRET']},'blender':bool(shutil.which('blender'))},indent=2))

if __name__=='__main__':main()
