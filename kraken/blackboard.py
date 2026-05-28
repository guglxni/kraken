"""Parquet blackboard — kraken.findings and kraken.plans.

Agents NEVER call each other directly. They communicate by writing and
reading from this blackboard via Coral SQL.

The Parquet files are registered with Coral as local-file sources on startup,
making them queryable with standard SQL (SELECT, JOIN, WHERE, etc.).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import structlog

from kraken.models import Finding, Plan

logger = structlog.get_logger(__name__)

# Default blackboard directory
_BLACKBOARD_DIR = Path.home() / ".kraken"
_FINDINGS_PATH = _BLACKBOARD_DIR / "findings.parquet"
_PLANS_PATH = _BLACKBOARD_DIR / "plans.parquet"

# Arrow schemas (must match Coral source spec column definitions)
_FINDINGS_SCHEMA = pa.schema([
    pa.field("finding_id", pa.string()),
    pa.field("voyage_id", pa.string()),
    pa.field("agent", pa.string()),
    pa.field("kind", pa.string()),
    pa.field("payload", pa.string()),  # JSON-serialized dict
    pa.field("created_at", pa.timestamp("ms", tz="UTC")),
])

_PLANS_SCHEMA = pa.schema([
    pa.field("plan_id", pa.string()),
    pa.field("voyage_id", pa.string()),
    pa.field("kind", pa.string()),
    pa.field("target_agent", pa.string()),
    pa.field("priority", pa.string()),
    pa.field("params", pa.string()),  # JSON-serialized dict
    pa.field("status", pa.string()),
    pa.field("created_at", pa.timestamp("ms", tz="UTC")),
])


class Blackboard:
    """Read/write interface for the Parquet blackboard.

    Agents write findings here; Quartermaster reads and JOINs them via Coral.
    """

    def __init__(self, directory: Path = _BLACKBOARD_DIR) -> None:
        self.directory = directory
        self.findings_path = directory / "findings.parquet"
        self.plans_path = directory / "plans.parquet"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        if not self.findings_path.exists():
            pq.write_table(
                pa.table(
                    {f.name: pa.array([], type=f.type) for f in _FINDINGS_SCHEMA},
                    schema=_FINDINGS_SCHEMA,
                ),
                self.findings_path,
            )
        if not self.plans_path.exists():
            pq.write_table(
                pa.table(
                    {f.name: pa.array([], type=f.type) for f in _PLANS_SCHEMA},
                    schema=_PLANS_SCHEMA,
                ),
                self.plans_path,
            )

    def write_finding(self, finding: Finding) -> str:
        """Append a finding to the blackboard. Returns finding_id."""
        import json

        existing = pq.read_table(self.findings_path)
        new_row = pa.table(
            {
                "finding_id": [finding.finding_id],
                "voyage_id": [finding.voyage_id],
                "agent": [finding.agent],
                "kind": [finding.kind],
                "payload": [json.dumps(finding.payload)],
                "created_at": pa.array(
                    [finding.created_at], type=pa.timestamp("ms", tz="UTC")
                ),
            },
            schema=_FINDINGS_SCHEMA,
        )
        combined = pa.concat_tables([existing, new_row])
        pq.write_table(combined, self.findings_path)

        logger.info(
            "finding_written",
            finding_id=finding.finding_id,
            voyage_id=finding.voyage_id,
            agent=finding.agent,
            kind=finding.kind,
        )
        return finding.finding_id

    def write_plan(self, plan: Plan) -> str:
        """Append a plan to the blackboard. Returns plan_id."""
        import json

        existing = pq.read_table(self.plans_path)
        new_row = pa.table(
            {
                "plan_id": [plan.plan_id],
                "voyage_id": [plan.voyage_id],
                "kind": [plan.kind],
                "target_agent": [plan.target_agent],
                "priority": [plan.priority],
                "params": [json.dumps(plan.params)],
                "status": [plan.status],
                "created_at": pa.array(
                    [plan.created_at], type=pa.timestamp("ms", tz="UTC")
                ),
            },
            schema=_PLANS_SCHEMA,
        )
        combined = pa.concat_tables([existing, new_row])
        pq.write_table(combined, self.plans_path)

        logger.info(
            "plan_written",
            plan_id=plan.plan_id,
            voyage_id=plan.voyage_id,
            kind=plan.kind,
            target_agent=plan.target_agent,
        )
        return plan.plan_id

    def read_findings(
        self,
        voyage_id: str | None = None,
        agent: str | None = None,
        kind: str | None = None,
    ) -> list[Finding]:
        """Read findings from the blackboard with optional filters."""
        import json

        table = pq.read_table(self.findings_path)
        df = table.to_pydict()

        results = []
        for i in range(len(df["finding_id"])):
            if voyage_id and df["voyage_id"][i] != voyage_id:
                continue
            if agent and df["agent"][i] != agent:
                continue
            if kind and df["kind"][i] != kind:
                continue
            results.append(
                Finding(
                    finding_id=df["finding_id"][i],
                    voyage_id=df["voyage_id"][i],
                    agent=df["agent"][i],  # type: ignore[arg-type]
                    kind=df["kind"][i],
                    payload=json.loads(df["payload"][i]),
                    created_at=df["created_at"][i].as_py(),
                )
            )
        return results

    def update_plan_status(
        self,
        plan_id: str,
        status: str,
    ) -> None:
        """Update a plan's status (pending → running → done/failed)."""
        import pyarrow.compute as pc

        table = pq.read_table(self.plans_path)
        mask = pc.equal(table["plan_id"], plan_id)
        indices = mask.to_pylist()
        statuses = table["status"].to_pylist()
        for i, match in enumerate(indices):
            if match:
                statuses[i] = status
        updated = table.set_column(
            table.schema.get_field_index("status"),
            "status",
            pa.array(statuses),
        )
        pq.write_table(updated, self.plans_path)


# Module-level singleton for convenience
_blackboard: Blackboard | None = None


def get_blackboard(directory: Path = _BLACKBOARD_DIR) -> Blackboard:
    global _blackboard
    if _blackboard is None:
        _blackboard = Blackboard(directory)
    return _blackboard
