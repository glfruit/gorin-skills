from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mlx_whisper_adapter.py"


class MlxWhisperAdapterCliTests(unittest.TestCase):
    def test_missing_absolute_local_model_is_not_reclassified_as_remote(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root / "media.wav"
            output = root / "transcript.json"
            missing_model = root / "missing-model"
            media.write_bytes(b"fixture")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "transcribe",
                    str(media),
                    "--output",
                    str(output),
                    "--model",
                    str(missing_model),
                    "--dry-run",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("local model directory not found", result.stderr)
            self.assertFalse(output.exists())

    def test_transcribe_normalizes_word_timestamps_and_records_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_modules = root / "fake-modules"
            fake_modules.mkdir()
            fake_modules.joinpath("mlx_whisper.py").write_text(
                textwrap.dedent(
                    """\
                    def transcribe(media, **options):
                        assert options["word_timestamps"] is True
                        assert options["task"] == "transcribe"
                        assert options["language"] == "en"
                        return {
                            "text": " Hello Armin.",
                            "language": "en",
                            "segments": [
                                {
                                    "start": 0.0,
                                    "end": 1.25,
                                    "text": " Hello Armin.",
                                    "tokens": [1, 2, 3],
                                    "words": [
                                        {
                                            "start": 0.0,
                                            "end": 0.4,
                                            "word": " Hello",
                                            "probability": 0.99,
                                        },
                                        {
                                            "start": 0.4,
                                            "end": 1.25,
                                            "word": " Armin.",
                                            "probability": 0.75,
                                        },
                                    ],
                                }
                            ],
                        }
                    """
                ),
                encoding="utf-8",
            )
            media = root / "audio.m4a"
            media_raw = b"fake audio bytes"
            media.write_bytes(media_raw)
            model = root / "pinned-model"
            model.mkdir()
            output = root / "whisper.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(fake_modules)
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "transcribe",
                    str(media),
                    "--output",
                    str(output),
                    "--model",
                    str(model),
                    "--language",
                    "en",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(Path(payload["output"]), output.resolve())
            transcript = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(transcript["backend"], "mlx-whisper")
            self.assertEqual(transcript["model"], str(model.resolve()))
            self.assertTrue(transcript["word_timestamps"])
            self.assertEqual(transcript["language"], "en")
            self.assertEqual(transcript["media"]["path"], str(media.resolve()))
            self.assertEqual(
                transcript["media"]["sha256"], hashlib.sha256(media_raw).hexdigest()
            )
            self.assertEqual(transcript["segments"][0]["text"], "Hello Armin.")
            self.assertNotIn("tokens", transcript["segments"][0])
            self.assertEqual(
                transcript["segments"][0]["words"],
                [
                    {"start": 0.0, "end": 0.4, "word": " Hello", "probability": 0.99},
                    {"start": 0.4, "end": 1.25, "word": " Armin.", "probability": 0.75},
                ],
            )

    def test_transcribe_skips_zero_duration_words_when_usable_spans_remain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_modules = root / "fake-modules"
            fake_modules.mkdir()
            fake_modules.joinpath("mlx_whisper.py").write_text(
                textwrap.dedent(
                    """\
                    def transcribe(media, **options):
                        return {
                            "text": " I'm very sitting next to it.",
                            "language": "en",
                            "segments": [
                                {
                                    "start": 83.32,
                                    "end": 85.28,
                                    "text": " I'm very sitting next to it.",
                                    "words": [
                                        {
                                            "word": " next",
                                            "start": 84.88,
                                            "end": 85.12,
                                            "probability": 0.97900390625,
                                        },
                                        {
                                            "word": " to",
                                            "start": 85.12,
                                            "end": 85.28,
                                            "probability": 0.97802734375,
                                        },
                                        {
                                            "word": " it.",
                                            "start": 85.28,
                                            "end": 85.28,
                                            "probability": 0.5146484375,
                                        },
                                    ],
                                },
                                {
                                    "start": 160.02,
                                    "end": 163.7,
                                    "text": " And over the past four years now, I guess,",
                                    "words": [
                                        {
                                            "word": " now,",
                                            "start": 162.22,
                                            "end": 162.42,
                                            "probability": 0.93896484375,
                                        },
                                        {
                                            "word": " I",
                                            "start": 162.56,
                                            "end": 162.56,
                                            "probability": 0.982421875,
                                        },
                                        {
                                            "word": " guess,",
                                            "start": 162.56,
                                            "end": 162.7,
                                            "probability": 0.99951171875,
                                        },
                                    ],
                                },
                                {
                                    "start": 200.6,
                                    "end": 200.9,
                                    "text": " I love it.",
                                    "words": [
                                        {
                                            "word": " I",
                                            "start": 200.6,
                                            "end": 200.6,
                                            "probability": 0.130615234375,
                                        },
                                        {
                                            "word": " love",
                                            "start": 200.6,
                                            "end": 200.6,
                                            "probability": 0.8232421875,
                                        },
                                        {
                                            "word": " it.",
                                            "start": 200.6,
                                            "end": 200.9,
                                            "probability": 0.6650390625,
                                        },
                                    ],
                                },
                            ],
                        }
                    """
                ),
                encoding="utf-8",
            )
            media = root / "audio.wav"
            media.write_bytes(b"fake audio bytes")
            model = root / "pinned-model"
            model.mkdir()
            output = root / "whisper.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(fake_modules)
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "transcribe",
                    str(media),
                    "--output",
                    str(output),
                    "--model",
                    str(model),
                    "--language",
                    "en",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            transcript = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                transcript["segments"][0]["words"],
                [
                    {
                        "start": 84.88,
                        "end": 85.12,
                        "word": " next",
                        "probability": 0.979004,
                    },
                    {
                        "start": 85.12,
                        "end": 85.28,
                        "word": " to",
                        "probability": 0.978027,
                    },
                ],
            )
            self.assertEqual(
                transcript["segments"][1]["words"],
                [
                    {
                        "start": 162.22,
                        "end": 162.42,
                        "word": " now,",
                        "probability": 0.938965,
                    },
                    {
                        "start": 162.56,
                        "end": 162.7,
                        "word": " guess,",
                        "probability": 0.999512,
                    },
                ],
            )
            self.assertEqual(
                transcript["segments"][2]["words"],
                [
                    {
                        "start": 200.6,
                        "end": 200.9,
                        "word": " it.",
                        "probability": 0.665039,
                    }
                ],
            )

    def test_transcribe_skips_empty_zero_duration_segments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_modules = root / "fake-modules"
            fake_modules.mkdir()
            fake_modules.joinpath("mlx_whisper.py").write_text(
                textwrap.dedent(
                    """\
                    def transcribe(media, **options):
                        return {
                            "text": " Hello.",
                            "language": "en",
                            "segments": [
                                {
                                    "start": 0.0,
                                    "end": 1.0,
                                    "text": " Hello.",
                                    "words": [
                                        {"word": " Hello.", "start": 0.0, "end": 1.0}
                                    ],
                                },
                                {
                                    "start": 1.0,
                                    "end": 1.0,
                                    "text": "",
                                    "words": [],
                                },
                            ],
                        }
                    """
                ),
                encoding="utf-8",
            )
            media = root / "audio.wav"
            media.write_bytes(b"fake audio bytes")
            model = root / "pinned-model"
            model.mkdir()
            output = root / "whisper.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(fake_modules)
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "transcribe",
                    str(media),
                    "--output",
                    str(output),
                    "--model",
                    str(model),
                    "--language",
                    "en",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            transcript = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(transcript["segments"]), 1)
            self.assertEqual(transcript["segments"][0]["text"], "Hello.")

    def test_transcribe_chunks_long_media_and_deduplicates_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            fake_modules = root / "fake-modules"
            fake_modules.mkdir()
            ffprobe = fake_bin / "ffprobe"
            ffprobe.write_text(
                f"#!{sys.executable}\nprint('1205.0')\n",
                encoding="utf-8",
            )
            ffprobe.chmod(0o755)
            ffmpeg = fake_bin / "ffmpeg"
            ffmpeg.write_text(
                textwrap.dedent(
                    f"""\
                    #!{sys.executable}
                    from pathlib import Path
                    import sys

                    arguments = sys.argv[1:]
                    start = arguments[arguments.index("-ss") + 1]
                    Path(arguments[-1]).write_text(start, encoding="utf-8")
                    """
                ),
                encoding="utf-8",
            )
            ffmpeg.chmod(0o755)
            fake_modules.joinpath("mlx_whisper.py").write_text(
                textwrap.dedent(
                    """\
                    from pathlib import Path


                    def transcribe(media, **options):
                        offset = float(Path(media).read_text(encoding="utf-8"))
                        if offset == 0.0:
                            words = [
                                {"word": " Alpha", "start": 590.0, "end": 591.0},
                                {"word": " duplicate", "start": 598.0, "end": 599.0},
                                {"word": " boundary", "start": 600.2, "end": 600.8},
                            ]
                        elif offset == 595.0:
                            words = [
                                {"word": " duplicate", "start": 3.0, "end": 4.0},
                                {"word": " boundary", "start": 5.2, "end": 5.8},
                                {"word": " omega", "start": 603.0, "end": 604.0},
                                {"word": " next", "start": 605.2, "end": 605.8},
                            ]
                        elif offset == 1195.0:
                            words = [
                                {"word": " omega", "start": 3.0, "end": 4.0},
                                {"word": " next", "start": 5.2, "end": 5.8},
                                {"word": " End.", "start": 9.0, "end": 9.5},
                            ]
                        else:
                            raise AssertionError(f"unexpected chunk offset: {offset}")
                        return {
                            "text": "".join(word["word"] for word in words),
                            "language": "en",
                            "segments": [
                                {
                                    "start": words[0]["start"],
                                    "end": words[-1]["end"],
                                    "text": "".join(word["word"] for word in words),
                                    "words": words,
                                }
                            ],
                        }
                    """
                ),
                encoding="utf-8",
            )
            media = root / "long-media.m4a"
            media_raw = b"long media fixture"
            media.write_bytes(media_raw)
            with media.open("r+b") as handle:
                handle.seek(1024 * 1024)
                handle.write(b"\0")
            model = root / "pinned-model"
            model.mkdir()
            output = root / "whisper.json"
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
            env["PYTHONPATH"] = str(fake_modules)
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "transcribe",
                    str(media),
                    "--output",
                    str(output),
                    "--model",
                    str(model),
                    "--language",
                    "en",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("MLX Whisper chunk 1/3", result.stderr)
            self.assertIn("MLX Whisper chunk 2/3", result.stderr)
            self.assertIn("MLX Whisper chunk 3/3", result.stderr)
            transcript = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                transcript["inference"],
                {
                    "mode": "chunked",
                    "chunk_count": 3,
                    "chunk_seconds": 600.0,
                    "overlap_seconds": 5.0,
                },
            )
            self.assertEqual(
                [
                    (word["word"], word["start"], word["end"])
                    for segment in transcript["segments"]
                    for word in segment["words"]
                ],
                [
                    (" Alpha", 590.0, 591.0),
                    (" duplicate", 598.0, 599.0),
                    (" boundary", 600.2, 600.8),
                    (" omega", 1198.0, 1199.0),
                    (" next", 1200.2, 1200.8),
                    (" End.", 1204.0, 1204.5),
                ],
            )
            self.assertEqual(
                transcript["media"]["sha256"],
                hashlib.sha256(media.read_bytes()).hexdigest(),
            )

    def test_remote_model_dry_run_reports_required_approval_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root / "audio.m4a"
            media.write_bytes(b"fake audio bytes")
            output = root / "whisper.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "transcribe",
                    str(media),
                    "--output",
                    str(output),
                    "--dry-run",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "dry-run")
            self.assertEqual(payload["model_source"], "huggingface")
            self.assertTrue(payload["would_download_model"])
            self.assertTrue(payload["requires_model_download_approval"])
            self.assertFalse(payload["files_written"])
            self.assertFalse(payload["inference_run"])
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
