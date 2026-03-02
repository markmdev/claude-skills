---
name: audit-blitz
description: >
  Run a comprehensive multi-dimensional code audit in parallel — error handling,
  UX states, observability, code review, and code health review. Each fixing audit
  runs in its own worktree so changes don't conflict. Results are reviewed for
  quality before merging. Use this skill whenever the user says "run all audits",
  "audit blitz", "full audit", "comprehensive review", "audit everything",
  "run audits in parallel", or any request to do a thorough codebase review
  covering multiple quality dimensions at once.
---

# Audit Blitz

Run five code quality audits in parallel, review their work critically, then merge and present a unified summary.

## The Five Audits

| Audit | What it does | Agent type | Isolation |
|-------|-------------|------------|-----------|
| Error audit | Finds and fixes silent error swallowing, fallbacks, config defaults | `meridian:implement` | Worktree |
| UX states audit | Finds and implements missing loading, empty, error states | `meridian:implement` | Worktree |
| Observability audit | Removes debug logs, adds context to log entries, tracks gaps | `meridian:implement` | Worktree |
| Code review | Finds bugs, logic errors, data flow issues | `meridian:code-reviewer` | None |
| Code health review | Finds dead code, pattern drift, over-engineering | `meridian:code-health-reviewer` | None |

The first three make code changes — they need worktree isolation so their fixes don't conflict. The last two only report findings.

## Step 1: Determine Scope

Ask the user what to audit if not clear. Common scopes:
- The entire project
- A specific directory (`src/`, `backend/`, `frontend/`)
- Specific files or modules

The user can also select which audits to run:
- "audit blitz — skip ux" → run 4 of 5
- "just the fixers" → skip code-reviewer and code-health-reviewer
- "just review, don't fix" → run only the two reviewers

Default: all five.

## Step 2: Load Audit Methodologies

Search for the audit skill files to get their full methodology:

```
~/.claude/plugins/**/error-audit/SKILL.md
~/.claude/plugins/**/ux-states-audit/SKILL.md
~/.claude/plugins/**/observability-audit/SKILL.md
```

If found, read each one — include their full content in the agent prompts.

If not found (plugin not installed), use these condensed instructions:
- **Error audit**: Find and fix silent error swallowing (empty catch blocks, log-and-continue, silent fallbacks, config defaults hiding misconfiguration). Every error must reach the user or crash explicitly.
- **UX states audit**: Find and implement missing loading, empty, and error states for every async operation and data-driven UI component. Use the app's existing UI patterns only.
- **Observability audit**: Remove debug `console.log`s, add context to thin log entries, add tracking for unmonitored external calls and critical operations. Use existing logging/tracking tools only.

## Step 3: Spawn All Agents in Parallel

In a **single message**, spawn all selected agents using the Agent tool. This is critical — launch everything at once for maximum parallelism.

### Fixing agents (worktree-isolated)

For each of the three audit types, spawn a `meridian:implement` agent with `isolation: "worktree"` and `model: "opus"`:

```
Prompt for each:

You are running a [audit-type] audit on this codebase.

Scope: [directory or files to audit]

[Full SKILL.md content from Step 2, or condensed instructions]

After completing the audit:
1. Commit all fixes with descriptive messages (one commit per logical group of fixes)
2. Provide a clear summary: what you found, what you fixed, file paths and line numbers
```

### Review agents (no worktree)

Spawn `meridian:code-reviewer` and `meridian:code-health-reviewer` with `model: "opus"`. These agent types have built-in prompts — just tell them the scope:

```
Prompt: Review the code in [scope]. Return structured findings with file paths,
line numbers, and severity.
```

## Step 4: Review Worktree Results

This is the critical quality gate. When the worktree agents finish, **do not merge blindly**. For each worktree that has changes:

1. **Read the diff**: `git diff main...<worktree-branch>` (or whatever the base branch is)
2. **Evaluate each change critically**:
   - Does the fix actually address a real problem, or is it unnecessary churn?
   - Does the fix follow the project's existing patterns and conventions?
   - Could the fix break existing behavior or tests?
   - Is the fix complete, or does it leave things half-done?
   - Is the fix over-engineered relative to the problem?
3. **Reject bad changes**: If a fix is wrong, unnecessary, or low-quality, don't merge it. Note it in the summary as "rejected" with the reason.
4. **Run tests if available**: Before merging, check if the project has tests. Run them against each worktree branch to catch regressions.

Only merge changes that pass your review. The agents are autonomous and may produce mediocre fixes — your job is to be the quality filter.

## Step 5: Merge Approved Changes

For each worktree branch that passed review (one at a time):

```bash
git merge <worktree-branch> --no-edit
```

If there are merge conflicts:
1. List the conflicting files
2. For each conflict, understand what both sides changed
3. Resolve by keeping both changes where they don't overlap, or choosing the better fix when they do
4. Commit the merge resolution

Merge in this order to minimize conflicts: error-audit first, then observability-audit, then ux-states-audit (error fixes are most foundational).

After all merges, run tests again to verify nothing broke.

## Step 6: Present Summary

```markdown
## Audit Blitz Results

### Error Audit
- X issues found, Y fixed, Z rejected
- [Accepted changes with file paths]
- [Rejected changes with reasons]

### UX States Audit
- X missing states found, Y implemented, Z rejected
- [Accepted changes]
- [Rejected changes]

### Observability Audit
- X issues found, Y fixed, Z rejected
- [Accepted changes]
- [Rejected changes]

### Code Review Findings
- [Findings by severity — these are for the user to address manually]

### Code Health Findings
- [Findings — dead code, pattern drift, refactoring opportunities]

### Summary
- Total issues found: X
- Auto-fixed and merged: Y
- Rejected (low quality): Z
- Manual attention needed: W
- Tests: passing/failing
```

Highlight anything that needs the user's manual attention — especially code review findings, since those are never auto-fixed.
