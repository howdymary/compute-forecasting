"""Existing source-verified memory clients, scoped budgets and new identities."""
import json
import math
from pathlib import Path

from mochi.smooth_v17.finalize_memory import ReviewServices


class NavigationServices(ReviewServices):
    def __init__(self, run_id, directory, charge, commit):
        super().__init__()
        self.run_id, self.directory, self.charge, self.commit = run_id, Path(directory), charge, commit
        self.actors = {r: run_id + '-' + r for r in ['researcher', 'designer', 'experimenter', 'critic']}
        self.audience, self.private = run_id + '-shared', run_id + '-critic'

    def journal(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / 'memory-journal.json').write_text(json.dumps({'records': self.records,
            'pending': self.pending, 'reads': self.reads, 'calls': self.calls,
            'sources': self.sources, 'decisions': self.decisions}, indent=2) + '\n')

    async def request(self, method, path, payload=None):
        await self.commit()
        if method == 'POST' and path == '/recall':
            await self.charge('past_actual_recalls', 1)
            await self.charge('past_estimated_credits', 1)
            await self.charge('modeled_provider_usd', .0003)
        if method == 'POST' and path == '/ingest':
            size = len(payload['content'].encode('utf-8'))
            assert size <= 6000, 'Keep numerical arrays in artifacts, not semantic memory'
            await self.charge('past_writes', 1)
            await self.charge('past_ingested_bytes', size)
            await self.charge('past_estimated_credits', max(1, math.ceil(size / 350)))
            await self.charge('modeled_provider_usd', max(1, math.ceil(size / 350)) * .0003)
        return await super().request(method, path, payload)

    async def search(self, query):
        await self.charge('exa_searches', 1)
        await self.charge('modeled_provider_usd', .02)
        result = await super().search(query)
        self.journal()
        await self.commit()
        return result

    async def decide(self, *args, **kwargs):
        # Reserve the bounded context plus one decision token conservatively.
        await self.charge('inference_input_plus_max_output_tokens', 10000)
        await self.charge('modeled_provider_usd', .0101)
        result = await super().decide(*args, **kwargs)
        self.journal()
        await self.commit()
        return result
