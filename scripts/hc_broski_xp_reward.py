#!/usr/bin/env python3
"""HyperFocus Z0ne - THE-HYPERCODE BROski XP Reward Hook.

Publishes an XP award to Redis channel 'broski_economy' (DB 1).
Gracefully no-ops if Redis is offline.  Always exits 0.

Usage:
    python scripts/hc_broski_xp_reward.py --xp 10 --reason session_start
"""

import argparse
import json
import sys
from datetime import datetime

_REDIS_CHANNEL = "broski_economy"
_REDIS_DB = 1  # Sacred Rule: DB 1 = cache
_REDIS_CONTAINER = "redis"  # internal redis (data-net) -- not published to host


def _publish(channel, payload):
    body = json.dumps(payload)
    # 1) direct host TCP -- only works if redis 6379 is published to the host
    try:
        import redis
        r = redis.Redis(host="127.0.0.1", port=6379, db=_REDIS_DB, socket_connect_timeout=2)
        r.ping()
        r.publish(channel, body)
        return "tcp"
    except Exception:
        pass
    # 2) fallback: publish into the internal redis container via docker exec
    #    keeps redis on its internal network (Sacred Rule: data-net internal)
    try:
        import shutil
        import subprocess
        if shutil.which("docker"):
            proc = subprocess.run(
                ["docker", "exec", _REDIS_CONTAINER, "redis-cli", "-n", str(_REDIS_DB),
                 "PUBLISH", channel, body],
                capture_output=True, text=True, timeout=8,
            )
            if proc.returncode == 0:
                return "docker"
    except Exception:
        pass
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Award BROski$ XP via Redis")
    parser.add_argument("--xp", type=int, default=10)
    parser.add_argument("--reason", default="session_hook")
    args = parser.parse_args()

    print("\n[BROSKI XP] HyperFocus Z0ne -- THE-HYPERCODE")
    print("-" * 40)

    payload = {
        "event": "xp_award",
        "xp": args.xp,
        "reason": args.reason,
        "source": "the_hypercode_hook",
        "timestamp": datetime.now().isoformat(),
    }

    via = _publish(_REDIS_CHANNEL, payload)

    if via:
        print("   PASS  Published " + str(args.xp) + " XP  reason=" + args.reason + "  (via " + via + ")")
    else:
        print("   WARN  Redis unreachable -- XP award skipped (non-fatal)")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
