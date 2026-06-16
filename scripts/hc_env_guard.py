#!/usr/bin/env python3
"""HyperFocus Z0ne - THE-HYPERCODE Env Guard.

Reads hypercode-core/.env.core and checks required vars are set and non-placeholder.

Required:
  POSTGRES_PASSWORD  — Postgres DB password
  OPENAI_API_KEY     — OpenAI API key

Exits 0 on pass, 1 on failure.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "hypercode-core" / ".env.core"

REQUIRED = ["POSTGRES_PASSWORD", "OPENAI_API_KEY"]
_PLACEHOLDERS = {
    "", "changeme", "CHANGEME", "your_value_here", "paste_here",
    "CHANGEME_REQUIRED", "sk-placeholder-key", "sk-placeholder",
}


def _load_env(path):
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        val = v.strip().strip('"').strip("'")
        if val.startswith("${") and ":-" in val:
            val = val.split(":-")[1].rstrip("}")
        env[k.strip()] = val
    return env


def main() -> int:
    print("\n[ENV GUARD] HyperFocus Z0ne -- THE-HYPERCODE")
    print("-" * 40)
    print("   File: hypercode-core/.env.core")
    print()

    if not ENV_FILE.exists():
        print("   FAIL  hypercode-core/.env.core not found")
        print()
        print("FAIL  Env guard FAILED -- env file missing.\n")
        return 1

    env = _load_env(ENV_FILE)
    fails = []
    for key in REQUIRED:
        val = env.get(key, "")
        if val in _PLACEHOLDERS:
            print("   FAIL  " + key + " missing or placeholder")
            fails.append(key)
        else:
            print("   PASS  " + key)

    print()
    if fails:
        print("FAIL  Env guard FAILED -- " + str(len(fails)) + " missing var(s).\n")
        return 1

    print("PASS  All required THE-HYPERCODE env vars present. Guard passed!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
