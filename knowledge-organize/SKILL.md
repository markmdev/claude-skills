---
name: knowledge-organize
description: >
  Organize and curate the knowledge graph — review docs for staleness, duplication,
  missing links, structural issues, and unrecorded knowledge from recent sessions.
  Use when the user says "organize knowledge", "knowledge organize", "clean up knowledge",
  "tidy knowledge", "review knowledge", or wants to restructure domain documentation.
  Can target a specific domain or review everything.
disable-model-invocation: true
---

# Knowledge Organize

Periodic curation of the knowledge graph at `knowledge/`. Reviews docs for staleness, duplication, missing links, structural issues, and mines recent sessions for unrecorded knowledge.

## Step 1: Determine Scope

`$ARGUMENTS` is an optional domain name and flags.

- `/knowledge-organize` — all domains
- `/knowledge-organize x-growth` — single domain
- `/knowledge-organize x-growth --since 7d` — with time window for transcript mining

Read `knowledge/_index.md` to see all domains. If targeting a specific domain, read that domain's `_index.md` too.

## Step 2: Inventory Current State

For each domain in scope:

- List every doc in the folder (including any not listed in `_index.md`)
- Check cross-links between docs (grep for markdown links)
- Check last-modified dates via `git log`
- Note doc sizes (too large → split, too thin → merge)

## Step 3: Mine Recent Sessions

Activate the `/transcript-parser` skill — it provides commands for listing sessions, reading transcripts, and searching across conversations. Use it to find:

- Discussions about topics in the target domain(s) that weren't documented
- New facts, strategies, or insights that were discussed but never written to `knowledge/`
- Corrections to existing knowledge
- New topics that emerged but have no docs yet

Also check `memory/daily/` logs from the same period for knowledge-relevant entries.

Default time window: 7 days. Adjustable via `--since` flag.

## Step 4: Analyze for Issues

Check for:

**Staleness** — outdated information, dates that have passed, status fields that no longer reflect reality

**Duplication** — docs covering the same topic that should be merged, content duplicated across docs

**Missing links** — docs that mention topics covered by sibling docs but don't link, cross-domain connections that aren't linked, people referenced that should link to `knowledge/people/`

**Structural issues** — docs too large (split), too thin (merge), missing `_index.md`, docs without `summary` frontmatter

**Index drift** — `_index.md` files that don't list all docs in their folder

**Gaps** — topics discussed in sessions that have no docs, gaps listed in `_index.md` that now have enough content to fill

## Step 5: Execute Changes

Act on each issue found:

- Stale content → update with current info
- Duplicates → merge into better-structured doc
- Missing links → add inline markdown links
- Structural issues → split, merge, reorganize
- Gaps → create new docs from session content
- Index drift → update all affected `_index.md` files

Document format for new/updated docs:

- `summary` in frontmatter (mandatory, under 120 chars)
- Only `_index.md` files get `read_when` (for Reflex routing)
- Standard markdown relative links (not wiki-style)
- Useful prose, not just metadata containers

## Step 6: Report

Present a concise summary:

- **Changes made** (created/updated/merged/split with reasons)
- **New docs created** (what they cover, sourced from where)
- **Links added** (count)
- **Gaps remaining** (what still needs research or future sessions)

## Important Notes

- This skill modifies files — `disable-model-invocation` is true so the user triggers it deliberately
- The knowledge doc format: `summary` in frontmatter, useful prose body, inline markdown links, See Also section for related docs
- `_index.md` is the authoritative map of each domain — always update it after changes
