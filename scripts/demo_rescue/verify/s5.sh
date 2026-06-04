#!/usr/bin/env bash
# Stage 5 gate — FREEZE: cold restart, then every prior gate must pass against the
# fresh stack, and the runbook must exist (DEMO_RESCUE.md Phase 5). This is the
# "actually runs" proof.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"

echo "INFO: cold restart"
compose down >/dev/null 2>&1
compose up -d db web >/dev/null 2>&1
assert "web back up after cold restart" wait_for_http "$BASE/web/login" 300

for s in 1 2 3 4; do
  echo "INFO: re-running stage $s gate against cold-started stack"
  if bash "$HERE/s$s.sh"; then echo "PASS: stage $s gate (cold)"; else
    echo "FAIL: stage $s gate after cold restart"; GATE_FAILED=1; fi
done

[ -f "DEMO_RUNBOOK.md" ] \
  && echo "PASS: DEMO_RUNBOOK.md exists" \
  || { echo "FAIL: DEMO_RUNBOOK.md missing"; GATE_FAILED=1; }
grep -qi "admin@demo.com" DEMO_RUNBOOK.md 2>/dev/null \
  && echo "PASS: runbook lists demo logins" \
  || { echo "FAIL: runbook does not list demo logins"; GATE_FAILED=1; }
finish
