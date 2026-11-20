"""Run an engineering attempt from an immutable local source snapshot."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
ident=sys.argv[sys.argv.index('--id')+1]
assert ident and Path(ident).name==ident
snapshot=root/'artifacts/smooth-v16-engineering/source-snapshots'/ident/'src'
assert not snapshot.exists()
shutil.copytree(root/'src',snapshot,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
env={**os.environ,'PYTHONPATH':str(snapshot),'MOCHI_ROOT':str(root),
    'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONWARNINGS':'ignore'}
raise SystemExit(subprocess.call([sys.executable,'-u','-m','mochi.smooth_v16.engineering',*sys.argv[1:]],env=env))
