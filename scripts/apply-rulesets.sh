#!/usr/bin/env bash
# Apply the standard rulesets to one repository (ecosystem 3.1 and 6.5). Idempotent: a ruleset with
# the same name is updated in place, a missing one is created, others are left alone.
#
#   scripts/apply-rulesets.sh --repo gonzalomartinperez/portfolio --flow release            # dry run
#   scripts/apply-rulesets.sh --repo gonzalomartinperez/portfolio --flow release --apply    # write
#   scripts/apply-rulesets.sh --repo gonzalomartinperez/vps-ops --flow main-only --check    # drift report
#
# Flows: release (develop + main + v* tags), main-only (main + v* tags).
# Options: --merge-methods merge|squash|rebase (comma list; default merge; pequeverso-marketing: squash)
#          --rulesets-dir DIR (default: the rulesets/ next to this script)
# Only the keys present in rulesets/*.json are compared; server-side extras do not count as drift.
# Exit codes: 0 ok (or dry run), 1 drift in --check mode or a failed write, 2 usage error,
#             3 rulesets unavailable (HTTP 403: private repository of a personal account without a
#             paid plan; fall back to the five-layer main-only enforcement, ecosystem 3.1).
# Requires gh authenticated as the repository owner (admin) and jq.
set -euo pipefail

repo="" flow="" mode="dry-run" merge_methods="merge"
rules_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../rulesets" && pwd)"

usage() { sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-2}"; }
need_value() { [ "$#" -ge 2 ] && [ -n "$2" ] || { echo "$1 needs a value" >&2; usage 2; }; }

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) need_value "$@"; repo="$2"; shift 2 ;;
    --flow) need_value "$@"; flow="$2"; shift 2 ;;
    --merge-methods) need_value "$@"; merge_methods="$2"; shift 2 ;;
    --rulesets-dir) need_value "$@"; rules_dir="$2"; shift 2 ;;
    --apply) mode="apply"; shift ;;
    --check) mode="check"; shift ;;
    -h|--help) usage 0 ;;
    *) echo "unknown argument: $1" >&2; usage 2 ;;
  esac
done

[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { echo "--repo owner/name is required" >&2; usage 2; }
case "$flow" in
  release) files=(release-develop.json release-main.json tags.json) ;;
  main-only) files=(main-only.json tags.json) ;;
  *) echo "--flow must be release or main-only" >&2; usage 2 ;;
esac
[[ "$merge_methods" =~ ^(merge|squash|rebase)(,(merge|squash|rebase))*$ ]] || { echo "invalid --merge-methods" >&2; exit 2; }

err="$(mktemp)"
trap 'rm -f "$err"' EXIT

methods_json=$(jq -cn --arg m "$merge_methods" '$m | split(",")')

render() {  # ruleset file -> final JSON with the merge methods applied
  jq --argjson methods "$methods_json" '
    .rules |= map(if .type == "pull_request" then .parameters.allowed_merge_methods = $methods else . end)
  ' "$rules_dir/$1"
}

# Project a ruleset onto the keys the desired ruleset manages, in a stable order.
project() {  # $1 = desired JSON; stdin = any ruleset JSON
  jq -S --argjson want "$1" '
    def keep($w): if ($w | type) == "object" and (type == "object")
                  then with_entries(.key as $k | select($w | has($k)) | .value |= keep($w[$k]))
                  else . end;
    {name, target, enforcement, bypass_actors: (.bypass_actors // []), conditions,
     rules: [ .rules[] as $r
              | ($want.rules[] | select(.type == $r.type)) as $wr
              | $r | keep($wr) ] | sort_by(.type)}'
}

is_forbidden() { grep -Eq 'HTTP 403|\(403\)' "$err"; }

if ! existing=$(gh api "repos/$repo/rulesets?includes_parents=false&per_page=100" 2>"$err"); then
  if is_forbidden; then
    echo "rulesets unavailable for $repo (HTTP 403)" >&2
    exit 3
  fi
  cat "$err" >&2
  exit 1
fi

drift=0 rc=0
for f in "${files[@]}"; do
  desired=$(render "$f")
  name=$(jq -r .name <<<"$desired")
  want=$(project "$desired" <<<"$desired")
  id=$(jq -r --arg n "$name" '.[] | select(.name == $n and .source_type == "Repository") | .id' <<<"$existing" | head -n 1)
  if [ -n "$id" ]; then
    if ! current_raw=$(gh api "repos/$repo/rulesets/$id" 2>"$err"); then
      cat "$err" >&2; rc=1; continue
    fi
    current=$(project "$desired" <<<"$current_raw")
    if [ "$current" = "$want" ]; then
      echo "ok       $name (id $id) is up to date"
      continue
    fi
    drift=1
    if [ "$mode" = "apply" ]; then
      if gh api -X PUT "repos/$repo/rulesets/$id" --input - <<<"$desired" >/dev/null 2>"$err"; then
        echo "updated  $name (id $id)"
      else
        echo "FAILED   $name (id $id): $(cat "$err")" >&2
        if is_forbidden; then rc=3; else rc=1; fi
      fi
    else
      echo "differs  $name (id $id)"
      diff <(jq . <<<"$current") <(jq . <<<"$want") || true
    fi
  else
    drift=1
    if [ "$mode" = "apply" ]; then
      if new_id=$(gh api -X POST "repos/$repo/rulesets" --input - --jq .id <<<"$desired" 2>"$err"); then
        echo "created  $name (id $new_id)"
      else
        echo "FAILED   $name: $(cat "$err")" >&2
        if is_forbidden; then rc=3; else rc=1; fi
      fi
    else
      echo "missing  $name (would be created)"
    fi
  fi
done

if [ "$mode" = "dry-run" ] && [ "$drift" -eq 1 ]; then
  echo "dry run: nothing written; re-run with --apply"
fi
if [ "$mode" = "check" ] && [ "$drift" -eq 1 ] && [ "$rc" -eq 0 ]; then
  rc=1
fi
exit "$rc"
