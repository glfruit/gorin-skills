#!/usr/bin/env python3
"""Prepare source-locked review batches from platform and ASR transcripts."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unicodedata
from typing import Any, Sequence


SCHEMA_VERSION = 1
PIPELINE_VERSION = "0.2"
REVIEW_CONTRACT_VERSION = 2
DEFAULT_SIMILARITY_THRESHOLD = 0.92
DEFAULT_MATERIAL_SIMILARITY_THRESHOLD = 0.75
REVIEW_BATCH_SIZE = 50
REVIEW_CONTEXT_CUES = 2
WORD_ALIGNMENT_MARGIN_MS = 750
PLATFORM_ARCHIVE_NAME = "platform.original.srt"
HYPOTHESIS_ARCHIVE_NAME = "whisper.original.json"
MANIFEST_NAME = "review-manifest.json"
REVIEW_INPUT_DIR = "review-input"
REVIEW_OUTPUT_DIR = "review-output"
REQUIRED_REVIEW_INVARIANTS = {
    "platform_source_archive_unchanged",
    "asr_hypothesis_archive_unchanged",
    "cue_order_and_timeline_preserved",
    "all_review_items_adjudicated",
    "unreviewed_cues_preserved",
}


class ReviewError(RuntimeError):
    """A user-facing ASR review failure."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _archive_once(path: Path, data: bytes, label: str) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise ReviewError(f"write-once {label} archive already has different bytes")
        return
    _atomic_write(path, data)


def _load_subtitle_pipeline() -> Any:
    path = Path(__file__).resolve().with_name("subtitle_pipeline.py")
    spec = importlib.util.spec_from_file_location("jzsub_asr_review_subtitles", path)
    if spec is None or spec.loader is None:
        raise ReviewError(f"could not load subtitle pipeline: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_fetch_video() -> Any:
    path = Path(__file__).resolve().with_name("fetch_video.py")
    spec = importlib.util.spec_from_file_location("jzsub_asr_review_fetch", path)
    if spec is None or spec.loader is None:
        raise ReviewError(f"could not load fetch workflow: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_whisper(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewError("Whisper hypothesis must be UTF-8 JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("segments"), list):
        raise ReviewError("Whisper hypothesis must contain a segments array")
    media = value.get("media")
    media_hash = media.get("sha256") if isinstance(media, dict) else None
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("backend") != "mlx-whisper"
        or value.get("word_timestamps") is not True
        or not isinstance(value.get("model"), str)
        or not value["model"].strip()
        or value.get("model_source") not in {"local", "huggingface"}
        or not isinstance(value.get("language"), str)
        or not isinstance(media, dict)
        or not isinstance(media.get("path"), str)
        or not isinstance(media_hash, str)
        or len(media_hash) != 64
        or any(character not in "0123456789abcdef" for character in media_hash)
        or not isinstance(media.get("size_bytes"), int)
        or media["size_bytes"] < 0
    ):
        raise ReviewError(
            "Whisper hypothesis lacks complete MLX Whisper adapter provenance"
        )
    return value


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReviewError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReviewError(f"invalid JSON in {path}: {exc}") from exc


def _whisper_segments(value: dict[str, Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    previous_start = -1
    for position, raw_segment in enumerate(value["segments"], start=1):
        if not isinstance(raw_segment, dict):
            raise ReviewError(f"Whisper segment {position} must be an object")
        try:
            start = float(raw_segment["start"])
            end = float(raw_segment["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ReviewError(f"Whisper segment {position} has invalid timestamps") from exc
        text = raw_segment.get("text")
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or end <= start
            or start < previous_start
            or not isinstance(text, str)
            or not text.strip()
        ):
            raise ReviewError(f"Whisper segment {position} is invalid or out of order")
        previous_start = start
        raw_words = raw_segment.get("words")
        if not isinstance(raw_words, list) or not raw_words:
            raise ReviewError(
                f"Whisper segment {position} must contain word timestamps"
            )
        words: list[dict[str, Any]] = []
        previous_word_start = -1.0
        for word_position, raw_word in enumerate(raw_words, start=1):
            if not isinstance(raw_word, dict):
                raise ReviewError(
                    f"Whisper segment {position} word {word_position} must be an object"
                )
            try:
                word_start = float(raw_word["start"])
                word_end = float(raw_word["end"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ReviewError(
                    f"Whisper segment {position} word {word_position} has invalid timestamps"
                ) from exc
            word_text = raw_word.get("word")
            if (
                not math.isfinite(word_start)
                or not math.isfinite(word_end)
                or word_start < 0
                or word_end <= word_start
                or word_start < previous_word_start
                or not isinstance(word_text, str)
                or not word_text.strip()
            ):
                raise ReviewError(
                    f"Whisper segment {position} word {word_position} is invalid or out of order"
                )
            previous_word_start = word_start
            words.append(
                {
                    "start_ms": round(word_start * 1000),
                    "end_ms": round(word_end * 1000),
                    "text": word_text,
                }
            )
        segments.append(
            {
                "start_ms": round(start * 1000),
                "end_ms": round(end * 1000),
                "text": text.strip(),
                "words": words,
            }
        )
    if not segments:
        raise ReviewError("Whisper hypothesis contains no speech segments")
    return segments


def _comparison_tokens(value: str) -> list[str]:
    return [token.casefold() for token in _surface_tokens(value)]


def _similarity(platform: str, hypothesis: str) -> float:
    left = _comparison_tokens(platform)
    right = _comparison_tokens(hypothesis)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return round(difflib.SequenceMatcher(None, left, right).ratio(), 6)


def _surface_tokens(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", value)
    tokens: list[str] = []
    word: list[str] = []
    for index, character in enumerate(normalized):
        if character.isascii() and character.isalnum():
            word.append(character)
            continue
        if (
            unicodedata.category(character) == "Pd"
            and word
            and index + 1 < len(normalized)
            and normalized[index + 1].isascii()
            and normalized[index + 1].isalnum()
        ):
            continue
        if word:
            tokens.append("".join(word))
            word = []
        if character.isalnum():
            tokens.append(character)
    if word:
        tokens.append("".join(word))
    return tokens


def _is_name_like(token: str) -> bool:
    letters = [character for character in token if character.isalpha()]
    if len(letters) < 2:
        return False
    if all(character.isupper() for character in letters):
        return True
    return letters[0].isupper() and all(
        character.islower() for character in letters[1:]
    )


def _proper_name_disagreement(platform: str, hypothesis: str) -> bool:
    left = _surface_tokens(platform)
    right = _surface_tokens(hypothesis)
    matcher = difflib.SequenceMatcher(
        None,
        [token.casefold() for token in left],
        [token.casefold() for token in right],
    )
    for operation, left_start, left_end, right_start, right_end in matcher.get_opcodes():
        if operation != "replace":
            continue
        for left_token in left[left_start:left_end]:
            for right_token in right[right_start:right_end]:
                if (
                    (_is_name_like(left_token) or _is_name_like(right_token))
                    and difflib.SequenceMatcher(
                        None, left_token.casefold(), right_token.casefold()
                    ).ratio()
                    >= 0.6
                ):
                    return True
    return False


def _platform_cues(parsed: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"cue-{position:06d}",
            "position": position,
            "original_index": cue["original_index"],
            "timing_line": cue["timing_line"],
            "start_ms": cue["start_ms"],
            "end_ms": cue["end_ms"],
            "text": cue["text"],
            "text_sha256": _sha256_bytes(cue["text"].encode("utf-8")),
        }
        for position, cue in enumerate(parsed, start=1)
    ]


def _overlapping_hypothesis(
    cue: dict[str, Any], segments: Sequence[dict[str, Any]]
) -> str:
    window_start = max(0, cue["start_ms"] - WORD_ALIGNMENT_MARGIN_MS)
    window_end = cue["end_ms"] + WORD_ALIGNMENT_MARGIN_MS
    overlapping = [
        segment
        for segment in segments
        if segment["end_ms"] > window_start
        and segment["start_ms"] < window_end
    ]
    if any("words" in segment for segment in overlapping):
        candidate_words = [
            word
            for segment in overlapping
            for word in segment.get("words", [])
            if window_start
            <= (word["start_ms"] + word["end_ms"]) / 2
            < window_end
        ]
        platform_token_count = len(_comparison_tokens(cue["text"]))
        cue_center = (cue["start_ms"] + cue["end_ms"]) / 2
        best_text = ""
        best_key: tuple[int, float, float, int] | None = None
        for start in range(len(candidate_words)):
            for end in range(start + 1, len(candidate_words) + 1):
                selected = candidate_words[start:end]
                text = "".join(word["text"] for word in selected).strip()
                token_count = len(_comparison_tokens(text))
                span_center = (selected[0]["start_ms"] + selected[-1]["end_ms"]) / 2
                key = (
                    -abs(token_count - platform_token_count),
                    _similarity(cue["text"], text),
                    -abs(span_center - cue_center),
                    -len(selected),
                )
                if best_key is None or key > best_key:
                    best_key = key
                    best_text = text
        return best_text
    return " ".join(segment["text"] for segment in overlapping).strip()


def _review_items(
    cues: Sequence[dict[str, Any]],
    segments: Sequence[dict[str, Any]],
    threshold: float,
    material_threshold: float,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, cue in enumerate(cues):
        hypothesis = _overlapping_hypothesis(cue, segments)
        similarity = _similarity(cue["text"], hypothesis)
        if similarity < material_threshold:
            review_channel = "material"
        elif similarity < threshold and _proper_name_disagreement(
            cue["text"], hypothesis
        ):
            review_channel = "proper_name"
        else:
            continue
        before = cues[max(0, index - REVIEW_CONTEXT_CUES) : index]
        after = cues[index + 1 : index + 1 + REVIEW_CONTEXT_CUES]
        items.append(
            {
                "id": f"review-{cue['position']:06d}",
                "cue_id": cue["id"],
                "start_ms": cue["start_ms"],
                "end_ms": cue["end_ms"],
                "platform": cue["text"],
                "platform_sha256": cue["text_sha256"],
                "whisper_hypothesis": hypothesis,
                "similarity": similarity,
                "review_channel": review_channel,
                "context": {
                    "before": [
                        {"cue_id": item["id"], "platform": item["text"]}
                        for item in before
                    ],
                    "after": [
                        {"cue_id": item["id"], "platform": item["text"]}
                        for item in after
                    ],
                },
            }
        )
    return items


def _write_batches(
    work_dir: Path,
    source_language: str,
    items: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    input_dir = work_dir / REVIEW_INPUT_DIR
    input_dir.mkdir(parents=True, exist_ok=True)
    for stale in input_dir.glob("batch-*.json"):
        stale.unlink()
    batches: list[dict[str, Any]] = []
    for number, start in enumerate(range(0, len(items), REVIEW_BATCH_SIZE), start=1):
        selected = list(items[start : start + REVIEW_BATCH_SIZE])
        payload = _batch_payload(source_language, selected)
        encoded = _canonical_json_bytes(payload) + b"\n"
        path = (input_dir / f"batch-{number:04d}.json").resolve()
        _atomic_write(path, encoded)
        batches.append(
            {
                "path": str(path),
                "sha256": _sha256_bytes(encoded),
                "item_ids": [item["id"] for item in selected],
            }
        )
    return batches


def _batch_payload(
    source_language: str, items: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "review_contract_version": REVIEW_CONTRACT_VERSION,
        "source_language": source_language,
        "instruction": (
            "Choose the correct source text from the platform cue, Whisper "
            "hypothesis, and read-only context. Preserve the cue ID and output "
            "one reviewed string for every item."
        ),
        "items": list(items),
        "output_fields": ["id", "reviewed"],
    }


def prepare(
    platform_srt: Path,
    whisper_json: Path,
    work_dir: Path,
    source_language: str,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    material_similarity_threshold: float = DEFAULT_MATERIAL_SIMILARITY_THRESHOLD,
) -> Path:
    platform_srt = platform_srt.expanduser().resolve()
    whisper_json = whisper_json.expanduser().resolve()
    work_dir = work_dir.expanduser().resolve()
    source_language = source_language.strip()
    if not source_language:
        raise ReviewError("--source-language cannot be empty")
    if not 0 < similarity_threshold <= 1:
        raise ReviewError("--similarity-threshold must be greater than 0 and at most 1")
    if not 0 < material_similarity_threshold <= similarity_threshold:
        raise ReviewError(
            "--material-similarity-threshold must be greater than 0 and no "
            "greater than --similarity-threshold"
        )
    try:
        platform_raw = platform_srt.read_bytes()
        whisper_raw = whisper_json.read_bytes()
    except FileNotFoundError as exc:
        raise ReviewError(f"input file not found: {exc.filename}") from exc

    subtitle_pipeline = _load_subtitle_pipeline()
    try:
        parsed = subtitle_pipeline.parse_srt_bytes(platform_raw)
    except subtitle_pipeline.PipelineError as exc:
        raise ReviewError(str(exc)) from exc
    hypothesis = _read_whisper(whisper_raw)
    whisper_segments = _whisper_segments(hypothesis)
    cues = _platform_cues(parsed)
    items = _review_items(
        cues,
        whisper_segments,
        similarity_threshold,
        material_similarity_threshold,
    )

    work_dir.mkdir(parents=True, exist_ok=True)
    platform_archive = (work_dir / PLATFORM_ARCHIVE_NAME).resolve()
    hypothesis_archive = (work_dir / HYPOTHESIS_ARCHIVE_NAME).resolve()
    _archive_once(platform_archive, platform_raw, "platform source")
    _archive_once(hypothesis_archive, whisper_raw, "ASR hypothesis")
    batches = _write_batches(work_dir, source_language, items)
    decisions_dir = (work_dir / REVIEW_OUTPUT_DIR).resolve()
    decisions_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "review_contract_version": REVIEW_CONTRACT_VERSION,
        "source_language": source_language,
        "similarity_threshold": similarity_threshold,
        "material_similarity_threshold": material_similarity_threshold,
        "cue_count": len(cues),
        "review_count": len(items),
        "platform_source": {
            "original_path": str(platform_srt),
            "archive_path": str(platform_archive),
            "sha256": _sha256_bytes(platform_raw),
            "size_bytes": len(platform_raw),
        },
        "asr_hypothesis": {
            "original_path": str(whisper_json),
            "archive_path": str(hypothesis_archive),
            "sha256": _sha256_bytes(whisper_raw),
            "size_bytes": len(whisper_raw),
            "backend": hypothesis["backend"],
            "model": hypothesis.get("model"),
            "model_source": hypothesis["model_source"],
            "language": hypothesis.get("language"),
            "word_timestamps": hypothesis["word_timestamps"],
            "media": hypothesis["media"],
        },
        "cues": cues,
        "review_items": items,
        "review_batches": batches,
        "review_output_dir": str(decisions_dir),
    }
    manifest_path = (work_dir / MANIFEST_NAME).resolve()
    _atomic_write(manifest_path, _json_bytes(manifest))
    return manifest_path


def validate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ReviewError("review manifest root must be an object")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ReviewError("unsupported review manifest schema version")
    if manifest.get("pipeline_version") != PIPELINE_VERSION:
        raise ReviewError("unsupported ASR review pipeline version")
    if manifest.get("review_contract_version") != REVIEW_CONTRACT_VERSION:
        raise ReviewError("unsupported ASR review contract version")

    platform = manifest.get("platform_source")
    hypothesis_record = manifest.get("asr_hypothesis")
    if not isinstance(platform, dict) or not isinstance(hypothesis_record, dict):
        raise ReviewError("review manifest provenance is incomplete")
    try:
        platform_archive = Path(platform["archive_path"]).expanduser()
        hypothesis_archive = Path(hypothesis_record["archive_path"]).expanduser()
        platform_raw = platform_archive.read_bytes()
        hypothesis_raw = hypothesis_archive.read_bytes()
    except (KeyError, FileNotFoundError, TypeError) as exc:
        raise ReviewError("review manifest archive is missing") from exc
    if (
        _sha256_bytes(platform_raw) != platform.get("sha256")
        or len(platform_raw) != platform.get("size_bytes")
    ):
        raise ReviewError("platform source archive integrity check failed")
    if (
        _sha256_bytes(hypothesis_raw) != hypothesis_record.get("sha256")
        or len(hypothesis_raw) != hypothesis_record.get("size_bytes")
    ):
        raise ReviewError("ASR hypothesis archive integrity check failed")

    subtitle_pipeline = _load_subtitle_pipeline()
    try:
        expected_cues = _platform_cues(subtitle_pipeline.parse_srt_bytes(platform_raw))
    except subtitle_pipeline.PipelineError as exc:
        raise ReviewError(str(exc)) from exc
    hypothesis = _read_whisper(hypothesis_raw)
    segments = _whisper_segments(hypothesis)
    try:
        threshold = float(manifest["similarity_threshold"])
        material_threshold = float(manifest["material_similarity_threshold"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ReviewError("review manifest similarity thresholds are invalid") from exc
    if not 0 < material_threshold <= threshold <= 1:
        raise ReviewError("review manifest similarity thresholds are invalid")
    expected_items = _review_items(
        expected_cues,
        segments,
        threshold,
        material_threshold,
    )
    if manifest.get("cues") != expected_cues:
        raise ReviewError("review cue ledger differs from locked platform SRT")
    if manifest.get("review_items") != expected_items:
        raise ReviewError("review items differ from locked inputs")
    if manifest.get("cue_count") != len(expected_cues):
        raise ReviewError("review cue count is invalid")
    if manifest.get("review_count") != len(expected_items):
        raise ReviewError("review item count is invalid")

    batches = manifest.get("review_batches")
    if not isinstance(batches, list):
        raise ReviewError("review batch records are invalid")
    expected_batch_count = math.ceil(len(expected_items) / REVIEW_BATCH_SIZE)
    if len(batches) != expected_batch_count:
        raise ReviewError("review batch count is invalid")
    source_language = manifest.get("source_language")
    if not isinstance(source_language, str) or not source_language:
        raise ReviewError("review source language is invalid")
    for index, batch in enumerate(batches):
        if not isinstance(batch, dict) or not isinstance(batch.get("path"), str):
            raise ReviewError("review batch record is invalid")
        path = Path(batch["path"])
        try:
            encoded = path.read_bytes()
        except FileNotFoundError as exc:
            raise ReviewError(f"review batch not found: {path}") from exc
        if _sha256_bytes(encoded) != batch.get("sha256"):
            raise ReviewError(f"review batch SHA-256 mismatch: {path}")
        selected = expected_items[
            index * REVIEW_BATCH_SIZE : (index + 1) * REVIEW_BATCH_SIZE
        ]
        expected_payload = _batch_payload(source_language, selected)
        if _read_json(path) != expected_payload:
            raise ReviewError(f"review batch content differs from locked inputs: {path}")
        if batch.get("item_ids") != [item["id"] for item in selected]:
            raise ReviewError(f"review batch IDs are invalid: {path}")
    return manifest


def _decision_records(path: Path, expected_ids: Sequence[str]) -> list[dict[str, str]]:
    root = _read_json(path)
    records = root.get("decisions") if isinstance(root, dict) else None
    if not isinstance(records, list):
        raise ReviewError(f"review decisions in {path} must contain a decisions array")
    output: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {"id", "reviewed"}:
            raise ReviewError(f"invalid review decision in {path}")
        item_id = record.get("id")
        reviewed = record.get("reviewed")
        if not isinstance(item_id, str) or not isinstance(reviewed, str) or not reviewed.strip():
            raise ReviewError(f"invalid review decision in {path}")
        if "\r" in reviewed or "\n\n" in reviewed or any(
            unicodedata.category(character) == "Cc" and character != "\n"
            for character in reviewed
        ):
            raise ReviewError(f"review decision {item_id} contains invalid control text")
        output.append({"id": item_id, "reviewed": reviewed})
    if [record["id"] for record in output] != list(expected_ids):
        raise ReviewError(f"review decision IDs do not match batch: {path}")
    return output


def next_review_batch(manifest_path: Path) -> dict[str, Any]:
    manifest = validate_manifest(manifest_path)
    output_dir = Path(manifest["review_output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    pending: list[tuple[dict[str, Any], Path]] = []
    for batch in manifest["review_batches"]:
        input_path = Path(batch["path"])
        output_path = output_dir / input_path.name
        if not output_path.exists():
            pending.append((batch, output_path))
            continue
        _decision_records(output_path, batch["item_ids"])
    if not pending:
        return {"done": True, "remaining": 0, "decisions_dir": str(output_dir)}
    batch, output_path = pending[0]
    input_path = Path(batch["path"])
    return {
        "done": False,
        "remaining": len(pending),
        "input_path": str(input_path),
        "output_path": str(output_path),
        "batch": _read_json(input_path),
    }


def _load_decisions(
    manifest: dict[str, Any], decisions_dir: Path
) -> tuple[dict[str, str], list[dict[str, str]]]:
    decisions_dir = decisions_dir.expanduser().resolve()
    collected: dict[str, str] = {}
    files: list[dict[str, str]] = []
    for batch in manifest["review_batches"]:
        path = decisions_dir / Path(batch["path"]).name
        records = _decision_records(path, batch["item_ids"])
        for record in records:
            if record["id"] in collected:
                raise ReviewError(f"duplicate review decision ID: {record['id']}")
            collected[record["id"]] = record["reviewed"]
        files.append({"path": str(path), "sha256": _sha256_bytes(path.read_bytes())})
    expected_ids = [item["id"] for item in manifest["review_items"]]
    if list(collected) != expected_ids:
        raise ReviewError("review decisions are incomplete or out of order")
    return collected, files


def _reviewed_srt(manifest: dict[str, Any], decisions: dict[str, str]) -> bytes:
    decision_by_cue = {
        item["cue_id"]: decisions[item["id"]] for item in manifest["review_items"]
    }
    blocks: list[str] = []
    for cue in manifest["cues"]:
        text = decision_by_cue.get(cue["id"], cue["text"])
        index = cue["original_index"] or str(cue["position"])
        blocks.append(f"{index}\n{cue['timing_line']}\n{text}")
    return ("\n\n".join(blocks) + "\n").encode("utf-8")


def render(
    manifest_path: Path,
    decisions_dir: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    manifest_path = manifest_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    manifest = validate_manifest(manifest_path)
    decisions, decision_files = _load_decisions(manifest, decisions_dir)
    reviewed_raw = _reviewed_srt(manifest, decisions)
    subtitle_pipeline = _load_subtitle_pipeline()
    try:
        reviewed_cues = subtitle_pipeline.parse_srt_bytes(reviewed_raw)
    except subtitle_pipeline.PipelineError as exc:
        raise ReviewError(f"reviewed source is not valid SRT: {exc}") from exc
    if len(reviewed_cues) != len(manifest["cues"]):
        raise ReviewError("reviewed source changed the platform cue count")
    for source, reviewed in zip(manifest["cues"], reviewed_cues):
        if (
            source["timing_line"] != reviewed["timing_line"]
            or source["start_ms"] != reviewed["start_ms"]
            or source["end_ms"] != reviewed["end_ms"]
        ):
            raise ReviewError("reviewed source changed the platform timeline")

    output_dir.mkdir(parents=True, exist_ok=True)
    reviewed_path = (output_dir / "reviewed-source.srt").resolve()
    _atomic_write(reviewed_path, reviewed_raw)
    validation = {
        "schema_version": SCHEMA_VERSION,
        "structurally_valid": True,
        "validation_scope": "asr_source_review",
        "source_language": manifest["source_language"],
        "platform_source_sha256": manifest["platform_source"]["sha256"],
        "asr_hypothesis_sha256": manifest["asr_hypothesis"]["sha256"],
        "reviewed_source_sha256": _sha256_bytes(reviewed_raw),
        "cue_count": len(manifest["cues"]),
        "review_count": len(manifest["review_items"]),
        "decision_count": len(decisions),
        "decision_files": decision_files,
        "review_manifest": {
            "path": str(manifest_path),
            "sha256": _sha256_bytes(manifest_path.read_bytes()),
        },
        "reviewed_source": str(reviewed_path),
        "invariants": {
            "platform_source_archive_unchanged": True,
            "asr_hypothesis_archive_unchanged": True,
            "cue_order_and_timeline_preserved": True,
            "all_review_items_adjudicated": True,
            "unreviewed_cues_preserved": True,
        },
    }
    validation_path = (output_dir / "review-validation.json").resolve()
    _atomic_write(validation_path, _json_bytes(validation))
    return reviewed_path, validation_path


def apply_review(download_manifest: Path, validation_path: Path) -> int:
    """Attach a validated derived SRT and resume the existing translation stage."""

    download_manifest = download_manifest.expanduser().resolve()
    validation_path = validation_path.expanduser().resolve()
    manifest = _read_json(download_manifest)
    validation = _read_json(validation_path)
    if not isinstance(manifest, dict):
        raise ReviewError("download manifest root must be an object")
    if not isinstance(validation, dict):
        raise ReviewError("review validation root must be an object")
    if (
        validation.get("schema_version") != SCHEMA_VERSION
        or validation.get("validation_scope") != "asr_source_review"
        or validation.get("structurally_valid") is not True
    ):
        raise ReviewError("review validation is not a successful ASR source review")
    invariants = validation.get("invariants")
    if (
        not isinstance(invariants, dict)
        or set(invariants) != REQUIRED_REVIEW_INVARIANTS
        or not all(value is True for value in invariants.values())
    ):
        raise ReviewError("review validation invariants are incomplete")

    review_manifest_record = validation.get("review_manifest")
    review_manifest_value = (
        review_manifest_record.get("path")
        if isinstance(review_manifest_record, dict)
        else None
    )
    if not isinstance(review_manifest_value, str):
        raise ReviewError("review validation has no locked review manifest")
    review_manifest_path = Path(review_manifest_value).expanduser().resolve()
    try:
        review_manifest_raw = review_manifest_path.read_bytes()
    except FileNotFoundError as exc:
        raise ReviewError(f"review manifest not found: {review_manifest_path}") from exc
    if _sha256_bytes(review_manifest_raw) != review_manifest_record.get("sha256"):
        raise ReviewError("review manifest SHA-256 does not match validation")
    locked_review = validate_manifest(review_manifest_path)

    output_value = manifest.get("output_directory")
    output_dir = (
        Path(output_value).expanduser().resolve()
        if isinstance(output_value, str)
        else download_manifest.parent
    )
    if download_manifest != output_dir / "download-manifest.json":
        raise ReviewError("download manifest is outside its declared output directory")
    execution = manifest.get("execution")
    artifacts = manifest.get("artifacts")
    subtitle = artifacts.get("subtitle") if isinstance(artifacts, dict) else None
    if not isinstance(execution, dict) or execution.get("asr_review_requested") is not True:
        raise ReviewError("download manifest did not request automatic-caption review")
    if not isinstance(subtitle, dict) or subtitle.get("kind") != "automatic":
        raise ReviewError("ASR review can only be applied to an automatic subtitle track")
    source_language = subtitle.get("language")
    if (
        not isinstance(source_language, str)
        or validation.get("source_language") != source_language
        or locked_review.get("source_language") != source_language
    ):
        raise ReviewError("review source language differs from the downloaded subtitle")

    source_record = subtitle.get("source_srt")
    source_value = source_record.get("path") if isinstance(source_record, dict) else None
    if not isinstance(source_value, str):
        raise ReviewError("download manifest has no immutable platform source SRT")
    platform_path = Path(source_value).expanduser()
    if not platform_path.is_absolute():
        platform_path = output_dir / platform_path
    try:
        platform_raw = platform_path.read_bytes()
    except FileNotFoundError as exc:
        raise ReviewError(f"platform source SRT not found: {platform_path}") from exc
    platform_hash = _sha256_bytes(platform_raw)
    if (
        source_record.get("sha256") != platform_hash
        or validation.get("platform_source_sha256") != platform_hash
        or locked_review["platform_source"].get("sha256") != platform_hash
    ):
        raise ReviewError("platform source SRT provenance does not match the review")

    reviewed_value = validation.get("reviewed_source")
    if not isinstance(reviewed_value, str):
        raise ReviewError("review validation has no reviewed source SRT")
    reviewed_path = Path(reviewed_value).expanduser().resolve()
    try:
        reviewed_raw = reviewed_path.read_bytes()
    except FileNotFoundError as exc:
        raise ReviewError(f"reviewed source SRT not found: {reviewed_path}") from exc
    reviewed_hash = _sha256_bytes(reviewed_raw)
    if validation.get("reviewed_source_sha256") != reviewed_hash:
        raise ReviewError("reviewed source SRT SHA-256 does not match validation")
    decisions, decision_files = _load_decisions(
        locked_review, Path(locked_review["review_output_dir"])
    )
    if (
        validation.get("decision_files") != decision_files
        or validation.get("decision_count") != len(decisions)
        or validation.get("review_count") != len(locked_review["review_items"])
        or validation.get("asr_hypothesis_sha256")
        != locked_review["asr_hypothesis"]["sha256"]
        or reviewed_raw != _reviewed_srt(locked_review, decisions)
    ):
        raise ReviewError("reviewed source differs from the locked review decisions")

    subtitle_pipeline = _load_subtitle_pipeline()
    try:
        platform_cues = subtitle_pipeline.parse_srt_bytes(platform_raw)
        reviewed_cues = subtitle_pipeline.parse_srt_bytes(reviewed_raw)
    except subtitle_pipeline.PipelineError as exc:
        raise ReviewError(f"could not validate reviewed SRT timeline: {exc}") from exc
    if len(platform_cues) != len(reviewed_cues) or len(reviewed_cues) != validation.get(
        "cue_count"
    ):
        raise ReviewError("reviewed source changed the platform cue count")
    for platform_cue, reviewed_cue in zip(platform_cues, reviewed_cues):
        if (
            platform_cue["timing_line"] != reviewed_cue["timing_line"]
            or platform_cue["start_ms"] != reviewed_cue["start_ms"]
            or platform_cue["end_ms"] != reviewed_cue["end_ms"]
        ):
            raise ReviewError("reviewed source changed the platform timeline")

    reviewed_record = {
        "path": str(reviewed_path),
        "sha256": reviewed_hash,
        "size_bytes": len(reviewed_raw),
        "content_role": "reviewed-derived-source",
        "derived_from": {"path": source_value, "sha256": platform_hash},
        "review_validation": {
            "path": str(validation_path),
            "sha256": _sha256_bytes(validation_path.read_bytes()),
        },
    }
    existing = subtitle.get("reviewed_source_srt")
    if existing is not None and existing != reviewed_record:
        raise ReviewError("download manifest already has a different reviewed source SRT")
    subtitle["reviewed_source_srt"] = reviewed_record
    execution["asr_review_validation"] = str(validation_path)
    _atomic_write(download_manifest, _json_bytes(manifest))

    fetch_video = _load_fetch_video()
    try:
        return int(fetch_video._advance_bilingual_stage(download_manifest))
    except fetch_video.FetchError as exc:
        raise ReviewError(f"could not resume bilingual workflow: {exc}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare immutable platform subtitles with a secondary ASR hypothesis."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser(
        "prepare", help="archive inputs and create compact disagreement review batches"
    )
    command.add_argument("platform_srt", type=Path)
    command.add_argument("whisper_json", type=Path)
    command.add_argument("--work-dir", type=Path, required=True)
    command.add_argument("--source-language", required=True)
    command.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
    )
    command.add_argument(
        "--material-similarity-threshold",
        type=float,
        default=DEFAULT_MATERIAL_SIMILARITY_THRESHOLD,
    )
    next_command = commands.add_parser(
        "next-batch", help="print only the next pending compact review batch"
    )
    next_command.add_argument("--manifest", type=Path, required=True)
    render_command = commands.add_parser(
        "render", help="render a reviewed source SRT from complete decisions"
    )
    render_command.add_argument("--manifest", type=Path, required=True)
    render_command.add_argument("--decisions-dir", type=Path, required=True)
    render_command.add_argument("--output-dir", type=Path, required=True)
    apply_command = commands.add_parser(
        "apply", help="attach a validated reviewed SRT and resume translation"
    )
    apply_command.add_argument("--download-manifest", type=Path, required=True)
    apply_command.add_argument("--validation", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare":
            manifest = prepare(
                args.platform_srt,
                args.whisper_json,
                args.work_dir,
                args.source_language,
                args.similarity_threshold,
                args.material_similarity_threshold,
            )
            payload = {"ok": True, "manifest": str(manifest)}
        elif args.command == "next-batch":
            payload = {"ok": True, **next_review_batch(args.manifest)}
        elif args.command == "render":
            reviewed_source, validation = render(
                args.manifest,
                args.decisions_dir,
                args.output_dir,
            )
            payload = {
                "ok": True,
                "reviewed_source": str(reviewed_source),
                "validation": str(validation),
            }
        else:
            return apply_review(args.download_manifest, args.validation)
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except (ReviewError, OSError, UnicodeError) as exc:
        print(f"ASR review error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
