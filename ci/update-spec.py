#!/usr/bin/env python3
"""Synchronise the COPR spec with upstream and KDE Plasma releases.

The script is intentionally dependency-free so it can run on a bare GitHub
Actions runner (or in a Fedora container) without extra Python packages.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "plasma-ions-china.spec"
STATE = ROOT / "packaging" / "state.json"
CHROOTS = ROOT / "copr" / "chroots.txt"

UPSTREAM_REPO = "arenekosreal/plasma-ions-china"
USER_AGENT = "plasma-ions-china-copr-ci/1.0"


def log(message: str) -> None:
    print(message, file=sys.stderr)


def fetch(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
    attempts: int = 3,
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if 400 <= error.code < 500:
                raise
            last_error = error
        except (OSError, http.client.HTTPException) as error:
            last_error = error
        log(f"warning: fetch failed ({attempt}/{attempts}) for {url}: {last_error}")
        time.sleep(2 * attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def fetch_text(url: str, *, headers: dict[str, str] | None = None, timeout: int = 60) -> str:
    return fetch(url, headers=headers, timeout=timeout).decode("utf-8", "replace")


def download_archive(url: str) -> bytes:
    """Download a source archive, preferring curl for its transfer retry support."""
    curl = shutil.which("curl")
    if not curl:
        return fetch(url, timeout=180, attempts=5)

    with tempfile.NamedTemporaryFile() as temporary:
        command = [
            curl,
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--retry",
            "5",
            "--retry-delay",
            "2",
            "--retry-all-errors",
            "--output",
            temporary.name,
            url,
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as error:
            raise RuntimeError(f"failed to download {url}: curl exited with {error.returncode}") from error
        return Path(temporary.name).read_bytes()


def github_json(path: str):
    headers = {}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return json.loads(fetch(f"https://api.github.com{path}", headers=headers))


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def latest_upstream() -> dict[str, str | bool]:
    tags = github_json(f"/repos/{UPSTREAM_REPO}/tags?per_page=100")
    candidates = []
    for tag in tags:
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", tag["name"])
        if match:
            candidates.append((tuple(int(part) for part in match.groups()), tag))
    if not candidates:
        raise RuntimeError(f"no release tags found in {UPSTREAM_REPO}")

    _, tag = max(candidates, key=lambda item: item[0])
    match = re.fullmatch(r"v?(\d+\.\d+\.\d+)", tag["name"])
    assert match is not None
    tag_version = match.group(1)

    head = github_json(f"/repos/{UPSTREAM_REPO}/commits/main")
    commit = head["sha"]
    if commit == tag["commit"]["sha"]:
        version = tag_version
        snapshot = False
    else:
        timestamp = re.sub(r"[^0-9]", "", head["commit"]["committer"]["date"])[:14]
        version = f"{tag_version}^{timestamp}git{commit[:7]}"
        snapshot = True

    log(f"Downloading source archive for {version} ({commit[:12]})...")
    archive = download_archive(f"https://codeload.github.com/{UPSTREAM_REPO}/tar.gz/{commit}")
    digest = hashlib.sha256(archive).hexdigest()
    return {
        "tag": tag["name"],
        "version": version,
        "cmake_version": tag_version,
        "commit": commit,
        "sha256": digest,
        "snapshot": snapshot,
    }


def latest_kde_stable() -> str:
    page = fetch_text("https://download.kde.org/stable/plasma/")
    versions = set(re.findall(r'href="(\d+\.\d+\.\d+)/"', page))
    if not versions:
        raise RuntimeError("could not find a Plasma release on download.kde.org")
    return max(versions, key=version_key)


def fedora_plasma(release: str) -> str:
    payload = json.loads(fetch_text(f"https://mdapi.fedoraproject.org/{release}/pkg/plasma-workspace"))
    version = payload.get("version")
    if not version:
        raise RuntimeError(f"plasma-workspace has no version in Fedora {release}")
    return str(version)


def opensuse_plasma() -> str:
    history = fetch_text(
        "https://api.opensuse.org/public/source/openSUSE:Factory/plasma6-workspace/_history?limit=1"
    )
    match = re.search(r"<version>([^<]+)</version>", history)
    if not match:
        raise RuntimeError("could not find plasma6-workspace version in openSUSE:Factory")
    return match.group(1).strip()


def read_chroots() -> list[str]:
    chroots = []
    if not CHROOTS.exists():
        return chroots
    for line in CHROOTS.read_text(encoding="utf-8").splitlines():
        chroot = line.split("#", 1)[0].strip()
        if chroot:
            chroots.append(chroot)
    return chroots


def chroot_plasma_checks() -> dict[str, object]:
    chroots = read_chroots()
    checks: dict[str, object] = {"stable": latest_kde_stable}

    fedora_releases = set()
    for chroot in chroots:
        match = re.match(r"fedora-(\d+)-", chroot)
        if match:
            fedora_releases.add(match.group(1))
    for release in sorted(fedora_releases, key=int):
        checks[f"fedora_{release}"] = lambda release=release: fedora_plasma(f"f{release}")
    if any(chroot.startswith("fedora-rawhide-") for chroot in chroots):
        checks["fedora_rawhide"] = lambda: fedora_plasma("rawhide")
    if any(chroot.startswith("opensuse-tumbleweed-") for chroot in chroots):
        checks["opensuse_factory"] = opensuse_plasma
    return checks


def detect_kde(previous: dict[str, str]) -> dict[str, str]:
    checks = chroot_plasma_checks()
    result = {}
    for key, check in checks.items():
        try:
            result[key] = check()
        except Exception as error:  # noqa: BLE001 - keep the previous value on a flaky endpoint
            log(f"warning: could not check KDE version ({key}): {error}")
            result[key] = previous.get(key)
    return result


def parse_spec(text: str) -> dict[str, str]:
    patterns = {
        "version": r"^Version:\s*(\S+)",
        "cmake_version": r"^%global upstream_version\s+(\S+)",
        "commit": r"^%global commit\s+(\S+)",
        "sha256": r"^# Source0 SHA256:\s*(\S+)",
    }
    parsed = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        if not match:
            raise RuntimeError(f"cannot find {key} in {SPEC.name}")
        parsed[key] = match.group(1)
    return parsed


def replace_field(text: str, pattern: str, value: str) -> str:
    updated, count = re.subn(
        pattern,
        lambda match: match.group(1) + value,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError(f"failed to update {pattern!r}")
    return updated


def write_github_output(**values: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with open(output, "a", encoding="utf-8") as stream:
        for key, value in values.items():
            value = str(value).replace("\n", " ")
            print(f"{key}={value}", file=stream)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="write updates to the spec and state file")
    args = parser.parse_args()

    spec_text = SPEC.read_text(encoding="utf-8")
    spec = parse_spec(spec_text)

    previous_state: dict = {}
    if STATE.exists():
        previous_state = json.loads(STATE.read_text(encoding="utf-8"))
    previous_kde = previous_state.get("kde") or {}

    upstream = latest_upstream()
    kde = detect_kde(previous_kde)

    version_changed = spec["version"] != upstream["version"]
    cmake_version_changed = spec["cmake_version"] != upstream["cmake_version"]
    commit_changed = spec["commit"] != upstream["commit"]
    sha_changed = spec["sha256"] != upstream["sha256"]
    kde_changed = bool(previous_state) and previous_kde != kde

    updated = spec_text
    if version_changed:
        updated = replace_field(updated, r"^(Version:\s*)\S+", upstream["version"])
    if cmake_version_changed:
        updated = replace_field(
            updated,
            r"^(%global upstream_version\s+)\S+",
            upstream["cmake_version"],
        )
    if commit_changed:
        updated = replace_field(updated, r"^(%global commit\s+)\S+", upstream["commit"])
    if sha_changed:
        updated = replace_field(updated, r"^(# Source0 SHA256:\s*)\S+", upstream["sha256"])
    new_state = {
        "schema": 1,
        "upstream": {
            "tag": upstream["tag"],
            "version": upstream["version"],
            "cmake_version": upstream["cmake_version"],
            "commit": upstream["commit"],
            "source_sha256": upstream["sha256"],
            "snapshot": upstream["snapshot"],
        },
        "kde": kde,
    }
    state_text = json.dumps(new_state, indent=2, sort_keys=True) + "\n"

    spec_changed = updated != spec_text
    state_changed = not STATE.exists() or STATE.read_text(encoding="utf-8") != state_text

    if spec_changed or state_changed:
        changes = []
        if version_changed:
            kind = "snapshot" if upstream["snapshot"] else "tag"
            changes.append(f"upstream {kind} {upstream['version']}")
        if kde_changed:
            changes.append("KDE update")
        if not changes:
            changes.append("state update")
        summary = ", ".join(changes)
    else:
        summary = f"up to date ({upstream['tag']})"

    log(f"Spec: {summary}")
    log(f"KDE versions: {json.dumps(kde, sort_keys=True)}")

    if args.update:
        if spec_changed:
            SPEC.write_text(updated, encoding="utf-8")
        if state_changed:
            STATE.parent.mkdir(parents=True, exist_ok=True)
            STATE.write_text(state_text, encoding="utf-8")

    write_github_output(
        changed=str(spec_changed or state_changed).lower(),
        rebuild=str(
            version_changed
            or cmake_version_changed
            or commit_changed
            or sha_changed
            or kde_changed
        ).lower(),
        summary=summary,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, RuntimeError, json.JSONDecodeError, KeyError) as error:
        log(f"error: {error}")
        raise SystemExit(1)
