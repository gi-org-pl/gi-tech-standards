#!/usr/bin/env bash
# Publishes the pre-check on the pull request: the one "Pre-check" comment
# (found again by its hidden marker), the inline comments, the label and the
# exit status of the required job. The reviewer cannot post anything itself;
# render.py turns its structured result into escaped text first. Nothing the
# reviewer wrote is echoed into workflow commands or logs.
#
# The exit status is the contract of the required check: 0 only for
# "clean" and "advisory", and for a merge-queue entry whose pull request
# passed on the same head; 1 for everything else, skips included.
#
# Usage: report.sh start | notchecked | queue | report | error
#   start       create the labels if missing and take them off before a review
#   notchecked  the commit is not pre-checked (SKIP_REASON): labels off, the
#               comment says so, exit 1
#   queue       merge_group: pass if every pull request in the entry passed
#               this check on its current head (MERGE_HEAD_REF, CHECK_RUN_ID)
#   report      publish RESULT_FILE with SCOPE_FILE
#   error       the pre-check did not finish (REASON is a fixed code), exit 1
#
# Environment: REPO, PR_NUMBER, HEAD_SHA, BASE_SHA, GH_TOKEN, RUN_URL, MODEL,
# STANDARDS_SHA, RESULT_FILE, SCOPE_FILE, COVERAGE, USAGE_JSON, TOOLS_USED,
# REASON, SKIP_REASON, MERGE_HEAD_REF, CHECK_RUN_ID.
set -euo pipefail

: "${REPO:?}"
MODE="${1:?usage: report.sh start|notchecked|queue|report|error}"
HERE=$(cd "$(dirname "$0")" && pwd)
MARKER="<!-- gi-pre-check -->"
LABEL_CLEAN="pre-check: clean"
LABEL_ADVISORY="pre-check: advisory"
LABEL_CHANGES="pre-check: changes"
LABEL_HUMAN="pre-check: human review"

ensure_label() {
  gh api "repos/$REPO/labels" -f name="$1" -f color="$2" -f description="$3" > /dev/null 2>&1 || true
}

remove_label() {
  local encoded
  encoded=$(jq -rn --arg label "$1" '$label | @uri')
  gh api -X DELETE "repos/$REPO/issues/$PR_NUMBER/labels/$encoded" > /dev/null 2>&1 || true
}

remove_labels() {
  local label
  for label in "$LABEL_CLEAN" "$LABEL_ADVISORY" "$LABEL_CHANGES" "$LABEL_HUMAN"; do
    remove_label "$label"
  done
}

comment_id() {
  gh api --paginate "repos/$REPO/issues/$PR_NUMBER/comments?per_page=100" \
    --jq ".[] | select(.user.login == \"github-actions[bot]\" and (.body | startswith(\"$MARKER\"))) | .id" | sed -n 1p
}

# The freshness guard, called right before every write: the run publishes
# only while the pull request is still at the head (and base) it reviewed.
# A moved head ends quietly (the newer run publishes); a moved base fails.
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
  if [ -n "${BASE_SHA:-}" ] && [ "$base" != "$BASE_SHA" ]; then
    return 1
  fi
  return 0
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
  {
    echo "$MARKER"
    echo "## Pre-check"
    echo
    echo "$1"
  } > "$body"
  upsert_comment "$body"
}

case "$MODE" in
start)
  : "${PR_NUMBER:?}" "${HEAD_SHA:?}"
  guard || true
  ensure_label "$LABEL_CLEAN" "0e8a16" "AI pre-check reported no findings; not an approval"
  ensure_label "$LABEL_ADVISORY" "c2e0c6" "AI pre-check passed with advisory findings; not an approval"
  ensure_label "$LABEL_CHANGES" "d93f0b" "AI pre-check found something to fix"
  ensure_label "$LABEL_HUMAN" "fbca04" "AI pre-check cannot judge this pull request; a person reviews it"
  remove_labels
  exit 0
  ;;
notchecked)
  : "${PR_NUMBER:?}" "${HEAD_SHA:?}"
  if guard; then :; fi
  remove_labels
  guard || true
  note_comment "**Result:** not pre-checked for commit \`${HEAD_SHA:0:7}\` - ${SKIP_REASON:-the run was skipped.} A person reviews this pull request; the \`frontend-pre-check / review\` check fails until a pre-check runs, so merging needs a person with the right to bypass it." \
    || echo "::warning::Could not update the Pre-check comment."
  echo "::error title=Pre-check::Not pre-checked. See the Pre-check comment on the pull request."
  exit 1
  ;;
queue)
  : "${MERGE_HEAD_REF:?}" "${CHECK_RUN_ID:?}"
  # The name of this very check, e.g. "frontend-pre-check / review".
  name=$(gh api "repos/$REPO/check-runs/$CHECK_RUN_ID" --jq .name)
  mapfile -t prs < <(grep -oE 'pr-[0-9]+-' <<< "$MERGE_HEAD_REF" | grep -oE '[0-9]+' | sort -u)
  if (( ${#prs[@]} == 0 )); then
    echo "::error title=Pre-check::The merge queue entry names no pull request."
    exit 1
  fi
  for pr in "${prs[@]}"; do
    head=$(gh api "repos/$REPO/pulls/$pr" --jq .head.sha)
    encoded=$(jq -rn --arg name "$name" '$name | @uri')
    passed=$(gh api "repos/$REPO/commits/$head/check-runs?check_name=$encoded&filter=latest" \
      --jq '[.check_runs[] | select(.app.slug == "github-actions")] | sort_by(.completed_at) | last | .conclusion // "missing"')
    if [ "$passed" != success ]; then
      echo "::error title=Pre-check::Pull request #$pr has no passing pre-check on its head ${head:0:7} ($passed)."
      exit 1
    fi
    echo "Pull request #$pr passed the pre-check on its head ${head:0:7}."
  done
  echo "Every pull request in this merge queue entry passed the pre-check on its head. The merged result itself was not reviewed."
  exit 0
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
  exit 1
  ;;
report) ;;
*)
  echo "Unknown mode" >&2
  exit 2
  ;;
esac

: "${PR_NUMBER:?}" "${HEAD_SHA:?}" "${RESULT_FILE:?}" "${SCOPE_FILE:?}"
BASE_SHA=${BASE_SHA:-$(jq -r '.base // ""' "$SCOPE_FILE")}
out=$(mktemp -d)
python3 "$HERE/render.py" "$RESULT_FILE" "$SCOPE_FILE" "$out"
outcome=$(cat "$out/outcome")
case "$outcome" in
  clean | advisory | changes | human | quarantine) ;;
  *) REASON=invalid exec bash "$0" error ;;
esac

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

if ! guard; then
  echo "::error title=Pre-check::The base branch moved during publication; re-run the job."
  exit 1
fi
upsert_comment "$out/comment.md"

guard || { echo "::error title=Pre-check::The base branch moved during publication; re-run the job."; exit 1; }
case "$outcome" in
  clean) gh api "repos/$REPO/issues/$PR_NUMBER/labels" -f "labels[]=$LABEL_CLEAN" > /dev/null || true ;;
  advisory) gh api "repos/$REPO/issues/$PR_NUMBER/labels" -f "labels[]=$LABEL_ADVISORY" > /dev/null || true ;;
  changes) gh api "repos/$REPO/issues/$PR_NUMBER/labels" -f "labels[]=$LABEL_CHANGES" > /dev/null || true ;;
  human | quarantine) gh api "repos/$REPO/issues/$PR_NUMBER/labels" -f "labels[]=$LABEL_HUMAN" > /dev/null || true ;;
esac
# A push between the last guard and the label: take the label off again.
if ! guard; then
  remove_labels
  exit 1
fi

# Usage, as far as the run reports it; only numbers and tool names.
if [ -n "${USAGE_JSON:-}" ] && [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  jq -r --arg coverage "${COVERAGE:-none}" --arg tools "${TOOLS_USED:-}" '
    def n: if type == "number" then . else "-" end;
    "### Pre-check usage\n",
    "| Turns | Duration (s) | Input tokens | Cache read | Cache write | Output tokens | Permission denials | API-price estimate (USD) | Diff read | Tools available |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    "| \(.num_turns | n) | \(if (.duration_ms | type) == "number" then (.duration_ms / 1000 | floor) else "-" end) | \(.usage.input_tokens | n) | \(.usage.cache_read_input_tokens | n) | \(.usage.cache_creation_input_tokens | n) | \(.usage.output_tokens | n) | \(.permission_denials_count | n) | \(if (.total_cost_usd | type) == "number" then (.total_cost_usd * 100 | round / 100) else "-" end) | \($coverage) | \($tools) |"
  ' <<< "$USAGE_JSON" >> "$GITHUB_STEP_SUMMARY" 2> /dev/null || true
fi

case "$outcome" in
  clean) echo "Pre-check: clean." ;;
  advisory) echo "Pre-check: passed with advisory findings." ;;
  changes)
    echo "::error title=Pre-check::Changes needed. See the Pre-check comment on the pull request."
    exit 1
    ;;
  human)
    echo "::error title=Pre-check::A person has to review this pull request. See the Pre-check comment."
    exit 1
    ;;
  quarantine)
    echo "::error title=Pre-check::The result was withheld. See the Pre-check comment."
    exit 1
    ;;
esac
