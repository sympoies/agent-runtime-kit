# git push of skill-removal branch -> ci-gate-stack pre-push hook (bash scripts/ci/all.sh)
==[ ci/all.sh position 7 ]== agent-runtime audit-drift (root + tests/drift fixtures)
audit-drift [extra/warn/claude] plugins/conversation/skills/test-first/SKILL.md: live runtime surface exists under an install-map root but is not tracked by the install map
audit-drift [extra/warn/codex] skills/conversation/test-first: live runtime surface exists under an install-map root but is not tracked by the install map
audit-drift: 25 finding(s); highest-severity exit=1
exit status 1
ci-gate-stack
error: failed to push some refs to 'github.com:graysurf/agent-runtime-kit.git'

# prune-stale refuses (foreign symlink -> primary build):
agent-runtime prune-stale ... --dry-run
  ? skip foreign symlink plugins/conversation/skills/test-first/SKILL.md -> .../graysurf/agent-runtime-kit/build/codex/.../test-first/SKILL.md

# repo content clean at block tier:
agent-runtime audit-drift --fail-on block  ->  EXIT 0 (25 findings, gated to 0 by --fail-on block)
