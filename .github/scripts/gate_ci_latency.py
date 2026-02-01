import json
import os
import sys
import time
from pathlib import Path

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def pct_change(current: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0
    return ((current - baseline) / baseline) * 100.0

def moving_averages(history: list, window_sizes=(10, 20, 50)) -> dict:
    res = {}
    for w in window_sizes:
        last = history[-w:] if len(history) >= w else history
        res[w] = sum(last) / max(len(last), 1)
    return res

def analyze_subfolders(root: str) -> dict:
    tests = []
    configs = []
    artifacts = []
    for p in Path(root).rglob('*'):
        name = p.name.lower()
        if p.is_file():
            if name.startswith('test_') and name.endswith('.py'):
                tests.append(str(p))
            if name in ('pytest.ini', 'pyproject.toml', 'requirements.txt'):
                configs.append(str(p))
            if name.endswith('.tgz') or name.endswith('.zip') or name.endswith('.json'):
                artifacts.append(str(p))
    return {"tests": tests, "configs": configs, "artifacts": artifacts}

def main() -> None:
    baseline_path = os.getenv("BASELINE_PATH", ".github/ci-latency-baseline.json")
    durations_dir = os.getenv("DURATIONS_DIR", "./durations")
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    history_path = os.getenv("HISTORY_PATH", ".github/durations-history.json")

    baseline = load_json(baseline_path)
    threshold = float(baseline.get("threshold_percent", 5))
    stages_cfg = baseline.get("stages", {})

    durations: dict = {}
    for name in ("test", "build", "deploy"):
        file_path = os.path.join(durations_dir, f"{name}-duration.json")
        if os.path.exists(file_path):
            try:
                data = load_json(file_path)
                durations[name] = float(data.get("duration_ms", 0))
            except Exception:
                durations[name] = 0.0
        else:
            durations[name] = 0.0

    report_lines = []
    report_lines.append("CI Latency Regression Gate")
    report_lines.append("")
    report_lines.append("Stage | Current (ms) | Baseline (ms) | Change (%)")
    report_lines.append("--- | --- | --- | ---")

    regressions: dict = {}
    worst_stage = None
    worst_delta = -1.0

    for stage, current_ms in durations.items():
        baseline_ms = float(stages_cfg.get(stage, {}).get("baseline_ms", 0))
        change = pct_change(current_ms, baseline_ms)
        report_lines.append(f"{stage} | {int(current_ms)} | {int(baseline_ms)} | {change:.2f}")
        if change > threshold:
            regressions[stage] = change
        delta = current_ms - baseline_ms
        if delta > worst_delta:
            worst_delta = delta
            worst_stage = stage

    history = {}
    if os.path.exists(history_path):
        try:
            history = load_json(history_path)
        except Exception:
            history = {}
    ts = int(time.time() * 1000)
    for stage, ms in durations.items():
        arr = history.get(stage, [])
        arr.append(ms)
        history[stage] = arr[-200:]
    try:
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f)
    except Exception:
        pass

    report_lines.append("")
    report_lines.append("Moving Averages (ms)")
    report_lines.append("Stage | MA(10) | MA(20) | MA(50)")
    report_lines.append("--- | --- | --- | ---")
    for stage, arr in history.items():
        avgs = moving_averages(arr)
        report_lines.append(f"{stage} | {avgs.get(10, 0):.0f} | {avgs.get(20, 0):.0f} | {avgs.get(50, 0):.0f}")

    sub = analyze_subfolders('.')
    report_lines.append("")
    report_lines.append(f"Subfolder analysis: tests={len(sub['tests'])} configs={len(sub['configs'])} artifacts={len(sub['artifacts'])}")

    cov_path = os.path.join(durations_dir, 'coverage-json', 'coverage.json')
    if os.path.exists(cov_path):
        try:
            cov = load_json(cov_path)
            totals = cov.get('totals', {})
            pct = totals.get('percent_covered', 0)
            report_lines.append("")
            report_lines.append(f"Coverage total: {pct}%")
        except Exception:
            pass

    vuln_path = os.path.join(durations_dir, 'pip-audit', 'pip-audit.json')
    if os.path.exists(vuln_path):
        try:
            vulns = load_json(vuln_path)
            count = len(vulns) if isinstance(vulns, list) else 0
            report_lines.append("")
            report_lines.append(f"Dependency vulnerabilities: {count}")
        except Exception:
            pass

    if worst_stage is not None:
        report_lines.append("")
        report_lines.append(f"Bottleneck: {worst_stage} (+{int(worst_delta)} ms vs baseline)")

    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write("\n".join(report_lines) + "\n")
        except Exception:
            pass

    if regressions:
        print("\n".join(report_lines))
        print("Regression detected:")
        for stage, change in regressions.items():
            print(f" - {stage}: {change:.2f}% over baseline")
        sys.exit(1)
    else:
        print("\n".join(report_lines))
        print("No regressions over threshold.")

if __name__ == "__main__":
    main()
