import os
import json
import sys
from pathlib import Path

def load_json(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def dir_size(root: str) -> int:
    total = 0
    for p in Path(root).rglob('*'):
        if p.is_file():
            try:
                total += p.stat().st_size
            except Exception:
                pass
    return total

def top_files(root: str, n=10) -> list:
    files = []
    for p in Path(root).rglob('*'):
        if p.is_file():
            try:
                files.append((p.as_posix(), p.stat().st_size))
            except Exception:
                pass
    files.sort(key=lambda x: x[1], reverse=True)
    return files[:n]

def pct_change(current: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0 if current == 0 else 100.0
    return ((current - baseline) / baseline) * 100.0

def main():
    baseline_path = os.getenv('BUNDLE_BASELINE', '.github/bundle-size-baseline.json')
    dist_dir = os.getenv('DIST_DIR', 'hyperflow-editor/dist')
    summary_path = os.getenv('GITHUB_STEP_SUMMARY')

    baseline = load_json(baseline_path)
    threshold = float(baseline.get('threshold_percent', 5))
    baseline_total = int(baseline.get('baseline_total_bytes', 0))

    current_total = dir_size(dist_dir)
    change = pct_change(current_total, baseline_total)
    top = top_files(dist_dir)

    lines = []
    lines.append('Web Bundle Size Report')
    lines.append('')
    lines.append(f'Total size: {current_total} bytes (baseline {baseline_total}, change {change:.2f}%)')
    lines.append('Top files:')
    for path, size in top:
        lines.append(f' - {path} : {size} bytes')
    if summary_path:
        try:
            with open(summary_path, 'a', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
        except Exception:
            pass
    if change > threshold:
        print('\n'.join(lines))
        sys.exit(1)
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
