---
name: transcript-parser
description: Parse, search, and analyze Claude Code conversation transcripts from ~/.claude/projects/. Use when the user wants to review past sessions, find what they worked on, search conversation history, analyze tool usage patterns, understand their Claude workflow, debug past interactions, or do any meta-analysis of how they use Claude Code. Also use when asked about "transcripts", "conversation history", "past sessions", "what did I work on", "which tools do I use", or reviewing past Claude interactions for workflow improvement.
---

# Transcript Parser

Analyze Claude Code conversation transcripts stored in `~/.claude/projects/`. Use the bundled Python script for all transcript queries.

## Quick Reference

The script lives at `~/.claude/skills/transcript-parser/scripts/parse_transcript.py`. Run it with Python 3:

```bash
python ~/.claude/skills/transcript-parser/scripts/parse_transcript.py <command> [options]
```

### Commands

| Command | What it does | Example |
|---------|-------------|---------|
| `list-sessions` (or `ls`) | List sessions across all projects | `... ls -n 10` |
| `read <session-id>` | Read a specific session's conversation | `... read deaf3112-7eb8-...` |
| `read --last N` | Read N most recent sessions (batch mode) | `... read --last 3 --brief` |
| `recent` | Show recent messages across all sessions | `... recent --since 2026-02-27` |
| `search <query>` | Search transcripts for keywords | `... search "meridian"` |
| `tools` | Tool usage patterns and workflow analysis | `... tools --since 2026-02-01` |

### Common Flags

| Flag | Description |
|------|-------------|
| `--json` | Output as JSON instead of readable text |
| `--project` / `-p` | Filter to a specific project (partial match on slug) |
| `--include-subagents` | Include subagent messages (excluded by default) |
| `--limit` / `-n` | Max entries/results to return |
| `--since` | Filter by time — bare dates use local timezone (e.g. `--since 2026-03-03`), full ISO timestamps use UTC |
| `--types` | Comma-separated entry types: `user`, `assistant`, `system` |
| `--no-tool-results` | Filter out tool result blocks — shows only human-typed messages and assistant text (read, recent) |
| `--brief` | Single-line condensed view per entry — shows conversation arc without full content (read) |
| `--last N` | Read N most recent sessions in one call — combine with `--brief` for arc views (read) |

## How Transcripts Work

Each Claude Code session produces a JSONL file at `~/.claude/projects/{project-slug}/{session-uuid}.jsonl`. Project slugs are the working directory path with `/` replaced by `-` (e.g., `/Users/mark/clawd` → `-Users-mark-clawd`).

Key things to know:
- **One session = one file.** Sessions don't span multiple files.
- **Subagent messages** have `isSidechain: true` and live in `{session-uuid}/subagents/agent-{hash}.jsonl`. The main file also contains subagent entries inline.
- **Streaming entries**: Assistant responses stream in as multiple JSONL lines sharing the same `requestId`. The script deduplicates these automatically.
- **Entry types**: `user`, `assistant`, `system`, `file-history-snapshot`, `progress`, `queue-operation`. The script skips noise types (snapshots, progress, queue) by default.

For the full schema, read [references/transcript-schema.md](references/transcript-schema.md).

## Workflow Patterns

### "What did I work on yesterday?"
```bash
python .../parse_transcript.py read --last 5 --brief --since 2026-02-27
```

### "Show me my last 10 sessions"
```bash
python .../parse_transcript.py ls -n 10
```

### "Show me the conversation arc from recent sessions"
```bash
python .../parse_transcript.py read --last 5 --brief --no-tool-results
```

### "Read user messages only (no tool output noise)"
```bash
python .../parse_transcript.py read <session-uuid> --types user --no-tool-results
```

### "Find where I discussed topic X"
```bash
python .../parse_transcript.py search "topic X" -n 20
```

### "What tools do I use most in project Y?"
```bash
python .../parse_transcript.py tools -p project-slug
```

### "Show me my workflow patterns this week"
```bash
python .../parse_transcript.py tools --since 2026-02-24
```

### "Read the full conversation from session Z"
```bash
python .../parse_transcript.py read <session-uuid>
```

## Interpreting Results

### Tool usage output
- **Tool calls**: Frequency of each tool (Bash, Read, Edit, etc.). High Edit/Write counts suggest code generation sessions. High Agent counts suggest delegation-heavy workflows. High Read counts before Edit suggests careful exploration before changes.
- **Recent examples**: Shows actual tool arguments so you can see patterns — which files get touched most, what commands get run.
- **Turn duration**: Wall-clock time per turn. Long turns often mean complex tool chains.

### When analyzing workflow patterns
- Look at tool call ratios — lots of Read before Edit suggests careful exploration
- Compare session lengths across projects to spot which projects involve longest sessions
- Search for error patterns (`"is_error": true` in tool results) to find friction points
- Look at Agent tool usage to understand delegation patterns

## Important Notes

- The script uses only Python stdlib — no dependencies needed.
- Large sessions (>100MB) may take a few seconds to parse. Use `--limit` to constrain output.
- Subagent transcripts are excluded by default because they add volume without always adding insight. Use `--include-subagents` when you specifically need to see what subagents did.
- When the user asks a vague question like "what did I do today", use `recent --since` with today's date first, then drill into specific sessions with `read` if needed.
