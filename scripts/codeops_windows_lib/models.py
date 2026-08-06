"""Immutable result models for native Windows prerequisite evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any


class Readiness(str, Enum):
    """Readiness severity in increasing order of operational impact."""

    READY = "READY"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class ExitClass(IntEnum):
    """Stable process exits for successful, malformed, and blocked evaluation."""

    SUCCESS = 0
    INTERNAL_ERROR = 1
    BLOCKED = 2


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One stable prerequisite decision and its user-facing remediation."""

    code: str
    status: Readiness
    message: str
    remediation: str | None

    def to_payload(self) -> dict[str, Any]:
        """Return the deterministic JSON-compatible representation."""
        return {
            "code": self.code,
            "status": self.status.value,
            "message": self.message,
            "remediation": self.remediation,
        }


@dataclass(frozen=True, slots=True)
class PreflightResult:
    """Aggregate readiness decision for one validated session request."""

    schema_version: int
    status: Readiness
    session_id: str
    checks: tuple[CheckResult, ...]

    @property
    def exit_code(self) -> int:
        """Return the stable process exit implied by the aggregate status."""
        if self.status is Readiness.BLOCKED:
            return int(ExitClass.BLOCKED)
        return int(ExitClass.SUCCESS)

    def to_payload(self) -> dict[str, Any]:
        """Return the closed camel-case wire payload."""
        return {
            "schemaVersion": self.schema_version,
            "status": self.status.value,
            "sessionId": self.session_id,
            "checks": [check.to_payload() for check in self.checks],
        }

    def to_json(self) -> str:
        """Render compact UTF-8-safe JSON with deterministic key ordering."""
        return json.dumps(
            self.to_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


class PreflightInputError(ValueError):
    """Raised when a caller violates the closed request contract."""


class PreflightInternalError(RuntimeError):
    """Raised with a sanitized message when a dependency cannot be evaluated."""
