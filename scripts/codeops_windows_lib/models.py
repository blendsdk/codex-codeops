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

    @classmethod
    def from_payload(cls, payload: object) -> "CheckResult":
        """Parse one closed check payload from a validated attestation."""
        if not isinstance(payload, dict) or set(payload) != {
            "code",
            "status",
            "message",
            "remediation",
        }:
            raise ValueError("attested check payload is malformed")
        code = payload["code"]
        message = payload["message"]
        remediation = payload["remediation"]
        if not isinstance(code, str) or not isinstance(message, str):
            raise ValueError("attested check text is malformed")
        if remediation is not None and not isinstance(remediation, str):
            raise ValueError("attested remediation is malformed")
        return cls(code, Readiness(payload["status"]), message, remediation)


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

    @classmethod
    def from_payload(cls, payload: object) -> "PreflightResult":
        """Parse the closed result payload stored in a bound attestation."""
        if not isinstance(payload, dict) or set(payload) != {
            "schemaVersion",
            "status",
            "sessionId",
            "checks",
        }:
            raise ValueError("attested result payload is malformed")
        if payload["schemaVersion"] != 1 or not isinstance(payload["sessionId"], str):
            raise ValueError("attested result identity is malformed")
        checks = payload["checks"]
        if not isinstance(checks, list):
            raise ValueError("attested checks are malformed")
        return cls(
            1,
            Readiness(payload["status"]),
            payload["sessionId"],
            tuple(CheckResult.from_payload(check) for check in checks),
        )


class PreflightInputError(ValueError):
    """Raised when a caller violates the closed request contract."""


class PreflightInternalError(RuntimeError):
    """Raised with a sanitized message when a dependency cannot be evaluated."""
