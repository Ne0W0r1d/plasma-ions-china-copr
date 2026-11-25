#!/usr/bin/env python3
"""Build source RPMs grouped by the Plasma version of their target chroots.

The output is a TSV matrix consumed by the COPR workflow:

    <plasma_version>\t<comma-separated chroots>\t<srpm path>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def log(message: str) -> None:
    print(message, file=sys.stderr)


def read_chroots(path: Path) -> list[str]:
    chroots = []
    for line in path.read_text(encoding="utf-8").splitlines():
        chroot = line.split("#", 1)[0].strip()
        if chroot:
            chroots.append(chroot)
    return chroots


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def state_key(chroot: str) -> str | None:
    if chroot.startswith("fedora-rawhide-"):
        return "fedora_rawhide"
    match = re.match(r"fedora-(\d+)-", chroot)
    if match:
        return f"fedora_{match.group(1)}"
    if chroot.startswith("opensuse-tumbleweed-"):
        return "opensuse_factory"
    return None


def plasma_version_for(chroot: str, kde: dict[str, str]) -> str:
    key = state_key(chroot)
    version = kde.get(key) if key else None
    if not version:
        version = kde.get("stable")
    match = re.match(r"\d+(?:\.\d+)*", str(version or ""))
    return match.group(0) if match else "0.0.0"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default=str(ROOT / "packaging" / "state.json"))
    parser.add_argument("--chroots", default=str(ROOT / "copr" / "chroots.txt"))
    parser.add_argument("--spec", default=str(ROOT / "plasma-ions-china.spec"))
    parser.add_argument("--outdir", default=str(ROOT / "out"))
    parser.add_argument("--dry-run", action="store_true", help="only print the matrix")
    args = parser.parse_args()

    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    kde = state.get("kde") or {}
    chroots = read_chroots(Path(args.chroots))
    if not chroots:
        log("error: no chroots configured")
        return 1

    groups: dict[str, list[str]] = {}
    for chroot in chroots:
        version = plasma_version_for(chroot, kde)
        groups.setdefault(version, []).append(chroot)

    spec = str(Path(args.spec).resolve())
    outdir = Path(args.outdir)

    for version in sorted(groups, key=version_key):
        group = groups[version]
        if args.dry_run:
            print(f"{version}\t{','.join(group)}\t-")
            continue

        build_dir = outdir / f"plasma{version}"
        log(f"Building SRPM for Plasma {version}: {', '.join(group)}")
        environment = os.environ.copy()
        environment["PLASMA_VERSION"] = version
        process = subprocess.run(
            [str(ROOT / "ci" / "build-srpm.sh"), spec, str(build_dir)],
            env=environment,
            text=True,
            capture_output=True,
        )
        if process.returncode != 0:
            log(process.stdout)
            log(process.stderr)
            return process.returncode
        srpm_lines = [line for line in process.stdout.splitlines() if line.strip()]
        if not srpm_lines:
            log(f"error: no SRPM path returned for Plasma {version}")
            return 1
        print(f"{version}\t{','.join(group)}\t{srpm_lines[-1]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
