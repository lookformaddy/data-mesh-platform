"""Publish gate: a product version ships only if it passes its own
declared contract. Two independent checks, both fail-closed:

1. Schema check — every sample record must carry all required fields
   with values of the declared type (int accepts bool-free ints only;
   number accepts int/float; date accepts ISO YYYY-MM-DD strings).
2. SLO check — the version's observed signals must meet the product's
   SLO thresholds (freshness, completeness, availability).

A blocked publish never mutates published_version, so consumers keep
reading the last good version.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .errors import NotFoundError, ValidationError
from .models import HealthSignal, VersionedSchema

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "date": lambda v: isinstance(v, str) and _is_date(v),
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_date(value: str) -> bool:
    if not _DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


@dataclass
class GateResult:
    allowed: bool
    violations: list[str] = field(default_factory=list)


def check_schema(schema: VersionedSchema,
                 records: list[dict]) -> list[str]:
    violations: list[str] = []
    by_name = {f.name: f for f in schema.fields}
    for i, record in enumerate(records):
        for name in schema.required_names():
            if name not in record or record[name] is None:
                violations.append(f"record {i}: missing required field '{name}'")
        for name, value in record.items():
            f = by_name.get(name)
            if f is None:
                violations.append(f"record {i}: unknown field '{name}'")
            elif value is not None and not _TYPE_CHECKS[f.type](value):
                violations.append(
                    f"record {i}: field '{name}' expected {f.type}, got {type(value).__name__}")
    return violations


def check_slo(signal: HealthSignal, slo) -> list[str]:
    violations: list[str] = []
    if signal.newest_data_age_hours > slo.freshness_hours:
        violations.append(
            f"freshness {signal.newest_data_age_hours}h exceeds SLO {slo.freshness_hours}h")
    if signal.completeness < slo.completeness_min:
        violations.append(
            f"completeness {signal.completeness} below SLO {slo.completeness_min}")
    if signal.availability < slo.availability_min:
        violations.append(
            f"availability {signal.availability} below SLO {slo.availability_min}")
    return violations


def evaluate_publish(schema: VersionedSchema, records: list[dict],
                     signal: HealthSignal, slo) -> GateResult:
    violations = check_schema(schema, records) + check_slo(signal, slo)
    return GateResult(allowed=not violations, violations=violations)
