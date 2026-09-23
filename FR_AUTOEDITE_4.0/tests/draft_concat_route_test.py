#!/usr/bin/env python3
"""Regression test: long draft plans must bypass the giant xfade graph."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fr_autoedite", ROOT / "app" / "fr_autoedite.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

called = []
module._concat_copy_segments_with_progress = lambda segments, target: called.append((len(segments), target))
# Um draft explícito curto também não deve cair nas junções com xfade.
module.concat_segments(
    [Path(f"short-{i}.mp4") for i in range(8)],
    Path("short-draft.mp4"),
    [{"transition": "dissolve"}] * 8,
    0.18,
    draft=True,
)
assert called == [(8, Path("short-draft.mp4"))]

module.concat_segments(
    [Path(f"segment-{i}.mp4") for i in range(73)],
    Path("draft.mp4"),
    [{"duration": 1.0}] * 73,
    0.18,
)
assert called[-1][0] == 73
print("DRAFT CONCAT ROUTE TEST OK")
