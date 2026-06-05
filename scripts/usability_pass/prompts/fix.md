The verification gate for the stage you just worked on FAILED when the orchestrator ran it
against the running docker stack. The gate output is appended below.

Re-enter the cycle at ANALYZE:
1. Read the failure lines. Check `docker compose logs --tail=150 web` for matching tracebacks.
2. Update your `docs/usability_pass/S<N>_PLAN.md` with the corrective step BEFORE editing.
3. Apply the smallest fix. If your previous approach caused this, revert it
   (`git checkout -- <file>`) rather than patching the patch.
4. If the fix touches modules/security/views: re-run the module upgrade and restart web so the
   running stack reflects your change.
5. Re-run the SAME gate yourself until it prints `GATE: PASSED`, then
   `git add -A && git commit`.

Do not expand scope. Do not modify the gate.
