"""Reuse authenticated clients with a separate study journal and audiences."""
import json
from ..curriculum.world import ROOT
from ..terrain_v12.services import TerrainServices


class ContinuationServices(TerrainServices):
    def journal(self):
        path = ROOT / 'artifacts/terrain-v13-training' / (self.run_id + '-memory-journal.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'pending': self.pending, 'ready': self.records}, indent=2) + '\n')
