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
# Requires gh authenticated as the repository owner. Rulesets on private repositories of a personal
# account need a paid plan; the script reports HTTP 403 and exits 3 so the caller can fall back to the
# five-layer main-only enforcement (ecosystem 3.1).
set -euo pipefail

repo="" flow="" mode="dry-run" merge_methods="merge"
rules_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../rulesets" && pwd)"

usage() { sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) repo="${2:-}"; shift 2 ;;
    --flow) flow="${2:-}"; shift 2 ;;
    --apply) mode="apply"; shift ;;
    --check) mode="check"; shift ;;
    --merge-methods) merge_methods="${2:-}"; shift 2 ;;
    --rulesets-dir) rules_dir="${2:-}"; shift 2 ;;
    -h|--help) usage 0 ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { echo "--repo owner/name is required" >&2; usage; }
case "$flow" in
  release) files=(release-develop.json release-main.json tags.json) ;;
  main-only) files=(main-only.json tags.json) ;;
  *) echo "--flow must be release or main-only" >&2; usage ;;
esac
[[ "$merge_methods" =~ ^(merge|squash|rebase)(,(merge|squash|rebase))*$ ]] || { echo "invalid --merge-methods" >&2; exit 2; }

methods_json=$(jq -cn --arg m "$merge_methods" '$m | split(",")')

render() {  # ruleset file -> final JSON with the merge methods applied
  jq --argjson methods "$methods_json" '
    .rules |= map(if .type == "pull_request" then .parameters.allowed_merge_methods = $methods else . end)
  ' "$rules_dir/$1"
}

normalize() {  # fields we manage, stable order; server-added defaults are dropped before comparing
  jq -S '{name, target, enforcement, bypass_actors: (.bypass_actors // []),
          conditions, rules: (.rules | sort_by(.type) | map(del(.parameters.required_reviewers?, .parameters.require_extra_approval_for_unattributed_changes?)))}'
}

if ! existing=$(gh api "repos/$repo/rulesets?includes_parents=false&per_page=100" 2>/tmp/apply-rulesets.err); then
  if grep -q "403" /tmp/apply-rulesets.err; then
    echo "rulesets unavailable for $repo (HTTP 403: private repository on a plan without rulesets)" >&2
    exit 3
  fi
  cat /tmp/apply-rulesets.err >&2
  exit 1
fi

drift=0
for f in "${files[@]}"; do
  desired=$(render "$f")
  name=$(jq -r .name <<<"$desired")
  id=$(jq -r --arg n "$name" '.[] | select(.name == $n and .source_type == "Repository") | .id' <<<"$existing" | head -n 1)
  if [ -n "$id" ]; then
    current=$(gh api "repos/$repo/rulesets/$id" | normalize)
    if [ "$current" = "$(normalize <<<"$desired")" ]; then
      echo "ok       $name (id $id) is up to date"
      continue
    fi
    drift=1
    case "$mode" in
      apply) gh api -X PUT "repos/$repo/rulesets/$id" --input - <<<"$desired" >/dev/null && echo "updated  $name (id $id)" ;;
      *) echo "differs  $name (id $id)"; diff <(echo "$current" | jq .) <(normalize <<<"$desired" | jq .) || true ;;
    esac
  else
    drift=1
    case "$mode" in
      apply) new_id=$(gh api -X POST "repos/$repo/rulesets" --input - <<<"$desired" --jq .id) && echo "created  $name (id $new_id)" ;;
      *) echo "missing  $name (would be created)" ;;
    esac
  fi
done

if [ "$mode" = "dry-run" ] && [ "$drift" -eq 1 ]; then
  echo "dry run: nothing written; re-run with --apply"
fi
if [ "$mode" = "check" ] && [ "$drift" -eq 1 ]; then
  exit 1
fi
exit 0
