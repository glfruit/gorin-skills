from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fetch_video.py"
SPEC = importlib.util.spec_from_file_location("jzsub_test_fetch_video_module", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
fetch_video = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch_video)


class FetchVideoSourceBoundaryTests(unittest.TestCase):
    def test_single_audio_track_is_selected_with_explicit_evidence(self) -> None:
        selected = fetch_video.source_audio_track_from_probe(
            {
                "original_language": "en",
                "formats": [
                    {
                        "format_id": "140",
                        "vcodec": "none",
                        "acodec": "aac",
                        "language": "en",
                        "abr": 96,
                    },
                    {
                        "format_id": "251",
                        "vcodec": "none",
                        "acodec": "opus",
                        "language": "en",
                        "abr": 128,
                    }
                ],
            }
        )

        self.assertEqual(selected["format_id"], "251")
        self.assertEqual(selected["language"], "en")
        self.assertEqual(selected["bitrate_bps"], 128000)
        self.assertIn("single_audio_track", selected["selection_evidence"])

    def test_original_audio_wins_over_a_higher_bitrate_chinese_dub(self) -> None:
        selected = fetch_video.source_audio_track_from_probe(
            {
                "original_language": "en",
                "formats": [
                    {
                        "format_id": "251-en",
                        "vcodec": "none",
                        "acodec": "opus",
                        "language": "en",
                        "format_note": "English original (default)",
                        "abr": 128,
                    },
                    {
                        "format_id": "251-zh",
                        "vcodec": "none",
                        "acodec": "opus",
                        "language": "zh-CN",
                        "format_note": "Chinese dubbed",
                        "abr": 160,
                    },
                ],
            }
        )

        self.assertEqual(selected["format_id"], "251-en")
        self.assertIn("platform_original", selected["selection_evidence"])
        self.assertIn("source_language_match", selected["selection_evidence"])

    def test_unique_platform_original_is_selected_without_top_level_language(self) -> None:
        selected = fetch_video.source_audio_track_from_probe(
            {
                "formats": [
                    {
                        "format_id": "251-en",
                        "vcodec": "none",
                        "acodec": "opus",
                        "language": "en",
                        "format_note": "English original",
                        "abr": 128,
                    },
                    {
                        "format_id": "251-zh",
                        "vcodec": "none",
                        "acodec": "opus",
                        "language": "zh-CN",
                        "format_note": "Chinese dubbed",
                        "abr": 160,
                    },
                ]
            }
        )

        self.assertEqual(selected["format_id"], "251-en")
        self.assertIn("platform_original", selected["selection_evidence"])

    def test_multiple_platform_original_identities_do_not_use_bitrate_as_a_tiebreak(self) -> None:
        info = {
            "formats": [
                {
                    "format_id": "251-en",
                    "vcodec": "none",
                    "acodec": "opus",
                    "language": "en",
                    "format_note": "English original",
                    "abr": 128,
                },
                {
                    "format_id": "251-fr",
                    "vcodec": "none",
                    "acodec": "opus",
                    "language": "fr",
                    "format_note": "French original",
                    "abr": 192,
                },
            ]
        }

        with self.assertRaises(fetch_video.SourceAudioSelectionError):
            fetch_video.source_audio_track_from_probe(info)

    def test_ambiguous_audio_fails_closed_and_language_override_recovers(self) -> None:
        info = {
            "formats": [
                {
                    "format_id": "251-en",
                    "vcodec": "none",
                    "acodec": "opus",
                    "language": "en",
                    "abr": 128,
                },
                {
                    "format_id": "251-fr",
                    "vcodec": "none",
                    "acodec": "opus",
                    "language": "fr",
                    "abr": 144,
                },
            ]
        }

        with self.assertRaises(fetch_video.SourceAudioSelectionError) as raised:
            fetch_video.source_audio_track_from_probe(info)
        self.assertEqual(raised.exception.classification, "needs_attention")

        selected = fetch_video.source_audio_track_from_probe(
            info, source_audio_language="fr"
        )
        self.assertEqual(selected["format_id"], "251-fr")
        self.assertIn("operator_language_override", selected["selection_evidence"])

    def test_active_and_upcoming_sources_return_deferred_evidence(self) -> None:
        active = fetch_video.source_availability_from_probe(
            {"live_status": "is_live", "release_timestamp": 1784300000}
        )
        upcoming = fetch_video.source_availability_from_probe(
            {"live_status": "is_upcoming", "release_timestamp": 1784400000}
        )

        self.assertEqual(active["status"], "source_deferred")
        self.assertEqual(active["reason"], "active_livestream")
        self.assertEqual(upcoming["status"], "source_deferred")
        self.assertEqual(upcoming["reason"], "upcoming_premiere")
        self.assertEqual(upcoming["release_timestamp"], 1784400000)

    def test_shorts_and_completed_live_vod_use_stable_source_types(self) -> None:
        short = fetch_video.source_type_from_probe(
            {
                "webpage_url": "https://www.youtube.com/watch?v=short-fixture",
                "live_status": "not_live",
            },
            "https://www.youtube.com/shorts/short-fixture",
        )
        completed_live = fetch_video.source_type_from_probe(
            {
                "webpage_url": "https://www.youtube.com/watch?v=live-fixture",
                "live_status": "was_live",
            },
            "https://www.youtube.com/watch?v=live-fixture",
        )

        self.assertEqual(short, "short")
        self.assertEqual(completed_live, "completed_live_vod")

    def test_download_selector_uses_the_proven_source_audio_format(self) -> None:
        selector = fetch_video.format_selector_for_source_audio(
            {"format_id": "251-en"}
        )

        self.assertEqual(selector, "bv*+251-en/b[format_id=251-en]")

    def test_active_source_cli_writes_deferred_manifest_without_downloading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            output_dir = root / "output"
            bin_dir.mkdir()
            fake_ytdlp = bin_dir / "yt-dlp"
            fake_ytdlp.write_text(
                f"#!{sys.executable}\n"
                + textwrap.dedent(
                    """\
                    import json
                    print(json.dumps({
                        "id": "active-fixture",
                        "title": "Active fixture",
                        "extractor_key": "Youtube",
                        "webpage_url": "https://www.youtube.com/watch?v=active-fixture",
                        "live_status": "is_live",
                        "release_timestamp": 1784300000,
                        "subtitles": {},
                        "automatic_captions": {},
                    }))
                    """
                ),
                encoding="utf-8",
            )
            fake_ytdlp.chmod(0o755)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "https://www.youtube.com/watch?v=active-fixture",
                    "--output-dir",
                    str(output_dir),
                    "--deliver",
                    "library",
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": str(bin_dir)},
                check=False,
            )

            self.assertEqual(result.returncode, 3, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "source_deferred")
            manifest = json.loads(
                (output_dir / "download-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["availability"]["reason"], "active_livestream")
            self.assertFalse(manifest["execution"]["complete"])

    def test_ambiguous_audio_cli_writes_structured_needs_attention_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            output_dir = root / "output"
            bin_dir.mkdir()
            fake_ytdlp = bin_dir / "yt-dlp"
            fake_ytdlp.write_text(
                f"#!{sys.executable}\n"
                + textwrap.dedent(
                    """\
                    import json
                    print(json.dumps({
                        "id": "ambiguous-audio",
                        "title": "Ambiguous audio",
                        "extractor_key": "Youtube",
                        "webpage_url": "https://www.youtube.com/watch?v=ambiguous-audio",
                        "duration": 1,
                        "subtitles": {"en": [{"ext": "srt"}]},
                        "automatic_captions": {},
                        "formats": [
                            {"format_id": "251-en", "vcodec": "none", "acodec": "opus", "language": "en", "abr": 128},
                            {"format_id": "251-fr", "vcodec": "none", "acodec": "opus", "language": "fr", "abr": 144},
                        ],
                    }))
                    """
                ),
                encoding="utf-8",
            )
            fake_ytdlp.chmod(0o755)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "https://www.youtube.com/watch?v=ambiguous-audio",
                    "--output-dir",
                    str(output_dir),
                    "--deliver",
                    "library",
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": str(bin_dir)},
                check=False,
            )

            self.assertEqual(result.returncode, 3, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "needs_attention")
            self.assertEqual(payload["reason"], "source_audio_ambiguous")
            self.assertEqual(payload["available_languages"], ["en", "fr"])


class FetchVideoLibraryDeliveryTests(unittest.TestCase):
    def test_library_delivery_is_a_non_burning_dry_run_target(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "https://www.youtube.com/watch?v=fixture",
                "--output-dir",
                "/tmp/gorin-jzsub-library-fixture",
                "--deliver",
                "library",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["deliverable"], "library")
        self.assertFalse(plan["files_written"])


class FetchVideoRuntimeDiagnosticsTests(unittest.TestCase):
    def _advance_manifest(self, manifest_path: Path) -> tuple[int, dict[str, object]]:
        spec = importlib.util.spec_from_file_location("jzsub_test_fetch_video", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec else None)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            return_code = module._advance_bilingual_stage(manifest_path)
        return return_code, json.loads(output.getvalue())

    def _write_review_manifest(self, root: Path, kind: str) -> Path:
        source = root / "platform.srt"
        source.write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nHello, Mario.\n",
            encoding="utf-8",
        )
        manifest_path = root / "download-manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "output_directory": str(root),
                    "deliverable": "full",
                    "target_language": "zh-CN",
                    "source": {"title": "Review state fixture"},
                    "execution": {"asr_review_requested": True},
                    "artifacts": {
                        "intermediate": {"path": "source.mkv"},
                        "media_streams": [],
                        "subtitle": {
                            "language": "en",
                            "kind": kind,
                            "source_srt": {"path": source.name},
                        },
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return manifest_path

    def _write_executable(self, directory: Path, name: str, source: str) -> Path:
        path = directory / name
        path.write_text(source, encoding="utf-8")
        path.chmod(0o755)
        return path

    def _run_cli(
        self, *, missing_runtime: bool, allow_remote_ejs: bool = False
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            output_dir = root / "output"
            bin_dir.mkdir()

            fake_ytdlp = f"#!{sys.executable}\n" + textwrap.dedent(
                """\
                import json
                from pathlib import Path
                import os
                import sys

                args = sys.argv[1:]
                missing_runtime = os.environ.get("FAKE_YTDLP_MISSING_RUNTIME") == "1"
                if "--dump-single-json" in args:
                    runtime = "none" if missing_runtime else "deno-2.8.3"
                    print(f"[debug] JS runtimes: {runtime}", file=sys.stderr)
                    print(json.dumps({
                        "id": "runtime-fixture",
                        "title": "Runtime Fixture",
                        "extractor_key": "Youtube",
                        "webpage_url": "https://www.youtube.com/watch?v=runtime-fixture",
                        "duration": 1,
                        "subtitles": {"en": [{"ext": "srt"}]},
                        "automatic_captions": {},
                    }))
                    raise SystemExit(0)

                if "--write-subs" in args:
                    if missing_runtime:
                        print(
                            "WARNING: [youtube] No supported JavaScript runtime could be found.",
                            file=sys.stderr,
                        )
                    output_root = Path(args[args.index("-P") + 1])
                    template = args[args.index("-o") + 1].removeprefix("subtitle:")
                    subtitle = output_root / template.replace("%(ext)s", "srt")
                    subtitle.write_text(
                        "1\\n00:00:00,000 --> 00:00:01,000\\nHello\\n",
                        encoding="utf-8",
                    )
                    raise SystemExit(0)

                print("unexpected fake yt-dlp invocation", file=sys.stderr)
                raise SystemExit(2)
                """
            )
            self._write_executable(bin_dir, "yt-dlp", fake_ytdlp)
            no_op = f"#!{sys.executable}\nraise SystemExit(0)\n"
            self._write_executable(bin_dir, "ffmpeg", no_op)
            self._write_executable(bin_dir, "ffprobe", no_op)

            env = os.environ.copy()
            env["PATH"] = str(bin_dir)
            if missing_runtime:
                env["FAKE_YTDLP_MISSING_RUNTIME"] = "1"
            command = [
                sys.executable,
                str(SCRIPT),
                "https://www.youtube.com/watch?v=runtime-fixture",
                "--output-dir",
                str(output_dir),
                "--deliver",
                "subs",
            ]
            if allow_remote_ejs:
                command.append("--allow-remote-ejs")
            result = subprocess.run(
                command,
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
            return json.loads(
                (output_dir / "download-manifest.json").read_text(encoding="utf-8")
            )

    def test_cli_does_not_warn_when_ytdlp_reports_an_embedded_js_runtime(self) -> None:
        manifest = self._run_cli(missing_runtime=False)

        warnings = manifest["warnings"]
        self.assertIsInstance(warnings, list)
        assert isinstance(warnings, list)
        self.assertFalse(
            any("JavaScript runtime" in warning for warning in warnings),
            warnings,
        )

    def test_cli_preserves_ytdlp_missing_runtime_warning(self) -> None:
        manifest = self._run_cli(missing_runtime=True)

        warnings = manifest["warnings"]
        self.assertIsInstance(warnings, list)
        assert isinstance(warnings, list)
        self.assertTrue(
            any("No supported JavaScript runtime" in warning for warning in warnings),
            warnings,
        )

    def test_cli_accepts_wrapper_runtime_for_remote_ejs(self) -> None:
        manifest = self._run_cli(
            missing_runtime=False,
            allow_remote_ejs=True,
        )

        self.assertEqual(manifest["status"], "subs_complete")

    def test_dry_run_declares_optional_auto_subtitle_review(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "https://www.youtube.com/watch?v=review-fixture",
                "--output-dir",
                "/tmp/review-fixture",
                "--review-auto-subs",
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
        self.assertEqual(payload["deliverable"], "full")
        self.assertTrue(payload["review_auto_subs"])
        self.assertFalse(payload["network_accessed"])
        self.assertFalse(payload["files_written"])

    def test_requested_review_pauses_an_automatic_subtitle_before_translation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self._write_review_manifest(root, "automatic")

            return_code, payload = self._advance_manifest(manifest_path)

            self.assertEqual(return_code, 3)
            self.assertEqual(payload["status"], "asr_transcription_required")
            updated = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                updated["execution"]["next_stage"], "asr_transcription_required"
            )
            self.assertFalse((root / "subtitles").exists())

    def test_requested_review_does_not_pause_a_manual_subtitle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self._write_review_manifest(root, "manual")

            return_code, payload = self._advance_manifest(manifest_path)

            self.assertEqual(return_code, 3)
            self.assertEqual(payload["status"], "bilingual_required")
            updated = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["execution"]["next_stage"], "translation_required")


if __name__ == "__main__":
    unittest.main()
