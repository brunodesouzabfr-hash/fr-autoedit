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
module.concat_segments(
    [Path(f"segment-{i}.mp4") for i in range(73)],
    Path("draft.mp4"),
    [{"duration": 1.0}] * 73,
    0.18,
)
assert called and called[0][0] == 73
print("DRAFT CONCAT ROUTE TEST OK")
