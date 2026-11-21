"""Recompute reported component/recovery measurements from public joint data."""
import gzip
import hashlib
import json
import math
from pathlib import Path

from mochi.visual_motion_v22.metrics import arm_smoothness

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web/desk/visual-motion-v22'
report = json.loads((WEB / 'report.json').read_text())
packed = (WEB / report['arm_measurement_data']['file']).read_bytes()
assert hashlib.sha256(packed).hexdigest() == report['arm_measurement_data']['sha256']
records = json.loads(gzip.decompress(packed))
windows = samples = 0
for ident, entries in records.items():
    for item in entries:
        computed = arm_smoothness(item)
        for name, expected in item['measurements'].items():
            if isinstance(expected, (int, float)):
                assert math.isclose(computed[name], expected, rel_tol=1e-12, abs_tol=1e-12), (ident, name)
        windows += 1
        samples += len(item['control_telemetry'])
result = {'verified': True, 'records': len(records), 'windows': windows, 'samples': samples,
    'data_sha256': hashlib.sha256(packed).hexdigest(),
    'scope': 'Numerical reproducibility from published measured joint positions; no independent hardware validation or causal attribution.'}
(ROOT / 'evidence/visual-motion-v22/arm-data-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
