#!/usr/bin/env bash
# Fill in the publishing placeholders in one shot.
#
#   ./scripts/configure.sh --user octocat --email me@example.com --name "Octo Cat"
#
# --user is required (it replaces YOUR_GITHUB_USER and <your-handle>).
# --email / --name are optional: when given and this directory is a git repo,
# they are also written to the LOCAL git config, which is what keeps your
# commits from carrying a corporate address.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

USER_HANDLE=""
EMAIL=""
NAME=""

while [ $# -gt 0 ]; do
  case "$1" in
    --user)  USER_HANDLE="${2:-}"; shift 2 ;;
    --email) EMAIL="${2:-}"; shift 2 ;;
    --name)  NAME="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$USER_HANDLE" ]; then
  echo "error: --user <github-handle> is required" >&2
  exit 2
fi

# Refuse corporate mailboxes. The domain list comes from the environment on
# purpose: hard-coding a real employer domain here would publish the employer.
#   CORP_EMAIL_DOMAINS="example.com,example.org" ./scripts/configure.sh ...
CORP_EMAIL_DOMAINS="${CORP_EMAIL_DOMAINS:-corp.example.com}"
if [ -n "$EMAIL" ]; then
  IFS=',' read -r -a _corp <<< "$CORP_EMAIL_DOMAINS"
  for _d in "${_corp[@]}"; do
    [ -z "$_d" ] && continue
    case "$EMAIL" in
      *@"$_d"|*"$_d")
        echo "error: refusing corporate email '$EMAIL' (matched '$_d') for a personal repository" >&2
        exit 2 ;;
    esac
  done
fi

# Replace the handle in README, publish docs and pyproject.
for f in README.md docs/PUBLISH.md pyproject.toml; do
  [ -f "$f" ] || continue
  sed -i.bak "s/YOUR_GITHUB_USER/${USER_HANDLE}/g; s|<your-handle>|${USER_HANDLE}|g" "$f"
  rm -f "$f.bak"
done

echo "handle  -> ${USER_HANDLE}"
grep -rn "github.com/${USER_HANDLE}" README.md pyproject.toml docs/PUBLISH.md | head -5 || true

if [ -n "$EMAIL" ] || [ -n "$NAME" ]; then
  if git rev-parse --git-dir >/dev/null 2>&1; then
    if [ -n "$NAME" ]; then git config user.name "$NAME"; fi
    if [ -n "$EMAIL" ]; then git config user.email "$EMAIL"; fi
    echo "git identity (local) -> $(git config user.name) <$(git config user.email)>"
  else
    echo "note: not a git repository yet; run 'git init' then re-run with --email/--name"
  fi
fi

echo "done. next: ./scripts/scan-sensitive.sh && git init -b main"
