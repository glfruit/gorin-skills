from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


SKILL_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_SCRIPT = SKILL_ROOT / "scripts" / "subtitle_pipeline.py"
EXECUTOR_SCRIPT = SKILL_ROOT / "scripts" / "translation_executor.py"
SPEC = importlib.util.spec_from_file_location("subtitle_pipeline", PIPELINE_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
pipeline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pipeline)


FAKE_CODEX = r"""#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
import time

arguments = sys.argv[1:]
output_path = Path(arguments[arguments.index("--output-last-message") + 1])
codex_home = Path(os.environ["CODEX_HOME"])
mode = (codex_home / "mode").read_text(encoding="utf-8").strip()
prompt = sys.stdin.read()
batch = json.loads(prompt.split("<translation-batch>\n", 1)[1].split("\n</translation-batch>", 1)[0])
probe = {
    "arguments": arguments,
    "codex_home": os.environ.get("CODEX_HOME"),
    "home": os.environ.get("HOME"),
    "cwd": os.getcwd(),
    "has_real_codex_marker": os.environ.get("REAL_CODEX_MARKER") is not None,
}
(codex_home / "probe.json").write_text(json.dumps(probe), encoding="utf-8")
counter_path = codex_home / "counter"
counter = int(counter_path.read_text()) + 1 if counter_path.exists() else 1
counter_path.write_text(str(counter))

if mode == "timeout":
    time.sleep(5)
if mode == "unavailable" or (mode == "unavailable_once" and counter == 1) or (mode == "partial" and counter == 2):
    print("provider temporarily unavailable", file=sys.stderr)
    raise SystemExit(7)
if mode == "authentication":
    print("not logged in; authentication required", file=sys.stderr)
    raise SystemExit(1)
if mode == "quota":
    print("usage limit reached; quota exceeded", file=sys.stderr)
    raise SystemExit(1)

translations = []
for item in batch["items"]:
    source = item["source"]
    translation = (
        "请于 00:30 访问 https://example.com #Archive"
        if source.startswith("Visit ")
        else "这是第 " + source.rsplit(" ", 1)[-1] + " 行"
    )
    translations.append({"id": item["id"], "translation": translation})
if mode == "copy":
    translations = [
        {"id": item["id"], "translation": item["source"]}
        for item in batch["items"]
    ]
if mode == "invalid_structure":
    translations = translations[:-1]
if mode == "protected_token":
    translations[0]["translation"] = "受损译文"
if mode == "extended_token":
    translations[0]["translation"] = translations[0]["translation"].replace(
        "https://example.com", "https://example.com.evil"
    )
output_path.write_text(json.dumps({"translations": translations}, ensure_ascii=False), encoding="utf-8")
"""


def make_srt(count: int) -> bytes:
    blocks = []
    for index in range(count):
        source = (
            "Visit https://example.com at 00:30 #Archive"
            if index == 0
            else f"Line {index}"
        )
        blocks.append(
            f"{index + 1}\n00:{index // 60:02d}:{index % 60:02d},000 --> "
            f"00:{index // 60:02d}:{index % 60:02d},900\n{source}"
        )
    return ("\n\n".join(blocks) + "\n").encode()


def make_srt_from_sources(sources: list[str]) -> bytes:
    blocks = [
        f"{index}\n00:00:{index - 1:02d},000 --> 00:00:{index - 1:02d},900\n{source}"
        for index, source in enumerate(sources, start=1)
    ]
    return ("\n\n".join(blocks) + "\n").encode()


class TranslationExecutorCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.srt"
        self.fake_codex = self.root / "fake-codex"
        self.fake_codex.write_text(FAKE_CODEX, encoding="utf-8")
        self.fake_codex.chmod(self.fake_codex.stat().st_mode | stat.S_IXUSR)
        self.api_requests: list[dict] = []
        self.api_mode = "normal"
        self.test_credential = secrets.token_urlsafe(24)
        outer = self

        class ApiHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length))
                outer.api_requests.append(
                    {
                        "path": self.path,
                        "authorization_valid": self.headers.get("Authorization")
                        == f"Bearer {outer.test_credential}",
                        "body": request,
                    }
                )
                if outer.api_mode == "authentication":
                    self.send_response(401)
                    self.end_headers()
                    return
                prompt = request["messages"][-1]["content"]
                batch = json.loads(
                    prompt.split("<translation-batch>\n", 1)[1].split(
                        "\n</translation-batch>", 1
                    )[0]
                )
                translations = []
                for item in batch["items"]:
                    source = item["source"]
                    translation = (
                        "请于 00:30 访问 https://example.com #Archive"
                        if source.startswith("Visit ")
                        else "这是第 " + source.rsplit(" ", 1)[-1] + " 行"
                    )
                    if outer.api_mode == "copy" or (
                        outer.api_mode == "repair_once" and len(outer.api_requests) == 1
                    ):
                        translation = source
                    elif outer.api_mode == "refusal":
                        translation = "抱歉 我无法翻译 " + source
                    elif outer.api_mode == "abnormal_length":
                        translation = "译" * 200 + " " + source
                    elif outer.api_mode == "target_language":
                        translation = "English translation " + source
                    elif outer.api_mode == "empty":
                        translation = ""
                    elif outer.api_mode == "repeated":
                        translation = "重复译文"
                    elif outer.api_mode == "protected_token":
                        translation = "受损译文"
                    translations.append(
                        {"id": item["id"], "translation": translation}
                    )
                content = json.dumps(
                    {"translations": translations}, ensure_ascii=False
                )
                response = json.dumps(
                    {"choices": [{"message": {"content": content}}]}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def log_message(self, format: str, *args: object) -> None:
                pass

        self.api_server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
        self.api_thread = threading.Thread(
            target=self.api_server.serve_forever, daemon=True
        )
        self.api_thread.start()
        self.addCleanup(self.api_server.server_close)
        self.addCleanup(self.api_server.shutdown)

    def prepare_request(
        self,
        mode: str,
        *,
        cue_count: int = 2,
        timeout_seconds: float = 2,
        cancelled: bool = False,
        max_batch_attempts: int = 1,
    ) -> tuple[Path, Path, Path]:
        self.source.write_bytes(make_srt(cue_count))
        manifest_path = pipeline.prepare(self.source, self.root / "subtitles", "en")
        codex_home = self.root / f"isolated-codex-home-{mode}"
        codex_home.mkdir(exist_ok=True)
        (codex_home / "mode").write_text(mode, encoding="utf-8")
        cancellation_path = self.root / "cancel.requested"
        if cancelled:
            cancellation_path.touch()
        request = {
            "schema_version": "1.0.0",
            "attempt_id": f"attempt-fixture-{mode}",
            "subtitle_manifest": str(manifest_path),
            "provider": {
                "adapter": "codex",
                "model": "fixture-model",
            },
            "limits": {
                "batch_timeout_seconds": timeout_seconds,
                "max_batch_attempts": max_batch_attempts,
            },
            "cancellation_path": str(cancellation_path),
            "progress_path": str(self.root / f"progress-{mode}.jsonl"),
        }
        request_path = self.root / f"request-{mode}.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        return request_path, manifest_path, codex_home

    def enable_test_api_credential(self) -> None:
        os.environ["WP005B_TEST_API_KEY"] = self.test_credential
        self.addCleanup(os.environ.pop, "WP005B_TEST_API_KEY", None)

    def run_executor(
        self,
        request_path: Path,
        *,
        codex_home: Path | None = None,
        api_config: Path | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        environment = os.environ.copy()
        environment["REAL_CODEX_MARKER"] = "must-not-reach-provider"
        command = [
                sys.executable,
                str(EXECUTOR_SCRIPT),
                "run",
                "--request",
                str(request_path),
                "--codex-home",
                str(
                    codex_home
                    or self.root
                    / f"isolated-codex-home-{request_path.stem.removeprefix('request-')}"
                ),
                "--codex-executable",
                str(self.fake_codex),
            ]
        if api_config is not None:
            command.extend(["--api-config", str(api_config)])
        result = subprocess.run(
            command,
            cwd=SKILL_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(result.stdout)
        return result, payload

    def prepare_api_request(
        self,
        service: str = "deepseek",
        *,
        suffix: str = "api",
        sources: list[str] | None = None,
        target_language: str = "zh-CN",
    ) -> tuple[Path, Path, Path]:
        api_root = self.root / suffix
        api_root.mkdir()
        source = api_root / "source.srt"
        source.write_bytes(
            make_srt_from_sources(sources) if sources is not None else make_srt(2)
        )
        manifest_path = pipeline.prepare(
            source,
            api_root / "subtitles",
            "en",
            target_language=target_language,
        )
        request = {
            "schema_version": "1.0.0",
            "attempt_id": f"attempt-fixture-{suffix}",
            "subtitle_manifest": str(manifest_path),
            "provider": {
                "adapter": "openai-compatible",
                "service": service,
                "model": "fixture-model",
            },
            "limits": {
                "batch_timeout_seconds": 2,
                "max_batch_attempts": 1,
            },
            "cancellation_path": str(api_root / "cancel.requested"),
            "progress_path": str(api_root / "progress.jsonl"),
            "paid_attempt": {
                "media_job_id": f"fixture-media-job-{suffix}",
                "ordinal": 1,
                "reservation": {
                    "id": "fixture-reservation-1",
                    "max_input_tokens": 10000,
                    "max_output_tokens": 10000,
                },
                "additional_attempt_approval": None,
            },
            "quality": {
                "rules_version": "deterministic-v1",
                "max_repairs": 1,
                "high_assurance_review": False,
            },
            "circuit_breaker": {"state": "closed"},
        }
        request_path = api_root / "request.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        api_config = api_root / f"api-config-{service}.json"
        api_config.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "service": service,
                    "base_url": (
                        f"http://127.0.0.1:{self.api_server.server_port}/v1"
                    ),
                    "credential_env": "WP005B_TEST_API_KEY",
                }
            ),
            encoding="utf-8",
        )
        return request_path, manifest_path, api_config

    def test_openai_compatible_deepseek_attempt_promotes_machine_validated_output(
        self,
    ) -> None:
        request_path, manifest_path, api_config = self.prepare_api_request()
        self.enable_test_api_credential()

        result, payload = self.run_executor(request_path, api_config=api_config)

        self.assertEqual(result.returncode, 0, (result.stderr, payload))
        self.assertEqual(payload["status"], "succeeded")
        self.assertEqual(payload["quality_status"], "machine_validated")
        self.assertEqual(payload["provider"]["service"], "deepseek")
        self.assertEqual(len(self.api_requests), 1)
        self.assertTrue(self.api_requests[0]["authorization_valid"])
        diagnostic = self.execution_manifest(request_path, manifest_path)
        self.assertEqual(
            diagnostic["formal_translation_provider"], payload["provider"]
        )
        self.assertFalse(
            diagnostic["high_assurance_review"]["translation_contribution"]
        )
        self.assertNotIn(self.test_credential, json.dumps(diagnostic))

    def test_deepseek_and_openai_are_mutually_exclusive_adapter_configs(self) -> None:
        self.enable_test_api_credential()
        for service in ("deepseek", "openai"):
            with self.subTest(service=service):
                request_path, _, api_config = self.prepare_api_request(
                    service, suffix=f"api-{service}"
                )
                result, payload = self.run_executor(
                    request_path, api_config=api_config
                )
                self.assertEqual(result.returncode, 0, payload)
                self.assertEqual(payload["provider"]["service"], service)

        request_path, _, api_config = self.prepare_api_request(
            "deepseek", suffix="api-mismatch"
        )
        config = json.loads(api_config.read_text())
        config["service"] = "openai"
        api_config.write_text(json.dumps(config))
        count = len(self.api_requests)
        result, payload = self.run_executor(request_path, api_config=api_config)
        self.assertEqual(result.returncode, 29)
        self.assertEqual(payload["failure_class"], "configuration")
        self.assertEqual(len(self.api_requests), count)

    def test_paid_attempt_budget_approval_and_circuit_breaker_fail_before_http(
        self,
    ) -> None:
        cases = ("budget", "approval", "circuit")
        for case in cases:
            with self.subTest(case=case):
                request_path, _, api_config = self.prepare_api_request(
                    suffix=f"api-{case}"
                )
                request = json.loads(request_path.read_text())
                if case == "budget":
                    request["paid_attempt"]["reservation"]["max_input_tokens"] = 1
                elif case == "approval":
                    request["paid_attempt"]["ordinal"] = 2
                else:
                    request["circuit_breaker"] = {"state": "open"}
                request_path.write_text(json.dumps(request))

                result, payload = self.run_executor(
                    request_path, api_config=api_config
                )

                self.assertIn(result.returncode, {28, 29})
                self.assertIn(
                    payload["failure_class"], {"budget_exhausted", "configuration"}
                )
                self.assertEqual(self.api_requests, [])

    def test_authentication_failure_opens_capability_circuit_breaker(self) -> None:
        request_path, _, api_config = self.prepare_api_request()
        self.api_mode = "authentication"
        self.enable_test_api_credential()

        result, payload = self.run_executor(request_path, api_config=api_config)

        self.assertEqual(result.returncode, 20)
        self.assertEqual(payload["failure_class"], "authentication")
        self.assertTrue(payload["circuit_breaker_opened"])
        self.assertEqual(len(self.api_requests), 1)

    def test_quality_gate_repairs_once_with_same_provider(self) -> None:
        request_path, _, api_config = self.prepare_api_request()
        self.api_mode = "repair_once"
        self.enable_test_api_credential()

        result, payload = self.run_executor(request_path, api_config=api_config)

        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(len(self.api_requests), 2)
        self.assertEqual(
            {request["body"]["model"] for request in self.api_requests},
            {"fixture-model"},
        )

    def test_quality_gate_rejects_obvious_bad_translations_after_one_repair(
        self,
    ) -> None:
        self.enable_test_api_credential()
        for mode in ("copy", "refusal", "abnormal_length", "target_language"):
            with self.subTest(mode=mode):
                self.api_requests.clear()
                self.api_mode = mode
                request_path, manifest_path, api_config = self.prepare_api_request(
                    suffix=f"api-quality-{mode}"
                )

                result, payload = self.run_executor(
                    request_path, api_config=api_config
                )

                self.assertEqual(result.returncode, 27, payload)
                self.assertEqual(payload["status"], "needs_attention")
                self.assertEqual(payload["quality_status"], "quality_rejected")
                self.assertEqual(len(self.api_requests), 2)
                self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_quality_boundary_rejects_empty_repeated_and_token_damaged_output(
        self,
    ) -> None:
        self.enable_test_api_credential()
        cases = {
            "empty": (None, 24, "invalid_structure"),
            "repeated": (["Hello there", "Good morning"], 27, "quality_rejected"),
            "protected_token": (None, 24, "invalid_structure"),
        }
        for mode, (sources, exit_code, failure_class) in cases.items():
            with self.subTest(mode=mode):
                self.api_requests.clear()
                self.api_mode = mode
                request_path, manifest_path, api_config = self.prepare_api_request(
                    suffix=f"api-boundary-{mode}", sources=sources
                )

                result, payload = self.run_executor(
                    request_path, api_config=api_config
                )

                self.assertEqual(result.returncode, exit_code, payload)
                self.assertEqual(payload["failure_class"], failure_class)
                self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_quality_gate_fails_closed_for_wrong_or_unsupported_target_script(
        self,
    ) -> None:
        self.enable_test_api_credential()
        for target_language in ("ru", "vi"):
            with self.subTest(target_language=target_language):
                self.api_requests.clear()
                request_path, manifest_path, api_config = self.prepare_api_request(
                    suffix=f"api-language-{target_language}",
                    target_language=target_language,
                )

                result, payload = self.run_executor(
                    request_path, api_config=api_config
                )

                self.assertEqual(result.returncode, 27, payload)
                self.assertEqual(payload["status"], "needs_attention")
                self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_high_assurance_evidence_is_independent_and_never_contributes_text(
        self,
    ) -> None:
        self.enable_test_api_credential()
        for decision, exit_code in (("pass", 0), ("reject", 27)):
            with self.subTest(decision=decision):
                self.api_requests.clear()
                request_path, manifest_path, api_config = self.prepare_api_request(
                    suffix=f"api-review-{decision}"
                )
                request = json.loads(request_path.read_text())
                subtitle_manifest = json.loads(manifest_path.read_text())
                first_batch = json.loads(
                    Path(subtitle_manifest["translation_batches"][0]["path"]).read_text()
                )
                sampled_cue = first_batch["items"][0]["id"]
                request["quality"]["high_assurance_review"] = {
                    "review_attempt_id": f"fixture-review-{decision}",
                    "reviewer": {
                        "adapter": "openai-compatible",
                        "service": "openai",
                        "model": "review-fixture-model",
                    },
                    "reservation_id": "fixture-review-reservation",
                    "decision": decision,
                    "reviewed_locations": [sampled_cue],
                    "issue_locations": [] if decision == "pass" else [sampled_cue],
                    "translation_contribution": False,
                }
                request_path.write_text(json.dumps(request))

                result, payload = self.run_executor(
                    request_path, api_config=api_config
                )

                self.assertEqual(result.returncode, exit_code, payload)
                diagnostic = self.execution_manifest(request_path, manifest_path)
                review = diagnostic["high_assurance_review"]
                self.assertTrue(review["requested"])
                self.assertEqual(review["decision"], decision)
                self.assertFalse(review["translation_contribution"])
                self.assertNotIn("translation", review)

    def test_high_assurance_reviewer_cannot_be_the_translation_provider(self) -> None:
        request_path, _, api_config = self.prepare_api_request(
            suffix="api-review-same-provider"
        )
        request = json.loads(request_path.read_text())
        request["quality"]["high_assurance_review"] = {
            "review_attempt_id": "fixture-review-same-provider",
            "reviewer": request["provider"],
            "reservation_id": "fixture-review-reservation",
            "decision": "pass",
            "reviewed_locations": ["fixture-cue"],
            "issue_locations": [],
            "translation_contribution": False,
        }
        request_path.write_text(json.dumps(request))

        result, payload = self.run_executor(request_path, api_config=api_config)

        self.assertEqual(result.returncode, 26)
        self.assertEqual(payload["failure_class"], "software_error")
        self.assertEqual(self.api_requests, [])

    def test_high_assurance_uses_distinct_attempt_and_reservation(self) -> None:
        for duplicate in ("attempt", "reservation"):
            with self.subTest(duplicate=duplicate):
                self.api_requests.clear()
                request_path, _, api_config = self.prepare_api_request(
                    suffix=f"api-review-duplicate-{duplicate}"
                )
                request = json.loads(request_path.read_text())
                request["quality"]["high_assurance_review"] = {
                    "review_attempt_id": (
                        request["attempt_id"]
                        if duplicate == "attempt"
                        else "fixture-independent-review"
                    ),
                    "reviewer": {
                        "adapter": "openai-compatible",
                        "service": "openai",
                        "model": "review-fixture-model",
                    },
                    "reservation_id": (
                        request["paid_attempt"]["reservation"]["id"]
                        if duplicate == "reservation"
                        else "fixture-independent-reservation"
                    ),
                    "decision": "pass",
                    "reviewed_locations": ["fixture-cue"],
                    "issue_locations": [],
                    "translation_contribution": False,
                }
                request_path.write_text(json.dumps(request))

                result, payload = self.run_executor(
                    request_path, api_config=api_config
                )

                self.assertEqual(result.returncode, 26)
                self.assertEqual(payload["failure_class"], "software_error")
                self.assertEqual(self.api_requests, [])

    def test_high_assurance_reviews_every_flagged_cue_after_repair(self) -> None:
        self.enable_test_api_credential()
        for coverage, exit_code in (("sample-only", 24), ("all-flagged", 0)):
            with self.subTest(coverage=coverage):
                self.api_requests.clear()
                self.api_mode = "repair_once"
                request_path, manifest_path, api_config = self.prepare_api_request(
                    suffix=f"api-review-coverage-{coverage}"
                )
                subtitle_manifest = json.loads(manifest_path.read_text())
                batch = json.loads(
                    Path(subtitle_manifest["translation_batches"][0]["path"]).read_text()
                )
                cue_ids = [item["id"] for item in batch["items"]]
                request = json.loads(request_path.read_text())
                request["quality"]["high_assurance_review"] = {
                    "review_attempt_id": f"fixture-review-{coverage}",
                    "reviewer": {
                        "adapter": "openai-compatible",
                        "service": "openai",
                        "model": "review-fixture-model",
                    },
                    "reservation_id": f"fixture-review-reservation-{coverage}",
                    "decision": "pass",
                    "reviewed_locations": (
                        cue_ids[:1] if coverage == "sample-only" else cue_ids
                    ),
                    "issue_locations": [],
                    "translation_contribution": False,
                }
                request_path.write_text(json.dumps(request))

                result, payload = self.run_executor(
                    request_path, api_config=api_config
                )

                self.assertEqual(result.returncode, exit_code, payload)
                self.assertEqual(
                    bool(self.formal_outputs(manifest_path)), exit_code == 0
                )

    def formal_outputs(self, manifest_path: Path) -> list[Path]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return sorted(Path(manifest["translation_output_dir"]).glob("*.json"))

    def execution_manifest(self, request_path: Path, manifest_path: Path) -> dict:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        path = (
            manifest_path.parent
            / "translation-executions"
            / request["attempt_id"]
            / "execution-manifest.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_complete_attempt_promotes_ordered_codex_output_and_isolates_runtime(
        self,
    ) -> None:
        request_path, manifest_path, codex_home = self.prepare_request("normal")

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["schema_version"], "1.0.0")
        self.assertEqual(payload["status"], "succeeded")
        self.assertEqual(
            payload["provider"], {"adapter": "codex", "model": "fixture-model"}
        )
        self.assertEqual(payload["completed_batches"], payload["total_batches"])
        self.assertTrue(payload["formal_translation_promoted"])
        self.assertEqual(payload["quality_status"], "machine_validated")
        self.assertEqual(len(self.formal_outputs(manifest_path)), 1)
        pipeline.load_translations(
            json.loads(manifest_path.read_text(encoding="utf-8")),
            self.formal_outputs(manifest_path)[0].parent,
        )

        probe = json.loads((codex_home / "probe.json").read_text(encoding="utf-8"))
        self.assertEqual(Path(probe["codex_home"]), codex_home.resolve())
        self.assertNotEqual(probe["home"], str(Path.home()))
        self.assertNotEqual(probe["cwd"], str(SKILL_ROOT))
        self.assertFalse(probe["has_real_codex_marker"])
        self.assertIn("--ephemeral", probe["arguments"])
        self.assertIn("--ignore-user-config", probe["arguments"])
        self.assertEqual(
            probe["arguments"][probe["arguments"].index("--disable") + 1],
            "shell_tool",
        )
        self.assertIn('approval_policy="never"', probe["arguments"])
        self.assertIn('web_search="disabled"', probe["arguments"])
        self.assertEqual(
            probe["arguments"][probe["arguments"].index("--sandbox") + 1], "read-only"
        )
        progress = [
            json.loads(line)
            for line in Path(json.loads(request_path.read_text())["progress_path"])
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual(
            [event["sequence"] for event in progress], list(range(1, len(progress) + 1))
        )
        self.assertEqual(progress[-1]["event"], "attempt_succeeded")
        diagnostic = self.execution_manifest(request_path, manifest_path)
        subtitle_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(
            diagnostic["source_transcript_sha256"],
            subtitle_manifest["source"]["sha256"],
        )
        self.assertTrue(
            all(
                {"duration_ms", "provider_exit_code", "output_sha256"} <= set(batch)
                for batch in diagnostic["batch_diagnostics"]
            )
        )
        self.assertNotIn("prompt", json.dumps(diagnostic).lower())
        self.assertNotIn("stderr", json.dumps(diagnostic).lower())

    def test_timeout_has_stable_failure_class_and_no_formal_output(self) -> None:
        request_path, manifest_path, _ = self.prepare_request(
            "timeout", timeout_seconds=0.05
        )

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 23)
        self.assertEqual(payload["failure_class"], "timeout")
        self.assertFalse(payload["formal_translation_promoted"])
        self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_invalid_structure_has_stable_failure_class_and_no_formal_output(
        self,
    ) -> None:
        request_path, manifest_path, _ = self.prepare_request("invalid_structure")

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 24)
        self.assertEqual(payload["failure_class"], "invalid_structure")
        self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_omitting_quality_configuration_cannot_bypass_default_gate(self) -> None:
        request_path, manifest_path, _ = self.prepare_request("copy")

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 27, payload)
        self.assertEqual(payload["quality_status"], "quality_rejected")
        self.assertEqual(payload["status"], "needs_attention")
        self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_mid_attempt_exit_never_promotes_partial_batches(self) -> None:
        request_path, manifest_path, _ = self.prepare_request("partial", cue_count=81)

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 22)
        self.assertEqual(payload["failure_class"], "provider_unavailable")
        self.assertEqual(payload["completed_batches"], 1)
        self.assertFalse(payload["formal_translation_promoted"])
        self.assertEqual(self.formal_outputs(manifest_path), [])
        diagnostic = self.execution_manifest(request_path, manifest_path)
        failed = diagnostic["batch_diagnostics"][-1]
        self.assertEqual(failed["provider_exit_code"], 7)
        self.assertIn("duration_ms", failed)

    def test_provider_failures_map_to_stable_classes(self) -> None:
        cases = {
            "authentication": (20, "authentication"),
            "quota": (21, "quota_exhausted"),
            "unavailable": (22, "provider_unavailable"),
        }
        for mode, (exit_code, failure_class) in cases.items():
            with self.subTest(mode=mode):
                request_path, _, _ = self.prepare_request(mode)
                result, payload = self.run_executor(request_path)
                self.assertEqual(result.returncode, exit_code)
                self.assertEqual(payload["failure_class"], failure_class)

    def test_cancellation_is_classified_without_starting_provider(self) -> None:
        request_path, manifest_path, codex_home = self.prepare_request(
            "normal", cancelled=True
        )

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 25)
        self.assertEqual(payload["failure_class"], "cancelled")
        self.assertFalse((codex_home / "probe.json").exists())
        self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_protected_token_damage_is_invalid_structure(self) -> None:
        request_path, manifest_path, _ = self.prepare_request("protected_token")

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 24)
        self.assertEqual(payload["failure_class"], "invalid_structure")
        self.assertIn("protected token", payload["failure_summary"])
        self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_protected_token_extension_is_invalid_structure(self) -> None:
        request_path, manifest_path, _ = self.prepare_request("extended_token")

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 24)
        self.assertEqual(payload["failure_class"], "invalid_structure")
        self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_retry_preserves_cue_order_and_protected_tokens(self) -> None:
        request_path, manifest_path, codex_home = self.prepare_request(
            "unavailable_once", max_batch_attempts=2
        )

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["status"], "succeeded")
        self.assertEqual((codex_home / "counter").read_text(), "2")
        translations = json.loads(self.formal_outputs(manifest_path)[0].read_text())
        self.assertEqual(
            [record["id"] for record in translations["translations"]],
            [
                segment["id"]
                for segment in json.loads(manifest_path.read_text())["segments"]
            ],
        )
        self.assertIn(
            "https://example.com", translations["translations"][0]["translation"]
        )
        self.assertIn("00:30", translations["translations"][0]["translation"])
        self.assertIn("#Archive", translations["translations"][0]["translation"])

    def test_missing_codex_executable_is_provider_unavailable(self) -> None:
        request_path, _, _ = self.prepare_request("normal")
        request = json.loads(request_path.read_text())
        request_path.write_text(json.dumps(request))
        original = self.fake_codex
        self.fake_codex = self.root / "missing-codex"
        try:
            result, payload = self.run_executor(request_path)
        finally:
            self.fake_codex = original

        self.assertEqual(result.returncode, 22)
        self.assertEqual(payload["failure_class"], "provider_unavailable")

    def test_interactive_codex_home_is_rejected_as_software_error(self) -> None:
        request_path, manifest_path, _ = self.prepare_request("normal")

        result, payload = self.run_executor(
            request_path, codex_home=Path.home() / ".codex"
        )

        self.assertEqual(result.returncode, 26)
        self.assertEqual(payload["failure_class"], "software_error")
        self.assertFalse(payload["formal_translation_promoted"])
        self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_progress_io_error_returns_stable_software_error_contract(self) -> None:
        request_path, manifest_path, _ = self.prepare_request("normal")
        request = json.loads(request_path.read_text())
        request["progress_path"] = str(self.root)
        request_path.write_text(json.dumps(request))

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 26)
        self.assertEqual(payload["failure_class"], "software_error")
        self.assertEqual(payload["attempt_id"], request["attempt_id"])
        self.assertEqual(payload["provider"], request["provider"])
        self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_invalid_manifest_returns_complete_failure_result_contract(self) -> None:
        request_path, manifest_path, _ = self.prepare_request("normal")
        request = json.loads(request_path.read_text())
        request["subtitle_manifest"] = str(self.root / "missing-manifest.json")
        request_path.write_text(json.dumps(request))

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 24)
        self.assertEqual(
            set(payload),
            {
                "schema_version",
                "attempt_id",
                "status",
                "provider",
                "completed_batches",
                "total_batches",
                "formal_translation_promoted",
                "failure_class",
                "failure_summary",
            },
        )
        self.assertEqual(payload["attempt_id"], request["attempt_id"])
        self.assertEqual(payload["provider"], request["provider"])
        self.assertEqual(payload["failure_class"], "invalid_structure")
        self.assertEqual(self.formal_outputs(manifest_path), [])

    def test_invalid_provider_length_returns_schema_safe_software_error(self) -> None:
        request_path, manifest_path, _ = self.prepare_request("normal")
        request = json.loads(request_path.read_text())
        request["provider"]["adapter"] = "x" * 65
        request_path.write_text(json.dumps(request))

        result, payload = self.run_executor(request_path)

        self.assertEqual(result.returncode, 26)
        self.assertEqual(payload["failure_class"], "software_error")
        self.assertEqual(payload["provider"]["adapter"], "unknown")
        self.assertLessEqual(len(payload["provider"]["model"]), 200)
        self.assertEqual(self.formal_outputs(manifest_path), [])


if __name__ == "__main__":
    unittest.main()
