# Claude Code Transcript Schema

Reference for the JSONL transcript format used by Claude Code.

## File Organization

```
~/.claude/projects/
  {project-slug}/                       # e.g. -Users-mark-clawd
    sessions-index.json                  # Optional session index
    {session-uuid}.jsonl                 # One file per session
    {session-uuid}/                      # Per-session directory (optional)
      subagents/
        agent-{hash}.jsonl               # Subagent transcripts
      tool-results/
        toolu_{id}.txt                   # Externalized tool outputs
        toolu_{id}.json                  # Structured tool outputs (images)
```

**Project slug**: Working directory path with `/` → `-` and leading `-`.
Example: `/Users/mark/clawd` → `-Users-mark-clawd`

**Session files**: UUID4 filenames like `deaf3112-7eb8-4613-b2ec-7b0e0a1f8e6e.jsonl`

## Entry Types

Each JSONL line is a self-contained JSON object with a `type` field.

### type: "user"

User messages and tool results.

**Key fields:**
- `message.role`: always `"user"`
- `message.content`: **string** for human messages, **array** for tool results
- `parentUuid`: links to previous message (null for first)
- `isSidechain`: true for subagent messages
- `sessionId`, `version`, `gitBranch`, `cwd`
- `timestamp`: ISO 8601

**Tool result content block:**
```json
{
  "type": "tool_result",
  "content": "output text",
  "is_error": false,
  "tool_use_id": "toolu_..."
}
```

### type: "assistant"

Assistant responses with tool calls and thinking.

**Key fields:**
- `message.model`: e.g. `"claude-opus-4-6"`
- `message.content`: array of content blocks
- `message.usage`: token counts
- `message.stop_reason`: `"tool_use"` or null
- `requestId`: groups streaming entries (multiple lines share same requestId)

**Content block types:**
- `{"type": "text", "text": "..."}` — plain text
- `{"type": "thinking", "thinking": "...", "signature": "..."}` — extended thinking
- `{"type": "tool_use", "id": "toolu_...", "name": "Bash", "input": {...}}` — tool invocation

**Streaming behavior**: A single API request produces multiple JSONL lines as content blocks stream in. Each shares the same `requestId`. Take the **last entry per requestId** for the complete response.

### type: "system"

System events.

**Subtypes:**
- `"turn_duration"` — `durationMs` field, how long a turn took
- `"stop_hook_summary"` — records stop hook execution

### type: "file-history-snapshot"

File change tracking for undo/restore. Metadata, not conversation.

### type: "progress"

Hook and agent progress events. High-volume noise — skip in most analyses.

### type: "queue-operation"

Message queue management (enqueue, dequeue, popAll).

## Token Usage

Found in `assistant` entries at `message.usage`:

```json
{
  "input_tokens": 3,
  "cache_creation_input_tokens": 26,
  "cache_read_input_tokens": 21334,
  "output_tokens": 14,
  "service_tier": "standard"
}
```

## Message Threading

Messages form a tree via `parentUuid` → `uuid`. The first message has `parentUuid: null`. Subagent messages are interleaved with `isSidechain: true`.
