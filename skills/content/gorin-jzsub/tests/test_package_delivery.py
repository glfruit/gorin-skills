from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "package_delivery.py"
SPEC = importlib.util.spec_from_file_location("package_delivery", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
packaging = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packaging)


class PackageDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self._write_job()

    def _write(self, relative_path: str, content: bytes) -> dict[str, object]:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return {"path": relative_path, "size_bytes": len(content)}

    def _write_job(self) -> None:
        master = self._write("video.master.mp4", b"source master")
        cover = self._write("cover.jpg", b"cover")
        original = self._write("video.source-original.en.vtt", b"original subtitle")
        source_srt = self._write("video.source-srt.en.srt", b"source transcript")
        self._write("subtitles/rendered/source.srt", b"rendered source")
        self._write("subtitles/rendered/zh-CN.srt", b"target subtitle")
        self._write("subtitles/rendered/bilingual.srt", b"bilingual subtitle")
        self._write(
            "subtitles/rendered/validation.json",
            json.dumps(
                {
                    "structurally_valid": True,
                    "translation_quality_reviewed": False,
                    "target_language": "zh-CN",
                }
            ).encode(),
        )
        manifest = {
            "schema_version": 1,
            "created_at": "2026-07-17T00:00:00+00:00",
            "deliverable": "library",
            "target_language": "zh-CN",
            "output_directory": str(self.root),
            "source": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "extractor": "Youtube",
                "id": "dQw4w9WgXcQ",
                "title": "Fixture title",
                "description": "Fixture description",
                "channel_id": "UC-fixture",
                "channel_name": "Fixture Channel",
                "upload_date": "2024-01-02",
                "duration_seconds": 1.0,
                "declared_language": "en",
            },
            "selection": {
                "source_audio_track": {
                    "format_id": "140",
                    "language": "en",
                    "bitrate_bps": 128000,
                    "selection_evidence": ["single_audio_track"],
                }
            },
            "artifacts": {
                "lossless_mp4_master": master,
                "intermediate": None,
                "cover": cover,
                "media_streams": [
                    {
                        "index": 0,
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 16,
                        "height": 16,
                    },
                    {
                        "index": 1,
                        "codec_type": "audio",
                        "codec_name": "aac",
                    },
                ],
                "subtitle": {
                    "language": "en",
                    "kind": "manual",
                    "original": original,
                    "source_srt": source_srt,
                },
            },
        }
        self.download_manifest = self.root / "download-manifest.json"
        self.download_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    def test_builds_a_complete_library_acquisition_package(self) -> None:
        package = packaging.build_library_package(
            self.download_manifest,
            translation_provider="codex",
            translation_model="fixture-model",
            quality_status="operator_reviewed",
            quality_rules_version="fixture-rules-1",
        )

        manifest = json.loads(
            (package / "delivery-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["schema_version"], "1.1.0")
        self.assertEqual(manifest["source"]["source_id"], "dQw4w9WgXcQ")
        self.assertEqual(
            {artifact["role"] for artifact in manifest["artifacts"]},
            {
                "source_master",
                "source_transcript",
                "source_subtitle",
                "target_subtitle",
                "bilingual_subtitle",
                "thumbnail",
            },
        )
        self.assertEqual(manifest["metadata"]["localized_projections"], [])
        self.assertEqual(manifest["provenance"]["translation"]["provider"], "codex")
        source_master = next(
            artifact
            for artifact in manifest["artifacts"]
            if artifact["role"] == "source_master"
        )
        self.assertEqual(
            source_master["media"]["source_audio_track"]["selection_evidence"],
            ["yt_dlp_requested_format_bitrate", "single_audio_track"],
        )
        self.assertTrue((package / "artifacts/source-master.mp4").is_file())
        self.assertTrue((package / "metadata/source.json").is_file())
        self.assertEqual(
            packaging.verify_acquisition_package(package)["package_id"],
            "youtube:dQw4w9WgXcQ:acquisition:1",
        )

    def test_rejects_a_tampered_existing_package(self) -> None:
        package = packaging.build_library_package(
            self.download_manifest,
            translation_provider="codex",
            translation_model="fixture-model",
            quality_status="operator_reviewed",
            quality_rules_version="fixture-rules-1",
        )
        (package / "artifacts/source-master.mp4").write_bytes(b"tampered")

        with self.assertRaisesRegex(packaging.PackageError, "size mismatch"):
            packaging.build_library_package(
                self.download_manifest,
                translation_provider="codex",
                translation_model="fixture-model",
                quality_status="operator_reviewed",
                quality_rules_version="fixture-rules-1",
            )

    def test_refuses_machine_validated_without_an_automatic_quality_gate(self) -> None:
        with self.assertRaisesRegex(
            packaging.PackageError, "requires operator_reviewed"
        ):
            packaging.build_library_package(
                self.download_manifest,
                translation_provider="codex",
                translation_model="fixture-model",
                quality_status="machine_validated",
                quality_rules_version="fixture-rules-1",
            )

    def test_builds_a_separate_localized_metadata_projection_with_protected_spans(self) -> None:
        source = json.loads(self.download_manifest.read_text(encoding="utf-8"))
        source["source"]["title"] = "Release notes #Archive"
        source["source"]["description"] = (
            "00:30 Chapter one\nhttps://example.com/watch?v=1\n"
            "mail@example.com\n#Archive"
        )
        self.download_manifest.write_text(json.dumps(source), encoding="utf-8")
        localized = self.root / "localized-metadata.zh-CN.json"
        localized.write_text(
            json.dumps(
                {
                    "locale": "zh-CN",
                    "title": "发布说明 #Archive",
                    "description": (
                        "00:30 第一章\nhttps://example.com/watch?v=1\n"
                        "mail@example.com\n#Archive"
                    ),
                }
            ),
            encoding="utf-8",
        )

        package = packaging.build_library_package(
            self.download_manifest,
            translation_provider="codex",
            translation_model="fixture-model",
            quality_status="operator_reviewed",
            quality_rules_version="fixture-rules-1",
            localized_metadata=localized,
        )

        manifest = json.loads(
            (package / "delivery-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["schema_version"], "1.1.0")
        self.assertEqual(
            manifest["metadata"]["localized_projections"][0]["locale"], "zh-CN"
        )
        projection = json.loads(
            (package / "metadata/zh-CN.json").read_text(encoding="utf-8")
        )
        snapshot = json.loads(
            (package / "metadata/source.json").read_text(encoding="utf-8")
        )
        self.assertEqual(snapshot["title"], "Release notes #Archive")
        self.assertEqual(projection["title"], "发布说明 #Archive")
        self.assertTrue(projection["protected_spans_preserved"])

    def test_rejects_localized_metadata_that_changes_a_protected_span(self) -> None:
        source = json.loads(self.download_manifest.read_text(encoding="utf-8"))
        source["source"]["description"] = "Docs: https://example.com/source"
        self.download_manifest.write_text(json.dumps(source), encoding="utf-8")
        localized = self.root / "localized-metadata.zh-CN.json"
        localized.write_text(
            json.dumps(
                {
                    "locale": "zh-CN",
                    "title": "本地化标题",
                    "description": "文档：https://example.com/changed",
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(packaging.PackageError, "protected spans"):
            packaging.build_library_package(
                self.download_manifest,
                translation_provider="codex",
                translation_model="fixture-model",
                quality_status="operator_reviewed",
                quality_rules_version="fixture-rules-1",
                localized_metadata=localized,
            )

    def test_rejects_localized_metadata_that_breaks_chapter_line_structure(self) -> None:
        source = json.loads(self.download_manifest.read_text(encoding="utf-8"))
        source["source"]["description"] = "00:30 Chapter one"
        self.download_manifest.write_text(json.dumps(source), encoding="utf-8")
        localized = self.root / "localized-metadata.zh-CN.json"
        localized.write_text(
            json.dumps(
                {
                    "locale": "zh-CN",
                    "title": "本地化标题",
                    "description": "第一章 00:30",
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(packaging.PackageError, "chapter timestamp structure"):
            packaging.build_library_package(
                self.download_manifest,
                translation_provider="codex",
                translation_model="fixture-model",
                quality_status="operator_reviewed",
                quality_rules_version="fixture-rules-1",
                localized_metadata=localized,
            )

    def test_localization_failure_keeps_snapshot_and_records_a_bounded_warning(self) -> None:
        package = packaging.build_library_package(
            self.download_manifest,
            translation_provider="codex",
            translation_model="fixture-model",
            quality_status="operator_reviewed",
            quality_rules_version="fixture-rules-1",
            localization_failure="retry_exhausted",
        )

        manifest = json.loads(
            (package / "delivery-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["metadata"]["localized_projections"], [])
        self.assertEqual(
            manifest["metadata"]["localization_warnings"],
            ["localized_metadata_retry_exhausted"],
        )
        snapshot = json.loads(
            (package / "metadata/source.json").read_text(encoding="utf-8")
        )
        self.assertEqual(snapshot["title"], "Fixture title")
        self.assertEqual(snapshot["description"], "Fixture description")

    def test_records_each_supported_source_transcript_provenance(self) -> None:
        for source_kind, expected in (
            ("manual", "platform_manual"),
            ("automatic", "platform_automatic"),
            ("asr", "asr"),
        ):
            with self.subTest(source_kind=source_kind):
                source = json.loads(self.download_manifest.read_text(encoding="utf-8"))
                source["artifacts"]["subtitle"]["kind"] = source_kind
                if source_kind == "asr":
                    source["artifacts"]["subtitle"]["original"] = None
                self.download_manifest.write_text(json.dumps(source), encoding="utf-8")

                package = packaging.build_library_package(
                    self.download_manifest,
                    translation_provider="codex",
                    translation_model="fixture-model",
                    quality_status="operator_reviewed",
                    quality_rules_version="fixture-rules-1",
                )

                manifest = json.loads(
                    (package / "delivery-manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(
                    manifest["provenance"]["source_transcript"]["kind"], expected
                )
                if source_kind == "asr":
                    artifacts = {
                        artifact["role"]: artifact for artifact in manifest["artifacts"]
                    }
                    self.assertEqual(
                        artifacts["source_subtitle"]["sha256"],
                        artifacts["source_transcript"]["sha256"],
                    )
                shutil.rmtree(package)
                self._write_job()

    def test_source_audio_language_override_cannot_relabel_an_existing_selection(self) -> None:
        with self.assertRaisesRegex(packaging.PackageError, "cannot relabel"):
            packaging.build_library_package(
                self.download_manifest,
                translation_provider="codex",
                translation_model="fixture-model",
                quality_status="operator_reviewed",
                quality_rules_version="fixture-rules-1",
                source_audio_language="fr",
            )

    def test_existing_package_rejects_a_different_localized_projection_intent(self) -> None:
        first = self.root / "localized-first.json"
        first.write_text(
            json.dumps(
                {
                    "locale": "zh-CN",
                    "title": "第一个标题",
                    "description": "第一个简介",
                }
            ),
            encoding="utf-8",
        )
        packaging.build_library_package(
            self.download_manifest,
            translation_provider="codex",
            translation_model="fixture-model",
            quality_status="operator_reviewed",
            quality_rules_version="fixture-rules-1",
            localized_metadata=first,
        )
        second = self.root / "localized-second.json"
        second.write_text(
            json.dumps(
                {
                    "locale": "zh-CN",
                    "title": "第二个标题",
                    "description": "第二个简介",
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(packaging.PackageError, "localized metadata differs"):
            packaging.build_library_package(
                self.download_manifest,
                translation_provider="codex",
                translation_model="fixture-model",
                quality_status="operator_reviewed",
                quality_rules_version="fixture-rules-1",
                localized_metadata=second,
            )


if __name__ == "__main__":
    unittest.main()
