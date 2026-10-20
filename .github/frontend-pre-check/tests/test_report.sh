#!/usr/bin/env bash
# Integration test of report.sh against a fake gh: the exit status of every
# mode, which is the contract of the required check, and what gets published.
# Run: bash .github/frontend-pre-check/test_report.sh
set -uo pipefail

HERE=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin"
cat > "$T/bin/gh" << 'EOF'
#!/usr/bin/env bash
echo "gh $*" >> "$FAKE_LOG"
args="$*"
case "$args" in
  *'pulls/1 --jq "\(.head.sha) \(.base.sha)"'*) echo "$FAKE_HEAD $FAKE_BASE" ;;
  *"pulls/"*" --jq .head.sha"*) echo "$FAKE_HEAD" ;;
  *"check-runs/"*" --jq .name"*) echo "frontend-pre-check / review" ;;
  *"commits/"*"/check-runs"*) echo "$FAKE_CHECK" ;;
  *"--input -"*) cat > /dev/null ;;
esac
if [ -n "${FAKE_FAIL:-}" ] && [[ "$args" == *"$FAKE_FAIL"* ]]; then
  exit 1
fi
for a in "$@"; do
  case "$a" in body=@*) cp "${a#body=@}" "$FAKE_POSTED" ;; esac
done
exit 0
EOF
chmod +x "$T/bin/gh"
export PATH="$T/bin:$PATH" FAKE_LOG="$T/log" FAKE_POSTED="$T/posted.md"
HEAD_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
BASE_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
export REPO=gi-org-pl/x PR_NUMBER=1 HEAD_SHA BASE_SHA
export FAKE_HEAD=$HEAD_SHA FAKE_BASE=$BASE_SHA FAKE_CHECK=success RUN_URL=https://github.com/gi-org-pl/x/actions/runs/1

failures=0
check() { # name expected-exit command...
  local name="$1" expected="$2" status
  shift 2
  : > "$FAKE_LOG"
  rm -f "$FAKE_POSTED"
  "$@" > "$T/out" 2>&1
  status=$?
  if [ "$status" -ne "$expected" ]; then
    echo "FAIL $name: exit $status, expected $expected"
    sed 's/^/    /' "$T/out"
    failures=$((failures + 1))
  else
    echo "ok   $name"
  fi
}
posted_has() { grep -q -- "$1" "$FAKE_POSTED" 2> /dev/null; }
labelled() { grep -q -- "labels\[\]=$1" "$FAKE_LOG"; }

decisions='{"data_structures":[],"state":[],"api_contracts":[],"ux_behaviours":[],"new_dependencies":[],"architecture":[]}'
mk_result() { echo "{\"result\":\"passed\",\"summary\":\"s\",\"decisions\":$decisions,\"findings\":$1,\"checked\":[],\"not_checked\":[],\"qa\":[]}" > "$T/result.json"; }
cat > "$T/scope.json" << EOF
{"head":"$HEAD_SHA","base":"$BASE_SHA","standards":"$HEAD_SHA","reviewed":["src/a.ts"],"file_count":1,"diff_lines":3,
 "max_diff_lines":3000,"unlisted":0,"truncated":false,"not_reviewed":[],"excluded":[],"excluded_lines":0,"safe_assets":[],
 "unreviewable":[],"human_paths":[],"workflow_changes":[],"renamed":[],"issues":[],"figma":[],"docs":[],
 "repo_docs":[],"cut_sources":[],"notes":[],"hunks":{"src/a.ts":[{"LEFT":[1,3],"RIGHT":[1,4]}]}}
EOF
report() { RESULT_FILE="$T/result.json" SCOPE_FILE="$T/scope.json" COVERAGE=full bash "$HERE/report.sh" report; }

check "a skip fails the required check" 1 env SKIP_REASON="the pull request comes from a fork." bash "$HERE/report.sh" notchecked
posted_has "not pre-checked" || { echo "FAIL skip comment"; failures=$((failures + 1)); }

check "merge queue: the pull request passed on its head" 0 env MERGE_HEAD_REF=refs/heads/gh-readonly-queue/main/pr-1-abc CHECK_RUN_ID=5 bash "$HERE/report.sh" queue
check "merge queue: no passing check" 1 env FAKE_CHECK=failure MERGE_HEAD_REF=refs/heads/gh-readonly-queue/main/pr-1-abc CHECK_RUN_ID=5 bash "$HERE/report.sh" queue
check "merge queue: no pull request in the ref" 1 env MERGE_HEAD_REF=refs/heads/other CHECK_RUN_ID=5 bash "$HERE/report.sh" queue

mk_result '[]'
check "clean passes" 0 report
labelled "pre-check: clean" || { echo "FAIL clean label"; failures=$((failures + 1)); }

mk_result '[{"severity":"non-blocking","path":"src/a.ts","title":"t","body":"advisory body","inline":false}]'
check "advisory passes" 0 report
labelled "pre-check: advisory" || { echo "FAIL advisory label"; failures=$((failures + 1)); }
posted_has "advisory body" || { echo "FAIL advisory body in the comment"; failures=$((failures + 1)); }

mk_result '[{"severity":"blocking","path":"src/a.ts","title":"t","body":"blocking body","inline":true,"line":2}]'
check "a blocking finding fails" 1 report
posted_has "blocking body" || { echo "FAIL blocking body in the comment"; failures=$((failures + 1)); }

check "a moved head publishes nothing" 0 env FAKE_HEAD=cccccccccccccccccccccccccccccccccccccccc bash -c "RESULT_FILE='$T/result.json' SCOPE_FILE='$T/scope.json' COVERAGE=full bash '$HERE/report.sh' report"
if grep -q "issues/1/comments -F" "$FAKE_LOG"; then echo "FAIL moved head posted"; failures=$((failures + 1)); fi

mk_result '[]'
check "a moved base fails and does not publish the result" 1 env FAKE_BASE=dddddddddddddddddddddddddddddddddddddddd bash -c "RESULT_FILE='$T/result.json' SCOPE_FILE='$T/scope.json' COVERAGE=full bash '$HERE/report.sh' report"
posted_has "base branch moved" || { echo "FAIL base moved comment"; failures=$((failures + 1)); }

check "an incomplete reading fails" 1 bash -c "RESULT_FILE='$T/result.json' SCOPE_FILE='$T/scope.json' COVERAGE=partial bash '$HERE/report.sh' report"

mk_result '[{"severity":"non-blocking","path":"src/a.ts","title":"t","body":"password = hunter2hunter2x","inline":false}]'
check "a credential-like output is withheld and fails" 1 report
if posted_has "hunter2"; then echo "FAIL leaked value published"; failures=$((failures + 1)); fi

echo '{"result":"bogus"}' > "$T/result.json"
check "an invalid result fails" 1 report

check "an unfinished run fails" 1 env REASON=failed bash "$HERE/report.sh" error

# The review job's dispatch (report.sh publish) for every way the gate and the
# analysis can end.
mk_result '[]'
RJ=$(cat "$T/result.json")
SJ=$(cat "$T/scope.json")
check "publish: a superseded gate does not pass" 1 env GATE=cancelled bash "$HERE/report.sh" publish
check "publish: a failed gate fails" 1 env GATE=failure bash "$HERE/report.sh" publish
check "publish: a skip fails" 1 env GATE=success VERDICT=skip GATE_REASON="the pull request is a draft." bash "$HERE/report.sh" publish
check "publish: a blocked run fails" 1 env GATE=success VERDICT=block GATE_REASON="limit." bash "$HERE/report.sh" publish
check "publish: an unknown verdict fails" 1 env GATE=success VERDICT=other bash "$HERE/report.sh" publish
check "publish: a merge queue entry dispatches" 0 env GATE=success VERDICT=queue MERGE_HEAD_REF=refs/heads/gh-readonly-queue/main/pr-1-abc CHECK_RUN_ID=5 bash "$HERE/report.sh" publish
check "publish: a superseded analysis does not pass" 1 env GATE=success VERDICT=run ANALYSE=cancelled bash "$HERE/report.sh" publish
check "publish: a failed analysis fails" 1 env GATE=success VERDICT=run ANALYSE=failure ABORT=failed bash "$HERE/report.sh" publish
check "publish: a clean analysis passes" 0 env GATE=success VERDICT=run ANALYSE=success RESULT_JSON="$RJ" SCOPE_JSON="$SJ" COVERAGE=full bash "$HERE/report.sh" publish
check "publish: an empty result fails" 1 env GATE=success VERDICT=run ANALYSE=success RESULT_JSON="" SCOPE_JSON="$SJ" bash "$HERE/report.sh" publish
check "an API failure while publishing fails" 1 env FAKE_FAIL="pulls/1 --jq" bash -c "RESULT_FILE='$T/result.json' SCOPE_FILE='$T/scope.json' COVERAGE=full bash '$HERE/report.sh' report"

if (( failures )); then
  echo "$failures failure(s)"
  exit 1
fi
echo "all report.sh checks passed"
