"""Class schema --- the current project decision on detector class taxonomy.

[Decision 0009](../../../docs/decisions/0009-counter-uav-single-class.md): "One
class, `uav`. No size, type or friend/foe subdivision." That decision is CLOSED for
the class list; the hard-negative taxonomy is explicitly left OPEN (OD-B2) and is not
invented here. A hard-negative image is simply a sample with zero annotations --- the
standard object-detection convention, needing no special class.

This module is deliberately small: the class list is a project decision, not an
engineering choice, so it is represented as configuration a caller must supply (or
import the current decision's constant), never hard-coded inside validation logic.
"""

from __future__ import annotations

from dataclasses import dataclass


class ClassSchemaError(ValueError):
    """A ``ClassSchema`` is internally inconsistent (duplicate or empty names)."""


@dataclass(frozen=True, slots=True)
class ClassSchema:
    """An ordered list of class names; position is the ``class_id``.

    Deliberately minimal: no per-class metadata (anchor sizes, colours, parent
    categories) is invented here.
    """

    class_names: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.class_names:
            raise ClassSchemaError("ClassSchema must name at least one class")
        if any(not name for name in self.class_names):
            raise ClassSchemaError("ClassSchema class names must be non-empty strings")
        if len(set(self.class_names)) != len(self.class_names):
            raise ClassSchemaError(f"ClassSchema has duplicate class names: {self.class_names}")

    def __len__(self) -> int:
        return len(self.class_names)

    def name_for_id(self, class_id: int) -> str | None:
        if 0 <= class_id < len(self.class_names):
            return self.class_names[class_id]
        return None

    def id_for_name(self, class_name: str) -> int | None:
        try:
            return self.class_names.index(class_name)
        except ValueError:
            return None

    def is_valid(self, class_id: int, class_name: str) -> bool:
        """True only if ``class_id`` is in range AND its canonical name matches."""
        return self.name_for_id(class_id) == class_name


#: The current project decision (0009): single class `uav`, closed for the class
#: list. Hard negatives are zero-annotation samples, not a class. Importable for
#: convenience; validation functions still take a ClassSchema explicitly so a caller
#: is never silently bound to this constant if the decision changes.
COUNTER_UAV_CLASS_SCHEMA = ClassSchema(("uav",))
