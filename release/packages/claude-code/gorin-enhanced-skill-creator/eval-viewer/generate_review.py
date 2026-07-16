#!/usr/bin/env python3
"""Generate a self-contained HTML review page from eval workspace results.

Reads iteration directories containing eval metadata and benchmark.json,
then produces an HTML file with two tabs: Outputs (side-by-side comparison)
and Benchmark (summary table + CSS bar chart).

Usage:
    python3 generate_review.py --workspace PATH [--output PATH] \
                               [--previous-workspace PATH]

Exit codes:
    0 — success
    1 — partial success (some files missing)
    2 — error (workspace not found, no data)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from html import escape
from pathlib import Path


def iteration_sort_key(path: Path) -> tuple[int, str]:
    match = re.fullmatch(r"iteration-(\d+)", path.name)
    if match:
        return (int(match.group(1)), path.name)
    return (float("inf"), path.name)



def load_json_file(path: Path, label: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: skipping {label} at {path}: {exc}", file=sys.stderr)
        return None



def load_workspace(workspace: Path) -> dict:
    """Load all eval metadata and benchmark from a workspace iteration directory.

    Returns the newest iteration's data, or None.
    """
    iteration_dirs = sorted(
        [d for d in workspace.iterdir() if d.is_dir() and d.name.startswith("iteration-")],
        key=iteration_sort_key,
    )
    if not iteration_dirs:
        return None

    for latest in reversed(iteration_dirs):
        benchmark_path = latest / "benchmark.json"
        if not benchmark_path.exists():
            continue

        benchmark = load_json_file(benchmark_path, "benchmark.json")
        if benchmark is None:
            continue

        cases = []
        for entry in latest.iterdir():
            meta_path = entry / "eval_metadata.json"
            if entry.is_dir() and meta_path.exists():
                case_data = load_json_file(meta_path, "eval_metadata.json")
                if case_data is not None:
                    cases.append(case_data)

        cases.sort(key=lambda c: c.get("id", ""))
        return {"benchmark": benchmark, "cases": cases, "iteration_dir": str(latest)}

    return None


def escape_json(obj) -> str:
    """JSON-encode and HTML-escape for embedding in script tags."""
    return escape(json.dumps(obj, ensure_ascii=False))


def generate_html(current: dict, previous: dict | None) -> str:
    """Generate the full self-contained HTML page."""
    cases = current["cases"]
    benchmark = current["benchmark"]
    prev_benchmark = previous["benchmark"] if previous else None

    # Build per-case HTML for Tab 1
    case_rows = []
    for c in cases:
        cid = escape(c.get("id", ""))
        prompt = escape(c.get("prompt", ""))
        expected_raw = c.get("expected", "")
        expected_str = escape(str(expected_raw))
        with_out = escape(c.get("with_skill_output", ""))
        without_out = escape(c.get("without_skill_output", ""))
        grading = c.get("grading", {})
        passed = grading.get("passed", False)
        notes = escape(grading.get("notes", ""))
        status_icon = "✅" if passed else "❌"
        status_class = "pass" if passed else "fail"

        case_rows.append(f"""
        <div class="case-card" data-case-id="{cid}">
          <div class="case-header">
            <span class="case-id">{cid}</span>
            <span class="case-status {status_class}">{status_icon} {notes}</span>
          </div>
          <div class="case-meta">
            <strong>Prompt:</strong> {prompt}<br>
            <strong>Expected:</strong> {expected_str}
          </div>
          <div class="outputs-grid">
            <div class="output-panel">
              <div class="panel-label">With Skill</div>
              <pre class="output-text">{with_out}</pre>
            </div>
            <div class="output-panel">
              <div class="panel-label">Without Skill</div>
              <pre class="output-text">{without_out}</pre>
            </div>
          </div>
          <div class="feedback-row">
            <textarea class="feedback-textarea" data-id="{cid}"
                      placeholder="Feedback for {cid}..."></textarea>
          </div>
        </div>""")

    cases_html = "\n".join(case_rows)

    # Build benchmark table for Tab 2
    per_case_rows = []
    for pc in benchmark.get("per_case", []):
        pid = escape(pc.get("id", ""))
        p_passed = pc.get("passed", False)
        tw = pc.get("tokens_with", 0)
        two = pc.get("tokens_without", 0)
        tmw = pc.get("time_with_ms", 0)
        tmwo = pc.get("time_without_ms", 0)
        icon = "✅" if p_passed else "❌"
        per_case_rows.append(f"""
          <tr>
            <td>{pid}</td>
            <td>{icon}</td>
            <td>{tw}</td>
            <td>{two}</td>
            <td>{tmw}</td>
            <td>{tmwo}</td>
          </tr>""")

    # Previous workspace delta
    delta_html = ""
    if prev_benchmark:
        curr_rate = benchmark.get("pass_rate", 0)
        prev_rate = prev_benchmark.get("pass_rate", 0)
        delta = curr_rate - prev_rate
        delta_sign = "+" if delta >= 0 else ""
        delta_class = "positive" if delta >= 0 else "negative"
        delta_html = f"""
        <div class="delta-banner {delta_class}">
          <strong>Δ vs Previous (iteration-{prev_benchmark.get('iteration', '?')}):</strong>
          Pass rate {prev_rate:.0%} → {curr_rate:.0%}
          ({delta_sign}{delta:.0%}) |
          Avg tokens (with) {prev_benchmark.get('avg_tokens_with', 0):.0f} → {benchmark.get('avg_tokens_with', 0):.0f} |
          Avg time (with) {prev_benchmark.get('avg_time_with_ms', 0):.0f}ms → {benchmark.get('avg_time_with_ms', 0):.0f}ms
        </div>"""

    # Bar chart via inline CSS
    pass_rate = benchmark.get("pass_rate", 0)
    total = benchmark.get("total_cases", 0)
    passed_count = sum(1 for pc in benchmark.get("per_case", []) if pc.get("passed", False))
    fail_count = total - passed_count
    bar_pass_width = pass_rate * 100

    summary_stats = f"""
    <div class="summary-stats">
      <div class="stat-card">
        <div class="stat-label">Pass Rate</div>
        <div class="stat-value">{pass_rate:.0%}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Cases</div>
        <div class="stat-value">{total}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Baseline Pass Rate</div>
        <div class="stat-value">{benchmark.get('baseline_pass_rate', 0):.0%}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Tokens (with)</div>
        <div class="stat-value">{benchmark.get('avg_tokens_with', 0):.0f}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Tokens (without)</div>
        <div class="stat-value">{benchmark.get('avg_tokens_without', 0):.0f}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Time (with)</div>
        <div class="stat-value">{benchmark.get('avg_time_with_ms', 0):.0f}ms</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Time (without)</div>
        <div class="stat-value">{benchmark.get('avg_time_without_ms', 0):.0f}ms</div>
      </div>
    </div>
    <div class="bar-chart">
      <div class="bar-pass" style="width:{bar_pass_width}%">{passed_count} passed</div>
      <div class="bar-fail" style="width:{100 - bar_pass_width}%">{fail_count} failed</div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Eval Review — Iteration {escape(str(benchmark.get('iteration', '?')))}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #f5f5f5; color: #333; padding: 1rem; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.5rem; }}
  .subtitle {{ color: #666; font-size: 0.85rem; margin-bottom: 1rem; }}

  /* Tabs */
  .tabs {{ display: flex; gap: 0; border-bottom: 2px solid #ddd; margin-bottom: 1rem; }}
  .tab {{ padding: 0.6rem 1.2rem; cursor: pointer; border: none; background: none;
          font-size: 0.95rem; font-weight: 500; color: #666; border-bottom: 2px solid transparent;
          margin-bottom: -2px; transition: all 0.2s; }}
  .tab:hover {{ color: #333; }}
  .tab.active {{ color: #2563eb; border-bottom-color: #2563eb; }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}

  /* Case cards */
  .case-card {{ background: #fff; border-radius: 8px; padding: 1rem;
                margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .case-header {{ display: flex; justify-content: space-between; align-items: center;
                 margin-bottom: 0.5rem; }}
  .case-id {{ font-weight: 600; font-family: monospace; font-size: 0.9rem; }}
  .case-status {{ font-size: 0.8rem; }}
  .case-status.pass {{ color: #16a34a; }}
  .case-status.fail {{ color: #dc2626; }}
  .case-meta {{ font-size: 0.85rem; color: #555; margin-bottom: 0.75rem;
                line-height: 1.5; }}
  .outputs-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }}
  .output-panel {{ border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden; }}
  .panel-label {{ background: #f9fafb; padding: 0.4rem 0.6rem; font-size: 0.78rem;
                 font-weight: 600; color: #555; border-bottom: 1px solid #e5e7eb; }}
  .output-text {{ padding: 0.6rem; font-size: 0.82rem; white-space: pre-wrap;
                 word-break: break-word; max-height: 300px; overflow-y: auto; margin: 0;
                 font-family: inherit; }}
  .feedback-row {{ margin-top: 0.75rem; }}
  .feedback-textarea {{ width: 100%; min-height: 60px; padding: 0.5rem;
                       border: 1px solid #d1d5db; border-radius: 6px;
                       font-size: 0.85rem; resize: vertical; font-family: inherit; }}
  .feedback-textarea:focus {{ outline: none; border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37,99,235,0.15); }}

  /* Submit bar */
  .submit-bar {{ margin-top: 1rem; text-align: center; }}
  .submit-btn {{ padding: 0.6rem 1.5rem; background: #2563eb; color: #fff; border: none;
                border-radius: 6px; font-size: 0.9rem; cursor: pointer; transition: background 0.2s; }}
  .submit-btn:hover {{ background: #1d4ed8; }}

  /* Benchmark tab */
  .summary-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
                    gap: 0.75rem; margin-bottom: 1rem; }}
  .stat-card {{ background: #fff; padding: 0.75rem; border-radius: 8px;
               box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center; }}
  .stat-label {{ font-size: 0.75rem; color: #666; margin-bottom: 0.25rem; }}
  .stat-value {{ font-size: 1.3rem; font-weight: 700; color: #111; }}

  .bar-chart {{ display: flex; height: 32px; border-radius: 6px; overflow: hidden;
               margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .bar-pass {{ background: #22c55e; display: flex; align-items: center; justify-content: center;
              color: #fff; font-size: 0.78rem; font-weight: 600; min-width: 2rem; }}
  .bar-fail {{ background: #ef4444; display: flex; align-items: center; justify-content: center;
              color: #fff; font-size: 0.78rem; font-weight: 600; min-width: 2rem; }}

  .delta-banner {{ padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem;
                  font-size: 0.85rem; }}
  .delta-banner.positive {{ background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; }}
  .delta-banner.negative {{ background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }}

  .benchmark-table {{ width: 100%; border-collapse: collapse; background: #fff;
                     border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .benchmark-table th {{ background: #f9fafb; padding: 0.6rem 0.75rem; text-align: left;
                        font-size: 0.78rem; font-weight: 600; color: #555;
                        border-bottom: 2px solid #e5e7eb; }}
  .benchmark-table td {{ padding: 0.5rem 0.75rem; font-size: 0.82rem;
                        border-bottom: 1px solid #f3f4f6; }}

  /* Responsive */
  @media (max-width: 768px) {{
    .outputs-grid {{ grid-template-columns: 1fr; }}
    .summary-stats {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
</head>
<body>

<h1>📊 Eval Review</h1>
<div class="subtitle">Iteration {escape(str(benchmark.get('iteration', '?')))} —
  {escape(benchmark.get('timestamp', ''))} —
  {benchmark.get('total_cases', 0)} cases</div>

<div class="tabs">
  <button class="tab active" data-tab="outputs">Outputs</button>
  <button class="tab" data-tab="benchmark">Benchmark</button>
</div>

<div id="tab-outputs" class="tab-content active">
  {cases_html}
  <div class="submit-bar">
    <button class="submit-btn" id="submit-feedback">💾 Download feedback.json</button>
  </div>
</div>

<div id="tab-benchmark" class="tab-content">
  {summary_stats}
  {delta_html}
  <table class="benchmark-table">
    <thead>
      <tr>
        <th>ID</th><th>Pass</th><th>Tokens (with)</th><th>Tokens (without)</th>
        <th>Time w/ (ms)</th><th>Time w/o (ms)</th>
      </tr>
    </thead>
    <tbody>
      {" ".join(per_case_rows)}
    </tbody>
  </table>
</div>

<script>
(function() {{
  // Tab switching
  document.querySelectorAll('.tab').forEach(function(tab) {{
    tab.addEventListener('click', function() {{
      document.querySelectorAll('.tab').forEach(function(t) {{ t.classList.remove('active'); }});
      document.querySelectorAll('.tab-content').forEach(function(c) {{ c.classList.remove('active'); }});
      tab.classList.add('active');
      document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    }});
  }});

  // Feedback download
  document.getElementById('submit-feedback').addEventListener('click', function() {{
    var entries = [];
    document.querySelectorAll('.feedback-textarea').forEach(function(ta) {{
      var fb = ta.value.trim();
      if (fb) {{
        entries.push({{ id: ta.dataset.id, feedback: fb }});
      }}
    }});
    var data = {{
      timestamp: new Date().toISOString(),
      per_case: entries
    }};
    var blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'feedback.json';
    a.click();
    URL.revokeObjectURL(url);
  }});
}})();
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate HTML review page from eval workspace")
    parser.add_argument("--workspace", required=True,
                        help="Path to eval workspace directory")
    parser.add_argument("--output", default=None,
                        help="Output HTML file path (default: <workspace>/review.html)")
    parser.add_argument("--previous-workspace", default=None,
                        help="Path to previous workspace for delta comparison")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"Error: workspace not found: {workspace}", file=sys.stderr)
        sys.exit(2)

    current = load_workspace(workspace)
    if not current:
        print(f"Error: no iteration data found in {workspace}", file=sys.stderr)
        sys.exit(2)

    if not current["cases"]:
        print(f"Error: no eval cases found in {current['iteration_dir']}", file=sys.stderr)
        sys.exit(2)

    previous = None
    if args.previous_workspace:
        prev_path = Path(args.previous_workspace).resolve()
        if prev_path.is_dir():
            previous = load_workspace(prev_path)
            if not previous:
                print(f"Warning: no data in previous workspace {prev_path}", file=sys.stderr)

    html = generate_html(current, previous)

    output_path = Path(args.output) if args.output else workspace / "review.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    print(f"Review page written to: {output_path}")
    print(f"  {len(current['cases'])} cases, iteration {current['benchmark'].get('iteration', '?')}")
    sys.exit(0)


if __name__ == "__main__":
    main()
