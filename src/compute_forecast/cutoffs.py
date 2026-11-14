"""Fail-closed information boundaries for historical benchmark contexts."""
from datetime import date, datetime
from .contracts import Evidence, Observation, Phase, Record, Result, Scope


def visible_observations(rows: list[Observation], *, origin_period: date, cutoff: datetime):
    if cutoff.tzinfo is None:
        raise ValueError("cutoff must include timezone")
    return [
        row for row in rows
        if row.period <= origin_period and row.available_at <= cutoff
    ]


def eligible_evidence(item: Evidence, context: Scope) -> bool:
    if context.study != "benchmark" or context.market_cutoff is None:
        return False
    return (
        item.scope.study == "benchmark"
        and item.historical_status == "verified"
        and item.verified_available_at is not None
        and item.verified_available_at <= context.market_cutoff
        and bool(item.version_locator)
        and bool(item.snapshot_sha256)
    )


def accept_memory_source(source: Record, context: Scope) -> bool:
    if source.scope.study != context.study:
        return False
    if source.scope.task_id != context.task_id:
        return False
    if source.scope.phase == Phase.FINAL and context.phase != Phase.FINAL:
        return False
    if context.study != "benchmark":
        return True
    if isinstance(source, Evidence):
        return eligible_evidence(source, context)
    if isinstance(source, Result):
        return (
            context.market_cutoff is not None
            and source.max_input_available_at <= context.market_cutoff
        )
    # Other derived records need full lineage validation by the coordinator.
    return False
