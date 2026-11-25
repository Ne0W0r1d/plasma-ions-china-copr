#!/usr/bin/env bash
set -euo pipefail

here=$(dirname "$(realpath "$0")")
project=${1:-${COPR_PROJECT:-}}

if [[ -z "$project" ]]; then
    echo "usage: $0 <owner/project>" >&2
    exit 2
fi

chroots=()
while IFS= read -r chroot; do
    case "$chroot" in
        ''|'#'*) continue ;;
    esac
    chroots+=(--chroot "$chroot")
done < "$here/chroots.txt"

description="Plasma weather ions for Chinese users (COPR packaging of arenekosreal/plasma-ions-china)"
instructions="Install with: sudo dnf copr enable ${project}"

if copr-cli get "$project" >/dev/null 2>&1; then
    echo "Updating chroots for ${project}..." >&2
    # Only touch the chroot list here. Description and instructions are owned
    # by the project maintainer and must not be overwritten on every CI run.
    copr-cli modify "$project" "${chroots[@]}" >&2
else
    echo "Creating ${project}..." >&2
    copr-cli create "$project" "${chroots[@]}" \
        --description "$description" \
        --instructions "$instructions" \
        --enable-net off >&2
fi

copr-cli get "$project" | sed -n '/^Chroots:/,/^[A-Z]/p' >&2
