#!/usr/bin/env python3
"""Build an immutable library Acquisition Package from verified job artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from typing import Any, Sequence
import urllib.parse


DELIVERY_SCHEMA_VERSION = "1.1.0"
GORIN_JZSUB_VERSION = "0.5.0"
PACKAGE_DIRECTORY_NAME = "acquisition-package"
LANGUAGE_TAG = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
LOCALIZATION_FAILURES = frozenset({"provider_failed", "validation_failed", "retry_exhausted"})
PROTECTED_SPAN_PATTERNS = (
    re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?<!\d)(?:\d{1,2}:)?\d{1,2}:\d{2}(?!\d)"),
    re.compile(r"(?<![\w])#[\w-]+", re.UNICODE),
)


class PackageError(RuntimeError):
    """The job cannot be promoted to an Acquisition Package."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageError(f"could not read JSON file: {path.name}") from exc
    if not isinstance(value, dict):
        raise PackageError(f"JSON root must be an object: {path.name}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    data = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_reference(path: Path, package_root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(package_root).as_posix(),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }


def _package_file(package_root: Path, relative_path: Any) -> Path:
    if not isinstance(relative_path, str) or not relative_path or "\\" in relative_path:
        raise PackageError("Acquisition Package contains an invalid file path")
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != relative_path:
        raise PackageError(
            f"Acquisition Package path is not canonical: {relative_path}"
        )
    candidate = package_root.joinpath(*pure.parts)
    current = package_root
    for part in pure.parts:
        current = current / part
        if current.is_symlink():
            raise PackageError(
                f"Acquisition Package must not contain symlinks: {relative_path}"
            )
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise PackageError(
            f"Acquisition Package file is missing: {relative_path}"
        ) from exc
    if not resolved.is_relative_to(package_root) or not resolved.is_file():
        raise PackageError(
            f"Acquisition Package file escapes its root: {relative_path}"
        )
    return resolved


def verify_acquisition_package(
    package_root: Path, expected_package_id: str | None = None
) -> dict[str, Any]:
    package_root = package_root.expanduser().resolve(strict=True)
    manifest = _read_json(package_root / "delivery-manifest.json")
    if manifest.get("schema_version") != DELIVERY_SCHEMA_VERSION:
        raise PackageError("Acquisition Package has an unsupported schema version")
    if (
        expected_package_id is not None
        and manifest.get("package_id") != expected_package_id
    ):
        raise PackageError("Acquisition Package identity differs from the current job")

    metadata = manifest.get("metadata")
    artifacts = manifest.get("artifacts")
    if not isinstance(metadata, dict) or not isinstance(artifacts, list):
        raise PackageError("Acquisition Package has no metadata or artifacts")
    snapshot = metadata.get("snapshot")
    projections = metadata.get("localized_projections")
    if not isinstance(snapshot, dict) or not isinstance(projections, list):
        raise PackageError("Acquisition Package metadata references are invalid")
    references = [snapshot, *projections, *artifacts]
    paths = [
        reference.get("path") for reference in references if isinstance(reference, dict)
    ]
    if len(paths) != len(references) or len(paths) != len(set(paths)):
        raise PackageError("Acquisition Package paths must be declared exactly once")

    for reference in references:
        path = _package_file(package_root, reference["path"])
        if path.stat().st_size != reference.get("size_bytes"):
            raise PackageError(
                f"Acquisition Package size mismatch: {reference['path']}"
            )
        if _sha256(path) != reference.get("sha256"):
            raise PackageError(
                f"Acquisition Package checksum mismatch: {reference['path']}"
            )

    actual = {
        path.relative_to(package_root).as_posix()
        for path in package_root.rglob("*")
        if path.is_file() and path.name != "delivery-manifest.json"
    }
    symlinks = [path for path in package_root.rglob("*") if path.is_symlink()]
    if symlinks:
        raise PackageError("Acquisition Package must not contain symlinks")
    if actual != set(paths):
        raise PackageError("Acquisition Package declared and actual file sets differ")
    required_roles = {
        "source_master",
        "source_transcript",
        "source_subtitle",
        "target_subtitle",
        "bilingual_subtitle",
        "thumbnail",
    }
    roles = [
        artifact.get("role") for artifact in artifacts if isinstance(artifact, dict)
    ]
    if any(roles.count(role) != 1 for role in required_roles):
        raise PackageError("Acquisition Package required artifact roles are incomplete")
    return manifest


def _job_file(job_root: Path, record: Any, label: str) -> Path:
    value = record.get("path") if isinstance(record, dict) else None
    if not isinstance(value, str) or not value:
        raise PackageError(f"download manifest has no {label} path")
    if "\\" in value:
        raise PackageError(f"{label} path must use POSIX separators")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or str(relative) != value:
        raise PackageError(f"{label} path is not job-relative")
    candidate = job_root.joinpath(*relative.parts)
    if candidate.is_symlink():
        raise PackageError(f"{label} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise PackageError(f"declared {label} is missing") from exc
    if not resolved.is_relative_to(job_root) or not resolved.is_file():
        raise PackageError(f"declared {label} is outside the job directory")
    return resolved


def _copy_artifact(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if _sha256(source) != _sha256(target):
        raise PackageError(
            f"copied artifact failed checksum verification: {target.name}"
        )
    return target


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PackageError(f"{label} is required")
    return value.strip()


def _language(value: Any, label: str) -> str:
    language = _required_string(value, label)
    if not LANGUAGE_TAG.fullmatch(language):
        raise PackageError(f"{label} must be a language tag")
    return language


def _upload_date(value: Any) -> str:
    raw = _required_string(value, "source upload date")
    if re.fullmatch(r"[0-9]{8}", raw):
        raw = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    try:
        return dt.date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise PackageError("source upload date must be YYYY-MM-DD or YYYYMMDD") from exc


def _youtube_url(value: Any) -> str:
    url = _required_string(value, "canonical YouTube URL")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "youtube.com",
        "www.youtube.com",
    }:
        raise PackageError(
            "library delivery currently requires a canonical YouTube URL"
        )
    return url


def _stream(artifacts: dict[str, Any], kind: str) -> dict[str, Any]:
    streams = artifacts.get("media_streams")
    if not isinstance(streams, list):
        raise PackageError("download manifest has no media stream probe")
    matches = [
        stream
        for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == kind
    ]
    if len(matches) != 1:
        raise PackageError(f"library baseline requires exactly one {kind} stream")
    return matches[0]


def _positive_number(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PackageError(f"{label} must be a positive number") from exc
    if number <= 0:
        raise PackageError(f"{label} must be a positive number")
    return number


def _artifact_record(
    role: str,
    path: Path,
    package_root: Path,
    *,
    language: str | None = None,
    media: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {"role": role, **_file_reference(path, package_root)}
    if language is not None:
        record["language"] = language
    if media is not None:
        record["media"] = media
    return record


def _unique_strings(values: Sequence[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        if isinstance(value, str) and value and value not in result:
            result.append(value)
    return result


def _transcript_kind(value: Any) -> str:
    normalized = str(value or "").lower()
    if normalized in {"manual", "subtitles", "platform_manual"}:
        return "platform_manual"
    if normalized in {"automatic", "automatic_captions", "platform_automatic"}:
        return "platform_automatic"
    if normalized == "asr":
        return "asr"
    raise PackageError("source transcript kind is not recognized")


def _protected_spans(*values: str) -> Counter[str]:
    spans: Counter[str] = Counter()
    for value in values:
        for pattern in PROTECTED_SPAN_PATTERNS:
            spans.update(match.group(0).rstrip(".,;:!?，。；：！？") for match in pattern.finditer(value))
    return spans


def _localized_metadata_input(
    path: Path,
    *,
    job_root: Path,
    target_language: str,
    source_title: str,
    source_description: str,
) -> dict[str, Any]:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = job_root / candidate
    if candidate.is_symlink():
        raise PackageError("localized metadata input must not be a symlink")
    try:
        candidate = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise PackageError("localized metadata input is missing") from exc
    if not candidate.is_relative_to(job_root) or not candidate.is_file():
        raise PackageError("localized metadata input must be inside the job directory")
    localized = _read_json(candidate)
    if set(localized) != {"locale", "title", "description"}:
        raise PackageError(
            "localized metadata input must contain only locale, title, and description"
        )
    locale = _language(localized.get("locale"), "localized metadata locale")
    if locale != target_language:
        raise PackageError("localized metadata locale differs from the target language")
    title = _required_string(localized.get("title"), "localized metadata title")
    description = localized.get("description")
    if not isinstance(description, str):
        raise PackageError("localized metadata description must be a string")
    if _protected_spans(source_title, source_description) != _protected_spans(
        title, description
    ):
        raise PackageError("localized metadata did not preserve protected spans")
    return {
        "locale": locale,
        "title": title,
        "description": description,
        "protected_spans_preserved": True,
    }


def build_library_package(
    download_manifest: Path,
    *,
    translation_provider: str,
    translation_model: str,
    quality_status: str,
    quality_rules_version: str,
    source_audio_language: str | None = None,
    localized_metadata: Path | None = None,
    localization_failure: str | None = None,
    tool_revision: str | None = None,
) -> Path:
    download_manifest = download_manifest.expanduser().resolve()
    download = _read_json(download_manifest)
    if download.get("deliverable") != "library":
        raise PackageError("download manifest deliverable must be library")

    output_value = download.get("output_directory")
    job_root = (
        Path(output_value).expanduser().resolve()
        if isinstance(output_value, str)
        else download_manifest.parent
    )
    if job_root != download_manifest.parent.resolve():
        raise PackageError(
            "download manifest must be stored at its output_directory root"
        )

    source = download.get("source")
    artifacts = download.get("artifacts")
    selection = download.get("selection")
    if not isinstance(source, dict) or not isinstance(artifacts, dict):
        raise PackageError("download manifest source and artifacts are required")
    if not isinstance(selection, dict):
        raise PackageError("download manifest selection is required")

    subtitle = artifacts.get("subtitle")
    if not isinstance(subtitle, dict):
        raise PackageError("library delivery requires a source subtitle")
    source_language = _language(subtitle.get("language"), "source subtitle language")
    target_language = _language(download.get("target_language"), "target language")
    if localized_metadata is not None and localization_failure is not None:
        raise PackageError(
            "localized metadata input and localization failure are mutually exclusive"
        )
    if localization_failure is not None and localization_failure not in LOCALIZATION_FAILURES:
        raise PackageError("localized metadata failure classification is not recognized")

    master_record = artifacts.get("lossless_mp4_master") or artifacts.get(
        "intermediate"
    )
    master_source = _job_file(job_root, master_record, "Source Master")
    cover_source = _job_file(job_root, artifacts.get("cover"), "cover")
    transcript_source = _job_file(
        job_root, subtitle.get("source_srt"), "Source Transcript"
    )
    transcript_kind = _transcript_kind(subtitle.get("kind"))
    source_subtitle_source = _job_file(
        job_root,
        subtitle.get("original") if transcript_kind != "asr" else subtitle.get("source_srt"),
        "source subtitle",
    )
    rendered_root = job_root / "subtitles" / "rendered"
    target_source = _job_file(
        job_root,
        {"path": f"subtitles/rendered/{target_language}.srt"},
        "target subtitle",
    )
    bilingual_source = _job_file(
        job_root,
        {"path": "subtitles/rendered/bilingual.srt"},
        "bilingual subtitle",
    )
    validation_report = _read_json(rendered_root / "validation.json")
    if validation_report.get("structurally_valid") is not True:
        raise PackageError("rendered subtitle validation is not structurally valid")
    if validation_report.get("target_language") != target_language:
        raise PackageError("rendered subtitle target language differs from the job")

    if quality_status != "operator_reviewed":
        raise PackageError(
            "library v0.4 requires operator_reviewed until an automatic quality gate exists"
        )
    provider = _required_string(translation_provider, "translation provider")
    model = _required_string(translation_model, "translation model")
    rules_version = _required_string(quality_rules_version, "quality rules version")

    video_stream = _stream(artifacts, "video")
    audio_stream = _stream(artifacts, "audio")
    audio_selection = selection.get("source_audio_track")
    if not isinstance(audio_selection, dict):
        raise PackageError("download manifest has no Source Audio Track selection")
    audio_selection_evidence = _unique_strings(
        audio_selection.get("selection_evidence", [])
        if isinstance(audio_selection.get("selection_evidence"), list)
        else []
    )
    if not any(
        item
        in {
            "single_audio_track",
            "platform_original",
            "platform_default",
            "operator_language_override",
        }
        for item in audio_selection_evidence
    ):
        raise PackageError(
            "Source Audio Track selection lacks single/original/default/override evidence"
        )
    audio_language = _language(
        source_audio_language
        or audio_selection.get("language")
        or source.get("declared_language"),
        "Source Audio Track language",
    )
    stream_bitrate = audio_stream.get("bit_rate")
    bitrate_value = stream_bitrate or audio_selection.get("bitrate_bps")
    audio_bitrate = int(_positive_number(bitrate_value, "audio bitrate"))
    bitrate_evidence = (
        "ffprobe_stream_bitrate"
        if stream_bitrate is not None
        else "yt_dlp_requested_format_bitrate"
    )
    duration = _positive_number(source.get("duration_seconds"), "source duration")

    source_id = _required_string(source.get("id"), "source ID")
    package_id = f"youtube:{source_id}:acquisition:1"
    destination = job_root / PACKAGE_DIRECTORY_NAME
    if destination.exists():
        existing = verify_acquisition_package(destination, package_id)
        expected_translation = {
            "provider": provider,
            "model": model,
            "quality_status": quality_status,
            "quality_rules_version": rules_version,
        }
        if existing.get("provenance", {}).get("translation") != expected_translation:
            raise PackageError(
                "existing Acquisition Package translation provenance differs from this run"
            )
        existing_artifacts = {
            artifact["role"]: artifact
            for artifact in existing["artifacts"]
            if isinstance(artifact, dict) and isinstance(artifact.get("role"), str)
        }
        current_sources = {
            "source_master": master_source,
            "source_transcript": transcript_source,
            "source_subtitle": source_subtitle_source,
            "target_subtitle": target_source,
            "bilingual_subtitle": bilingual_source,
            "thumbnail": cover_source,
        }
        if any(
            existing_artifacts[role]["sha256"] != _sha256(path)
            for role, path in current_sources.items()
        ):
            raise PackageError(
                "existing Acquisition Package artifacts differ from the current job"
            )
        return destination

    staging = Path(tempfile.mkdtemp(prefix=".acquisition-package.", dir=job_root))
    try:
        master_target = _copy_artifact(
            master_source,
            staging / "artifacts" / f"source-master{master_source.suffix.lower()}",
        )
        transcript_target = _copy_artifact(
            transcript_source, staging / "artifacts" / "source-transcript.srt"
        )
        source_subtitle_target = _copy_artifact(
            source_subtitle_source,
            staging
            / "artifacts"
            / f"source-subtitle.{source_language}{source_subtitle_source.suffix.lower()}",
        )
        target_subtitle_target = _copy_artifact(
            target_source, staging / "artifacts" / f"target.{target_language}.srt"
        )
        bilingual_target = _copy_artifact(
            bilingual_source, staging / "artifacts" / f"bilingual.{target_language}.srt"
        )
        cover_target = _copy_artifact(
            cover_source,
            staging / "artifacts" / f"thumbnail{cover_source.suffix.lower()}",
        )

        canonical_url = _youtube_url(source.get("url"))
        metadata_snapshot = {
            "title": _required_string(source.get("title"), "source title"),
            "description": str(source.get("description") or ""),
            "channel_id": _required_string(source.get("channel_id"), "channel ID"),
            "channel_name": _required_string(
                source.get("channel_name"), "channel name"
            ),
            "upload_date": _upload_date(source.get("upload_date")),
            "canonical_url": canonical_url,
            "language": source_language,
            "duration_seconds": duration,
        }
        tags = source.get("tags")
        if isinstance(tags, list) and all(isinstance(item, str) for item in tags):
            if len(tags) != len(set(tags)):
                raise PackageError("source metadata tags must be unique")
            metadata_snapshot["tags"] = tags
        metadata_path = staging / "metadata" / "source.json"
        _write_json(metadata_path, metadata_snapshot)
        localized_references: list[dict[str, Any]] = []
        localization_warnings: list[str] = []
        if localized_metadata is not None:
            projection = _localized_metadata_input(
                localized_metadata,
                job_root=job_root,
                target_language=target_language,
                source_title=metadata_snapshot["title"],
                source_description=metadata_snapshot["description"],
            )
            projection_path = staging / "metadata" / f"{target_language}.json"
            _write_json(projection_path, projection)
            localized_references.append(
                {
                    "locale": target_language,
                    **_file_reference(projection_path, staging),
                }
            )
        elif localization_failure is not None:
            localization_warnings.append(
                f"localized_metadata_{localization_failure}"
            )

        source_master_media = {
            "kind": "video",
            "container": master_source.suffix.lower().lstrip("."),
            "video_codec": _required_string(
                video_stream.get("codec_name"), "video codec"
            ),
            "width": int(_positive_number(video_stream.get("width"), "video width")),
            "height": int(_positive_number(video_stream.get("height"), "video height")),
            "duration_seconds": duration,
            "source_audio_track": {
                "language": audio_language,
                "format_id": _required_string(
                    audio_selection.get("format_id"), "Source Audio Track format ID"
                ),
                "codec": _required_string(
                    audio_stream.get("codec_name"), "audio codec"
                ),
                "bitrate_bps": audio_bitrate,
                "selection_evidence": _unique_strings(
                    [
                        bitrate_evidence,
                        *audio_selection_evidence,
                    ]
                ),
            },
        }
        artifact_records = [
            _artifact_record(
                "source_master",
                master_target,
                staging,
                media=source_master_media,
            ),
            _artifact_record(
                "source_transcript",
                transcript_target,
                staging,
                language=source_language,
            ),
            _artifact_record(
                "source_subtitle",
                source_subtitle_target,
                staging,
                language=source_language,
            ),
            _artifact_record(
                "target_subtitle",
                target_subtitle_target,
                staging,
                language=target_language,
            ),
            _artifact_record(
                "bilingual_subtitle",
                bilingual_target,
                staging,
                language=target_language,
            ),
            _artifact_record("thumbnail", cover_target, staging),
        ]

        tool = {"name": "gorin-jzsub", "version": GORIN_JZSUB_VERSION}
        if tool_revision is not None:
            revision = _required_string(tool_revision, "tool revision")
            if not re.fullmatch(r"[0-9a-f]{7,64}", revision):
                raise PackageError("tool revision must be a lowercase Git revision")
            tool["revision"] = revision

        now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        manifest = {
            "schema_version": DELIVERY_SCHEMA_VERSION,
            "package_id": package_id,
            "created_at": now,
            "source": {
                "platform": "youtube",
                "source_id": source_id,
                "canonical_url": canonical_url,
                "source_type": source.get("source_type") or "video",
                "channel": {
                    "id": metadata_snapshot["channel_id"],
                    "name": metadata_snapshot["channel_name"],
                },
                "upload_date": metadata_snapshot["upload_date"],
            },
            "metadata": {
                "snapshot": _file_reference(metadata_path, staging),
                "localized_projections": localized_references,
                **(
                    {"localization_warnings": localization_warnings}
                    if localization_warnings
                    else {}
                ),
            },
            "artifacts": artifact_records,
            "provenance": {
                "acquisition_tool": tool,
                "source_transcript": {
                    "kind": transcript_kind,
                    "language": source_language,
                    "artifact_path": "artifacts/source-transcript.srt",
                },
                "translation": {
                    "provider": provider,
                    "model": model,
                    "quality_status": quality_status,
                    "quality_rules_version": rules_version,
                },
            },
            "validation": {
                "package_complete": True,
                "checksums_verified": True,
                "validated_at": now,
                "validator": {
                    "name": "gorin-jzsub-package-delivery",
                    "version": GORIN_JZSUB_VERSION,
                },
            },
        }
        _write_json(staging / "delivery-manifest.json", manifest)
        verify_acquisition_package(staging, package_id)
        os.replace(staging, destination)
        return destination
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an immutable library Acquisition Package."
    )
    parser.add_argument("download_manifest", type=Path)
    parser.add_argument("--translation-provider", required=True)
    parser.add_argument("--translation-model", required=True)
    parser.add_argument(
        "--quality-status",
        choices=("operator_reviewed",),
        required=True,
    )
    parser.add_argument("--quality-rules-version", required=True)
    parser.add_argument("--source-audio-language")
    localization = parser.add_mutually_exclusive_group()
    localization.add_argument("--localized-metadata", type=Path)
    localization.add_argument(
        "--localization-failure",
        choices=tuple(sorted(LOCALIZATION_FAILURES)),
    )
    parser.add_argument("--tool-revision")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        package = build_library_package(
            args.download_manifest,
            translation_provider=args.translation_provider,
            translation_model=args.translation_model,
            quality_status=args.quality_status,
            quality_rules_version=args.quality_rules_version,
            source_audio_language=args.source_audio_language,
            localized_metadata=args.localized_metadata,
            localization_failure=args.localization_failure,
            tool_revision=args.tool_revision,
        )
    except (PackageError, OSError) as exc:
        print(f"library package error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"complete": True, "package": str(package)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
