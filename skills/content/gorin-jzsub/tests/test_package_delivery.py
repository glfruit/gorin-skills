from __future__ import annotations

import importlib.util
import json
from pathlib import Path
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
                    "selection_evidence": ["yt_dlp_requested_format"],
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
                        "bit_rate": "128000",
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
        self.assertEqual(manifest["schema_version"], "1.0.0")
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


if __name__ == "__main__":
    unittest.main()
