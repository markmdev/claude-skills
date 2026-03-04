#!/usr/bin/env python3
"""Parse and query Claude Code conversation transcripts.

Reads JSONL transcript files from ~/.claude/projects/ and provides
subcommands for listing sessions, reading conversations, searching,
and computing usage stats.
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Entry types that represent actual conversation turns
CONVERSATION_TYPES = {"user", "assistant"}
# Noise types to skip by default
SKIP_TYPES = {"file-history-snapshot", "progress", "queue-operation"}


def clean_content_blocks(content) -> list[dict]:
    """Extract clean content blocks from raw message content. No truncation."""
    if isinstance(content, str):
        return [{"type": "text", "text": content}] if content.strip() else []

    if not isinstance(content, list):
        return [{"type": "text", "text": str(content)}]

    blocks = []
    for block in content:
        if not isinstance(block, dict):
            continue

        block_type = block.get("type", "")

        if block_type == "text":
            text = block.get("text", "")
            if text.strip():
                blocks.append({"type": "text", "text": text})

        elif block_type == "thinking":
            # Skip thinking by default — internal reasoning, not workflow signal
            pass

        elif block_type == "tool_use":
            name = block.get("name", "unknown")
            inp = block.get("input", {})
            # Clean heavy fields from tool inputs
            clean_inp = {}
            for k, v in inp.items():
                if isinstance(v, str) and len(v) > 500:
                    clean_inp[k] = v[:500] + f"... [{len(v)} chars total]"
                else:
                    clean_inp[k] = v
            blocks.append({"type": "tool_use", "tool": name, "input": clean_inp})

        elif block_type == "tool_result":
            result_content = block.get("content", "")
            is_error = block.get("is_error", False)
            if isinstance(result_content, str):
                if len(result_content) > 500:
                    result_content = result_content[:500] + f"... [{len(result_content)} chars total]"
            else:
                result_content = "(complex content)"
            blocks.append({
                "type": "tool_result",
                "content": result_content,
                "is_error": is_error,
            })

    return blocks


def slim_entry(entry: dict) -> dict:
    """Strip an entry down to essential fields for clean JSON output. Full content, no truncation."""
    etype = entry.get("type", "")
    ts = entry.get("timestamp", "")

    if etype == "user":
        content = entry.get("message", {}).get("content", "")
        return {
            "timestamp": ts,
            "type": "user",
            "content": clean_content_blocks(content),
            "is_sidechain": entry.get("isSidechain", False),
        }

    elif etype == "assistant":
        msg = entry.get("message", {})
        content = msg.get("content", [])
        return {
            "timestamp": ts,
            "type": "assistant",
            "model": msg.get("model", ""),
            "content": clean_content_blocks(content),
            "is_sidechain": entry.get("isSidechain", False),
        }

    elif etype == "system":
        result = {"timestamp": ts, "type": "system", "subtype": entry.get("subtype", "")}
        if entry.get("subtype") == "turn_duration":
            result["duration_seconds"] = round(entry.get("durationMs", 0) / 1000, 1)
        return result

    return {"timestamp": ts, "type": etype}


def parse_timestamp(ts: str) -> datetime:
    """Parse ISO timestamp, handling both Z and +00:00 suffixes.

    Returns a timezone-aware datetime. Bare date strings (e.g. '2026-02-25')
    are interpreted as midnight in the local timezone — the intuitive meaning
    when a user types --since 2026-02-25. Full ISO timestamps with time
    components default to UTC if no timezone is specified.
    """
    # Bare date (no time component) → interpret as midnight local time
    if len(ts) <= 10 and "T" not in ts:
        local_tz = datetime.now().astimezone().tzinfo
        dt = datetime.fromisoformat(ts)
        return dt.replace(tzinfo=local_tz)

    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    # Ensure timezone-aware — naive datetimes default to UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def iter_jsonl(path: Path):
    """Yield parsed JSON objects from a JSONL file, skipping bad lines."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def get_project_dirs() -> list[Path]:
    """Return all project directories sorted by name."""
    if not PROJECTS_DIR.exists():
        return []
    return sorted(
        [d for d in PROJECTS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")],
        key=lambda p: p.name,
    )


def get_session_files(project_dir: Path) -> list[Path]:
    """Return JSONL session files in a project directory (not subagent files)."""
    return sorted(
        [f for f in project_dir.glob("*.jsonl") if f.stem != "sessions-index"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def session_summary(path: Path) -> dict | None:
    """Extract summary info from a session file without reading the whole thing."""
    first_user_msg = None
    first_ts = None
    last_ts = None
    msg_count = 0
    session_id = None
    version = None
    model = None
    git_branch = None

    for entry in iter_jsonl(path):
        entry_type = entry.get("type", "")
        if entry_type in SKIP_TYPES:
            continue

        ts = entry.get("timestamp")
        if ts:
            parsed = parse_timestamp(ts)
            if first_ts is None or parsed < first_ts:
                first_ts = parsed
            if last_ts is None or parsed > last_ts:
                last_ts = parsed

        if entry_type == "user" and not entry.get("isSidechain"):
            msg_count += 1
            if session_id is None:
                session_id = entry.get("sessionId")
            if version is None:
                version = entry.get("version")
            if git_branch is None:
                git_branch = entry.get("gitBranch")
            content = entry.get("message", {}).get("content", "")
            if isinstance(content, str) and content.strip() and first_user_msg is None:
                # Skip system commands
                if not content.startswith("<command-name>"):
                    first_user_msg = content[:200]

        elif entry_type == "assistant" and not entry.get("isSidechain"):
            msg_count += 1
            if model is None:
                model = entry.get("message", {}).get("model")

    if msg_count == 0:
        return None

    return {
        "session_id": session_id or path.stem,
        "file": str(path),
        "first_prompt": first_user_msg or "(no user message)",
        "message_count": msg_count,
        "started": first_ts.isoformat() if first_ts else None,
        "ended": last_ts.isoformat() if last_ts else None,
        "model": model,
        "version": version,
        "git_branch": git_branch,
        "file_size_kb": round(path.stat().st_size / 1024, 1),
    }


def dedup_assistant_entries(entries: list[dict]) -> list[dict]:
    """Merge streaming assistant entries — combine all content blocks per requestId.

    Claude Code streams responses incrementally: each JSONL entry for the same
    requestId contains only the latest content block (not the accumulated set).
    A single response producing [thinking, text, tool_use, tool_use] writes 4
    entries each with 1 block. We merge them into one entry with all 4 blocks.
    """
    seen_request_ids: dict[str, int] = {}
    result = []

    for entry in entries:
        if entry.get("type") == "assistant":
            req_id = entry.get("requestId")
            if req_id:
                if req_id in seen_request_ids:
                    # Merge content blocks into the existing entry
                    idx = seen_request_ids[req_id]
                    existing = result[idx]
                    existing_content = existing.get("message", {}).get("content", [])
                    new_content = entry.get("message", {}).get("content", [])
                    if isinstance(existing_content, list) and isinstance(new_content, list):
                        existing_content.extend(new_content)
                    # Update metadata from the latest entry (model, timestamp, etc.)
                    existing["timestamp"] = entry.get("timestamp", existing.get("timestamp", ""))
                    existing_msg = existing.get("message", {})
                    new_msg = entry.get("message", {})
                    if new_msg.get("model"):
                        existing_msg["model"] = new_msg["model"]
                    if new_msg.get("stop_reason"):
                        existing_msg["stop_reason"] = new_msg["stop_reason"]
                    continue
                seen_request_ids[req_id] = len(result)
        result.append(entry)

    return result


def format_content(content, no_tool_results: bool = False) -> str:
    """Format message content (string or array) into readable text.

    Args:
        content: Raw message content (string, list of blocks, or other).
        no_tool_results: If True, skip tool_result blocks entirely.
    """
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return str(content)

    parts = []
    for block in content:
        if not isinstance(block, dict):
            parts.append(str(block))
            continue

        block_type = block.get("type", "")

        if block_type == "text":
            text = block.get("text", "")
            if text.strip():
                parts.append(text)

        elif block_type == "thinking":
            # Skip thinking blocks — internal reasoning, not workflow signal
            pass

        elif block_type == "tool_use":
            name = block.get("name", "unknown")
            inp = block.get("input", {})
            # Show a compact representation of tool input
            if isinstance(inp, dict):
                if name == "Bash":
                    cmd = inp.get("command", "")
                    parts.append(f"[tool: {name}] {cmd}")
                elif name == "Read":
                    parts.append(f"[tool: {name}] {inp.get('file_path', '')}")
                elif name == "Write":
                    parts.append(f"[tool: {name}] {inp.get('file_path', '')}")
                elif name == "Edit":
                    parts.append(f"[tool: {name}] {inp.get('file_path', '')}")
                elif name == "Grep":
                    parts.append(f"[tool: {name}] pattern={inp.get('pattern', '')}")
                elif name == "Glob":
                    parts.append(f"[tool: {name}] {inp.get('pattern', '')}")
                elif name == "Agent":
                    desc = inp.get("description", "")
                    prompt = inp.get("prompt", "")
                    parts.append(f"[tool: {name}] {desc}" + (f"\n  {prompt}" if prompt else ""))
                else:
                    # Generic: show all key args
                    summary = ", ".join(f"{k}={str(v)[:200]}" for k, v in inp.items())
                    parts.append(f"[tool: {name}] {summary}")
            else:
                parts.append(f"[tool: {name}]")

        elif block_type == "tool_result":
            if no_tool_results:
                continue
            result_content = block.get("content", "")
            is_error = block.get("is_error", False)
            prefix = "[tool error]" if is_error else "[tool result]"
            if isinstance(result_content, str):
                if len(result_content) > 500:
                    result_content = result_content[:500] + f"... [{len(result_content)} chars total]"
                parts.append(f"{prefix} {result_content}")
            else:
                parts.append(f"{prefix} (complex content)")

    return "\n".join(parts)


def format_entry_readable(entry: dict, no_tool_results: bool = False) -> str:
    """Format a single entry as readable text.

    Args:
        entry: Parsed JSONL entry dict.
        no_tool_results: If True, skip tool_result blocks in content formatting.
    """
    entry_type = entry.get("type", "unknown")
    ts = entry.get("timestamp", "")
    if ts:
        try:
            dt = parse_timestamp(ts)
            ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            ts_str = ts
    else:
        ts_str = ""

    if entry_type == "user":
        is_sidechain = entry.get("isSidechain", False)
        role = "[subagent-user]" if is_sidechain else "[user]"
        content = format_content(entry.get("message", {}).get("content", ""),
                                 no_tool_results=no_tool_results)
        return f"{ts_str} {role}\n{content}\n"

    elif entry_type == "assistant":
        is_sidechain = entry.get("isSidechain", False)
        model = entry.get("message", {}).get("model", "")
        role = "[subagent-assistant]" if is_sidechain else "[assistant]"
        model_tag = f" ({model})" if model else ""
        content = format_content(entry.get("message", {}).get("content", []),
                                 no_tool_results=no_tool_results)
        return f"{ts_str} {role}{model_tag}\n{content}\n"

    elif entry_type == "system":
        subtype = entry.get("subtype", "")
        if subtype == "turn_duration":
            duration_ms = entry.get("durationMs", 0)
            return f"--- turn duration: {duration_ms/1000:.1f}s ---\n"
        elif subtype == "stop_hook_summary":
            return f"--- stop hooks ran ({entry.get('hookCount', 0)} hooks) ---\n"
        return f"--- system: {subtype} ---\n"

    return ""


def read_session(path: Path, include_subagents: bool = False,
                 entry_types: set | None = None,
                 since: datetime | None = None,
                 until: datetime | None = None,
                 limit: int | None = None,
                 no_tool_results: bool = False) -> list[dict]:
    """Read and filter entries from a session file.

    Args:
        path: Path to the JSONL session file.
        include_subagents: If True, include subagent (sidechain) entries.
        entry_types: If set, only include entries with these types.
        since: If set, only include entries after this timestamp.
        until: If set, only include entries before this timestamp.
        limit: If set, return only the last N entries.
        no_tool_results: If True, skip user entries that contain only tool_result
            blocks (no human-typed content).
    """
    entries = []
    for entry in iter_jsonl(path):
        etype = entry.get("type", "")

        # Skip noise types
        if etype in SKIP_TYPES:
            continue

        # Filter subagent entries
        if not include_subagents and entry.get("isSidechain", False):
            continue

        # Filter by entry type
        if entry_types and etype not in entry_types:
            continue

        # Filter by timestamp
        if since or until:
            ts = entry.get("timestamp")
            if ts:
                try:
                    entry_ts = parse_timestamp(ts)
                    if since and entry_ts < since:
                        continue
                    if until and entry_ts > until:
                        continue
                except (ValueError, TypeError):
                    pass

        # Skip user entries that are purely tool results (no human text)
        if no_tool_results and etype == "user":
            content = entry.get("message", {}).get("content", "")
            if isinstance(content, list) and content:
                if all(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                    continue

        entries.append(entry)

    # Deduplicate streaming assistant entries
    entries = dedup_assistant_entries(entries)

    # Apply limit (from the end — most recent)
    if limit and len(entries) > limit:
        entries = entries[-limit:]

    return entries


def compute_tool_stats(entries: list[dict]) -> dict:
    """Compute tool usage and workflow stats from a list of entries."""
    tool_counts: Counter = Counter()
    tool_args: defaultdict = defaultdict(list)  # tool -> list of key args
    models_used: Counter = Counter()
    turn_durations: list[float] = []
    user_msg_count = 0
    assistant_msg_count = 0

    for entry in entries:
        etype = entry.get("type", "")

        if etype == "user" and not entry.get("isSidechain"):
            content = entry.get("message", {}).get("content", "")
            if isinstance(content, str) and content.strip():
                user_msg_count += 1

        elif etype == "assistant":
            assistant_msg_count += 1
            msg = entry.get("message", {})
            model = msg.get("model", "unknown")
            models_used[model] += 1

            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "unknown")
                        tool_counts[name] += 1
                        # Capture key args for pattern analysis
                        inp = block.get("input", {})
                        if isinstance(inp, dict):
                            if name == "Bash":
                                cmd = inp.get("command", "")[:80]
                                tool_args[name].append(cmd)
                            elif name in ("Read", "Write", "Edit"):
                                tool_args[name].append(inp.get("file_path", ""))
                            elif name == "Agent":
                                tool_args[name].append(inp.get("description", "")[:60])

        elif etype == "system" and entry.get("subtype") == "turn_duration":
            turn_durations.append(entry.get("durationMs", 0) / 1000)

    return {
        "tool_calls": dict(tool_counts.most_common()),
        "total_tool_calls": sum(tool_counts.values()),
        "tool_examples": {k: v[:5] for k, v in tool_args.items()},  # top 5 examples per tool
        "models_used": dict(models_used),
        "user_messages": user_msg_count,
        "assistant_messages": assistant_msg_count,
        "turn_count": len(turn_durations),
        "total_duration_seconds": round(sum(turn_durations), 1) if turn_durations else None,
        "avg_turn_seconds": round(sum(turn_durations) / len(turn_durations), 1) if turn_durations else None,
    }


# ─── Subcommands ───────────────────────────────────────────────

def cmd_list_sessions(args):
    """List sessions across projects."""
    project_filter = args.project
    limit = args.limit or 20
    since = parse_timestamp(args.since) if args.since else None
    until = parse_timestamp(args.until) if args.until else None

    sessions = []

    for project_dir in get_project_dirs():
        if project_filter and project_filter not in project_dir.name:
            continue

        for session_file in get_session_files(project_dir):
            summary = session_summary(session_file)
            if summary:
                # Filter by start timestamp
                if summary.get("started"):
                    try:
                        started_ts = parse_timestamp(summary["started"])
                        if since and started_ts < since:
                            continue
                        if until and started_ts > until:
                            continue
                    except (ValueError, TypeError):
                        pass
                summary["project"] = project_dir.name
                sessions.append(summary)

    # Sort by start time, most recent first
    sessions.sort(key=lambda s: s.get("started") or "", reverse=True)
    sessions = sessions[:limit]

    if args.json:
        json.dump(sessions, sys.stdout, indent=2)
        print()
    else:
        for s in sessions:
            started = s.get("started", "unknown")[:19]
            prompt = s.get("first_prompt", "")[:80]
            project = s.get("project", "")
            msgs = s.get("message_count", 0)
            size = s.get("file_size_kb", 0)
            model = s.get("model", "")
            print(f"{started}  [{project}]  {msgs} msgs  {size}KB  {model}")
            print(f"  {prompt}")
            print(f"  id: {s['session_id']}")
            print()


def _find_session_file(session_id: str) -> Path | None:
    """Find a session file by exact or partial UUID match."""
    for project_dir in get_project_dirs():
        candidate = project_dir / f"{session_id}.jsonl"
        if candidate.exists():
            return candidate

    # Try partial match
    for project_dir in get_project_dirs():
        for f in project_dir.glob("*.jsonl"):
            if session_id in f.stem:
                return f

    return None


def _collect_sessions(project_filter: str | None = None,
                      since: datetime | None = None,
                      until: datetime | None = None) -> list[dict]:
    """Collect session summaries across projects, optionally filtered."""
    sessions = []
    for project_dir in get_project_dirs():
        if project_filter and project_filter not in project_dir.name:
            continue
        for session_file in get_session_files(project_dir):
            summary = session_summary(session_file)
            if summary:
                if summary.get("started"):
                    try:
                        started_ts = parse_timestamp(summary["started"])
                        if since and started_ts < since:
                            continue
                        if until and started_ts > until:
                            continue
                    except (ValueError, TypeError):
                        pass
                summary["project"] = project_dir.name
                sessions.append(summary)
    sessions.sort(key=lambda s: s.get("started") or "", reverse=True)
    return sessions


def _print_session(path: Path, args, entry_types, since,
                   no_tool_results: bool, until: datetime | None = None):
    """Read and print a single session's entries."""
    entries = read_session(
        path,
        include_subagents=args.include_subagents,
        entry_types=entry_types,
        since=since,
        until=until,
        limit=args.limit,
        no_tool_results=no_tool_results,
    )

    if args.json:
        json.dump([slim_entry(e) for e in entries], sys.stdout, indent=2, default=str)
        print()
    else:
        for entry in entries:
            formatted = format_entry_readable(entry, no_tool_results=no_tool_results)
            if formatted:
                print(formatted)


def cmd_read(args):
    """Read a specific session or batch-read recent sessions with --last N."""
    if not args.session_id and not args.last:
        print("Error: provide a session_id or --last N", file=sys.stderr)
        sys.exit(1)
    if args.session_id and args.last:
        print("Error: provide session_id or --last, not both", file=sys.stderr)
        sys.exit(1)

    entry_types = set(args.types.split(",")) if args.types else None
    since = parse_timestamp(args.since) if args.since else None
    until = parse_timestamp(args.until) if args.until else None
    no_tool_results = getattr(args, "no_tool_results", False)

    if args.session_id:
        found = _find_session_file(args.session_id)
        if not found:
            print(f"Session not found: {args.session_id}", file=sys.stderr)
            sys.exit(1)
        _print_session(found, args, entry_types, since, no_tool_results, until=until)
    else:
        # Batch read: --last N
        sessions = _collect_sessions(
            project_filter=args.project,
            since=since,
            until=until,
        )
        sessions = sessions[:args.last]

        for s in sessions:
            path = Path(s["file"])
            project = s.get("project", "")
            started = s.get("started", "")[:19]
            msg_count = s.get("message_count", 0)
            print(f"\n{'='*60}")
            print(f"  {project} — {started} — {msg_count} msgs")
            print(f"{'='*60}\n")
            _print_session(path, args, entry_types, since, no_tool_results, until=until)


def cmd_recent(args):
    """Show recent messages across sessions."""
    project_filter = args.project
    limit = args.limit or 50
    since = parse_timestamp(args.since) if args.since else None
    until = parse_timestamp(args.until) if args.until else None
    entry_types = set(args.types.split(",")) if args.types else None
    no_tool_results = getattr(args, "no_tool_results", False)

    all_entries = []

    for project_dir in get_project_dirs():
        if project_filter and project_filter not in project_dir.name:
            continue

        for session_file in get_session_files(project_dir):
            # Quick size check — skip tiny files
            if session_file.stat().st_size < 100:
                continue

            entries = read_session(
                session_file,
                include_subagents=args.include_subagents,
                entry_types=entry_types,
                since=since,
                until=until,
                no_tool_results=no_tool_results,
            )
            for e in entries:
                e["_project"] = project_dir.name
                e["_file"] = str(session_file)
            all_entries.extend(entries)

            # If we've collected way more than needed, stop early
            if len(all_entries) > limit * 10:
                break

    # Sort by timestamp
    all_entries.sort(
        key=lambda e: e.get("timestamp", ""),
        reverse=True,
    )
    all_entries = all_entries[:limit]
    # Reverse so oldest is first
    all_entries.reverse()

    if args.json:
        slim = []
        for e in all_entries:
            s = slim_entry(e)
            s["project"] = e.get("_project", "")
            slim.append(s)
        json.dump(slim, sys.stdout, indent=2, default=str)
        print()
    else:
        current_project = None
        for entry in all_entries:
            proj = entry.get("_project", "")
            if proj != current_project:
                current_project = proj
                print(f"\n{'='*60}")
                print(f"  Project: {proj}")
                print(f"{'='*60}\n")
            formatted = format_entry_readable(entry, no_tool_results=no_tool_results)
            if formatted:
                print(formatted)


def cmd_search(args):
    """Search transcripts for a keyword/pattern."""
    query = args.query.lower()
    project_filter = args.project
    limit = args.limit or 20
    since = parse_timestamp(args.since) if args.since else None
    until = parse_timestamp(args.until) if args.until else None
    no_tool_results = getattr(args, "no_tool_results", False)

    results = []

    for project_dir in get_project_dirs():
        if project_filter and project_filter not in project_dir.name:
            continue

        for session_file in get_session_files(project_dir):
            for entry in iter_jsonl(session_file):
                etype = entry.get("type", "")
                if etype in SKIP_TYPES:
                    continue
                if not args.include_subagents and entry.get("isSidechain", False):
                    continue

                # Filter by timestamp
                if since or until:
                    ts = entry.get("timestamp")
                    if ts:
                        try:
                            entry_ts = parse_timestamp(ts)
                            if since and entry_ts < since:
                                continue
                            if until and entry_ts > until:
                                continue
                        except (ValueError, TypeError):
                            pass

                # Skip user entries that are purely tool results
                if no_tool_results and etype == "user":
                    content_raw = entry.get("message", {}).get("content", "")
                    if isinstance(content_raw, list) and content_raw:
                        if all(isinstance(b, dict) and b.get("type") == "tool_result" for b in content_raw):
                            continue

                # Search in message content
                msg = entry.get("message", {})
                content = msg.get("content", "")
                content_str = format_content(content, no_tool_results=no_tool_results)

                if query in content_str.lower():
                    results.append({
                        "project": project_dir.name,
                        "session_id": entry.get("sessionId", session_file.stem),
                        "timestamp": entry.get("timestamp", ""),
                        "type": etype,
                        "role": msg.get("role", etype),
                        "match_context": _extract_match_context(content_str, query),
                        "file": str(session_file),
                    })

                    if len(results) >= limit:
                        break
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    if args.json:
        json.dump(results, sys.stdout, indent=2)
        print()
    else:
        for r in results:
            ts = r["timestamp"][:19] if r["timestamp"] else "unknown"
            print(f"{ts}  [{r['project']}]  {r['role']}")
            print(f"  {r['match_context']}")
            print(f"  session: {r['session_id']}")
            print()


def _extract_match_context(text: str, query: str, context_chars: int = 120) -> str:
    """Extract text around the first match of query."""
    lower = text.lower()
    idx = lower.find(query)
    if idx == -1:
        return text[:context_chars]
    start = max(0, idx - context_chars // 2)
    end = min(len(text), idx + len(query) + context_chars // 2)
    snippet = text[start:end].replace("\n", " ")
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def cmd_tools(args):
    """Analyze tool usage patterns."""
    project_filter = args.project
    since = parse_timestamp(args.since) if args.since else None
    until = parse_timestamp(args.until) if args.until else None

    all_entries = []
    session_count = 0

    for project_dir in get_project_dirs():
        if project_filter and project_filter not in project_dir.name:
            continue

        for session_file in get_session_files(project_dir):
            entries = read_session(
                session_file,
                include_subagents=args.include_subagents,
                since=since,
                until=until,
            )
            if entries:
                session_count += 1
                all_entries.extend(entries)

    stats = compute_tool_stats(all_entries)
    stats["session_count"] = session_count

    if args.json:
        json.dump(stats, sys.stdout, indent=2)
        print()
    else:
        print(f"Sessions: {stats['session_count']}")
        print(f"User messages: {stats['user_messages']}")
        print(f"Assistant messages: {stats['assistant_messages']}")
        print(f"Turns: {stats['turn_count']}")
        if stats["total_duration_seconds"]:
            print(f"Total time: {stats['total_duration_seconds']:.0f}s ({stats['total_duration_seconds']/60:.1f}m)")
            print(f"Avg turn:   {stats['avg_turn_seconds']:.1f}s")
        print()
        print(f"Tool calls ({stats['total_tool_calls']} total):")
        for tool, count in sorted(stats["tool_calls"].items(), key=lambda x: -x[1]):
            pct = (count / stats["total_tool_calls"] * 100) if stats["total_tool_calls"] else 0
            bar = "#" * int(pct / 2)
            print(f"  {tool:20s} {count:5d}  {pct:4.1f}%  {bar}")
        print()
        # Show recent examples for top tools
        examples = stats.get("tool_examples", {})
        if examples:
            print("Recent examples (top tools):")
            for tool in list(stats["tool_calls"].keys())[:3]:
                if tool in examples and examples[tool]:
                    print(f"\n  {tool}:")
                    for ex in examples[tool][:3]:
                        print(f"    - {ex[:100]}")


def main():
    parser = argparse.ArgumentParser(
        description="Parse and query Claude Code conversation transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common args
    def add_common_args(sub):
        sub.add_argument("--json", action="store_true", help="Output as JSON")
        sub.add_argument("--project", "-p", help="Filter to project (partial match)")
        sub.add_argument("--include-subagents", action="store_true",
                         help="Include subagent transcripts")

    # list-sessions
    ls = subparsers.add_parser("list-sessions", aliases=["ls"],
                               help="List sessions across projects")
    add_common_args(ls)
    ls.add_argument("--limit", "-n", type=int, default=20, help="Max sessions to show")
    ls.add_argument("--since", help="Only sessions after this ISO timestamp")
    ls.add_argument("--until", help="Only sessions before this ISO timestamp")
    ls.set_defaults(func=cmd_list_sessions)

    # read
    rd = subparsers.add_parser("read", help="Read a specific session")
    add_common_args(rd)
    rd.add_argument("session_id", nargs="?", default=None,
                    help="Session UUID (or partial match)")
    rd.add_argument("--last", type=int, help="Read N most recent sessions")
    rd.add_argument("--no-tool-results", action="store_true",
                    help="Filter out tool_result blocks from output")
    rd.add_argument("--limit", "-n", type=int, help="Max entries to show")
    rd.add_argument("--since", help="Only entries after this ISO timestamp")
    rd.add_argument("--until", help="Only entries before this ISO timestamp")
    rd.add_argument("--types", help="Comma-separated entry types (user,assistant,system)")
    rd.set_defaults(func=cmd_read)

    # recent
    rc = subparsers.add_parser("recent", help="Show recent messages across sessions")
    add_common_args(rc)
    rc.add_argument("--no-tool-results", action="store_true",
                    help="Filter out tool_result blocks from output")
    rc.add_argument("--limit", "-n", type=int, default=50, help="Max entries to show")
    rc.add_argument("--since", help="Only entries after this ISO timestamp")
    rc.add_argument("--until", help="Only entries before this ISO timestamp")
    rc.add_argument("--types", help="Comma-separated entry types (user,assistant,system)")
    rc.set_defaults(func=cmd_recent)

    # search
    sr = subparsers.add_parser("search", help="Search transcripts for a keyword")
    add_common_args(sr)
    sr.add_argument("query", help="Search query (case-insensitive)")
    sr.add_argument("--no-tool-results", action="store_true",
                     help="Skip tool_result entries when searching")
    sr.add_argument("--limit", "-n", type=int, default=20, help="Max results")
    sr.add_argument("--since", help="Only entries after this ISO timestamp")
    sr.add_argument("--until", help="Only entries before this ISO timestamp")
    sr.set_defaults(func=cmd_search)

    # tools
    tl = subparsers.add_parser("tools", help="Analyze tool usage patterns")
    add_common_args(tl)
    tl.add_argument("--since", help="Only entries after this ISO timestamp")
    tl.add_argument("--until", help="Only entries before this ISO timestamp")
    tl.set_defaults(func=cmd_tools)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
