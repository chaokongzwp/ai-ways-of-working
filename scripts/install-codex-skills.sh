#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_source="${repo_root}/skills"
skill_target="${CODEX_HOME:-${HOME}/.codex}/skills"
bin_target="${HOME}/.local/bin"

mkdir -p "$skill_target" "$bin_target"

for skill in \
  beex-release-h5 \
  beex-release-ios \
  beex-release-android \
  beex-release-service \
  beex-release-web \
  beex-release-all; do
  source_path="${skill_source}/${skill}"
  [[ -f "${source_path}/SKILL.md" ]] || {
    echo "Missing skill: ${source_path}" >&2
    exit 1
  }
  ln -sfn "$source_path" "${skill_target}/${skill}"
  echo "Installed ${skill_target}/${skill} -> ${source_path}"
done

release_script="${skill_source}/beex-release-all/scripts/beex_release.py"
chmod +x "$release_script"
ln -sfn "$release_script" "${bin_target}/beex-release"
echo "Installed ${bin_target}/beex-release -> ${release_script}"
echo "Ensure ${bin_target} is in PATH."
