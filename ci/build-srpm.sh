#!/usr/bin/env bash
set -euo pipefail

spec=${1:-plasma-ions-china.spec}
outdir=${2:-$PWD}

spec=$(realpath "$spec")
mkdir -p "$outdir"
outdir=$(realpath "$outdir")
spec_name=$(basename "$spec")

plasma_version=${PLASMA_VERSION:-}
if [[ -z "$plasma_version" ]] && command -v rpm >/dev/null 2>&1; then
    for package in plasma-workspace plasma6-workspace kdeplasma-addons; do
        if value=$(rpm -q --qf '%{VERSION}' "$package" 2>/dev/null); then
            plasma_version=$value
            break
        fi
    done
fi
plasma_version=$(printf '%s' "${plasma_version:-0.0.0}" |
    grep -oE '^[0-9]+(\.[0-9]+)*' | head -n 1 || true)
plasma_version=${plasma_version:-0.0.0}
echo "Building source RPM for Plasma ${plasma_version}..." >&2

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

mkdir -p "$workdir/build" "$workdir/buildroot"
cp "$spec" "$workdir/$spec_name"
# COPR rebuilds the SRPM in the target chroot and re-expands the spec there.
# A command-line macro would not survive that step, so bake the Plasma version
# into the temporary spec instead. %{?dist} is intentionally left unexpanded so
# the target chroot supplies its own dist tag.
if ! grep -q '^Release:' "$workdir/$spec_name"; then
    echo "error: spec has no Release tag" >&2
    exit 1
fi
sed -i "s|^Release:.*|Release:        ${plasma_version}%{?dist}|" "$workdir/$spec_name"

echo "Downloading sources..." >&2
if command -v spectool >/dev/null 2>&1; then
    downloaded=
    for attempt in 1 2 3; do
        if spectool -g -C "$workdir" "$workdir/$spec_name" >&2; then
            downloaded=1
            break
        fi
        find "$workdir" -maxdepth 1 -name '*.tar.gz' -delete
        sleep $((attempt * 2))
    done
    if [[ -z "$downloaded" ]]; then
        echo "error: could not download Source0" >&2
        exit 1
    fi
else
    source_line=$(rpmspec -P "$spec" | sed -n 's/^Source0:[[:space:]]*//p' | head -n 1)
    if [[ -z "$source_line" ]]; then
        echo "error: Source0 is not defined" >&2
        exit 1
    fi
    url=${source_line%%#*}
    source_name=${source_line##*#/}
    if [[ "$source_name" == "$source_line" ]]; then
        source_name=${url##*/}
    fi
    curl --fail --silent --show-error --location \
        --retry 5 --retry-delay 2 --retry-all-errors \
        --output "$workdir/$source_name" "$url"
fi

expected=$(sed -n 's/^# Source0 SHA256:[[:space:]]*//p' "$spec" | head -n 1)
if [[ -n "$expected" ]]; then
    tarball=$(find "$workdir" -maxdepth 1 -name '*.tar.gz' -print -quit)
    if [[ -z "$tarball" ]]; then
        echo "error: Source0 tarball was not downloaded" >&2
        exit 1
    fi
    actual=$(sha256sum "$tarball" | cut -d ' ' -f 1)
    if [[ "$actual" != "$expected" ]]; then
        echo "error: checksum mismatch for $(basename "$tarball")" >&2
        echo "  expected: $expected" >&2
        echo "  actual:   $actual" >&2
        exit 1
    fi
fi

rpmbuild -bs "$workdir/$spec_name" \
    --define "_sourcedir $workdir" \
    --define "_builddir $workdir/build" \
    --define "_buildrootdir $workdir/buildroot" \
    --define "_srcrpmdir $outdir" >&2

srpm=$(find "$outdir" -maxdepth 1 -name '*.src.rpm' -printf '%T@ %p\n' |
    sort -n | tail -n 1 | cut -d ' ' -f 2-)
if [[ -z "$srpm" ]]; then
    echo "error: rpmbuild did not produce a source RPM in $outdir" >&2
    exit 1
fi
printf '%s\n' "$srpm"
