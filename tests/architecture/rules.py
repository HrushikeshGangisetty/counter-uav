"""Machine-readable statement of the PRD module boundaries.

[PRD 2.3] "Respecting them is not optional style guidance; it is what makes the
system testable and the safety argument auditable." [PRD 7.2] says to enforce them
"in review". Review is necessary and not sufficient, so they are also enforced here.

Editing this file is editing the architecture. Any change needs a decision-log entry.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Modules that must be pure: no I/O, no threads, no globals [PRD 2.3, 7.2].
PURE_MODULES = ("pod_geometry", "pod_guidance", "pod_state")

#: Import names that mean "GStreamer".
GSTREAMER = ("gi", "gstreamer", "pgi")
#: Import names that mean "the MAVLink/serial link".
MAVLINK_SERIAL = ("pymavlink", "serial", "mavutil")
#: Import names that mean "I/O, threads or the network".
IMPURE = (
    "socket",
    "threading",
    "asyncio",
    "multiprocessing",
    "subprocess",
    "concurrent",
    "queue",
    "requests",
    "websockets",
    "http",
    "urllib",
    "sqlite3",
    "shutil",
    "signal",
)


@dataclass(frozen=True)
class ModuleRule:
    name: str
    #: Import prefixes this module must never import, with the citation for each ban.
    banned: tuple[tuple[str, str], ...]
    #: If set, the module may import ONLY these top-level names (plus stdlib listed
    #: in STDLIB_ALWAYS_OK and its own submodules).
    allowlist: tuple[str, ...] | None = None
    pure: bool = False
    notes: str = ""
    #: Third-party/stdlib names exempted from the allowlist.
    extra_allowed: tuple[str, ...] = field(default_factory=tuple)


def _bans(pairs: tuple[tuple[tuple[str, ...], str], ...]) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    for names, citation in pairs:
        for n in names:
            out.append((n, citation))
    return tuple(out)


POD_MODULES = (
    "pod_contracts",
    "pod_config",
    "pod_perception",
    "pod_geometry",
    "pod_guidance",
    "pod_state",
    "pod_mavlink",
    "pod_gcs",
)

RULES: tuple[ModuleRule, ...] = (
    ModuleRule(
        name="pod_contracts",
        banned=_bans(
            (
                (GSTREAMER + MAVLINK_SERIAL, "pod_contracts is stdlib-only by design"),
                (
                    tuple(m for m in POD_MODULES if m != "pod_contracts"),
                    "pod_contracts must not depend on any module (docs/decisions/0015)",
                ),
            )
        ),
        allowlist=(),
        notes="Stdlib only. Imports nothing, so every module may import it.",
    ),
    ModuleRule(
        name="pod_config",
        banned=_bans(
            (
                (GSTREAMER + MAVLINK_SERIAL, "[PRD 2.3] pod_config must never import anything"),
                (
                    tuple(m for m in POD_MODULES if m not in ("pod_config", "pod_contracts")),
                    "[PRD 2.3] pod_config must never import anything",
                ),
            )
        ),
        allowlist=("pod_contracts", "yaml"),
        notes=(
            "[PRD 2.3] 'Must never import: Anything.' Impl-0 interpretation "
            "(docs/decisions/0016): stdlib + yaml + pod_contracts only."
        ),
    ),
    ModuleRule(
        name="pod_perception",
        banned=_bans(
            (
                (MAVLINK_SERIAL, "[PRD 2.3] pod_perception must never import pymavlink"),
                (
                    ("pod_mavlink", "pod_guidance", "pod_state"),
                    "[PRD 2.3] pod_perception must never import control logic",
                ),
            )
        ),
        notes="[PRD 2.3] 'Perception never imports MAVLink.' GStreamer is permitted here.",
    ),
    ModuleRule(
        name="pod_geometry",
        banned=_bans(
            (
                (GSTREAMER, "[PRD 2.3] pod_geometry must never import GStreamer"),
                (MAVLINK_SERIAL, "[PRD 2.3] pod_geometry must never import pymavlink"),
                (IMPURE, "[PRD 2.3, 7.2] pod_geometry is pure: no I/O, no threads"),
                (
                    ("pod_perception", "pod_mavlink", "pod_gcs", "simulation"),
                    "[PRD 2.3] pure modules depend only on contracts and config",
                ),
            )
        ),
        pure=True,
        extra_allowed=("numpy", "cv2", "pod_config", "pod_contracts"),
    ),
    ModuleRule(
        name="pod_guidance",
        banned=_bans(
            (
                (GSTREAMER, "[PRD 2.3] pod_guidance must never import GStreamer"),
                (MAVLINK_SERIAL, "[PRD 2.3] pod_guidance must never import pymavlink"),
                (IMPURE, "[PRD 2.3, 7.2] pod_guidance is pure: no I/O, no threads"),
                (
                    ("pod_perception", "pod_mavlink", "pod_gcs", "simulation"),
                    "[PRD 2.3] pure modules depend only on contracts and config",
                ),
            )
        ),
        pure=True,
        extra_allowed=("numpy", "pod_config", "pod_contracts"),
    ),
    ModuleRule(
        name="pod_state",
        banned=_bans(
            (
                (GSTREAMER, "[PRD 2.3] pod_state must never import GStreamer"),
                (MAVLINK_SERIAL, "[PRD 2.3] pod_state must never import pymavlink"),
                (IMPURE, "[PRD 2.3, 7.2] pod_state is pure: no I/O, no threads"),
                (
                    ("pod_perception", "pod_mavlink", "pod_gcs", "simulation"),
                    "[PRD 2.3] pure modules depend only on contracts and config",
                ),
            )
        ),
        pure=True,
        extra_allowed=("numpy", "pod_config", "pod_contracts"),
    ),
    ModuleRule(
        name="pod_mavlink",
        banned=_bans(
            (
                (GSTREAMER, "[PRD 2.3] pod_mavlink must never import GStreamer"),
                (
                    ("pod_perception", "pod_gcs"),
                    "[PRD 2.3] the link module does not reach into perception or the GCS",
                ),
            )
        ),
        notes="[PRD 1.3 invariant 7] the ONLY module permitted to hold the FC serial handle.",
    ),
    ModuleRule(
        name="pod_gcs",
        banned=_bans(
            (
                (MAVLINK_SERIAL, "[PRD 2.3] pod_gcs must never import pymavlink"),
                (
                    ("pod_mavlink",),
                    "[PRD 2.4] the GCS link is separate from the FC link and must survive pod death",
                ),
            )
        ),
        notes=(
            "[PRD 2.4] FC telemetry reaches the GCS over the FC's own radio, never "
            "relayed through the pod."
        ),
    ),
)

#: Stdlib names any module may import.
STDLIB_ALWAYS_OK = (
    "__future__",
    "dataclasses",
    "enum",
    "typing",
    "abc",
    "math",
    "json",
    "os",
    "sys",
    "pathlib",
    "collections",
    "functools",
    "itertools",
    "time",
    "re",
    "logging",
    "contextlib",
    "types",
    "copy",
    "string",
    "textwrap",
    "warnings",
)

RULES_BY_NAME = {r.name: r for r in RULES}
