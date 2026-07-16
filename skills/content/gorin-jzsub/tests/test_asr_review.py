from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "asr_review.py"


class AsrReviewCliTests(unittest.TestCase):
    def test_prepare_rejects_an_unattributed_whisper_shaped_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            platform_srt = root / "platform.srt"
            whisper_json = root / "whisper.json"
            work_dir = root / "review"
            platform_srt.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nHello.\n",
                encoding="utf-8",
            )
            whisper_json.write_text(
                json.dumps(
                    {
                        "text": "Hello.",
                        "language": "en",
                        "segments": [
                            {
                                "start": 0.0,
                                "end": 1.0,
                                "text": "Hello.",
                                "words": [
                                    {"start": 0.0, "end": 0.8, "word": "Hello."}
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(platform_srt),
                    str(whisper_json),
                    "--work-dir",
                    str(work_dir),
                    "--source-language",
                    "en",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("MLX Whisper adapter provenance", result.stderr)
            self.assertFalse((work_dir / "review-manifest.json").exists())

    def test_prepare_emits_only_reviewable_platform_whisper_disagreements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            platform_srt = root / "platform.srt"
            whisper_json = root / "whisper.json"
            work_dir = root / "review"
            platform_raw = (
                "1\n00:00:00,000 --> 00:00:02,000\nWelcome to JZSub.\n\n"
                "2\n00:00:02,000 --> 00:00:04,000\n"
                "Mario and Armin built this.\n\n"
                "3\n00:00:04,000 --> 00:00:06,000\nThanks for watching.\n"
            ).encode()
            platform_srt.write_bytes(platform_raw)
            whisper_raw = (
                json.dumps(
                    {
                        "schema_version": 1,
                        "backend": "mlx-whisper",
                        "model_source": "local",
                        "word_timestamps": True,
                        "media": {
                            "path": "fixture.mkv",
                            "sha256": "0" * 64,
                            "size_bytes": 1,
                        },
                        "text": (
                            "Welcome to JZSub. Mario and Armand built this. "
                            "Thanks for watching."
                        ),
                        "language": "en",
                        "model": "mlx-community/whisper-large-v3-turbo",
                        "segments": [
                            {
                                "start": 0.0,
                                "end": 2.0,
                                "text": "Welcome to JZSub.",
                                "words": [
                                    {"start": 0.0, "end": 0.5, "word": "Welcome"},
                                    {"start": 0.5, "end": 0.8, "word": " to"},
                                    {"start": 0.8, "end": 1.5, "word": " JZSub."},
                                ],
                            },
                            {
                                "start": 2.0,
                                "end": 4.0,
                                "text": "Mario and Armand built this.",
                                "words": [
                                    {"start": 2.0, "end": 2.4, "word": "Mario"},
                                    {"start": 2.4, "end": 2.7, "word": " and"},
                                    {"start": 2.7, "end": 3.1, "word": " Armand"},
                                    {"start": 3.1, "end": 3.5, "word": " built"},
                                    {"start": 3.5, "end": 3.9, "word": " this."},
                                ],
                            },
                            {
                                "start": 4.0,
                                "end": 6.0,
                                "text": "Thanks for watching.",
                                "words": [
                                    {"start": 4.0, "end": 4.6, "word": "Thanks"},
                                    {"start": 4.6, "end": 5.0, "word": " for"},
                                    {"start": 5.0, "end": 5.8, "word": " watching."},
                                ],
                            },
                        ],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            ).encode()
            whisper_json.write_bytes(whisper_raw)
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(platform_srt),
                    str(whisper_json),
                    "--work-dir",
                    str(work_dir),
                    "--source-language",
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
            manifest_path = Path(payload["manifest"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["cue_count"], 3)
            self.assertEqual(manifest["review_count"], 1)
            self.assertEqual(
                manifest["platform_source"]["sha256"],
                hashlib.sha256(platform_raw).hexdigest(),
            )
            self.assertEqual(
                manifest["asr_hypothesis"]["sha256"],
                hashlib.sha256(whisper_raw).hexdigest(),
            )
            self.assertEqual(
                Path(manifest["platform_source"]["archive_path"]).read_bytes(),
                platform_raw,
            )
            self.assertEqual(
                Path(manifest["asr_hypothesis"]["archive_path"]).read_bytes(),
                whisper_raw,
            )
            self.assertEqual(len(manifest["review_batches"]), 1)
            batch = json.loads(
                Path(manifest["review_batches"][0]["path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(batch["output_fields"], ["id", "reviewed"])
            self.assertEqual(len(batch["items"]), 1)
            item = batch["items"][0]
            self.assertEqual(item["id"], "review-000002")
            self.assertEqual(item["cue_id"], "cue-000002")
            self.assertEqual(item["platform"], "Mario and Armin built this.")
            self.assertEqual(item["whisper_hypothesis"], "Mario and Armand built this.")
            self.assertEqual(item["review_channel"], "proper_name")
            self.assertLess(item["similarity"], manifest["similarity_threshold"])

    def test_next_batch_decision_renders_a_derived_source_without_mutating_platform(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            platform_srt = root / "platform.srt"
            whisper_json = root / "whisper.json"
            work_dir = root / "review"
            render_dir = root / "rendered"
            platform_raw = (
                "7\n00:00:00,000 --> 00:00:02,000\nWelcome, Armine.\n"
            ).encode()
            platform_srt.write_bytes(platform_raw)
            whisper_json.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "backend": "mlx-whisper",
                        "model_source": "local",
                        "word_timestamps": True,
                        "media": {
                            "path": "fixture.mkv",
                            "sha256": "0" * 64,
                            "size_bytes": 1,
                        },
                        "text": "Welcome, Armin.",
                        "language": "en",
                        "model": "mlx-community/whisper-large-v3-turbo",
                        "segments": [
                            {
                                "start": 0.0,
                                "end": 2.0,
                                "text": "Welcome, Armin.",
                                "words": [
                                    {"start": 0.0, "end": 0.8, "word": "Welcome,"},
                                    {"start": 0.8, "end": 1.8, "word": " Armin."},
                                ],
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(platform_srt),
                    str(whisper_json),
                    "--work-dir",
                    str(work_dir),
                    "--source-language",
                    "en",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            manifest_path = Path(json.loads(prepared.stdout)["manifest"])

            pending = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "next-batch",
                    "--manifest",
                    str(manifest_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(pending.returncode, 0, pending.stderr)
            pending_payload = json.loads(pending.stdout)
            self.assertFalse(pending_payload["done"])
            self.assertEqual(pending_payload["remaining"], 1)
            output_path = Path(pending_payload["output_path"])
            output_path.write_text(
                json.dumps(
                    {
                        "decisions": [
                            {"id": "review-000001", "reviewed": "Welcome, Armin."}
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            rendered = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "render",
                    "--manifest",
                    str(manifest_path),
                    "--decisions-dir",
                    str(output_path.parent),
                    "--output-dir",
                    str(render_dir),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                check=False,
            )

            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            rendered_payload = json.loads(rendered.stdout)
            reviewed_source = Path(rendered_payload["reviewed_source"])
            validation = json.loads(
                Path(rendered_payload["validation"]).read_text(encoding="utf-8")
            )
            self.assertEqual(
                reviewed_source.read_text(encoding="utf-8"),
                "7\n00:00:00,000 --> 00:00:02,000\nWelcome, Armin.\n",
            )
            self.assertEqual(platform_srt.read_bytes(), platform_raw)
            self.assertEqual(
                (work_dir / "platform.original.srt").read_bytes(), platform_raw
            )
            self.assertTrue(validation["structurally_valid"])
            self.assertEqual(validation["cue_count"], 1)
            self.assertEqual(validation["decision_count"], 1)
            self.assertEqual(
                validation["platform_source_sha256"],
                hashlib.sha256(platform_raw).hexdigest(),
            )
            self.assertEqual(
                validation["reviewed_source_sha256"],
                hashlib.sha256(reviewed_source.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                Path(validation["review_manifest"]["path"]), manifest_path
            )
            self.assertEqual(
                validation["review_manifest"]["sha256"],
                hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            )

            platform_record = {
                "path": str(platform_srt),
                "sha256": hashlib.sha256(platform_raw).hexdigest(),
                "size_bytes": len(platform_raw),
            }
            download_manifest = root / "download-manifest.json"
            download_manifest.write_text(
                json.dumps(
                    {
                        "output_directory": str(root),
                        "deliverable": "full",
                        "target_language": "zh-CN",
                        "source": {"title": "ASR review fixture"},
                        "status": "asr_transcription_required",
                        "execution": {
                            "complete": False,
                            "next_stage": "asr_transcription_required",
                            "asr_review_requested": True,
                        },
                        "artifacts": {
                            "intermediate": None,
                            "media_streams": [],
                            "subtitle": {
                                "language": "en",
                                "kind": "automatic",
                                "source_srt": platform_record,
                                "original_is_never_modified_by_this_script": True,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            applied = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "apply",
                    "--download-manifest",
                    str(download_manifest),
                    "--validation",
                    rendered_payload["validation"],
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                check=False,
            )

            self.assertEqual(applied.returncode, 3, applied.stderr)
            self.assertEqual(json.loads(applied.stdout)["status"], "bilingual_required")
            updated = json.loads(download_manifest.read_text(encoding="utf-8"))
            subtitle = updated["artifacts"]["subtitle"]
            self.assertEqual(subtitle["source_srt"], platform_record)
            self.assertEqual(
                subtitle["reviewed_source_srt"]["path"], str(reviewed_source)
            )
            self.assertEqual(
                subtitle["reviewed_source_srt"]["sha256"],
                validation["reviewed_source_sha256"],
            )
            self.assertEqual(updated["execution"]["next_stage"], "translation_required")
            subtitle_manifest = Path(updated["execution"]["subtitle_manifest"])
            prepared_translation = json.loads(
                subtitle_manifest.read_text(encoding="utf-8")
            )
            self.assertEqual(
                prepared_translation["source"]["original_path"], str(reviewed_source)
            )
            self.assertEqual(platform_srt.read_bytes(), platform_raw)

    def test_prepare_uses_word_timestamps_when_one_whisper_segment_spans_cues(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            platform_srt = root / "platform.srt"
            whisper_json = root / "whisper.json"
            work_dir = root / "review"
            platform_srt.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nHello Mario\n\n"
                "2\n00:00:01,000 --> 00:00:02,000\nwelcome back\n",
                encoding="utf-8",
            )
            whisper_json.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "backend": "mlx-whisper",
                        "model": "mlx-community/whisper-large-v3-turbo",
                        "model_source": "local",
                        "word_timestamps": True,
                        "media": {
                            "path": "fixture.mkv",
                            "sha256": "0" * 64,
                            "size_bytes": 1,
                        },
                        "text": "Hello Mario welcome back",
                        "language": "en",
                        "segments": [
                            {
                                "start": 0.0,
                                "end": 2.0,
                                "text": "Hello Mario welcome back",
                                "words": [
                                    {"start": 0.0, "end": 0.4, "word": "Hello"},
                                    {"start": 0.4, "end": 0.9, "word": " Mario"},
                                    {"start": 1.0, "end": 1.5, "word": " welcome"},
                                    {"start": 1.5, "end": 1.9, "word": " back"},
                                ],
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(platform_srt),
                    str(whisper_json),
                    "--work-dir",
                    str(work_dir),
                    "--source-language",
                    "en",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(
                Path(json.loads(result.stdout)["manifest"]).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["cue_count"], 2)
            self.assertEqual(manifest["review_count"], 0)
            self.assertEqual(manifest["review_batches"], [])

    def test_prepare_matches_the_best_contiguous_words_for_a_rolling_cue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            platform_srt = root / "platform.srt"
            whisper_json = root / "whisper.json"
            work_dir = root / "review"
            platform_srt.write_text(
                "1\n00:00:07,560 --> 00:00:09,480\n>> Hey, Mario.\n",
                encoding="utf-8",
            )
            whisper_json.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "backend": "mlx-whisper",
                        "model": "mlx-community/whisper-large-v3-turbo",
                        "model_source": "local",
                        "word_timestamps": True,
                        "media": {
                            "path": "fixture.wav",
                            "sha256": "0" * 64,
                            "size_bytes": 1,
                        },
                        "text": "Hey, Mario. Hey, Ben.",
                        "language": "en",
                        "segments": [
                            {
                                "start": 6.8,
                                "end": 10.1,
                                "text": "Hey, Mario. Hey, Ben.",
                                "words": [
                                    {"start": 7.0, "end": 7.3, "word": "Hey,"},
                                    {"start": 7.4, "end": 8.1, "word": " Mario."},
                                    {"start": 9.0, "end": 9.3, "word": " Hey,"},
                                    {"start": 9.4, "end": 10.0, "word": " Ben."},
                                ],
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(platform_srt),
                    str(whisper_json),
                    "--work-dir",
                    str(work_dir),
                    "--source-language",
                    "en",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(
                Path(json.loads(result.stdout)["manifest"]).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["review_count"], 0)
            self.assertEqual(manifest["review_batches"], [])

    def test_prepare_ignores_an_intra_word_hyphen_difference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            platform_srt = root / "platform.srt"
            whisper_json = root / "whisper.json"
            work_dir = root / "review"
            platform_srt.write_text(
                "1\n00:00:00,000 --> 00:00:04,000\n"
                ">> I'm pretty okayish, I guess. I'm\n",
                encoding="utf-8",
            )
            whisper_json.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "backend": "mlx-whisper",
                        "model": "mlx-community/whisper-large-v3-turbo",
                        "model_source": "local",
                        "word_timestamps": True,
                        "media": {
                            "path": "fixture.wav",
                            "sha256": "0" * 64,
                            "size_bytes": 1,
                        },
                        "text": "I'm pretty okay-ish, I guess. I'm",
                        "language": "en",
                        "segments": [
                            {
                                "start": 0.0,
                                "end": 4.0,
                                "text": "I'm pretty okay-ish, I guess. I'm",
                                "words": [
                                    {"start": 0.0, "end": 0.4, "word": "I'm"},
                                    {"start": 0.4, "end": 0.9, "word": " pretty"},
                                    {"start": 0.9, "end": 1.6, "word": " okay-ish,"},
                                    {"start": 1.6, "end": 1.9, "word": " I"},
                                    {"start": 1.9, "end": 2.5, "word": " guess."},
                                    {"start": 2.5, "end": 3.0, "word": " I'm"},
                                ],
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(platform_srt),
                    str(whisper_json),
                    "--work-dir",
                    str(work_dir),
                    "--source-language",
                    "en",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(
                Path(json.loads(result.stdout)["manifest"]).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["review_count"], 0)

    def test_prepare_uses_material_and_proper_name_review_channels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            platform_srt = root / "platform.srt"
            whisper_json = root / "whisper.json"
            work_dir = root / "review"
            platform_srt.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\n"
                "The red bird flew away.\n\n"
                "2\n00:00:04,000 --> 00:00:06,000\n"
                "I'm here with Armen who's normally here.\n\n"
                "3\n00:00:08,000 --> 00:00:10,000\n"
                "and we thought it'd be fun um to do an\n\n"
                "4\n00:00:12,000 --> 00:00:14,000\n"
                "I'm pretty okayish, I guess. I'm\n",
                encoding="utf-8",
            )
            whisper_json.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "backend": "mlx-whisper",
                        "model": "mlx-community/whisper-large-v3-turbo",
                        "model_source": "local",
                        "word_timestamps": True,
                        "media": {
                            "path": "fixture.wav",
                            "sha256": "0" * 64,
                            "size_bytes": 1,
                        },
                        "text": (
                            "A blue car stopped here. "
                            "I'm here with Armin who's normally here. "
                            "and we thought it'd be fun to do an episode "
                            "I'm pretty OK-ish, I guess. I'm"
                        ),
                        "language": "en",
                        "segments": [
                            {
                                "start": 0.0,
                                "end": 2.0,
                                "text": "A blue car stopped here.",
                                "words": [
                                    {"start": 0.0, "end": 0.3, "word": "A"},
                                    {"start": 0.3, "end": 0.6, "word": " blue"},
                                    {"start": 0.6, "end": 0.9, "word": " car"},
                                    {"start": 0.9, "end": 1.3, "word": " stopped"},
                                    {"start": 1.3, "end": 1.8, "word": " here."},
                                ],
                            },
                            {
                                "start": 4.0,
                                "end": 6.0,
                                "text": "I'm here with Armin who's normally here.",
                                "words": [
                                    {"start": 4.0, "end": 4.2, "word": "I'm"},
                                    {"start": 4.2, "end": 4.5, "word": " here"},
                                    {"start": 4.5, "end": 4.8, "word": " with"},
                                    {"start": 4.8, "end": 5.1, "word": " Armin"},
                                    {"start": 5.1, "end": 5.4, "word": " who's"},
                                    {"start": 5.4, "end": 5.7, "word": " normally"},
                                    {"start": 5.7, "end": 5.9, "word": " here."},
                                ],
                            },
                            {
                                "start": 8.0,
                                "end": 10.0,
                                "text": "and we thought it'd be fun to do an episode",
                                "words": [
                                    {"start": 8.0, "end": 8.2, "word": "and"},
                                    {"start": 8.2, "end": 8.4, "word": " we"},
                                    {"start": 8.4, "end": 8.6, "word": " thought"},
                                    {"start": 8.6, "end": 8.8, "word": " it'd"},
                                    {"start": 8.8, "end": 9.0, "word": " be"},
                                    {"start": 9.0, "end": 9.2, "word": " fun"},
                                    {"start": 9.2, "end": 9.4, "word": " to"},
                                    {"start": 9.4, "end": 9.6, "word": " do"},
                                    {"start": 9.6, "end": 9.8, "word": " an"},
                                    {"start": 9.8, "end": 10.0, "word": " episode"},
                                ],
                            },
                            {
                                "start": 12.0,
                                "end": 14.0,
                                "text": "I'm pretty OK-ish, I guess. I'm",
                                "words": [
                                    {"start": 12.0, "end": 12.3, "word": "I'm"},
                                    {"start": 12.3, "end": 12.6, "word": " pretty"},
                                    {"start": 12.6, "end": 13.0, "word": " OK-ish,"},
                                    {"start": 13.0, "end": 13.2, "word": " I"},
                                    {"start": 13.2, "end": 13.6, "word": " guess."},
                                    {"start": 13.6, "end": 13.9, "word": " I'm"},
                                ],
                            },
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(platform_srt),
                    str(whisper_json),
                    "--work-dir",
                    str(work_dir),
                    "--source-language",
                    "en",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(
                Path(json.loads(result.stdout)["manifest"]).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["material_similarity_threshold"], 0.75)
            self.assertEqual(
                [
                    (item["cue_id"], item["review_channel"])
                    for item in manifest["review_items"]
                ],
                [
                    ("cue-000001", "material"),
                    ("cue-000002", "proper_name"),
                ],
            )


if __name__ == "__main__":
    unittest.main()
