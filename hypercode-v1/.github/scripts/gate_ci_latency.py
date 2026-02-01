import json, sys, os

def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def pct_change(current: float, baseline: float) -> float:
    if baseline <= 0: return 0.0
    return ((current - baseline) / baseline) * 100.0

def main():
    baseline_path = os.environ.get('BASELINE_PATH', '.github/ci-latency-baseline.json')
    baseline = load_json(baseline_path)
    threshold = float(baseline.get('threshold_percent', 5))

    stages_cfg = baseline.get('stages', {})
    durations = {}
    for key in ('test', 'build', 'deploy'):
        p = os.environ.get(f'{key.upper()}_DURATION_PATH', f'{key}-duration.json')
        if os.path.exists(p):
            data = load_json(p)
            durations[key] = float(data.get('duration_ms', 0))
        else:
            durations[key] = 0.0

    report = { 'threshold_percent': threshold, 'stages': {} }
    regressions = []
    for key, current in durations.items():
        base = float(stages_cfg.get(key, {}).get('baseline_ms', 0))
        change = pct_change(current, base)
        status = 'ok'
        if current > 0 and change > threshold:
            status = 'regression'
            regressions.append({ 'stage': key, 'current_ms': current, 'baseline_ms': base, 'change_percent': change })
        report['stages'][key] = {
            'current_ms': current,
            'baseline_ms': base,
            'change_percent': change,
            'status': status,
        }

    print('CI Latency Report')
    print(json.dumps(report, indent=2))

    if regressions:
        print('\nDetected regressions exceeding threshold:')
        for r in regressions:
            print(f"- {r['stage']}: {r['current_ms']:.0f}ms vs baseline {r['baseline_ms']:.0f}ms (+{r['change_percent']:.2f}%)")
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()

