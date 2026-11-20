"""Reuse authenticated clients with a separate study journal and audiences."""
import json
from ..curriculum.world import ROOT
from ..terrain_v12.services import TerrainServices


class ContinuationServices(TerrainServices):
    def journal(self):
        path = ROOT / 'artifacts/smooth-v16r1-training' / (self.run_id + '-memory-journal.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'pending': self.pending, 'ready': self.records}, indent=2) + '\n')

    def report(self):
        value=super().report()
        value['eligibility']['writers']=len({r['author'] for r in self.records.values()})
        value['eligibility']['readers']=len({r['reader'] for r in self.reads if r['source_id_verified']})
        return value
