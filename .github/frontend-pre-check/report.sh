#!/usr/bin/env bash
# Publishes the pre-check on the pull request: the one "Pre-check" comment
# (found again by its hidden marker), the inline comments, the label and the
# exit status of the required job. Bash because this part is GitHub I/O only;
# every decision comes from review/evaluate.py, the presentation from
# review/render.py, the outcome states, labels and exit codes from
# contracts.py. Nothing the reviewer wrote is echoed into workflow commands or
# logs.
#
# The exit status is the contract of the required check:
# `contracts.py passes OUTCOME` - 0 only for clean, advisory and queued.
#
# Usage: report.sh publish | start | notchecked | queue | report | error
#   publish     the review job: dispatches to one of the modes below
#   start       create the labels if missing and take them off before a review
#   notchecked  outcome "skipped" (SKIP_REASON): labels off, the comment says
#               so, exit 1
#   queue       merge_group: outcome "queued" if every pull request in the entry
#               passed this check on its current head (MERGE_HEAD_REF,
#               CHECK_RUN_ID), otherwise "human"
#   report      evaluate, render and publish RESULT_FILE with SCOPE_FILE
#   error       outcome "invalid" (REASON is a fixed code), exit 1
#
# Environment: REPO, PR_NUMBER, HEAD_SHA, BASE_SHA, GH_TOKEN, RUN_URL, MODEL,
# STANDARDS_SHA, RESULT_FILE, SCOPE_FILE, COVERAGE, USAGE_JSON, TOOLS_USED,
# REASON, SKIP_REASON, MERGE_HEAD_REF, CHECK_RUN_ID.
set -euo pipefail

: "${REPO:?}"
MODE="${1:?usage: report.sh publish|start|notchecked|queue|report|error}"
HERE=$(cd "$(dirname "$0")" && pwd)
CONTRACTS="$HERE/contracts.py"
MARKER="<!-- gi-pre-check -->"

finish() { # outcome: exit with the status the contract gives it
  if python3 "$CONTRACTS" passes "$1"; then exit 0; fi
  exit 1
}

remove_labels() {
  local label encoded
  while IFS=$'\t' read -r label _ _; do
    encoded=$(jq -rn --arg label "$label" '$label | @uri')
    gh api -X DELETE "repos/$REPO/issues/$PR_NUMBER/labels/$encoded" > /dev/null 2>&1 || true
  done < <(python3 "$CONTRACTS" labels)
}

set_label() { # outcome
  local label
  label=$(python3 "$CONTRACTS" label "$1")
  [ -z "$label" ] || gh api "repos/$REPO/issues/$PR_NUMBER/labels" -f "labels[]=$label" > /dev/null || true
}

comment_id() {
  gh api --paginate "repos/$REPO/issues/$PR_NUMBER/comments?per_page=100" \
    --jq ".[] | select(.user.login == \"github-actions[bot]\" and (.body | startswith(\"$MARKER\"))) | .id" | sed -n 1p
}

# The freshness guard, called right before every write: the run publishes
# only while the pull request is still at the head (and base) it reviewed.
# A moved head ends quietly (the newer run publishes); a moved base returns 1.
# If the pull request cannot be read, nothing more is published and the run
# fails.
guard() {
  local current base
  if ! current=$(gh api "repos/$REPO/pulls/$PR_NUMBER" --jq '"\(.head.sha) \(.base.sha)"'); then
    echo "::error title=Pre-check::Could not read the pull request; nothing more is published."
    exit 1
  fi
  base=${current#* }
  current=${current% *}
  if [ "$current" != "$HEAD_SHA" ]; then
    echo "The pull request moved on from ${HEAD_SHA:0:7} to ${current:0:7}; nothing more is published by this run."
    exit 0
  fi
  [ -z "${BASE_SHA:-}" ] || [ "$base" = "$BASE_SHA" ]
}

upsert_comment() {
  local file="$1" id
  id=$(comment_id) || id=""
  if [ -n "$id" ]; then
    gh api -X PATCH "repos/$REPO/issues/comments/$id" -F body=@"$file" > /dev/null
    echo "Updated the Pre-check comment."
  else
    gh api "repos/$REPO/issues/$PR_NUMBER/comments" -F body=@"$file" > /dev/null
    echo "Created the Pre-check comment."
  fi
}

note_comment() {
  local body
  body=$(mktemp)
  printf '%s\n## Pre-check\n\n%s\n' "$MARKER" "$1" > "$body"
  upsert_comment "$body"
}

case "$MODE" in
publish)
  # The review job: dispatch on how the gate and the analysis ended
  # (GATE, VERDICT, GATE_REASON, ANALYSE, ABORT, RESULT_JSON, SCOPE_JSON).
  if [ "${GATE:-}" = cancelled ]; then
    echo "The gate was superseded by a newer run. Nothing is published."
    exit 1
  fi
  if [ "${GATE:-}" != success ]; then
    if [ -n "${PR_NUMBER:-}" ]; then REASON=gate exec bash "$0" error; fi
    exit 1
  fi
  case "${VERDICT:-}" in
    queue) exec bash "$0" queue ;;
    skip | block) SKIP_REASON="${GATE_REASON:-}" exec bash "$0" notchecked ;;
    run) ;;
    *) echo "Unknown verdict."; exit 1 ;;
  esac
  if [ "${ANALYSE:-}" = cancelled ]; then
    echo "The review was superseded by a newer run. Nothing is published."
    exit 1
  fi
  if [ "${ANALYSE:-}" != success ] || [ -z "${RESULT_JSON:-}" ] || [ -z "${SCOPE_JSON:-}" ]; then
    REASON="${ABORT:-failed}" exec bash "$0" error
  fi
  work=$(mktemp -d)
  printf '%s' "$RESULT_JSON" > "$work/result.json"
  printf '%s' "$SCOPE_JSON" > "$work/scope.json"
  RESULT_FILE="$work/result.json" SCOPE_FILE="$work/scope.json" exec bash "$0" report
  ;;
start)
  : "${PR_NUMBER:?}" "${HEAD_SHA:?}"
  guard || true
  while IFS=$'\t' read -r label colour description; do
    gh api "repos/$REPO/labels" -f name="$label" -f color="$colour" -f description="$description" > /dev/null 2>&1 || true
  done < <(python3 "$CONTRACTS" labels)
  remove_labels
  exit 0
  ;;
notchecked)
  : "${PR_NUMBER:?}" "${HEAD_SHA:?}"
  guard || true
  remove_labels
  guard || true
  note_comment "**Result:** not pre-checked for commit \`${HEAD_SHA:0:7}\` - ${SKIP_REASON:-the run was skipped.} A person reviews this pull request; the \`frontend-pre-check / review\` check fails until a pre-check runs, so merging needs a person with the right to bypass it." \
    || echo "::warning::Could not update the Pre-check comment."
  echo "::error title=Pre-check::Not pre-checked. See the Pre-check comment on the pull request."
  finish skipped
  ;;
queue)
  : "${MERGE_HEAD_REF:?}" "${CHECK_RUN_ID:?}"
  # The name of this very check, e.g. "frontend-pre-check / review".
  name=$(gh api "repos/$REPO/check-runs/$CHECK_RUN_ID" --jq .name)
  mapfile -t prs < <(grep -oE 'pr-[0-9]+-' <<< "$MERGE_HEAD_REF" | grep -oE '[0-9]+' | sort -u)
  if (( ${#prs[@]} == 0 )); then
    echo "::error title=Pre-check::The merge queue entry names no pull request."
    finish human
  fi
  encoded=$(jq -rn --arg name "$name" '$name | @uri')
  for pr in "${prs[@]}"; do
    head=$(gh api "repos/$REPO/pulls/$pr" --jq .head.sha)
    passed=$(gh api "repos/$REPO/commits/$head/check-runs?check_name=$encoded&filter=latest" \
      --jq '[.check_runs[] | select(.app.slug == "github-actions")] | sort_by(.completed_at) | last | .conclusion // "missing"')
    if [ "$passed" != success ]; then
      echo "::error title=Pre-check::Pull request #$pr has no passing pre-check on its head ${head:0:7}."
      finish human
    fi
    echo "Pull request #$pr passed the pre-check on its head ${head:0:7}."
  done
  echo "Every pull request in this merge queue entry passed the pre-check on its head. The merged result itself was not reviewed."
  finish queued
  ;;
error)
  : "${PR_NUMBER:?}" "${HEAD_SHA:?}"
  [ "${REASON:-}" != outdated ] || exit 0
  guard || true
  remove_labels
  case "${REASON:-}" in
    unsafe_names) text="a file name in this pull request contains a control character or a backtick, so nothing was reviewed." ;;
    exclusion_policy) text="the caller's exclude_paths names a pattern outside the exclusion policy." ;;
    invalid) text="the reviewer returned no valid result." ;;
    gate) text="the gate job did not succeed, so nothing was reviewed." ;;
    *) text="the reviewer did not complete (a common cause is the usage limit of the subscription; re-run the job later)." ;;
  esac
  guard || true
  note_comment "**Result:** not finished - $text See the [workflow run]($RUN_URL). Nothing was decided: a person reviews the pull request."
  echo "::error title=Pre-check::The pre-check did not finish."
  finish invalid
  ;;
report) ;;
*)
  echo "Unknown mode" >&2
  exit 2
  ;;
esac

: "${PR_NUMBER:?}" "${HEAD_SHA:?}" "${RESULT_FILE:?}" "${SCOPE_FILE:?}"
BASE_SHA=${BASE_SHA:-$(jq -r '.base // ""' "$SCOPE_FILE" 2> /dev/null || echo "")}
out=$(mktemp -d)
python3 "$HERE/review/evaluate.py" "$RESULT_FILE" "$SCOPE_FILE" "$out/evaluation.json"
outcome=$(jq -r .outcome "$out/evaluation.json")
if [ "$outcome" = invalid ]; then
  REASON=invalid exec bash "$0" error
fi
python3 "$HERE/review/render.py" "$RESULT_FILE" "$SCOPE_FILE" "$out/evaluation.json" "$out"
python3 "$HERE/review/evaluate.py" check-output "$out/evaluation.json" "$out/comment.md" "$out/inline.json"
outcome=$(jq -r .outcome "$out/evaluation.json")
if [ "$(jq -r .withheld "$out/evaluation.json")" = true ]; then
  python3 "$HERE/review/render.py" withheld "$out/evaluation.json" "$out"
fi

if ! guard; then
  remove_labels
  note_comment "**Result:** not current - the base branch moved while commit \`${HEAD_SHA:0:7}\` was being reviewed, so the result is not published. Re-run the job." || true
  echo "::error title=Pre-check::The base branch moved during the review; re-run the job."
  exit 1
fi
remove_labels

# Inline comments are a convenience; every finding is in the Pre-check
# comment. A finding already commented on at the same place, on a line that
# still exists, is not posted again.
existing=$(gh api --paginate "repos/$REPO/pulls/$PR_NUMBER/comments?per_page=100" \
  --jq '.[] | select(.user.login == "github-actions[bot]" and .line != null) | .body' \
  | grep -oE 'gi-pre-check-finding [0-9a-f]{16}' | awk '{print $2}' | sort -u) || existing=""
posted=0 failed=0
attached=()
while IFS= read -r item; do
  [ -n "$item" ] || continue
  fingerprint=$(jq -r '.fingerprint' <<< "$item")
  [[ "$fingerprint" =~ ^[0-9a-f]{16}$ ]] || continue
  if grep -qx "$fingerprint" <<< "$existing"; then
    attached+=("$fingerprint")
    continue
  fi
  guard || break
  if jq -c --arg commit "$HEAD_SHA" '{commit_id: $commit, path, line, side, body}' <<< "$item" \
    | gh api "repos/$REPO/pulls/$PR_NUMBER/comments" --input - > /dev/null 2>&1; then
    posted=$(( posted + 1 ))
    attached+=("$fingerprint")
  else
    failed=$(( failed + 1 ))
  fi
done < <(jq -c '.[]' "$out/inline.json")
echo "Inline comments: $posted posted, $failed could not be attached (every finding is in the Pre-check comment)."
for fingerprint in "${attached[@]}"; do
  sed -i "s/<!-- inline $fingerprint -->/ (also as an inline comment)/" "$out/comment.md"
done
sed -i -E 's/<!-- inline [0-9a-f]{16} -->/ (could not be attached to the diff)/' "$out/comment.md"

guard || { echo "::error title=Pre-check::The base branch moved during publication; re-run the job."; exit 1; }
upsert_comment "$out/comment.md"
guard || { echo "::error title=Pre-check::The base branch moved during publication; re-run the job."; exit 1; }
set_label "$outcome"
# A push between the last guard and the label: take the label off again.
guard || { remove_labels; exit 1; }

# Usage, as far as the run reports it; only numbers, a fixed word and tool names.
if [ -n "${USAGE_JSON:-}" ] && [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  jq -r --arg coverage "${COVERAGE:-none}" --arg tools "${TOOLS_USED:-}" --arg outcome "$outcome" '
    def n: if type == "number" then . else "-" end;
    "### Pre-check usage\n",
    "| Outcome | Turns | Duration (s) | Input tokens | Cache read | Cache write | Output tokens | Permission denials | API-price estimate (USD) | Diff read | Tools available |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    "| \($outcome) | \(.num_turns | n) | \(if (.duration_ms | type) == "number" then (.duration_ms / 1000 | floor) else "-" end) | \(.usage.input_tokens | n) | \(.usage.cache_read_input_tokens | n) | \(.usage.cache_creation_input_tokens | n) | \(.usage.output_tokens | n) | \(.permission_denials_count | n) | \(if (.total_cost_usd | type) == "number" then (.total_cost_usd * 100 | round / 100) else "-" end) | \($coverage) | \($tools) |"
  ' <<< "$USAGE_JSON" >> "$GITHUB_STEP_SUMMARY" 2> /dev/null || true
fi

echo "Pre-check outcome: $outcome."
python3 "$CONTRACTS" passes "$outcome" || echo "::error title=Pre-check::The pre-check did not pass ($outcome). See the Pre-check comment on the pull request."
finish "$outcome"
