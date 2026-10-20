#!/usr/bin/env bash
# Publishes the pre-check result on the pull request: the one "Pre-check"
# comment (found again by its hidden marker and updated on every run), the
# label and the exit status of the job. The reviewer itself cannot post any of
# this; it only returns the structured result (result.schema.json).
#
# Usage: report.sh start | report | error | skipped
#   start   create the labels if the repository lacks them and take both off
#           the pull request while the review runs
#   report  render RESULT_JSON into the comment, set the label, log usage and
#           exit 1 when changes are needed
#   error   take the labels off and say in the comment that the pre-check
#           did not finish
#   skipped take the labels off and, if there is a Pre-check comment, say that
#           the new commits were not pre-checked (SKIP_REASON, HEAD_SHA)
#
# Environment: REPO, PR_NUMBER, GH_TOKEN, CTX (context directory),
# HEAD_SHA (the reviewed commit), RUN_URL, MODEL, RESULT_JSON and
# EXECUTION_FILE (report only).
set -euo pipefail

: "${REPO:?}" "${PR_NUMBER:?}"
MODE="${1:?usage: report.sh start|report|error}"
MARKER="<!-- gi-pre-check -->"
LABEL_PASSED="pre-check: passed"
LABEL_CHANGES="pre-check: changes"

ensure_label() {
  gh api "repos/$REPO/labels" -f name="$1" -f color="$2" -f description="$3" > /dev/null 2>&1 || true
}

remove_label() {
  local encoded
  encoded=$(jq -rn --arg label "$1" '$label | @uri')
  gh api -X DELETE "repos/$REPO/issues/$PR_NUMBER/labels/$encoded" > /dev/null 2>&1 || true
}

add_label() {
  gh api "repos/$REPO/issues/$PR_NUMBER/labels" -f "labels[]=$1" > /dev/null \
    || echo "::warning::Could not add the label \"$1\"."
}

# Creates the comment, or updates the one an earlier run created.
upsert_comment() {
  local file="$1" id
  id=$(gh api --paginate "repos/$REPO/issues/$PR_NUMBER/comments?per_page=100" \
    --jq ".[] | select(.user.login == \"github-actions[bot]\" and (.body | startswith(\"$MARKER\"))) | .id" | sed -n 1p) || id=""
  if [ -n "$id" ]; then
    gh api -X PATCH "repos/$REPO/issues/comments/$id" -F body=@"$file" > /dev/null
    echo "Updated the Pre-check comment $id."
  else
    gh api "repos/$REPO/issues/$PR_NUMBER/comments" -F body=@"$file" > /dev/null
    echo "Created the Pre-check comment."
  fi
}

# A run publishes nothing once the pull request has moved past the commit it
# reviewed: the run for the newer commit owns the comment and the labels.
current_or_exit() {
  local current
  [ -n "${HEAD_SHA:-}" ] || return 0
  current=$(gh api "repos/$REPO/pulls/$PR_NUMBER" --jq .head.sha) || return 0
  if [ "$current" != "$HEAD_SHA" ]; then
    echo "The pull request moved on from ${HEAD_SHA:0:7} to ${current:0:7}; this result is not published."
    exit 0
  fi
}

# Tokens never belong in a comment, whatever the reviewer was talked into.
redact() {
  sed -E 's/(sk-ant-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})/[redacted]/g'
}

case "$MODE" in
start)
  ensure_label "$LABEL_PASSED" "0e8a16" "AI pre-check found nothing to fix"
  ensure_label "$LABEL_CHANGES" "d93f0b" "AI pre-check found something to fix"
  remove_label "$LABEL_PASSED"
  remove_label "$LABEL_CHANGES"
  exit 0
  ;;
error)
  current_or_exit
  remove_label "$LABEL_PASSED"
  remove_label "$LABEL_CHANGES"
  body=$(mktemp)
  {
    echo "$MARKER"
    echo "## Pre-check"
    echo
    echo "**Result:** not finished. The reviewer did not complete - see the [workflow run]($RUN_URL)."
    echo "A common cause is the usage limit of the subscription; re-run the job later."
    echo "Nothing was decided: until the pre-check passes, a person reviews the pull request as usual."
  } > "$body"
  upsert_comment "$body"
  exit 0
  ;;
skipped)
  remove_label "$LABEL_PASSED"
  remove_label "$LABEL_CHANGES"
  id=$(gh api --paginate "repos/$REPO/issues/$PR_NUMBER/comments?per_page=100" \
    --jq ".[] | select(.user.login == \"github-actions[bot]\" and (.body | startswith(\"$MARKER\"))) | .id" | sed -n 1p) || id=""
  if [ -n "$id" ]; then
    body=$(mktemp)
    {
      echo "$MARKER"
      echo "## Pre-check"
      echo
      echo "**Result:** not run for commit \`${HEAD_SHA:0:7}\` - ${SKIP_REASON:-the run was skipped.}"
      echo "The result of the earlier run no longer applies to this pull request."
    } > "$body"
    upsert_comment "$body" || echo "::warning::Could not update the Pre-check comment."
  fi
  exit 0
  ;;
report) ;;
*)
  echo "Unknown mode: $MODE" >&2
  exit 2
  ;;
esac

: "${CTX:?}" "${RESULT_JSON:?}"
scope="$CTX/scope.json"
result_file=$(mktemp)
printf '%s' "$RESULT_JSON" > "$result_file"
jq -e '.result and .decisions and (.findings | type == "array")' "$result_file" > /dev/null

# The result follows from the findings alone: changes needed if and only if
# at least one of them is blocking.
blocking=$(jq '[.findings[] | select(.severity == "blocking")] | length' "$result_file")
returned=$(jq -r '.result' "$result_file")
result=passed
[ "$blocking" -eq 0 ] || result=changes
if [ "$returned" != "$result" ]; then
  echo "::warning::The reviewer returned \"$returned\" with $blocking blocking finding(s); the result is \"$result\"."
fi

head_short=$(jq -r '.head[0:7]' "$scope")
standards_sha=$(jq -r '.standards' "$scope")

body=$(mktemp)
{
  echo "$MARKER"
  echo "## Pre-check"
  echo
  if [ "$result" = passed ] && jq -e '.truncated' "$scope" > /dev/null; then
    echo "**Result:** passed for the reviewed files - the pull request is too large for a full pre-check (see below)."
  elif [ "$result" = passed ]; then
    echo "**Result:** passed - no blocking findings."
  else
    echo "**Result:** changes needed - $blocking blocking finding(s)."
  fi
  echo
  jq -r '.summary' "$result_file"

  if jq -e '.findings | length > 0' "$result_file" > /dev/null; then
    echo
    echo "### Findings"
    echo
    jq -r '.findings[] |
      "- **[\(.severity)]** `\(.path)\(if .line then ":\(.line)" else "" end)` - \(.title)" +
      (if .comment == "new" then " (inline comment)"
       elif .comment == "earlier" then " (inline comment from an earlier run)"
       else "" end)' "$result_file"
  fi

  echo
  echo "### Technical decisions in this PR"
  jq -r '
    [["data_structures", "Data structures"], ["state", "State"], ["api_contracts", "API contracts"],
     ["ux_behaviours", "UX behaviours"], ["new_dependencies", "New dependencies"], ["architecture", "Architecture"]]
    as $categories
    | .decisions as $d
    | $categories[]
    | "\n**\(.[1])**\n",
      (if ($d[.[0]] | length) > 0 then ($d[.[0]][] | "- \(.)") else "- None." end)
  ' "$result_file"

  echo
  echo "### What was checked"
  echo
  jq -r '"- The diff of \(.reviewed | length) file(s), \(.diff_lines) changed lines, at commit `\(.head[0:7])`."' "$scope"
  jq -r 'if (.issues | length) > 0 then "- Linked issues: \(.issues | join(", "))." else "- Linked issues: none found." end' "$scope"
  jq -r '"- Standards: gi-tech-standards at `\(.standards[0:7])`; the repository guide on the base branch: \(if (.repo_docs | length) > 0 then (.repo_docs | map("`\(.)`") | join(", ")) else "none found" end)."' "$scope"
  jq -r 'if (.docs | length) > 0 then "- Linked documents: \(.docs | map("`\(.)`") | join(", "))." else empty end' "$scope"
  jq -r '.checked[] | "- \(.)"' "$result_file"

  echo
  echo "### What was not checked"
  echo
  echo "- Runtime behaviour: nothing was built, run or tested by the pre-check."
  jq -r '
    if .truncated then
      "- **Too large for a full pre-check** (cap: \(.max_diff_lines) changed lines) - reviewed: \(.reviewed | map("`\(.)`") | join(", "))." +
      (if (.not_reviewed | length) > 0 then " Not reviewed: \(.not_reviewed | map("`\(.)`") | join(", "))." else "" end)
    else empty end,
    if ((.excluded + .no_patch) | length) > 0 then
      "- Left out as generated, lock or binary files, or without a diff: \((.excluded + .no_patch) | map("`\(.)`") | join(", "))."
    else empty end,
    if (.figma | length) > 0 then
      "- Visual fidelity against the Figma design - the reviewer cannot open Figma. Links: \([.figma | to_entries[] | "[\(.key + 1)](\(.value))"] | join(" "))."
    else empty end,
    (.notes[] | "- \(.)")
  ' "$scope"
  jq -r '.not_checked[] | "- \(.)"' "$result_file"

  echo
  echo "### For QA"
  echo
  if jq -e '.qa | length > 0' "$result_file" > /dev/null; then
    jq -r '.qa[] | "- \(.)"' "$result_file"
  else
    echo "- Nothing specific beyond the issue's acceptance criteria."
  fi

  echo
  echo "<sub>AI pre-check of commit \`$head_short\` with model \`${MODEL:-default}\` ([workflow run]($RUN_URL)), following [the reviewer instructions](https://github.com/gi-org-pl/gi-tech-standards/blob/$standards_sha/docs/frontend/PRE_CHECK_REVIEWER.md). The functionality is tested in QA, and a person accepts or rejects the pull request.</sub>"
} | redact > "$body"

current_or_exit
upsert_comment "$body"

if [ "$result" = passed ]; then
  add_label "$LABEL_PASSED"
else
  add_label "$LABEL_CHANGES"
fi

# Usage, as far as the run reports it. On a subscription the cost is the API
# price of the same tokens, not money spent.
if [ -n "${EXECUTION_FILE:-}" ] && [ -f "$EXECUTION_FILE" ]; then
  usage=$(jq -c '[.[] | select(.type == "result")] | last | {num_turns, duration_ms, total_cost_usd, usage}' "$EXECUTION_FILE" 2> /dev/null || echo '{}')
  echo "Usage: $usage"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    jq -r '
      "### Pre-check usage\n",
      "| Turns | Duration | Input tokens | Cache read | Cache write | Output tokens | API-price estimate |",
      "| --- | --- | --- | --- | --- | --- | --- |",
      "| \(.num_turns // "-") | \(if .duration_ms then "\(.duration_ms / 1000 | floor) s" else "-" end) | \(.usage.input_tokens // "-") | \(.usage.cache_read_input_tokens // "-") | \(.usage.cache_creation_input_tokens // "-") | \(.usage.output_tokens // "-") | \(if .total_cost_usd then "$\(.total_cost_usd * 100 | round / 100)" else "-" end) |"
    ' <<< "$usage" >> "$GITHUB_STEP_SUMMARY" || true
  fi
fi

[ -z "${GITHUB_OUTPUT:-}" ] || echo "posted=true" >> "$GITHUB_OUTPUT"

if [ "$result" = changes ]; then
  echo "::error title=Pre-check::Changes needed - $blocking blocking finding(s). See the Pre-check comment on the pull request."
  exit 1
fi
echo "Pre-check passed."
