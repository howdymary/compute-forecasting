"""Internal application contracts. These are NOT the unverified Pacific schema."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Phase(StrEnum):
    TRAIN = "train"
    DEVELOPMENT = "development"
    FINAL = "final"


class Scope(Contract):
    study: Literal["benchmark", "current_research"]
    phase: Phase
    task_id: str = Field(min_length=1)
    market_cutoff: AwareDatetime | None = None

    @model_validator(mode="after")
    def benchmark_requires_cutoff(self):
        if self.study == "benchmark" and self.market_cutoff is None:
            raise ValueError("benchmark records require a market cutoff")
        return self


class Record(Contract):
    schema_version: Literal["1"] = "1"
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    actor_id: str = Field(min_length=1)
    created_at: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_ids: tuple[UUID, ...] = ()
    scope: Scope

    def content_sha256(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Evidence(Record):
    kind: Literal["evidence"] = "evidence"
    url: str = Field(min_length=1)
    title: str
    retrieved_at: AwareDatetime
    reported_publication_at: AwareDatetime | None = None
    verified_available_at: AwareDatetime | None = None
    version_locator: str | None = None
    snapshot_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    claim: str
    supporting_excerpt: str
    license_status: Literal["verified", "restricted", "unknown"] = "unknown"
    historical_status: Literal["verified", "ineligible", "unknown"] = "unknown"
    affected_hypothesis_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def historical_proof(self):
        if self.historical_status == "verified":
            if not all((self.verified_available_at, self.version_locator, self.snapshot_sha256)):
                raise ValueError("verified historical evidence requires availability and version proof")
            if self.verified_available_at > self.retrieved_at:
                raise ValueError("verified availability cannot follow retrieval")
        return self


class Hypothesis(Record):
    kind: Literal["hypothesis"] = "hypothesis"
    statement: str
    comparison_config_ids: tuple[str, ...]
    evidence_ids: tuple[UUID, ...] = ()
    expected_mechanism: str
    falsification_rule: str
    status: Literal["proposed", "running", "supported", "rejected", "inconclusive"] = "proposed"
    result_ids: tuple[UUID, ...] = ()
    objection_ids: tuple[UUID, ...] = ()


class Candidate(Contract):
    representation: Literal["level", "log"]
    composition: Literal["target_only", "raw", "fixed_basket"]
    window_days: Literal[28, 56]
    alpha: Literal[1, 100]
    model_family: Literal["ridge"] = "ridge"

    @property
    def config_id(self) -> str:
        return canonical_hash(self.model_dump())[:16]


class Experiment(Record):
    kind: Literal["experiment"] = "experiment"
    config_id: str
    config_hash: str
    dataset_hash: str
    target_registry_hash: str
    protocol_hash: str
    code_sha: str
    fold_ids: tuple[str, ...]
    seed: int
    evidence_ids: tuple[UUID, ...] = ()
    memory_exchange_ids: tuple[UUID, ...] = ()
    status: Literal["proposed", "running", "completed", "failed", "ineligible"]
    modal_call_ids: tuple[str, ...] = ()


class Metric(Contract):
    target_key: str
    horizon_days: Literal[1, 3, 7]
    quantile: Literal[0.1, 0.5, 0.9]
    loss: float = Field(ge=0)
    origin_count: int = Field(ge=0)


class Result(Record):
    kind: Literal["result"] = "result"
    experiment_id: UUID
    split: Phase
    scores: tuple[Metric, ...]
    scorer_status: Literal["internal_only", "official_verified"]
    official_aggregate: float | None = None
    baseline_loss: float | None = Field(default=None, ge=0)
    skill: float | None = None
    origin_count: int = Field(ge=0)
    coverage_start: date | None = None
    coverage_end: date | None = None
    interval_coverage: float | None = Field(default=None, ge=0, le=1)
    failure_count: int = Field(default=0, ge=0)
    artifact_uris: tuple[str, ...] = ()
    runtime_seconds: float = Field(ge=0)
    resource_usage: dict[str, Any] = Field(default_factory=dict)
    cost_value: float | None = Field(default=None, ge=0)
    cost_status: Literal["billed", "estimated", "unavailable"] = "unavailable"
    max_input_available_at: AwareDatetime

    @model_validator(mode="after")
    def result_integrity(self):
        if self.scorer_status != "official_verified" and self.official_aggregate is not None:
            raise ValueError("unverified scorer cannot produce an official aggregate")
        if self.cost_status == "unavailable" and self.cost_value is not None:
            raise ValueError("unavailable cost must not contain an invented amount")
        if self.cost_status != "unavailable" and self.cost_value is None:
            raise ValueError("reported cost requires a value")
        cutoff = self.scope.market_cutoff
        if cutoff is not None and self.max_input_available_at > cutoff:
            raise ValueError("result inputs exceed market cutoff")
        return self


class MemoryExchange(Record):
    kind: Literal["memory_exchange"] = "memory_exchange"
    operation: Literal["write", "read", "use"]
    agent_identity: str
    audience: str
    source_record_ids: tuple[UUID, ...] = ()
    past_source_ids: tuple[str, ...] = ()
    past_ingestion_ids: tuple[str, ...] = ()
    past_artifact_ids: tuple[str, ...] = ()
    request_id: str
    consumed_by_decision_id: UUID | None = None
    accepted_source_ids: tuple[str, ...] = ()
    rejected_source_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def restricted_audience(self):
        if self.scope.study == "benchmark" and self.audience == "project":
            raise ValueError("benchmark memory must use a restricted audience")
        if self.operation == "use" and self.consumed_by_decision_id is None:
            raise ValueError("memory use requires the downstream decision ID")
        return self


class PolicyExample(Contract):
    task_id: str
    split: Phase
    observation: dict[str, Any]
    eligible_config_ids: tuple[str, ...]
    chosen_config_id: str
    teacher_result_ids: tuple[UUID, ...]
    feedback_result_ids: tuple[UUID, ...] = ()
    training_data_cutoff: AwareDatetime
    teacher_rule_version: str

    @model_validator(mode="after")
    def valid_demonstration(self):
        if self.split == Phase.FINAL:
            raise ValueError("final-period tasks cannot become policy training examples")
        if self.chosen_config_id not in self.eligible_config_ids:
            raise ValueError("teacher choice is not eligible")
        if not self.teacher_result_ids:
            raise ValueError("demonstrations require completed experiment evidence")
        return self


class Forecast(Contract):
    target_key: str
    origin_ts: AwareDatetime
    horizon_days: Literal[1, 3, 7]
    quantile: Literal[0.1, 0.5, 0.9]
    value: float = Field(gt=0)
    unit_from_registry: str
    config_id: str
    run_id: UUID


class Observation(Contract):
    """Internal daily fixture contract; official mapping awaits starter verification."""
    target_key: str
    period: date
    available_at: AwareDatetime
    value: float = Field(gt=0)
    unit: str


class OfficialContract(Contract):
    verified: bool = False
    starter_reference: str | None = None
    starter_sha256: str | None = None
    target_definitions_verified: bool = False
    origin_timezone_verified: bool = False
    export_schema_verified: bool = False
    scorer_verified: bool = False
    license_status: Literal["verified", "restricted", "unknown"] = "unknown"

    def require_ready(self) -> None:
        checks = {
            "starter_reference": self.starter_reference,
            "starter_sha256": self.starter_sha256,
            "target_definitions": self.target_definitions_verified,
            "origin_timezone": self.origin_timezone_verified,
            "export_schema": self.export_schema_verified,
            "scorer": self.scorer_verified,
            "dataset_license": self.license_status != "unknown",
            "verified": self.verified,
        }
        missing = [name for name, passed in checks.items() if not passed]
        if missing:
            raise RuntimeError("Official integration is blocked: " + ", ".join(missing))
