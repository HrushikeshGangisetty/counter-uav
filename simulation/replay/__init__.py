"""Replay input --- read and write JSONL sequences of contract messages.

[PRD 2.3] "a logged flight can be replayed offline for bit-identical guidance
output, which turns tuning questions into unit tests instead of flight tests."
This module is that mechanism's file format half.
"""

from __future__ import annotations

from .jsonl import read_track_frames, write_track_frames

__all__ = ["read_track_frames", "write_track_frames"]
