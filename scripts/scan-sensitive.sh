#!/usr/bin/env bash
# Mechanical desensitization gate.
#
# Usage: ./scripts/scan-sensitive.sh [path]
# Exit code 0 = clean, 1 = findings (do NOT publish until resolved).
#
# This checks *text* only. It cannot prove the repo is safe — it catches the
# obvious mistakes (company names, internal task ids, corp mail domains) so a
# human review can focus on judgement calls.

set -uo pipefail

ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT" || exit 2

fail=0

# --- what counts as "sensitive" is configuration, not part of the repo -----
# Hard-coding a real employer name / mail domain here would leak the very thing
# this gate is looking for, so the defaults are generic placeholders. Point the
# variables at your own values when you run it locally:
#
#   CORP_PATTERNS='acme|acme-corp' CORP_EMAIL_DOMAINS='acme.com' \
#     INTERNAL_ID_PATTERN='\bACME-[0-9]{2,}\b' ./scripts/scan-sensitive.sh
CORP_PATTERNS="${CORP_PATTERNS:-内部代号|保密|confidential|proprietary}"
CORP_EMAIL_DOMAINS="${CORP_EMAIL_DOMAINS:-corp.example.com}"
# 注意：这里不用 "${VAR:-默认值}" 写法——默认值里的 {3,} 会让 bash 提前收尾。
if [ -z "${INTERNAL_ID_PATTERN:-}" ]; then
  INTERNAL_ID_PATTERN='\bPROJ-[0-9]{3,}\b'
fi
CORP_DOMAIN_RE="$(printf '%s' "$CORP_EMAIL_DOMAINS" | tr ',' '|')"

report() {
  # $1 = label, $2 = pattern
  local label="$1" pattern="$2" hits
  hits=$(git grep -nIE "$pattern" -- \
      ':!*.lock' ':!scripts/scan-sensitive.sh' ':!scripts/configure.sh' ':!docs/DESENSITIZE.md' 2>/dev/null \
    || grep -rnIE "$pattern" . \
      --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv \
      --exclude=scan-sensitive.sh --exclude=configure.sh --exclude=DESENSITIZE.md 2>/dev/null)
  if [ -n "$hits" ]; then
    printf '\n[FAIL] %s\n%s\n' "$label" "$hits"
    fail=1
  else
    printf '[ ok ] %s\n' "$label"
  fi
}

# 1. Employer / organisation names
report "employer or org names" \
  "$CORP_PATTERNS"

# 2. Internal task / ticket ids
report "internal task ids" \
  "$INTERNAL_ID_PATTERN"

# 3. Corporate mail domains
report "corporate email domains" \
  "@(${CORP_DOMAIN_RE})\\b"

# 4. Secrets and credentials
report "possible secrets" \
  '(api[_-]?key|secret|passwd|password|token)\s*[:=]\s*["'"'"'][A-Za-z0-9_\-]{16,}'

# 5. Absolute local paths leaking a machine or user name
report "absolute local paths" \
  '/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|C:\\\\Users\\\\'

# 6. Commit identity check (needs a git history)
if git rev-parse --git-dir >/dev/null 2>&1; then
  ids=$(git log --format='%an <%ae>' 2>/dev/null | sort -u)
  if printf '%s' "$ids" | grep -qiE "@(${CORP_DOMAIN_RE})\\b"; then
    printf '\n[FAIL] commit authors use a corporate email:\n%s\n' "$ids"
    fail=1
  else
    printf '[ ok ] commit authors\n'
  fi
else
  printf '[skip] commit authors (not a git repository yet)\n'
fi

if [ "$fail" -ne 0 ]; then
  printf '\n=> findings above must be resolved before publishing.\n'
  exit 1
fi
printf '\n=> clean.\n'
