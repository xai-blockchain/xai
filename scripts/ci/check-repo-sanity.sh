#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

SIZE_LIMIT_MB="${SIZE_LIMIT_MB:-10}"
SKIP_SIZE_CHECK="${SKIP_SIZE_CHECK:-}"

check_globs() {
  local label="$1"
  shift
  local -a patterns=("$@")
  local -a matches=()

  while IFS= read -r -d '' file; do
    local lower="${file,,}"
    for pattern in "${patterns[@]}"; do
      if [[ "$lower" == $pattern ]]; then
        matches+=("$file")
        break
      fi
    done
  done < <(git ls-files -z)

  if (( ${#matches[@]} )); then
    echo "ERROR: tracked ${label} files detected:"
    printf '  %s\n' "${matches[@]}"
    return 1
  fi

  return 0
}

check_env_files() {
  local -a matches=()

  while IFS= read -r -d '' file; do
    if [[ "$file" == ".env" || "$file" == .env.* ]]; then
      case "$file" in
        .env.example|.env.template)
          ;;
        *)
          matches+=("$file")
          ;;
      esac
    fi
  done < <(git ls-files -z)

  if (( ${#matches[@]} )); then
    echo "ERROR: tracked environment files detected:"
    printf '  %s\n' "${matches[@]}"
    return 1
  fi

  return 0
}

check_size() {
  if [[ -n "$SKIP_SIZE_CHECK" ]]; then
    echo "SKIP_SIZE_CHECK set; skipping size check."
    return 0
  fi

  local limit_bytes=$((SIZE_LIMIT_MB * 1024 * 1024))
  local -a matches=()

  while IFS= read -r -d '' file; do
    local size
    size=$(stat -c %s "$file" 2>/dev/null || stat -f %z "$file")
    if (( size > limit_bytes )); then
      matches+=("$file ($size bytes)")
    fi
  done < <(git ls-files -z)

  if (( ${#matches[@]} )); then
    echo "ERROR: tracked files exceed ${SIZE_LIMIT_MB}MB:"
    printf '  %s\n' "${matches[@]}"
    return 1
  fi

  return 0
}

fail=0

if ! check_globs "binary" \
  "*.exe" "*.dll" "*.so" "*.dylib" "*.a" "*.o" "*.bin" "*.test" \
  "*.apk" "*.ipa" "*.aab" "*.deb" "*.rpm" "*.appimage"; then
  fail=1
fi

if ! check_globs "secret" \
  "*.pem" "*.key" "*.p12" "*.pfx" "*.keystore" "*.jks" "*.mnemonic"; then
  fail=1
fi

if ! check_env_files; then
  fail=1
fi

if ! check_size; then
  fail=1
fi

if (( fail )); then
  echo "Repo sanity checks failed."
  exit 1
fi

echo "Repo sanity checks passed."
