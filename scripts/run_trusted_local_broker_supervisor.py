"""One-shot/polling entrypoint for the host-only trusted broker supervisor."""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from dkg.trusted_local_supervisor import GitHubChecks, SubprocessHost, apply_release, load_config, parse_release_directives


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args()
    if args.poll_seconds < 15:
        raise SystemExit("--poll-seconds must be >= 15")
    config = load_config(args.config)
    token = os.environ.get("FOSSIL_SUPERVISOR_GITHUB_TOKEN", "").strip()
    evidence = GitHubChecks(token)
    while True:
        for release in parse_release_directives(evidence.comments()):
            print(apply_release(release, config=config, host=SubprocessHost(), evidence=evidence))
        if args.once:
            return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
