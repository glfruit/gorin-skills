# Upstream provenance

`gorin-jzsub` is a first-party adaptation of JZSub. It is not a floating
mirror or Git submodule.

- Upstream repository: <https://github.com/pengchujin/jzsub>
- Imported path: `skills/content/gorin-jzsub`
- Pinned revision: `b122dd18809082b44c9b7bf7380a3e3e04870c7a`
- Nearest release context at import: `v1.8.1` (the pinned revision is newer)
- Imported on: 2026-07-15
- License: MIT; see `LICENSE.upstream`

## Initial adaptation

- Renamed the canonical skill from `jzsub` to `gorin-jzsub`; `jzsub` remains
  a compatibility alias in `manifest.yaml`.
- Omitted upstream `agents/openai.yaml`. Target-specific packages are generated
  from this repository's manifest and adapters instead.
- Kept upstream `scripts/`, `tests/`, and `references/` byte-for-byte unchanged
  at initial import.

## Local changes after import

- Removed both the advisory warning and the `--allow-remote-ejs` hard failure
  based on a parent-shell `PATH` check for Deno. Wrapper-managed yt-dlp
  installations can provide a supported runtime privately, so runtime failure
  warnings now come from the yt-dlp process that actually performs the work.
- Added public CLI regression coverage for both a wrapper-provided runtime and
  a genuine yt-dlp missing-runtime warning.
- Added an opt-in automatic-caption review stage. A separate MLX Whisper adapter
  emits word-timestamped JSON; a source-locked review pipeline exposes only
  material disagreements, records human/agent adjudication, renders a derived
  SRT without replacing the platform source, and resumes the existing
  translation workflow only after provenance and timeline validation.
- Added public CLI tests for review-state routing, ASR normalization,
  disagreement batching, immutable-source rendering, and validated manifest
  attachment. Model installation and remote weight downloads remain explicit
  approval-gated host actions.
- Calibrated real rolling-caption alignment against MLX word timestamps: cue
  comparison now chooses the nearest-length, highest-similarity contiguous word
  span inside a bounded timing margin, and normalizes intra-word hyphenation.
  This removes adjacent-cue false positives without lowering the threshold that
  catches whole-word name disagreements.
- Normalized two real MLX alignment artifacts without fabricating timestamps:
  zero-duration words are omitted when usable spans remain, and empty
  zero-duration placeholder segments are ignored. Other malformed timelines
  still fail closed, with public CLI regressions covering both cases.
- Added transparent long-media MLX chunking behind the existing transcribe
  interface. Ten-minute responsibility windows use five seconds of context on
  both sides, assign overlap words by center time, restore original-media
  timestamps, and record inference provenance without duplicating boundary
  words.
- Split disagreement selection into a low-similarity `material` channel and a
  conservative `proper_name` replacement channel. On the five-minute rolling
  caption calibration sample this reduced review candidates from 58/132 to
  19/132 while retaining observed Armin, Mario, Pi, and Grok disagreements.

## Sync policy

Review upstream changes against the pinned revision, copy only understood
changes, rerun both the embedded Python tests and repository qualification,
then update the revision and this note. Local behavior changes belong here and
must not be represented as an exact upstream mirror.
