#!/usr/bin/env bash
# Publishes the pre-check on the pull request: the one "Pre-check" comment
# (found again by its hidden marker and updated on every run), the inline
# comments, the label and the exit status of the job. The reviewer cannot
# post anything itself; render.py turns its structured result into escaped
# Markdown first. Nothing the reviewer wrote is echoed into workflow commands
# or logs.
#
# Usage: report.sh start | report | error | skipped
#   start   create the labels if the repository lacks them and take them off
#           the pull request before a review
#   report  publish RESULT_FILE (the reviewer's result) with SCOPE_FILE; exit 1
#           unless the outcome is "no findings"
#   error   say in the comment that the pre-check did not finish (REASON is a
#           fixed code), take the labels off, exit 1
#   skipped take the labels off and mark an earlier comment as not run for
#           the new commit (SKIP_REASON)
#
# Environment: REPO, PR_NUMBER, HEAD_SHA, GH_TOKEN, RUN_URL, MODEL,
# STANDARDS_SHA, RESULT_FILE, SCOPE_FILE, USAGE_JSON, REASON, SKIP_REASON.
set -euo pipefail

: "${REPO:?}" "${PR_NUMBER:?}" "${HEAD_SHA:?}"
MODE="${1:?usage: report.sh start|report|error|skipped}"
HERE=$(cd "$(dirname "$0")" && pwd)
MARKER="<!-- gi-pre-check -->"
LABEL_PASSED="pre-check: no findings"
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
  remove_label "$LABEL_PASSED"
  remove_label "$LABEL_CHANGES"
  remove_label "$LABEL_HUMAN"
}

add_label() {
  gh api "repos/$REPO/issues/$PR_NUMBER/labels" -f "labels[]=$1" > /dev/null \
    || echo "::warning::Could not add a pre-check label."
}

comment_id() {
  gh api --paginate "repos/$REPO/issues/$PR_NUMBER/comments?per_page=100" \
    --jq ".[] | select(.user.login == \"github-actions[bot]\" and (.body | startswith(\"$MARKER\"))) | .id" | sed -n 1p
}

# Creates the comment, or updates the one an earlier run created.
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

# A run publishes nothing once the pull request has moved past the commit it
# reviewed: the run for the newer commit owns the comment and the labels. If
# the head cannot be read, nothing is published either.
current_head() {
  gh api "repos/$REPO/pulls/$PR_NUMBER" --jq .head.sha
}
current_or_exit() {
  local current
  if ! current=$(current_head); then
    echo "::error title=Pre-check::Could not read the head of the pull request; nothing is published."
    exit 1
  fi
  if [ "$current" != "$HEAD_SHA" ]; then
    echo "The pull request moved on from ${HEAD_SHA:0:7} to ${current:0:7}; this result is not published."
    exit 0
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
  current_or_exit
  ensure_label "$LABEL_PASSED" "0e8a16" "AI pre-check found nothing to fix; not an approval"
  ensure_label "$LABEL_CHANGES" "d93f0b" "AI pre-check found something to fix"
  ensure_label "$LABEL_HUMAN" "fbca04" "AI pre-check cannot judge this pull request; a person reviews it"
  remove_labels
  exit 0
  ;;
skipped)
  current_or_exit
  remove_labels
  if [ -n "$(comment_id || true)" ]; then
    note_comment "**Result:** not run for commit \`${HEAD_SHA:0:7}\` - ${SKIP_REASON:-the run was skipped.} The result of an earlier run no longer applies to this pull request." \
      || echo "::warning::Could not update the Pre-check comment."
  fi
  exit 0
  ;;
error)
  current_or_exit
  remove_labels
  case "${REASON:-}" in
    outdated) exit 0 ;;
    unsafe_names) text="a file name in this pull request contains a control character or a backtick, so nothing was reviewed." ;;
    invalid) text="the reviewer returned no valid result." ;;
    gate) text="the gate job did not succeed, so nothing was reviewed." ;;
    *) text="the reviewer did not complete (a common cause is the usage limit of the subscription; re-run the job later)." ;;
  esac
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

: "${RESULT_FILE:?}" "${SCOPE_FILE:?}"
out=$(mktemp -d)
python3 "$HERE/render.py" "$RESULT_FILE" "$SCOPE_FILE" "$out"
outcome=$(cat "$out/outcome")
case "$outcome" in
  passed | changes | human) ;;
  *)
    REASON=invalid exec bash "$0" error
    ;;
esac

current_or_exit
remove_labels

# Inline comments, each with a fingerprint of its finding; a finding that an
# earlier run already commented on, on a line that still exists, is skipped.
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
  if jq -c --arg commit "$HEAD_SHA" '{commit_id: $commit, path, line, side, body}' <<< "$item" \
    | gh api "repos/$REPO/pulls/$PR_NUMBER/comments" --input - > /dev/null 2>&1; then
    posted=$(( posted + 1 ))
    attached+=("$fingerprint")
  else
    failed=$(( failed + 1 ))
  fi
done < <(jq -c '.[]' "$out/inline.json")
echo "Inline comments: $posted posted, $failed could not be attached (they are listed in the Pre-check comment)."
for fingerprint in "${attached[@]}"; do
  sed -i "s/<!-- inline $fingerprint -->/ (inline comment)/" "$out/comment.md"
done
sed -i -E 's/<!-- inline [0-9a-f]{16} -->/ (could not be attached to the diff)/' "$out/comment.md"
upsert_comment "$out/comment.md"

case "$outcome" in
  passed) add_label "$LABEL_PASSED" ;;
  changes) add_label "$LABEL_CHANGES" ;;
  human) add_label "$LABEL_HUMAN" ;;
esac

# A push between the head check and the label would leave this label on the
# newer commit: check again and take it off if so.
if [ "$(current_head 2> /dev/null || echo unknown)" != "$HEAD_SHA" ]; then
  remove_labels
  echo "The pull request moved on while publishing; the labels were taken off again."
  exit 0
fi

# Usage, as far as the run reports it; only numbers are printed. On a
# subscription the cost is the API price of the same tokens, not money spent.
if [ -n "${USAGE_JSON:-}" ] && [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  jq -r '
    def n: if type == "number" then . else "-" end;
    "### Pre-check usage\n",
    "| Turns | Duration (s) | Input tokens | Cache read | Cache write | Output tokens | Permission denials | API-price estimate (USD) |",
    "| --- | --- | --- | --- | --- | --- | --- | --- |",
    "| \(.num_turns | n) | \(if (.duration_ms | type) == "number" then (.duration_ms / 1000 | floor) else "-" end) | \(.usage.input_tokens | n) | \(.usage.cache_read_input_tokens | n) | \(.usage.cache_creation_input_tokens | n) | \(.usage.output_tokens | n) | \(.permission_denials_count | n) | \(if (.total_cost_usd | type) == "number" then (.total_cost_usd * 100 | round / 100) else "-" end) |"
  ' <<< "$USAGE_JSON" >> "$GITHUB_STEP_SUMMARY" 2> /dev/null || true
fi

case "$outcome" in
  passed)
    echo "Pre-check: no findings."
    ;;
  changes)
    echo "::error title=Pre-check::Changes needed. See the Pre-check comment on the pull request."
    exit 1
    ;;
  human)
    echo "::error title=Pre-check::A person has to review this pull request. See the Pre-check comment."
    exit 1
    ;;
esac
