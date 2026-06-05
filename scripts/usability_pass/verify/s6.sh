#!/usr/bin/env bash
# Stage 6 gate — FREEZE: cold restart, every prior gate re-passes, parent checklist live,
# runbook exists (USABILITY_PASS.md change 9 + final proof).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"

echo "INFO: cold restart"
compose down >/dev/null 2>&1
compose up -d db web >/dev/null 2>&1
assert "web back up after cold restart" wait_for_http "$BASE/web/login" 300

# Parent onboarding checklist endpoint.
PARENT_JAR=$(mktemp)
http_login "DemoParent@demo.com" "dojo@2026" "$PARENT_JAR"
SUMMARY=$(curl -s -b "$PARENT_JAR" --max-time 20 "$BASE/my/dojo/onboarding/summary")
rm -f "$PARENT_JAR"
echo "$SUMMARY" | grep -q '"steps"' \
  && echo "PASS: /my/dojo/onboarding/summary returns steps for parent" \
  || { echo "FAIL: onboarding summary missing steps :: $(echo "$SUMMARY" | head -c 300)"; GATE_FAILED=1; }
echo "$SUMMARY" | grep -q '"progress_pct"' \
  && echo "PASS: onboarding summary includes progress_pct" \
  || { echo "FAIL: onboarding summary missing progress_pct"; GATE_FAILED=1; }

# Student sees only self (must not error; must return JSON).
STUDENT_JAR=$(mktemp)
http_login "demo1@demo.com" "dojo@2026" "$STUDENT_JAR"
SCODE=$(curl -s -b "$STUDENT_JAR" -o /tmp/upass_student_summary.json -w '%{http_code}' --max-time 20 "$BASE/my/dojo/onboarding/summary")
rm -f "$STUDENT_JAR"
if [ "$SCODE" = "200" ]; then echo "PASS: student onboarding summary returns 200"; else
  echo "FAIL: student onboarding summary returned $SCODE"; GATE_FAILED=1; fi

# Checklist visible on the portal home page.
PARENT_JAR=$(mktemp)
http_login "DemoParent@demo.com" "dojo@2026" "$PARENT_JAR"
HOME=$(curl -s -b "$PARENT_JAR" --max-time 20 "$BASE/my/dojo")
rm -f "$PARENT_JAR"
echo "$HOME" | grep -qi 'onboarding' \
  && echo "PASS: /my/dojo renders an onboarding block" \
  || { echo "FAIL: /my/dojo has no onboarding block"; GATE_FAILED=1; }

# Re-run every prior gate against the cold stack.
for s in 1 2 3 4 5; do
  echo "INFO: re-running stage $s gate against cold-started stack"
  if bash "$HERE/s$s.sh"; then echo "PASS: stage $s gate (cold)"; else
    echo "FAIL: stage $s gate after cold restart"; GATE_FAILED=1; fi
done

# Runbook.
[ -f "USABILITY_PASS_RUNBOOK.md" ] \
  && echo "PASS: USABILITY_PASS_RUNBOOK.md exists" \
  || { echo "FAIL: USABILITY_PASS_RUNBOOK.md missing"; GATE_FAILED=1; }
grep -qi "instructor_key" USABILITY_PASS_RUNBOOK.md 2>/dev/null \
  && echo "PASS: runbook documents instructor_key" \
  || { echo "FAIL: runbook does not document instructor_key"; GATE_FAILED=1; }
grep -qi "rotate" USABILITY_PASS_RUNBOOK.md 2>/dev/null \
  && echo "PASS: runbook documents token rotation" \
  || { echo "FAIL: runbook does not document token rotation"; GATE_FAILED=1; }
finish
