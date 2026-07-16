# Automatic-caption ASR review contract

Use this optional stage only when the platform-selected source track is
`automatic` and the user asked for a higher-confidence source review. It is a
second-opinion workflow, not an automatic correction system.

## Domain terms and authority

- **Platform source subtitle**: the immutable SRT selected and downloaded by
  JZSub. Its bytes, cue order, and timeline remain the provenance root.
- **ASR hypothesis**: timestamped JSON emitted by MLX Whisper. It is untrusted
  evidence and never overwrites a cue by itself.
- **Review item**: a platform cue whose normalized text materially disagrees
  with the time-aligned ASR hypothesis.
- **Review decision**: the active session agent's adjudicated source string for
  exactly one review item, based on the two hypotheses and read-only context.
- **Reviewed source subtitle**: a derived SRT containing reviewed decisions and
  unchanged non-review cues. It must preserve every platform cue boundary.

The ASR model is not a source of truth. A disagreement means “inspect this
cue,” not “Whisper wins.” Similarity thresholds trade missed errors against
false positives and do not measure transcript quality.

## State flow

Run the fetch with `--review-auto-subs`. If a manual track is selected, JZSub
skips this stage. If no suitable track exists, JZSub still completes as video
only and does not invent subtitles.

For an automatic track, the fetch exits 3 with
`status: asr_transcription_required`. Use the returned `asr_media`,
`platform_source_srt`, and exact `source_language` values.

1. Produce a word-timestamped hypothesis:

   ```bash
   <mlx-python> <skill-dir>/scripts/mlx_whisper_adapter.py transcribe \
     "<asr_media>" --output "<job-dir>/asr/whisper.json" \
     --model "<pinned-local-model-dir>" --language "<source_language>"
   ```

   `<mlx-python>` is the exact interpreter from the approved isolated
   `mlx-whisper` installation; do not assume the default `python3` can import
   it. `mlx-whisper` installation is a separate host change. A remote Hugging Face
   model ID also requires `--allow-model-download`; prefer a pinned local model
   directory for reproducibility. `--dry-run` reports the intended model source
   without importing MLX, running inference, downloading, or writing files.
   The adapter omits MLX alignment points whose word duration is exactly zero
   and empty zero-duration placeholder segments, because neither can provide a
   real review span. It still fails closed when a segment has no usable word
   timestamps or when malformed content carries a non-empty span. Media longer
   than ten minutes is decoded into ten-minute responsibility windows with five
   seconds of context on each side. Word centers assign each overlap to exactly
   one window; the adapter shifts retained timestamps back to the original
   media timeline and records the chunking mode in its output. Chunked runs emit
   one content-free `MLX Whisper chunk N/total` progress line per window.

2. Lock both hypotheses and create compact disagreement batches:

   ```bash
   python3 <skill-dir>/scripts/asr_review.py prepare \
     "<platform_source_srt>" "<job-dir>/asr/whisper.json" \
     --work-dir "<job-dir>/asr/review" \
     --source-language "<source_language>"
   ```

   The default review policy has two channels. `material` selects similarity
   below `0.75`; `proper_name` selects conservative Title Case or acronym
   replacements below the outer `0.92` threshold. Use
   `--material-similarity-threshold` and `--similarity-threshold` only when a
   reviewed calibration sample justifies different values. Every review item
   records its `review_channel`.

3. Request only one pending batch:

   ```bash
   python3 <skill-dir>/scripts/asr_review.py next-batch \
     --manifest "<job-dir>/asr/review/review-manifest.json"
   ```

   For `done:false`, adjudicate each `batch.items` record and write exactly:

   ```json
   {"decisions":[{"id":"unchanged-id","reviewed":"reviewed source text"}]}
   ```

   Use `platform`, `whisper_hypothesis`, and `context` as evidence. Preserve IDs
   and do not add, remove, reorder, merge, or split cues. Repeat until
   `done:true`. Never load the full review manifest or all batches into model
   context.

4. Render and validate the derived SRT:

   ```bash
   python3 <skill-dir>/scripts/asr_review.py render \
     --manifest "<job-dir>/asr/review/review-manifest.json" \
     --decisions-dir "<job-dir>/asr/review/review-output" \
     --output-dir "<job-dir>/asr/rendered"
   ```

5. Attach the validation to the original download manifest and resume the
   normal translation stage:

   ```bash
   python3 <skill-dir>/scripts/asr_review.py apply \
     --download-manifest "<job-dir>/download-manifest.json" \
     --validation "<job-dir>/asr/rendered/review-validation.json"
   ```

`apply` verifies source hashes, language, cue count, and every timeline boundary.
It retains `artifacts.subtitle.source_srt` and adds
`artifacts.subtitle.reviewed_source_srt` with derivation metadata. Its expected
exit 3 is the existing `bilingual_required` translation stage.

## Scope boundary

This contract reviews a platform automatic track. Generating captions for a
video with no platform subtitle is a different domain operation and is not
enabled by `--review-auto-subs`.
