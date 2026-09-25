#!/usr/bin/env python3
"""M7: lineage, duração, cobertura, cache e partes de proxy."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import fr_autoedite as fr  # noqa: E402
import proxy_integrity  # noqa: E402


class ProxyIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-proxy-integrity-")
        self.project = Path(self.temporary.name) / "projeto"
        (self.project / "originais").mkdir(parents=True)
        (self.project / "proxies").mkdir(parents=True)
        self.answers = fr.normalize_answers(fr.read_json(ROOT / "templates" / "questionario_base.json"))
        self.answers["project"].update(name="Integridade", slug="integridade")
        self.answers["local_analysis"]["enabled"] = False

    def tearDown(self):
        self.temporary.cleanup()

    def make_video(self, path: Path, duration: float = 3.0, *, audio_duration: float | None = None) -> None:
        command = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc2=size=320x180:rate=30:duration={duration}",
        ]
        if audio_duration is not None:
            command += ["-f", "lavfi", "-i", f"sine=frequency=880:sample_rate=48000:duration={audio_duration}"]
        command += ["-map", "0:v:0"]
        if audio_duration is not None:
            command += ["-map", "1:a:0"]
        command += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
        if audio_duration is not None:
            command += ["-c:a", "aac"]
        command += [str(path)]
        fr.run(command)

    def row(self, source: Path, proxy: Path, asset_id: str = "M0001") -> dict:
        return {
            "id": asset_id, "status": "ok", "media_type": "video",
            "source_path": source.relative_to(self.project).as_posix(),
            "proxy_path": proxy.relative_to(self.project).as_posix(),
        }

    def verify(self, row: dict, *, expected=None):
        return proxy_integrity.verify_asset(
            self.project, row,
            generation_parameters=fr.proxy_generation_parameters(row, self.answers),
            probe=fr.proxy_probe_metadata, decode_video=fr.decode_video_proxy,
            expected=expected,
        )

    def test_intact_no_audio_has_separate_hashes_duration_and_coverage(self):
        source = self.project / "originais" / "sem-audio.mp4"
        proxy = self.project / "proxies" / "sem-audio.mp4"
        self.make_video(source)
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        fr.create_video_proxy(source, proxy, 240, 24, source_duration=3)
        record = self.verify(self.row(source, proxy))
        self.assertEqual(record["status"], "verified")
        self.assertNotEqual(record["source_hash"], record["proxy_hash"])
        self.assertAlmostEqual(record["coverage_start"], 0.0)
        self.assertLessEqual(
            abs(record["proxy_duration"] - record["source_duration"]),
            record["duration_tolerance_sec"],
        )
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)

    def test_truncated_proxy_is_blocked_and_original_is_unchanged(self):
        source = self.project / "originais" / "fonte.mp4"
        proxy = self.project / "proxies" / "truncado.mp4"
        self.make_video(source)
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        fr.create_video_proxy(source, proxy, 240, 24, source_duration=3)
        proxy.write_bytes(proxy.read_bytes()[: max(1, proxy.stat().st_size // 3)])
        with self.assertRaisesRegex(proxy_integrity.ProxyIntegrityError, "ilegível|incompleto|decodificação"):
            self.verify(self.row(source, proxy))
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)

    def test_same_size_source_change_invalidates_cache_and_preserves_new_source(self):
        source = self.project / "originais" / "cor.tif"
        replacement = self.project / "outra.tif"
        Image.new("RGB", (64, 64), "#ff0000").save(source, compression="raw")
        Image.new("RGB", (64, 64), "#0000ff").save(replacement, compression="raw")
        self.assertEqual(source.stat().st_size, replacement.stat().st_size)
        first = fr.build_manifest(self.project, self.answers)
        first_record = first["media"][0]["proxy_integrity"]
        source.write_bytes(replacement.read_bytes())
        changed_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        second = fr.build_manifest(self.project, self.answers)
        second_record = second["media"][0]["proxy_integrity"]
        self.assertNotEqual(first_record["source_hash"], second_record["source_hash"])
        self.assertNotEqual(first_record["proxy_hash"], second_record["proxy_hash"])
        self.assertEqual(second_record["source_hash"], changed_hash)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), changed_hash)

    def test_vfr_rounding_and_longer_audio_use_video_coverage(self):
        source = self.project / "originais" / "vfr-audio.mp4"
        proxy = self.project / "proxies" / "vfr-audio.mp4"
        fr.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=3",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3.2",
            "-vf", "select='if(lt(t,1.5),not(mod(n,2)),1)'",
            "-fps_mode", "vfr", "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(source),
        ])
        source_meta = fr.proxy_probe_metadata(source)
        self.assertGreater(source_meta["audio_duration_sec"], source_meta["video_duration_sec"])
        fr.create_video_proxy(source, proxy, 240, 24, source_duration=3.2)
        record = self.verify(self.row(source, proxy))
        self.assertEqual(record["status"], "verified")
        self.assertLessEqual(
            abs(record["proxy_duration"] - record["source_duration"]),
            record["duration_tolerance_sec"],
        )

    def test_split_proxy_map_is_ordered_contiguous_and_complete(self):
        proxy = self.project / "proxies" / "grande.mp4"
        self.make_video(proxy, duration=8)
        proxy_hash = hashlib.sha256(proxy.read_bytes()).hexdigest()
        budget = max(32 * 1024, int(proxy.stat().st_size * 0.55))
        self.assertGreater(proxy.stat().st_size, budget)
        paths, inventory = fr.handoff_proxy_inventory(self.project, [proxy], budget)
        self.assertGreater(len(paths), 1)
        entries = inventory["entries"]
        self.assertEqual([entry["order"] for entry in entries], list(range(1, len(entries) + 1)))
        self.assertEqual(entries[0]["coverage_start"], 0.0)
        for left, right in zip(entries, entries[1:]):
            self.assertAlmostEqual(left["coverage_end"], right["coverage_start"], places=5)
        duration = fr.proxy_probe_metadata(proxy)["video_duration_sec"]
        self.assertAlmostEqual(entries[-1]["coverage_end"], duration, delta=0.25)
        self.assertTrue(all(path.stat().st_size <= budget for path in paths))
        self.assertEqual(hashlib.sha256(proxy.read_bytes()).hexdigest(), proxy_hash)

    def test_manifest_gate_detects_proxy_mutation(self):
        source = self.project / "originais" / "fonte.mp4"
        proxy = self.project / "proxies" / "proxy.mp4"
        self.make_video(source)
        fr.create_video_proxy(source, proxy, 240, 24, source_duration=3)
        row = self.row(source, proxy)
        row["proxy_integrity"] = self.verify(row)
        manifest = {"media": [copy.deepcopy(row)]}
        proxy.write_bytes(proxy.read_bytes() + b"mutacao")
        with self.assertRaisesRegex(proxy_integrity.ProxyIntegrityError, "mudou ou foi truncado"):
            proxy_integrity.ensure_manifest_integrity(
                self.project, manifest,
                parameters_for=lambda item: fr.proxy_generation_parameters(item, self.answers),
                probe=fr.proxy_probe_metadata, decode_video=fr.decode_video_proxy,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
