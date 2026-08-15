#!/usr/bin/env bash
set -euo pipefail

phase12_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
phase12_repo_root="$(cd "${phase12_script_dir}/.." && pwd)"
phase12_ua_path="${phase12_repo_root}/ref-opensource/Understand-Anything"
phase12_patch_path="${phase12_repo_root}/sidecar/patches/compute-batches-workdir.patch"
phase12_expected_pin="73559a160645359c57be44c174935899dec9f9f2"

git -C "${phase12_repo_root}" submodule update --init --recursive -- ref-opensource/Understand-Anything

phase12_actual_pin="$(git -C "${phase12_ua_path}" rev-parse HEAD)"
if [[ "${phase12_actual_pin}" != "${phase12_expected_pin}" ]]; then
  printf 'UA pin mismatch: expected %s, got %s\n' "${phase12_expected_pin}" "${phase12_actual_pin}" >&2
  exit 1
fi

if git -C "${phase12_ua_path}" apply --unidiff-zero --reverse --check "${phase12_patch_path}" >/dev/null 2>&1; then
  printf 'UA work-dir patch already applied\n'
elif git -C "${phase12_ua_path}" apply --unidiff-zero --check "${phase12_patch_path}" >/dev/null 2>&1; then
  git -C "${phase12_ua_path}" apply --unidiff-zero "${phase12_patch_path}"
  printf 'UA work-dir patch applied\n'
else
  printf 'UA work-dir patch does not match pinned source\n' >&2
  exit 1
fi

(
  cd "${phase12_ua_path}"
  corepack pnpm install --frozen-lockfile
  corepack pnpm --filter @understand-anything/core build
)

phase12_core_dist="${phase12_ua_path}/understand-anything-plugin/packages/core/dist/index.js"
if [[ ! -s "${phase12_core_dist}" ]]; then
  printf 'UA core build output missing: %s\n' "${phase12_core_dist}" >&2
  exit 1
fi

printf 'UA sidecar ready at pin %s\n' "${phase12_actual_pin}"
