#!/usr/bin/env python3
"""Explicit, provenance-recording adapter for optional MLX Whisper inference."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Sequence


DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
SCHEMA_VERSION = 1
CHUNK_SECONDS = 600.0
CHUNK_OVERLAP_SECONDS = 5.0
DURATION_PROBE_MIN_BYTES = 1024 * 1024


class AdapterError(RuntimeError):
    """A user-facing MLX Whisper adapter failure."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _finite_number(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise AdapterError(f"MLX Whisper returned an invalid {label}") from exc
    if not math.isfinite(number):
        raise AdapterError(f"MLX Whisper returned an invalid {label}")
    return round(number, 6)


def _normalize_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise AdapterError("MLX Whisper result root must be an object")
    text = result.get("text")
    language = result.get("language")
    raw_segments = result.get("segments")
    if not isinstance(text, str) or not isinstance(language, str):
        raise AdapterError("MLX Whisper result is missing text or language")
    if not isinstance(raw_segments, list) or not raw_segments:
        raise AdapterError("MLX Whisper result contains no segments")
    segments: list[dict[str, Any]] = []
    previous_start = -1.0
    for position, raw_segment in enumerate(raw_segments, start=1):
        if not isinstance(raw_segment, dict):
            raise AdapterError(f"MLX Whisper segment {position} must be an object")
        start = _finite_number(raw_segment.get("start"), f"segment {position} start")
        end = _finite_number(raw_segment.get("end"), f"segment {position} end")
        segment_text = raw_segment.get("text")
        raw_words = raw_segment.get("words")
        if (
            start == end
            and isinstance(segment_text, str)
            and not segment_text.strip()
            and isinstance(raw_words, list)
            and not raw_words
        ):
            # MLX can append empty point segments at or beyond the media end.
            # They carry no transcript evidence and cannot form a valid span.
            continue
        if start < 0 or end <= start or start < previous_start:
            raise AdapterError(f"MLX Whisper segment {position} timestamps are invalid")
        if not isinstance(segment_text, str) or not segment_text.strip():
            raise AdapterError(f"MLX Whisper segment {position} text is empty")
        previous_start = start
        segment: dict[str, Any] = {
            "start": start,
            "end": end,
            "text": segment_text.strip(),
        }
        if not isinstance(raw_words, list) or not raw_words:
            raise AdapterError(
                f"MLX Whisper segment {position} has no word timestamps; "
                "word_timestamps=True is required"
            )
        words: list[dict[str, Any]] = []
        previous_word_start = -1.0
        for word_position, raw_word in enumerate(raw_words, start=1):
            if not isinstance(raw_word, dict):
                raise AdapterError(
                    f"MLX Whisper segment {position} word {word_position} must be an object"
                )
            word_start = _finite_number(
                raw_word.get("start"), f"segment {position} word {word_position} start"
            )
            word_end = _finite_number(
                raw_word.get("end"), f"segment {position} word {word_position} end"
            )
            word_text = raw_word.get("word")
            if word_start == word_end:
                if (
                    word_start < 0
                    or word_start < previous_word_start
                    or not isinstance(word_text, str)
                    or not word_text.strip()
                ):
                    raise AdapterError(
                        f"MLX Whisper segment {position} word {word_position} is invalid"
                    )
                # MLX can emit words clamped to a single alignment point. Keep
                # the segment text, but omit spans whose duration would be fake.
                continue
            if (
                word_start < 0
                or word_end <= word_start
                or word_start < previous_word_start
                or not isinstance(word_text, str)
                or not word_text.strip()
            ):
                raise AdapterError(
                    f"MLX Whisper segment {position} word {word_position} is invalid"
                )
            previous_word_start = word_start
            word = {"start": word_start, "end": word_end, "word": word_text}
            probability = raw_word.get("probability")
            if probability is not None:
                word["probability"] = _finite_number(
                    probability,
                    f"segment {position} word {word_position} probability",
                )
            words.append(word)
        if not words:
            raise AdapterError(
                f"MLX Whisper segment {position} has no usable word timestamps"
            )
        segment["words"] = words
        segments.append(segment)
    if not segments:
        raise AdapterError("MLX Whisper result contains no usable segments")
    return {"text": text.strip(), "language": language, "segments": segments}


def _classify_model(model: str) -> tuple[str, str]:
    if not model.strip():
        raise AdapterError("model reference cannot be empty")
    candidate = Path(model).expanduser()
    if candidate.exists():
        if not candidate.is_dir():
            raise AdapterError(f"local model path is not a directory: {candidate}")
        return str(candidate.resolve()), "local"
    if candidate.is_absolute() or model.startswith(("./", "../", "~")):
        raise AdapterError(f"local model directory not found: {candidate}")
    return model, "huggingface"


def _resolve_model(model: str, allow_model_download: bool) -> tuple[str, str]:
    value, source = _classify_model(model)
    if source == "local":
        return value, source
    if not allow_model_download:
        raise AdapterError(
            "remote model identifiers may download weights; pass "
            "--allow-model-download only after that host change is approved, or use "
            "a pinned local model directory"
        )
    return value, source


def _probe_media_duration(media: Path) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(media),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:
        raise AdapterError("ffprobe is required to inspect long media") from exc
    if result.returncode != 0:
        raise AdapterError("ffprobe could not determine the media duration")
    duration = _finite_number(result.stdout.strip(), "media duration")
    if duration <= 0:
        raise AdapterError("ffprobe returned a non-positive media duration")
    return duration


def _chunk_windows(duration: float) -> list[dict[str, float]]:
    windows: list[dict[str, float]] = []
    core_start = 0.0
    while core_start < duration:
        core_end = min(duration, core_start + CHUNK_SECONDS)
        extract_start = max(0.0, core_start - CHUNK_OVERLAP_SECONDS)
        extract_end = min(duration, core_end + CHUNK_OVERLAP_SECONDS)
        windows.append(
            {
                "core_start": core_start,
                "core_end": core_end,
                "extract_start": extract_start,
                "extract_duration": extract_end - extract_start,
            }
        )
        core_start = core_end
    return windows


def _extract_audio_chunk(
    media: Path, output: Path, start: float, duration: float
) -> None:
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-ss",
                str(start),
                "-t",
                str(duration),
                "-i",
                str(media),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(output),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:
        raise AdapterError("ffmpeg is required to extract ASR chunks") from exc
    if result.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise AdapterError("ffmpeg could not extract an ASR audio chunk")


def _run_mlx_transcription(
    mlx_whisper: Any,
    media: Path,
    model_value: str,
    language: str | None,
) -> dict[str, Any]:
    try:
        result = mlx_whisper.transcribe(
            str(media),
            path_or_hf_repo=model_value,
            word_timestamps=True,
            language=language,
            task="transcribe",
            verbose=None,
        )
    except Exception as exc:
        raise AdapterError(f"MLX Whisper transcription failed: {exc}") from exc
    return _normalize_result(result)


def _crop_and_shift_chunk(
    normalized: dict[str, Any],
    extract_start: float,
    core_start: float,
    core_end: float,
    final_chunk: bool,
) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for segment in normalized["segments"]:
        words: list[dict[str, Any]] = []
        for raw_word in segment["words"]:
            start = round(raw_word["start"] + extract_start, 6)
            end = round(raw_word["end"] + extract_start, 6)
            center = (start + end) / 2
            if center < core_start or (
                center >= core_end and not (final_chunk and center <= core_end)
            ):
                continue
            word = {"start": start, "end": end, "word": raw_word["word"]}
            if "probability" in raw_word:
                word["probability"] = raw_word["probability"]
            words.append(word)
        if not words:
            continue
        text = "".join(word["word"] for word in words).strip()
        segments.append(
            {
                "start": words[0]["start"],
                "end": words[-1]["end"],
                "text": text,
                "words": words,
            }
        )
    return segments


def _transcribe_media(
    mlx_whisper: Any,
    media: Path,
    model_value: str,
    language: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if media.stat().st_size <= DURATION_PROBE_MIN_BYTES:
        normalized = _run_mlx_transcription(
            mlx_whisper, media, model_value, language
        )
        return normalized, {"mode": "single", "chunk_count": 1}
    duration = _probe_media_duration(media)
    if duration <= CHUNK_SECONDS:
        normalized = _run_mlx_transcription(
            mlx_whisper, media, model_value, language
        )
        return normalized, {"mode": "single", "chunk_count": 1}

    windows = _chunk_windows(duration)
    segments: list[dict[str, Any]] = []
    detected_language: str | None = None
    with tempfile.TemporaryDirectory(prefix="gorin-jzsub-mlx-") as directory:
        chunk_path = Path(directory) / "chunk.wav"
        for index, window in enumerate(windows):
            print(
                f"MLX Whisper chunk {index + 1}/{len(windows)}",
                file=sys.stderr,
                flush=True,
            )
            _extract_audio_chunk(
                media,
                chunk_path,
                window["extract_start"],
                window["extract_duration"],
            )
            try:
                normalized = _run_mlx_transcription(
                    mlx_whisper, chunk_path, model_value, language
                )
            finally:
                try:
                    chunk_path.unlink()
                except FileNotFoundError:
                    pass
            if detected_language is None:
                detected_language = normalized["language"]
            elif normalized["language"] != detected_language:
                raise AdapterError("MLX Whisper chunk languages are inconsistent")
            shifted = _crop_and_shift_chunk(
                normalized,
                window["extract_start"],
                window["core_start"],
                window["core_end"],
                index == len(windows) - 1,
            )
            if shifted and segments and shifted[0]["start"] < segments[-1]["start"]:
                raise AdapterError("MLX Whisper chunk merge is out of order")
            segments.extend(shifted)
    if not segments or detected_language is None:
        raise AdapterError("MLX Whisper chunks contain no usable speech segments")
    normalized = {
        "text": " ".join(segment["text"] for segment in segments).strip(),
        "language": detected_language,
        "segments": segments,
    }
    inference = {
        "mode": "chunked",
        "chunk_count": len(windows),
        "chunk_seconds": CHUNK_SECONDS,
        "overlap_seconds": CHUNK_OVERLAP_SECONDS,
    }
    return normalized, inference


def transcribe(
    media: Path,
    output: Path,
    model: str,
    language: str | None,
    allow_model_download: bool,
) -> Path:
    media = media.expanduser().resolve()
    output = output.expanduser().resolve()
    if not media.is_file():
        raise AdapterError(f"media file not found: {media}")
    if output.exists():
        raise AdapterError(f"refusing to overwrite existing transcript: {output}")
    model_value, model_source = _resolve_model(model, allow_model_download)
    try:
        mlx_whisper = importlib.import_module("mlx_whisper")
    except ModuleNotFoundError as exc:
        raise AdapterError(
            "mlx-whisper is not installed in this Python environment; installation "
            "is a separately approved host change"
        ) from exc
    normalized, inference = _transcribe_media(
        mlx_whisper, media, model_value, language
    )
    transcript = {
        "schema_version": SCHEMA_VERSION,
        "backend": "mlx-whisper",
        "model": model_value,
        "model_source": model_source,
        "word_timestamps": True,
        "inference": inference,
        "media": {
            "path": str(media),
            "sha256": _sha256(media),
            "size_bytes": media.stat().st_size,
        },
        **normalized,
    }
    _atomic_write(output, _json_bytes(transcript))
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run explicitly authorized MLX Whisper inference and normalize its output."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("transcribe", help="transcribe one local media file")
    command.add_argument("media", type=Path)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--model", default=DEFAULT_MODEL)
    command.add_argument("--language")
    command.add_argument("--allow-model-download", action="store_true")
    command.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        media = args.media.expanduser().resolve()
        output = args.output.expanduser().resolve()
        if args.dry_run:
            if not media.is_file():
                raise AdapterError(f"media file not found: {media}")
            model, model_source = _classify_model(args.model)
            would_download_model = model_source == "huggingface"
            payload = {
                "ok": True,
                "status": "dry-run",
                "media": str(media),
                "output": str(output),
                "model": model,
                "model_source": model_source,
                "would_download_model": would_download_model,
                "requires_model_download_approval": (
                    would_download_model and not args.allow_model_download
                ),
                "word_timestamps": True,
                "files_written": False,
                "inference_run": False,
            }
        else:
            result = transcribe(
                media,
                output,
                args.model,
                args.language,
                args.allow_model_download,
            )
            payload = {"ok": True, "output": str(result)}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except (AdapterError, OSError, UnicodeError) as exc:
        print(f"MLX Whisper adapter error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
