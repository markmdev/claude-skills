---
name: discuss
description: >
  Discuss a problem with other AI agents before implementing. Spawns one or more
  autonomous claude -p conversations with different perspectives (architect, critic,
  domain expert), runs multi-round discussions, and synthesizes findings. Use when
  facing design decisions, architecture tradeoffs, knowledge organization questions,
  or any problem that benefits from multiple viewpoints before committing to an approach.
  Also use proactively when you're uncertain about a direction.
---

# Discuss

Have autonomous conversations with other AI agents to explore a problem from multiple angles before implementing.

## When to Use

- Design decisions with multiple valid approaches
- Architecture tradeoffs you're uncertain about
- Knowledge organization and structure questions
- Anything where a second (or third) opinion would help
- Proactively — when you catch yourself unsure about a direction

## How It Works

You spawn `claude -p` subprocesses as discussion partners. Each gets a different system prompt defining its perspective. You drive the conversation for multiple rounds, then synthesize the insights back to the user.

## Spawning a Discussion Partner

```bash
# Generate a session ID for the conversation
UUID=$(python3 -c "import uuid; print(uuid.uuid4())")

# First message — set the role via --system-prompt
unset CLAUDECODE && claude -p "<your question>" \
  --system-prompt "<role description>" \
  --session-id "$UUID" \
  --setting-sources local \
  --model claude-opus-4-6

# Follow-up rounds — resume the same session
unset CLAUDECODE && claude -p "<follow-up>" \
  -r "$UUID" \
  --setting-sources local
```

Run from a temp directory (`/tmp/discuss-<topic>/`) to avoid project interference.

### Key flags

| Flag | Purpose |
|------|---------|
| `--system-prompt "..."` | Define the agent's perspective/role |
| `--session-id <uuid>` | Control session ID for first message |
| `-r <uuid>` | Resume conversation for follow-ups |
| `--setting-sources local` | No CLAUDE.md, no hooks — clean discussion |
| `--model claude-opus-4-6` | Always use Opus for discussion quality |

**Do NOT use `--no-session-persistence`** — that prevents resuming.

## Perspectives to Spawn

Define each perspective via `--system-prompt`. Tailor to the problem. Examples:

**Architecture review:**
- "You are a senior software architect. Focus on system design, scalability, and maintainability. Challenge assumptions. Prefer simple solutions over clever ones."
- "You are a pragmatic engineer who ships fast. Push back on over-engineering. Ask: what's the simplest thing that could work?"

**Knowledge/docs organization:**
- "You are an information architect. Focus on discoverability, cross-linking, and preventing knowledge rot. How would a newcomer find what they need?"
- "You are a minimalist editor. Challenge whether each piece of content earns its place. Less is more."

**Design decisions:**
- "You are an advocate for approach A. Make the strongest case you can."
- "You are an advocate for approach B. Make the strongest case you can."
- "You are a neutral evaluator. Listen to both sides and identify which arguments are strongest."

## Conversation Flow

1. **Frame the problem.** Give each agent the full context — what you're deciding, what constraints exist, what you've considered so far.

2. **Run 2-4 rounds.** After each response, follow up with probing questions, counterarguments, or new information. Don't just accept the first answer.

3. **Cross-pollinate.** Share agent A's argument with agent B: "Another perspective suggests X. What's your response?" This creates genuine debate.

4. **Synthesize.** After the discussions, summarize to the user:
   - What each perspective recommended
   - Where they agreed (high confidence)
   - Where they disagreed (needs user judgment)
   - Your recommendation based on the discussion

## Parallel Discussions

For speed, run multiple perspectives in parallel using Bash background processes:

```bash
# Spawn two perspectives simultaneously
(unset CLAUDECODE && claude -p "..." --system-prompt "architect" --session-id "$UUID_A" --setting-sources local --model claude-opus-4-6 > /tmp/discuss/architect.txt) &
(unset CLAUDECODE && claude -p "..." --system-prompt "pragmatist" --session-id "$UUID_B" --setting-sources local --model claude-opus-4-6 > /tmp/discuss/pragmatist.txt) &
wait
```

Then read both responses and cross-pollinate in follow-up rounds.

## Rules

- **Always synthesize back to the user.** The discussion is a tool, not the deliverable. Present clear findings.
- **Don't fabricate consensus.** If the agents disagree, say so. Let the user decide.
- **Keep rounds focused.** 2-4 rounds per agent. Diminishing returns after that.
- **Clean up.** The conversations persist in temp dirs. They're disposable — don't reference them across sessions.
