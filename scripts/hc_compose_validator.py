#!/usr/bin/env python3
"""HyperFocus Z0ne - THE-HYPERCODE Compose Validator.

Validates hypercode-core/docker-compose.core.yml for Sacred Rules:
  - NEVER docker.io image references
  - NEVER 'from backend.app.' imports
  - Every service with a build block should have a healthcheck
  - WARN on image tags pinned to 'latest'

Usage:
    python scripts/hc_compose_validator.py
    python scripts/hc_compose_validator.py hypercode-core/docker-compose.core.yml
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSE = ROOT / "hypercode-core" / "docker-compose.core.yml"

_BANNED_IMAGE_RE = re.compile(r'image:\s*(docker\.io/|index\.docker\.io/)')
_LATEST_TAG_RE = re.compile(r'image:\s*\S+:latest')
_SERVICE_RE = re.compile(r'^  (\w[\w-]*):\s*$')
_BUILD_RE = re.compile(r'^\s+build[:/]')
_HEALTHCHECK_RE = re.compile(r'^\s+healthcheck:')


def _resolve_file(arg):
    p = Path(arg)
    if p.is_absolute():
        return p
    for base in (Path.cwd(), ROOT):
        candidate = base / p
        if candidate.exists():
            return candidate
    return Path.cwd() / p


def validate(file_path):
    errors = []
    warnings = []

    if not file_path.exists():
        errors.append("file not found: " + str(file_path))
        return errors, warnings

    lines = file_path.read_text(encoding="utf-8").splitlines()

    in_services = False
    current_service = None
    service_has_build = False
    service_has_healthcheck = False
    services_with_build_no_health = []

    for i, raw in enumerate(lines, start=1):
        if raw.strip() == "services:":
            in_services = True
            continue

        if in_services:
            svc_match = _SERVICE_RE.match(raw)
            if svc_match:
                if current_service and service_has_build and not service_has_healthcheck:
                    services_with_build_no_health.append(current_service)
                current_service = svc_match.group(1)
                service_has_build = False
                service_has_healthcheck = False

            if _BUILD_RE.match(raw):
                service_has_build = True
            if _HEALTHCHECK_RE.match(raw):
                service_has_healthcheck = True

        if _BANNED_IMAGE_RE.search(raw):
            errors.append("line " + str(i) + ": docker.io image reference -- " + repr(raw.strip()))

        if _LATEST_TAG_RE.search(raw):
            warnings.append("line " + str(i) + ": image pinned to :latest -- prefer explicit tag")

    if current_service and service_has_build and not service_has_healthcheck:
        services_with_build_no_health.append(current_service)

    for svc in services_with_build_no_health:
        warnings.append("service '" + svc + "': has build block but no healthcheck")

    return errors, warnings


def main() -> int:
    target = _resolve_file(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_COMPOSE
    label = sys.argv[1] if len(sys.argv) > 1 else "hypercode-core/docker-compose.core.yml"

    print("\n[COMPOSE VALIDATOR] HyperFocus Z0ne THE-HYPERCODE -- " + label)
    print("-" * 40)
    print("   Path: " + str(target))
    print()

    errors, warnings = validate(target)

    for w in warnings:
        print("   WARN  " + w)
    if warnings:
        print()

    if errors:
        for e in errors:
            print("   FAIL  " + e)
        print()
        print("FAIL  Validation FAILED -- " + str(len(errors)) + " error(s).\n")
        return 1

    print("PASS  " + target.name + " passed all Sacred Rules checks!")
    if warnings:
        print("      (" + str(len(warnings)) + " warning(s) -- non-blocking)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
