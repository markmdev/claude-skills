---
name: self-improve
description: >
  Analyze Claude Code sessions to find workflow frictions, underused tools, stale
  instructions, documentation gaps, and opportunities for new skills or automation.
  Produces actionable improvement suggestions with prioritized recommendations.
  Use when the user says "self-improve", "analyze my workflow", "what can we improve",
  "find frictions", "optimize workflow", or asks about improving their Claude Code
  setup. Also suggest running this after long sessions, multi-session projects,
  or when the user seems frustrated with repetitive work.
---

# Self-Improve

Analyze recent sessions to find workflow frictions and turn them into concrete improvements — new skills, better docs, updated rules, or tool enhancements.

## Step 1: Determine Scope

Ask the user what to analyze:

- **Current session**: Analyze what just happened in this session
- **Recent sessions**: Last N sessions or last N days (default: 3 days)
- **Specific project**: Focus on a particular project's sessions
- **Cross-project**: Look for patterns across all projects

## Step 2: Gather Data

### Transcript analysis

To analyze past sessions, activate the `/transcript-parser` skill — it has the full reference for available commands, flags, and output formats. Use it to list sessions, read specific ones, search across transcripts, and analyze tool usage patterns for the time period in scope.

For the current session, you already have the conversation context — no transcript parsing needed.

### Environment scan

In parallel, discover what's available in the current project. Don't assume any specific framework or directory structure — adapt to what exists:

- **Skills**: Check `~/.claude/skills/` (personal) and `.claude/skills/` (project) for installed skills
- **Agents**: Check `.claude/agents/` for custom subagent definitions
- **Plugins**: Check `~/.claude/plugins/cache/` for installed plugins
- **CLAUDE.md**: Read `~/.claude/CLAUDE.md` (global) and `CLAUDE.md` (project) for current rules
- **Docs**: Search the project for markdown docs with frontmatter (`summary`, `read_when`) — these are knowledge files regardless of where they live
- **Hooks**: Check `.claude/settings.json` and any plugin hook registrations

## Step 3: Analyze for Improvement Signals

Look for these specific patterns in the transcript and environment data:

### Friction patterns (from transcripts)

- **User corrections**: "no, do it this way", "that's wrong", "I said X not Y" — gaps in instructions or understanding
- **Repeated manual steps**: The same multi-step workflow done across sessions that could be a skill
- **Long research phases**: Agent spending many turns exploring before finding the right file/pattern — a doc could shortcut this
- **Retry loops**: Agent trying an approach, failing, trying again — missing knowledge or bad instructions
- **User interruptions**: Frequent `[Request interrupted by user]` — agent going down wrong paths
- **Context re-establishment**: Agent re-learning the same project structure or conventions each session

### Tool and integration gaps (from transcripts)

- **External tool friction**: CLI tools, APIs, scripts where the agent struggled or took extra steps
- **Missing automation**: Manual sequences that could be scripted or turned into a skill
- **Workarounds**: Agent doing something the hard way because a better tool isn't available or isn't known
- **Undiscovered capabilities**: Tools or APIs used in one session that could benefit other workflows

### Knowledge gaps (from environment scan)

- **Stale CLAUDE.md rules**: Instructions that don't match observed behavior or are no longer relevant
- **Missing docs**: Knowledge that was discovered during sessions but never documented — the agent will have to rediscover it next time
- **Unused skills**: Skills that exist but never triggered during the analysis period — either the description is wrong or the skill isn't needed
- **Doc-skill mismatches**: Docs that describe workflows which should be skills, or skills that lack supporting docs

### Structural opportunities

- **Session patterns**: Something the agent figured out how to do through trial and error that could become a reusable skill
- **Cross-session knowledge**: Insights or decisions that keep being re-established because they're not persisted
- **Convention drift**: Project patterns changing without CLAUDE.md or docs being updated

## Step 4: Write the Report

Create `.claude/improvements/IMPROVEMENTS.md` (create the directory if needed).

Structure the file as a prioritized, scannable list:

```markdown
# Workflow Improvements

Generated: YYYY-MM-DD
Scope: [what was analyzed]
Sessions analyzed: N

## High Impact

### 1. [Short title]
**Signal**: [What was observed — specific examples from transcripts]
**Impact**: [Why this matters — time saved, friction reduced, errors prevented]
**Suggestion**: [What to build or change]
**Type**: [new-skill | new-doc | update-rule | tool-enhancement | automation]

### 2. ...

## Medium Impact

### 3. ...

## Low Impact / Nice to Have

### 5. ...
```

Limit to 5-8 suggestions. Quality over quantity — each should be clearly actionable with evidence from the transcripts.

## Step 5: Present to User

Show a concise summary — short bullet points, not the full doc:

```
Found N improvement opportunities from X sessions:

**High impact:**
- [Title] — [one sentence why]
- [Title] — [one sentence why]

**Medium:**
- [Title] — [one sentence why]

Full analysis: .claude/improvements/IMPROVEMENTS.md
```

Then ask: "Which of these would you like to work on? I'll create a detailed spec for each."

## Step 6: Create Detail Docs

For each improvement the user selects, create a detail doc at `.claude/improvements/<slug>.md`:

```markdown
# [Improvement Title]

## Problem
[What friction was observed, with specific transcript evidence]

## Current State
[How things work today — what files, tools, workflows are involved]

## Proposed Solution
[Concrete approach — what to build, what to change, what to document]

## Alternatives Considered
[Other approaches and why the proposed one is better]

## Implementation Notes
[Specific files to create/modify, dependencies, estimated complexity]

## Success Criteria
[How to know the improvement is working]
```

These docs serve as specs for implementation — detailed enough that the user can hand one to Claude and say "implement this" in a future session.

## What NOT to Suggest

- Don't suggest changes to Claude Code itself (the CLI tool) — only things within the user's control
- Don't suggest vague improvements ("write better prompts") — be specific about what prompt and what change
- Don't recommend tools you haven't seen evidence of need for — base everything on transcript data
- Don't flag standard Claude Code tool usage (Read, Write, Edit, Bash) as friction — focus on external tools, APIs, and workflow-level patterns
