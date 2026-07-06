# nils-cli v1.2.0 release, PR-mode deliver step
info: pushing release branch chore/release-1-2-0 to origin
info: opening + waiting + merging release PR via forge-cli pr deliver
error: unchecked_task_items: 3 unchecked task-list item(s) in the PR/MR description; disposition each (complete and check it off, or rewrite it as deferred with a follow-up ref) or pass --allow-unchecked-tasks with --allow-unchecked-tasks-reason to bypass
error: forge-cli pr deliver failed; release branch chore/release-1-2-0 left in place for recovery

# Offending generated PR body (project-bump-version-tag-release.sh:1395-1398):
## Test plan
- [ ] CI: required status checks green
- [ ] After merge: tag v1.2.0 and confirm release.yml publishes artifacts
- [ ] Tap stage updates homebrew formula
