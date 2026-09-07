"""pod_config exceptions."""

from __future__ import annotations


class ConfigError(Exception):
    """Malformed or missing configuration."""


class ConfigOpenError(ConfigError):
    """A value that is still an OPEN decision was read as if it were settled.

    Raised rather than returning a plausible default. [Doc 4 section 10] "Where a
    decision could not be traced to a document, no decision was written." The same
    discipline applies in code: an unmade decision must fail loudly at the point of
    use, not silently become a number someone later mistakes for a measurement.
    """


class ConfigReloadError(ConfigError):
    """Attempted to load configuration twice in one process.

    [PRD 7.2] safety-critical configuration is boot-time immutable.
    """
