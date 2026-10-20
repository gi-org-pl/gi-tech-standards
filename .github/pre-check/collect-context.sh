#!/usr/bin/env bash
# Collects everything the pre-check reviewer may read into one directory, so
# that the reviewer itself needs no GitHub access: the pull request, its diff
# (capped), the linked issues, Figma links, linked documents, the repository's
# guide from the base branch and earlier pre-check comments. Writes INDEX.md
# (what is where), scope.json (read by report.sh) and PROMPT.md (the prompt:
# the reviewer instructions and a pointer to INDEX.md).
#
# Environment:
#   REPO, PR_NUMBER     the pull request (owner/name, number)
#   CTX                 output directory
#   STANDARDS_DIR       checkout of gi-tech-standards
#   MAX_DIFF_LINES      changed lines (additions + deletions) reviewed at most
#   EXCLUDE_PATHS       newline-separated bash globs of files left out of the
#                       diff (tests, generated and lock files); matched against
#                       the whole path, where * also matches /
#   DOC_REPOS           newline-separated owner/name repositories whose linked
#                       documents are fetched (e.g. gi-org-pl/product)
#   HEAD_SHA            head commit of the event; the run stops if the pull
#                       request has moved on (a re-run of an old run)
#   GH_TOKEN            token for the GitHub API (read access is enough)
set -euo pipefail

: "${REPO:?}" "${PR_NUMBER:?}" "${CTX:?}" "${STANDARDS_DIR:?}"
MAX_DIFF_LINES="${MAX_DIFF_LINES:-3000}"
EXCLUDE_PATHS="${EXCLUDE_PATHS:-}"
DOC_REPOS="${DOC_REPOS:-}"
MAX_ISSUES=5
MAX_DOC_FILES=20
MAX_FILE_BYTES=300000

# CTX may already hold the standards checkout; only this script's own output
# is cleared.
rm -rf "$CTX/issues" "$CTX/docs" "$CTX/repo"
mkdir -p "$CTX/issues" "$CTX/docs" "$CTX/repo"
notes=()

# --- Pull request --------------------------------------------------------
gh api "repos/$REPO/pulls/$PR_NUMBER" > "$CTX/pr.json"
base_sha=$(jq -r '.base.sha' "$CTX/pr.json")
head_sha=$(jq -r '.head.sha' "$CTX/pr.json")
if [ -n "${HEAD_SHA:-}" ] && [ "$head_sha" != "$HEAD_SHA" ]; then
  echo "::error title=Pre-check::This run is for commit ${HEAD_SHA:0:7}, but the pull request is at ${head_sha:0:7} now. The run for the newer commit reviews it."
  exit 1
fi
jq -r '
  "# \(.title)\n",
  "- Pull request: \(.html_url)",
  "- Author: \(.user.login)",
  "- Branches: \(.head.ref) into \(.base.ref)",
  "- Head commit: \(.head.sha)",
  "- Labels: \([.labels[].name] | join(", "))",
  "",
  "## Description",
  "",
  (.body // "(empty)")
' "$CTX/pr.json" > "$CTX/pr.md"
pr_body=$(jq -r '.body // ""' "$CTX/pr.json")

# --- Diff, capped ----------------------------------------------------------
gh api --paginate "repos/$REPO/pulls/$PR_NUMBER/files?per_page=100" | jq -s 'add // []' > "$CTX/files.json"
# The API lists at most 3000 files of a pull request.
changed_files=$(jq -r '.changed_files' "$CTX/pr.json")
listed_files=$(jq 'length' "$CTX/files.json")
unlisted=$(( changed_files > listed_files ? changed_files - listed_files : 0 ))
if (( unlisted > 0 )); then
  notes+=("GitHub lists at most 3000 files of a pull request: $unlisted of its $changed_files changed files were not listed and not reviewed.")
fi

is_excluded() {
  local file="$1" pattern
  while IFS= read -r pattern; do
    [ -n "$pattern" ] || continue
    # shellcheck disable=SC2053 # the pattern is a glob on purpose
    [[ "$file" == $pattern ]] && return 0
  done <<< "$EXCLUDE_PATHS"
  return 1
}

: > "$CTX/diff.patch"
reviewed=() not_reviewed=() excluded=() no_patch=()
used=0
while IFS= read -r entry; do
  name=$(jq -r '.filename' <<< "$entry")
  changes=$(jq -r '.changes' <<< "$entry")
  if is_excluded "$name"; then
    excluded+=("$name")
    continue
  fi
  if ! jq -e 'has("patch")' <<< "$entry" > /dev/null; then
    no_patch+=("$name")
    continue
  fi
  if (( used + changes > MAX_DIFF_LINES )); then
    not_reviewed+=("$name")
    continue
  fi
  used=$(( used + changes ))
  reviewed+=("$name")
  jq -r '
    "diff --git a/\(.previous_filename // .filename) b/\(.filename)",
    "status: \(.status), +\(.additions) -\(.deletions)",
    "--- a/\(.previous_filename // .filename)",
    "+++ b/\(.filename)",
    .patch,
    ""
  ' <<< "$entry" >> "$CTX/diff.patch"
done < <(jq -c '.[]' "$CTX/files.json")

to_json() { if (( $# )); then printf '%s\n' "$@" | jq -R . | jq -s .; else echo '[]'; fi; }

# --- Linked issues ---------------------------------------------------------
owner=${REPO%/*}
name=${REPO#*/}
refs=$(
  {
    # shellcheck disable=SC2016 # GraphQL variables, not shell ones
    gh api graphql -f owner="$owner" -f name="$name" -F number="$PR_NUMBER" -f query='
      query($owner: String!, $name: String!, $number: Int!) {
        repository(owner: $owner, name: $name) {
          pullRequest(number: $number) {
            closingIssuesReferences(first: 10) { nodes { number repository { nameWithOwner } } }
          }
        }
      }' --jq '.data.repository.pullRequest.closingIssuesReferences.nodes[] | "\(.repository.nameWithOwner)#\(.number)"' || true
    grep -oE 'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[0-9]+' <<< "$pr_body" \
      | sed -E 's|https://github\.com/([^/]+/[^/]+)/issues/([0-9]+)|\1#\2|' || true
    grep -oE '(^|[^A-Za-z0-9_/.-])([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[0-9]+' <<< "$pr_body" \
      | sed -E 's/^[^A-Za-z0-9#]//' \
      | sed -E "s|^#|$REPO#|" || true
  } | awk 'NF && !seen[$0]++'
) || true

issues=()
not_read=()
links_text="$pr_body"
while IFS= read -r ref; do
  [ -n "$ref" ] || continue
  if (( ${#issues[@]} >= MAX_ISSUES )); then
    not_read+=("$ref")
    continue
  fi
  issue_repo=${ref%#*}
  issue_number=${ref#*#}
  if ! issue=$(gh api "repos/$issue_repo/issues/$issue_number" 2> /dev/null); then
    notes+=("Could not read the linked issue $ref.")
    continue
  fi
  # A "#123" in the description may point at a pull request; only issues count.
  if jq -e 'has("pull_request")' <<< "$issue" > /dev/null; then
    continue
  fi
  file="$CTX/issues/${issue_repo//\//-}-$issue_number.md"
  comments=$(gh api --paginate "repos/$issue_repo/issues/$issue_number/comments?per_page=100" 2> /dev/null | jq -s 'add // []' || echo '[]')
  comment_count=$(jq -s 'map(length) | add // 0' <<< "$comments")
  if (( comment_count > 100 )); then
    notes+=("The issue $ref has $comment_count comments; only the first 100 were read.")
  fi
  comments=$(jq -s 'add // [] | .[:100]' <<< "$comments")
  {
    jq -r '
      "# \(.title)\n",
      "- Issue: \(.html_url)",
      "- State: \(.state)",
      "- Labels: \([.labels[].name] | join(", "))",
      "",
      "## Description",
      "",
      (.body // "(empty)")
    ' <<< "$issue"
    jq -r '.[] | "\n## Comment by \(.user.login), \(.created_at)\n\n\(.body // "")"' <<< "$comments"
  } > "$file"
  issues+=("$ref")
  links_text+=$'\n'"$(cat "$file")"
done <<< "$refs"
if (( ${#not_read[@]} )); then
  notes+=("Only the first $MAX_ISSUES linked issues were read; these further references were not: ${not_read[*]}.")
fi

# --- Figma links -----------------------------------------------------------
grep -oE 'https://([a-z]+\.)?figma\.com/[^][()<>"'"'"' `]+' <<< "$links_text" | awk '!seen[$0]++' > "$CTX/figma-links.txt" || true
mapfile -t figma < "$CTX/figma-links.txt"

# --- Linked documents ------------------------------------------------------
# Writes a file from the API to $2, cut at MAX_FILE_BYTES.
fetch_raw() {
  local tmp
  tmp=$(mktemp)
  if gh api "$1" -H "Accept: application/vnd.github.raw" > "$tmp" 2> /dev/null; then
    head -c "$MAX_FILE_BYTES" "$tmp" > "$2"
    rm -f "$tmp"
    return 0
  fi
  rm -f "$tmp"
  return 1
}
docs=()
skipped_docs=()
fetch_doc() {
  local repo="$1" ref="$2" path="$3" target
  if (( ${#docs[@]} >= MAX_DOC_FILES )); then
    skipped_docs+=("$repo/$path")
    return 0
  fi
  target="$CTX/docs/$repo/$path"
  mkdir -p "$(dirname "$target")"
  if fetch_raw "repos/$repo/contents/$path?ref=$ref" "$target"; then
    docs+=("$repo/$path@$ref")
  else
    rm -f "$target"
    notes+=("Could not read the linked document $repo/$path at $ref.")
  fi
}
while IFS= read -r doc_repo; do
  [ -n "$doc_repo" ] || continue
  while IFS= read -r url; do
    [ -n "$url" ] || continue
    rest=${url#"https://github.com/$doc_repo/"}
    kind=${rest%%/*}
    rest=${rest#*/}
    ref=${rest%%/*}
    path=${rest#*/}
    path=${path%%[#?]*}
    [ "$path" != "$ref" ] || continue
    if [ "$kind" = blob ]; then
      fetch_doc "$doc_repo" "$ref" "$path"
    else
      while IFS= read -r child; do
        fetch_doc "$doc_repo" "$ref" "$child"
      done < <(gh api "repos/$doc_repo/contents/$path?ref=$ref" --jq '.[] | select(.type == "file" and (.name | test("\\.(md|mdx|txt)$"))) | .path' 2> /dev/null || true)
    fi
  done < <(grep -oE "https://github\.com/$doc_repo/(blob|tree)/[^][()<>\"' \`]+" <<< "$links_text" | awk '!seen[$0]++' || true)
done <<< "$DOC_REPOS"

find "$CTX/docs" -type d -empty -delete
if (( ${#skipped_docs[@]} )); then
  notes+=("Only the first $MAX_DOC_FILES linked documents were read; not read: ${skipped_docs[*]}.")
fi

# --- The repository's guide, from the base branch --------------------------
# Every AGENTS.md and CLAUDE.md at any depth, then at most 40 other documents.
gh api "repos/$REPO/git/trees/$base_sha?recursive=1" > "$CTX/tree.json"
if jq -e '.truncated' "$CTX/tree.json" > /dev/null; then
  notes+=("The base branch has too many files to list at once; guide files beyond the listed part may be missing from the context.")
fi
repo_docs=()
other_docs=0
skipped_repo_docs=0
while IFS= read -r path; do
  [ -n "$path" ] || continue
  if [[ "$path" != AGENTS.md && "$path" != */AGENTS.md && "$path" != CLAUDE.md && "$path" != */CLAUDE.md ]]; then
    if (( other_docs >= 40 )); then
      skipped_repo_docs=$(( skipped_repo_docs + 1 ))
      continue
    fi
    other_docs=$(( other_docs + 1 ))
  fi
  mkdir -p "$(dirname "$CTX/repo/$path")"
  if fetch_raw "repos/$REPO/contents/$path?ref=$base_sha" "$CTX/repo/$path"; then
    repo_docs+=("$path")
  fi
done < <(jq -r '.tree[] | select(.type == "blob") | .path' "$CTX/tree.json" \
  | grep -E '(^|/)(AGENTS|CLAUDE)\.md$|^(README\.md|CONTRIBUTING\.md|docs/.*\.mdx?|\.github/pull_request_template\.md)$' || true)

if (( skipped_repo_docs > 0 )); then
  notes+=("Only 40 documents of the repository guide besides AGENTS.md and CLAUDE.md were read; $skipped_repo_docs more were not.")
fi

# --- Earlier pre-check comments --------------------------------------------
gh api --paginate "repos/$REPO/pulls/$PR_NUMBER/comments?per_page=100" | jq -s '
  add // []
  | map(select(.user.login == "github-actions[bot]"))
  | map({path, line, side, outdated: (.line == null), commit: .commit_id[0:7], body: (.body[0:600])})
' > "$CTX/previous-comments.json"

# --- Scope and index -------------------------------------------------------
workflow_changes=()
for file in "${reviewed[@]}" "${not_reviewed[@]}" "${no_patch[@]}"; do
  [[ "$file" == .github/workflows/* ]] && workflow_changes+=("$file")
done
truncated=false
(( ${#not_reviewed[@]} == 0 && unlisted == 0 )) || truncated=true
standards_sha=$(git -C "$STANDARDS_DIR" rev-parse HEAD)

jq -n \
  --arg head "$head_sha" --arg base "$base_sha" --arg standards "$standards_sha" \
  --argjson max "$MAX_DIFF_LINES" --argjson used "$used" --argjson truncated "$truncated" \
  --argjson reviewed "$(to_json "${reviewed[@]}")" \
  --argjson not_reviewed "$(to_json "${not_reviewed[@]}")" \
  --argjson excluded "$(to_json "${excluded[@]}")" \
  --argjson no_patch "$(to_json "${no_patch[@]}")" \
  --argjson issues "$(to_json "${issues[@]}")" \
  --argjson figma "$(to_json "${figma[@]}")" \
  --argjson docs "$(to_json "${docs[@]}")" \
  --argjson repo_docs "$(to_json "${repo_docs[@]}")" \
  --argjson workflow_changes "$(to_json "${workflow_changes[@]}")" \
  --argjson notes "$(to_json "${notes[@]}")" \
  '{head: $head, base: $base, standards: $standards, max_diff_lines: $max, diff_lines: $used,
    truncated: $truncated, reviewed: $reviewed, not_reviewed: $not_reviewed, excluded: $excluded,
    no_patch: $no_patch, issues: $issues, figma: $figma, docs: $docs, repo_docs: $repo_docs,
    workflow_changes: $workflow_changes, notes: $notes}' > "$CTX/scope.json"

# shellcheck disable=SC2016 # literal backticks: Markdown code spans
list() { if (( $# )); then printf -- '- `%s`\n' "$@"; else echo "- none"; fi; }
{
  echo "# Pre-check context"
  echo
  echo "Pull request $REPO#$PR_NUMBER, head commit $head_sha, base commit $base_sha."
  echo "Standards: gi-tech-standards at $standards_sha, in \`.pre-check-context/standards/\`."
  echo
  echo "- \`.pre-check-context/pr.md\` - the pull request and its description"
  echo "- \`.pre-check-context/diff.patch\` - the diff of the reviewed files ($used changed lines)"
  echo "- \`.pre-check-context/issues/\` - linked issues"
  echo "- \`.pre-check-context/figma-links.txt\` - Figma links (cannot be opened; check the design comparison in the description)"
  echo "- \`.pre-check-context/docs/\` - linked documents"
  echo "- \`.pre-check-context/repo/\` - the repository's guide on the base branch"
  echo "- \`.pre-check-context/previous-comments.json\` - inline comments of earlier pre-check runs"
  echo
  echo "## Reviewed files"
  list "${reviewed[@]}"
  if [ "$truncated" = true ]; then
    echo
    echo "## Not reviewed: the pull request is too large for a full pre-check"
    echo
    echo "The diff is capped at $MAX_DIFF_LINES changed lines. Do not review these files and do not guess their content:"
    echo
    list "${not_reviewed[@]}"
  fi
  echo
  echo "## Left out of the diff: tests, test helpers, generated, lock or binary files"
  echo
  echo "Their names tell which tests changed; read one from the checkout only when a finding depends on it."
  echo
  list "${excluded[@]}" "${no_patch[@]}"
  echo
  echo "## Linked issues"
  list "${issues[@]}"
  echo
  echo "## Figma links"
  list "${figma[@]}"
  echo
  echo "## Linked documents"
  list "${docs[@]}"
  echo
  echo "## Repository guide (base branch)"
  list "${repo_docs[@]}"
  if (( ${#workflow_changes[@]} )); then
    echo
    echo "## This pull request changes CI workflows"
    list "${workflow_changes[@]}"
  fi
  if (( ${#notes[@]} )); then
    echo
    echo "## Notes"
    printf -- '- %s\n' "${notes[@]}"
  fi
} > "$CTX/INDEX.md"

# The prompt stays small whatever the size of the pull request: the action
# passes it in one environment variable, which Linux limits to 128 KiB.
{
  cat "$STANDARDS_DIR/docs/frontend/PRE_CHECK_REVIEWER.md"
  echo
  echo "---"
  echo
  echo "Pull request $REPO#$PR_NUMBER at commit $head_sha. Start by reading \`.pre-check-context/INDEX.md\`."
} > "$CTX/PROMPT.md"

# Only the rendered files are meant for the reviewer.
rm -f "$CTX/pr.json" "$CTX/files.json" "$CTX/tree.json"

echo "Context collected: ${#reviewed[@]} files reviewed ($used lines), ${#not_reviewed[@]} not reviewed, ${#excluded[@]} excluded, ${#issues[@]} issues, ${#figma[@]} Figma links, ${#docs[@]} documents."
