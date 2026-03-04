# Friction Patterns Reference

Known anti-patterns and improvement signals to look for when analyzing Claude Code sessions. Organized by category with detection methods and example improvements.

## Repeated Manual Steps

### Pattern: User repeatedly types the same setup commands
**Detection:** Search transcript for repeated user messages with similar content (same commands, same file paths, same instructions).
**Signal:** If the user types the same thing 3+ times across sessions, it should be automated (hook, skill, or CLAUDE.md instruction).
**Example improvement:** User always says "run tests before committing" → add to CLAUDE.md or pre-commit hook.

### Pattern: Agent keeps re-reading the same files
**Detection:** Multiple Read tool calls to the same file within one session, or across sessions.
**Signal:** If context is needed every time, it should be injected automatically (docs with frontmatter, CLAUDE.md, or context hook).

### Pattern: User corrects the agent repeatedly
**Detection:** User messages like "no, I meant...", "that's wrong...", "don't do that", "I said...".
**Signal:** The correction should become a CLAUDE.md rule or skill instruction so it sticks.

### Pattern: Copy-paste workflows between sessions
**Detection:** User pastes the same block of text, URLs, or configuration across multiple sessions.
**Signal:** The repeated content should live in a doc, TOOLS.md entry, or environment variable that the agent can access without the user pasting it.

## Tool and Integration Gaps

### Pattern: Manual web searches for the same APIs
**Detection:** Repeated WebSearch/WebFetch for the same library/API docs across sessions.
**Signal:** Create a doc in `.meridian/api-docs/` so the knowledge persists.

### Pattern: Workarounds for missing tools
**Detection:** User describes a multi-step process that could be a single skill invocation.
**Signal:** Create a skill that encapsulates the workflow.

### Pattern: Underused available tools
**Detection:** Agent uses general-purpose tools (Bash grep, Bash cat) when specialized tools exist (Grep, Read).
**Signal:** Update CLAUDE.md to prefer specific tools, or check if skills/agents could help.

### Pattern: External tool friction
**Detection:** Errors from CLI tools, API auth failures, version mismatches. Agent spends time debugging tooling instead of doing work.
**Signal:** Document the tool setup in TOOLS.md or create a setup script.

### Pattern: Agent builds one-off scripts instead of reusing existing ones
**Detection:** Agent writes a Bash or Python script inline to accomplish something a skill or existing script already handles.
**Signal:** The existing tool's description or activation keywords may need updating so the agent finds it. Or the workflow should become a skill if no tool exists yet.

## Knowledge and Documentation Gaps

### Pattern: Agent re-discovers the same facts
**Detection:** Agent explores the same code paths, reads the same config files, or makes the same architectural observations across sessions.
**Signal:** Document the knowledge in `.meridian/docs/` or `knowledge/` so it's available from session start.

### Pattern: Stale CLAUDE.md rules
**Detection:** Rules that reference old code patterns, deleted files, deprecated tools, or workflows that have changed.
**Signal:** Audit and clean up CLAUDE.md.

### Pattern: Missing skill for common workflows
**Detection:** User triggers the same multi-step workflow manually (e.g., "review this PR", "deploy to staging", "update the changelog").
**Signal:** Create a skill that captures the workflow.

### Pattern: Docs that are never read
**Detection:** Docs with `read_when` hints that don't match any tasks the user actually does. Or docs that exist but the agent never references them.
**Signal:** Update or remove stale docs. Adjust `read_when` keywords to match actual usage patterns.

### Pattern: Knowledge scattered across wrong locations
**Detection:** The same fact appears in CLAUDE.md, a knowledge doc, and a project doc — or a fact lives in CLAUDE.md when it should be a knowledge doc (or vice versa).
**Signal:** Consolidate into the canonical location. CLAUDE.md is for rules, knowledge/ is for domain expertise, .meridian/docs/ is for project implementation details.

## Session Structure Issues

### Pattern: Context window bloat
**Detection:** Very long sessions with many tool calls before meaningful work starts. Agent reads excessive files before acting.
**Signal:** Better context injection, more focused docs, or skills that preload the right context.

### Pattern: Agent goes down wrong paths
**Detection:** Agent starts implementing, then backtracks after user correction. Multiple "let me try a different approach" messages.
**Signal:** Interview step is missing — add planning phase or CLAUDE.md instruction to ask before acting.

### Pattern: No verification before stopping
**Detection:** Agent says "should work" or "build passes" without actually testing. Or agent declares success without running the code path that was changed.
**Signal:** Add verification instructions to CLAUDE.md or create a post-implementation checklist skill.

### Pattern: Premature implementation
**Detection:** Agent jumps straight to coding before understanding requirements. User has to course-correct mid-implementation.
**Signal:** Add a CLAUDE.md rule to ask clarifying questions first, or add an interview step to relevant skills.

## Convention Drift

### Pattern: Inconsistent patterns across files
**Detection:** Same operation done differently in different files (error handling, logging, API calls, component structure).
**Signal:** Document the canonical pattern in `.meridian/docs/` or CLAUDE.md.

### Pattern: Dependencies added without justification
**Detection:** New packages added that duplicate existing functionality or are unnecessary.
**Signal:** Add dependency review to code review process.

### Pattern: Style rules not enforced
**Detection:** CLAUDE.md says "do X" but transcripts show the agent doing Y without correction — the rule exists but isn't followed.
**Signal:** The rule may need to be more prominent (move higher in CLAUDE.md), more specific (add examples), or enforced via a hook/reviewer.
