"""Internal helper, shared by governor.py and machine.py.

Not part of pod_state's public API (see pod_state/__init__.py) --- this is
module-internal plumbing, not a cross-module contract.
"""

from __future__ import annotations

from pod_config import ConfigOpenError


def require(value: float | object, field_name: str) -> float:
    """Read a SafetyEnvelope field, raising ConfigOpenError instead of a plausible
    default if the underlying decision is still OPEN [house rule: a value not stated
    in a document and not measured is OPEN, and reading it raises at the point of
    use]. isinstance, not is_open(), because this doubles as the type narrowing that
    makes the caller's arithmetic type-check: a `float | _Open` value that survives
    this is a `float`."""
    if isinstance(value, (int, float)):
        return float(value)
    raise ConfigOpenError(
        f"airframe.safety.{field_name} is OPEN; pod_state refuses to guess a value no "
        "project document has settled"
    )
