---
name: recap
description: >
  Summarize recent Claude Code sessions for a project — what was accomplished,
  what's pending, decisions made, and current repo state. Uses transcript analysis
  to reconstruct context. Use this skill whenever the user says "recap",
  "catch me up", "what did I do", "where was I", "what happened", "session summary",
  "what's the status", "what did I work on", "pick up where I left off", or any
  request to understand recent work history. Also use when the user returns to a
  project after time away, switches between projects, or starts a session with
  "what's going on with [project]".
---

# Recap

Generate a concise summary of recent work by combining transcript analysis with current repo state. Built for the "I'm coming back — what's happening?" moment.

## Step 1: Determine Scope

Figure out what the user wants:

- **Current project** (default): Recap recent sessions in this project's directory
- **Named project**: "recap on x-cli" → filter to that project
- **All projects**: "what have I been working on" → cover everything
- **Time range**: Default to last 3 days. Adjust for "yesterday", "this week", "last week"

## Step 2: Gather Transcript Data

Activate the `/transcript-parser` skill — it has the full reference for commands, flags, and output formats.

Gather this data (in parallel where possible):

1. **Session list** — recent sessions for the time range, filtered by project if scoped
2. **User + assistant messages** — across sessions in the time range (these reveal intent and decisions)
3. **Tool usage patterns** — for the time range

For sessions that look important (high message count or long duration), read them individually to understand the arc of what happened. Focus on user messages for intent, assistant messages for what was actually done.

## Step 3: Gather Repo State

In parallel with transcript analysis:

```bash
git status
git branch --show-current
git log --oneline -15
git diff --stat          # uncommitted changes
git branch               # all local branches
gh pr list --state open 2>/dev/null   # open PRs if gh is available
```

If recapping multiple projects, check repo state for each.

## Step 4: Synthesize

Combine transcript and repo data into these sections:

### Done
What was completed — tasks finished, features shipped, bugs fixed, releases made. Be specific: "Released Meridian v0.6.0 with plugin architecture" not "worked on Meridian". Group by topic when multiple sessions covered the same thing.

### In Progress
Work that's started but not finished — uncommitted changes, open branches, open PRs. Connect these to transcript context when possible ("branch `feat/dark-mode` has 3 commits — from the session where you started dark mode implementation").

### Decisions
Architectural choices, approach selections, trade-offs made. These are the things that are easy to forget between sessions. Include the rationale when it was discussed.

### Next
Tasks mentioned but not started. Things deferred with "next session" or "later". Follow-up work identified during sessions. Open items from code reviews.

### Repo State
Current branch, clean/dirty, ahead/behind remote, stale branches.

## Presentation

Keep it scannable — 30 seconds to understand where things stand. Bullet points, not paragraphs. Bold the most important items.

When recapping multiple projects, lead with a one-line status per project, then expand on whichever project the user asks about or the one with the most recent activity.

Don't list every session — synthesize across sessions. If there were 8 sessions on Glyph in one day, summarize the arc ("Built navigation, polished UI, shipped phase 4") rather than listing each session's messages.
