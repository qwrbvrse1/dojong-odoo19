#!/usr/bin/env bash
# Demo-rescue orchestrator. Script drives everything; Claude Code only executes stages.
# Each stage: ANALYZE/PLAN/EXECUTE (Claude, scripted prompt) -> VERIFY (deterministic gate,
# run by THIS script against the local docker stack). Gate fails -> bounded retries with
# the gate output fed back. All work happens in a dedicated git worktree.
#
# Usage:  ./scripts/demo_rescue/run_rescue.sh            # full run, stages 0..5
#         ./scripts/demo_rescue/run_rescue.sh 2          # resume from stage 2
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE="${RESCUE_WORKTREE:-/opt/worktrees/dojong-odoo19/core-dojo-realignment}"

# Main repo resolution — the toolkit can live anywhere (e.g. ~automation/demo_rescue):
# 1. RESCUE_REPO env var, 2. toolkit sitting inside the repo (<repo>/scripts/demo_rescue),
# 3. derived from the worktree's git metadata.
if [ -n "${RESCUE_REPO:-}" ]; then
  ORIG_REPO="$RESCUE_REPO"
elif git -C "$HERE/../.." rev-parse --show-toplevel >/dev/null 2>&1; then
  ORIG_REPO="$(git -C "$HERE/../.." rev-parse --show-toplevel)"
elif [ -e "$WORKTREE/.git" ]; then
  _common="$(cd "$WORKTREE" && git rev-parse --git-common-dir)"
  case "$_common" in /*) : ;; *) _common="$WORKTREE/$_common" ;; esac
  ORIG_REPO="$(cd "$(dirname "$_common")" && pwd)"
else
  echo "FATAL: cannot locate main repo — set RESCUE_REPO=/path/to/dojong-odoo19" >&2; exit 1
fi
BRANCH="${RESCUE_BRANCH:-demo-rescue}"   # only used if WORKTREE must be created fresh
LOGDIR="$HERE/logs"
MAX_ATTEMPTS="${RESCUE_MAX_ATTEMPTS:-3}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_FLAGS="--dangerously-skip-permissions"
START_STAGE="${1:-0}"

# Same compose project name as the original checkout -> same named volumes (same DB),
# but containers mount code from the WORKTREE.
export COMPOSE_PROJECT_NAME="${RESCUE_PROJECT:-$(basename "$ORIG_REPO" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')}"
export RESCUE_BASE_URL="${RESCUE_BASE_URL:-http://localhost:8070}"
export RESCUE_DB="${RESCUE_DB:-odoo19}"

mkdir -p "$LOGDIR"
log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOGDIR/orchestrator.log"; }
die() { log "FATAL: $*"; exit 1; }

command -v "$CLAUDE_BIN" >/dev/null || die "claude CLI not found"
command -v docker >/dev/null || die "docker not found"

# ── Worktree setup ───────────────────────────────────────────────────────────
sync_working_state() {
  # The worktree must contain this toolkit + mission docs so Claude can self-verify
  # with the same gates the orchestrator runs (prompts reference repo-relative paths).
  mkdir -p "$WORKTREE/scripts"
  cp -R "$HERE" "$WORKTREE/scripts/" 2>/dev/null
  cp "$ORIG_REPO/DEMO_RESCUE.md" "$WORKTREE/DEMO_RESCUE.md" 2>/dev/null \
    || cp "$HERE/DEMO_RESCUE.md" "$WORKTREE/DEMO_RESCUE.md" 2>/dev/null
  # Carry over other untracked files from the original checkout (e.g. prep_kiosk_demo.sh)
  git -C "$ORIG_REPO" ls-files --others --exclude-standard | while read -r f; do
    [ -e "$WORKTREE/$f" ] && continue
    mkdir -p "$WORKTREE/$(dirname "$f")" && cp "$ORIG_REPO/$f" "$WORKTREE/$f"
  done
  # Uncommitted modifications from the original checkout (e.g. the menu repointing)
  if ! git -C "$ORIG_REPO" diff --quiet; then
    git -C "$ORIG_REPO" diff > /tmp/rescue-uncommitted.patch
    if git -C "$WORKTREE" apply --check /tmp/rescue-uncommitted.patch 2>/dev/null; then
      git -C "$WORKTREE" apply /tmp/rescue-uncommitted.patch
      log "Applied uncommitted diff from original checkout"
    else
      log "WARN: uncommitted diff already present or conflicts in worktree — skipped (Claude re-evaluates in S0)"
    fi
  fi
  if ! git -C "$WORKTREE" diff --quiet || [ -n "$(git -C "$WORKTREE" status --porcelain)" ]; then
    git -C "$WORKTREE" add -A
    git -C "$WORKTREE" commit -m "rescue: import working state + toolkit" >/dev/null 2>&1
  fi
}

setup_worktree() {
  if [ -d "$WORKTREE/.git" ] || [ -f "$WORKTREE/.git" ]; then
    log "Using existing worktree $WORKTREE (branch: $(git -C "$WORKTREE" branch --show-current))"
  else
    log "Worktree missing — creating $WORKTREE (branch $BRANCH from HEAD)"
    mkdir -p "$(dirname "$WORKTREE")"
    git -C "$ORIG_REPO" worktree add -B "$BRANCH" "$WORKTREE" HEAD || die "worktree add failed"
  fi
  sync_working_state
}

# ── Stage runner ─────────────────────────────────────────────────────────────
run_stage() {
  local n="$1" attempt=1 gate="$HERE/verify/s$n.sh" rc
  [ -x "$gate" ] || chmod +x "$gate"
  while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
    log "── Stage $n, attempt $attempt/$MAX_ATTEMPTS ──"
    local plog="$LOGDIR/s${n}_claude_a${attempt}.log"
    if [ "$attempt" -eq 1 ]; then
      local prompt; prompt="$(cat "$HERE/prompts/_common.md" "$HERE/prompts/s$n.md")"
      ( cd "$WORKTREE" && timeout "${RESCUE_STAGE_TIMEOUT:-1500}" \
          "$CLAUDE_BIN" -p "$prompt" $CLAUDE_FLAGS ) >"$plog" 2>&1
    else
      local fix; fix="$(cat "$HERE/prompts/fix.md"; echo; echo '--- GATE OUTPUT (FAILED) ---'; tail -n 120 "$LOGDIR/s${n}_gate_a$((attempt-1)).log")"
      ( cd "$WORKTREE" && timeout "${RESCUE_STAGE_TIMEOUT:-1500}" \
          "$CLAUDE_BIN" -c -p "$fix" $CLAUDE_FLAGS ) >"$plog" 2>&1
    fi
    rc=$?
    [ $rc -ne 0 ] && log "Stage $n: claude exited rc=$rc (continuing to gate anyway)"
    log "Stage $n: running gate verify/s$n.sh"
    ( cd "$WORKTREE" && bash "$gate" ) >"$LOGDIR/s${n}_gate_a${attempt}.log" 2>&1
    if [ $? -eq 0 ]; then
      log "Stage $n: GATE PASSED"
      git -C "$WORKTREE" add -A >/dev/null 2>&1
      git -C "$WORKTREE" commit -m "rescue: stage $n checkpoint (gate passed)" >/dev/null 2>&1
      return 0
    fi
    log "Stage $n: GATE FAILED (see $LOGDIR/s${n}_gate_a${attempt}.log)"
    attempt=$((attempt+1))
  done
  return 1
}

# ── Main ─────────────────────────────────────────────────────────────────────
setup_worktree
log "Project=$COMPOSE_PROJECT_NAME  Worktree=$WORKTREE  Base=$RESCUE_BASE_URL  DB=$RESCUE_DB"

# Stop any stack started from the original checkout so the worktree mounts win.
( cd "$ORIG_REPO" && docker compose down --remove-orphans >/dev/null 2>&1 )

for n in 0 1 2 3 4 5; do
  [ "$n" -lt "$START_STAGE" ] && continue
  run_stage "$n" || die "Stage $n failed after $MAX_ATTEMPTS attempts. Logs: $LOGDIR"
done

git -C "$WORKTREE" tag -f "demo-$(date +%Y%m%d-%H%M)" >/dev/null 2>&1
log "ALL STAGES PASSED. Demo build is in $WORKTREE (branch $BRANCH)."
log "Runbook: $WORKTREE/DEMO_RUNBOOK.md"
