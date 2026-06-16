#!/usr/bin/env python3
"""HyperFocus Z0ne - THE-HYPERCODE Session Start Hook.

Monorepo: hypercode-core (FastAPI) + hypercode-engine (Python pkg) + hyperflow-editor (React/Vite).
Writes a .focus_session_start marker and checks core project files exist.
Exits 0 on pass, 1 on hard failure.
"""

import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION_FILE = ROOT / ".focus_session_start"


def _ping(url):
    try:
        urllib.request.urlopen(url, timeout=3)
        return True
    except Exception:
        return False


def main() -> int:
    now = datetime.now()
    print("\n[SESSION START] HyperFocus Z0ne -- THE-HYPERCODE")
    print("-" * 40)
    print("   Time    : " + now.strftime("%Y-%m-%d %H:%M:%S"))

    SESSION_FILE.write_text(now.isoformat())

    readme_ok = (ROOT / "README.md").exists()
    compose_ok = (ROOT / "hypercode-core" / "docker-compose.core.yml").exists()
    env_ok = (ROOT / "hypercode-core" / ".env.core").exists()
    engine_ok = (ROOT / "hypercode-engine" / "pyproject.toml").exists()
    editor_ok = (ROOT / "hyperflow-editor" / "package.json").exists()
    core_ok = _ping("http://localhost:8000")
    editor_dev_ok = _ping("http://localhost:5173")

    print("   README.md                 : " + ("PASS found" if readme_ok else "FAIL missing"))
    print("   hypercode-core/compose    : " + ("PASS found" if compose_ok else "WARN missing"))
    print("   hypercode-core/.env.core  : " + ("PASS found" if env_ok else "WARN missing"))
    print("   hypercode-engine/pyproject: " + ("PASS found" if engine_ok else "WARN missing"))
    print("   hyperflow-editor/package  : " + ("PASS found" if editor_ok else "WARN missing"))
    print("   core API :8000            : " + ("PASS reachable" if core_ok else "WARN offline (run docker compose)"))
    print("   editor   :5173            : " + ("PASS reachable" if editor_dev_ok else "WARN offline (run npm run dev)"))
    print()

    if not readme_ok:
        print("FAIL  Session start FAILED -- README.md not found.\n")
        return 1

    print("PASS  THE-HYPERCODE session started. BROski forever! Let's build!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
