---
name: release
description: >
  Automate the full release pipeline — detect version scheme, generate changelog
  from commits, bump version, commit, tag, push, and create a GitHub Release.
  Works on any project by auto-detecting version sources and changelog format.
  Use this skill whenever the user says "release", "ship it", "tag and push",
  "commit and release", "bump version", "create a release", "new version",
  or any variation of publishing/tagging a new version. Also use when the user
  asks to "update the changelog" or "prepare a release" even if they don't
  explicitly say "release".
---

# Release

Automate the release pipeline from version detection through GitHub Release creation.

## Step 1: Detect Current Version

Find the version source. Check in this order. Record ALL files that contain a version — you'll update all of them in Step 4. The first match determines the canonical current version.

1. `package.json` → `version` field
2. `Cargo.toml` → `version` under `[package]`
3. `pyproject.toml` → `version` under `[project]` or `[tool.poetry]`
4. `.meridian/.version` → plain text version string
5. `VERSION` or `VERSION.txt` → plain text
6. `.claude-plugin/plugin.json` → `version` field
7. Git tags → first, run `git fetch --tags` to sync with remote, then find the latest semver tag: `git tag --sort=-v:refname | grep -E '^v?[0-9]' | head -1`

If nothing is found, ask the user what version to start from.

## Step 2: Determine the Bump

Get commits since the last tag:

```bash
git log $(git describe --tags --abbrev=0 2>/dev/null || git rev-list --max-parents=0 HEAD)..HEAD --oneline
```

Categorize each commit to determine bump type:

| Signal | Bump |
|--------|------|
| `BREAKING CHANGE:` in body, or `!` after type (e.g., `feat!:`) | **major** |
| `feat:`, `feature:`, or message clearly adds new functionality ("add", "implement", "new") | **minor** |
| Everything else: `fix:`, `chore:`, `refactor:`, `docs:`, `test:`, bug fixes, cleanup | **patch** |

The overall bump is the **highest** category found across all commits.

**Before proceeding**, show the user:
- Current version
- Proposed new version
- The commits that will be included (one-line each)

Wait for confirmation. The user might override the bump type.

## Step 3: Generate Changelog Entry

Check if `CHANGELOG.md` exists.

**If it exists**: Read the first 50 lines to understand the format (heading style, grouping, date format, whether it uses Keep a Changelog format, etc.). Match the existing style exactly.

**If it doesn't exist**: Create one using this format:

```markdown
# Changelog

## [X.Y.Z] - YYYY-MM-DD

### Added
- Feature descriptions

### Fixed
- Bug fix descriptions

### Changed
- Other changes
```

Write human-readable descriptions — not raw commit messages. A commit saying "feat(auth): implement JWT-based authentication" becomes "JWT-based authentication". Focus on what changed from a user's perspective.

Insert the new entry at the top, after any file header or title.

## Step 4: Update Version Files

Update every file identified in Step 1:
- `package.json` → update the `version` field
- `Cargo.toml` → update the `version` field
- `.meridian/.version` → replace file content
- `VERSION` / `VERSION.txt` → replace file content
- `.claude-plugin/plugin.json` → update the `version` field
- Any other files that embed the version (README badges, etc.) — search if unsure

If the project has `package-lock.json`, run `npm install --package-lock-only` to sync it.

## Step 5: Commit, Tag, Push

```bash
git add -A
git commit -m "Release vX.Y.Z"
git tag vX.Y.Z
git push origin <current-branch> --tags
```

Push to the current branch. Don't create a new branch.

## Step 6: Create GitHub Release

```bash
gh release create vX.Y.Z \
  --title "vX.Y.Z — <short summary>" \
  --notes "<release notes>"
```

**Title**: Include a short, descriptive summary of the most significant change. Examples: "v0.6.0 — Plugin Architecture", "v1.2.0 — Dark Mode", "v0.3.1 — Fix Token Refresh".

**Notes**: Describe user-facing changes — what's new, what's fixed, what's changed. Group by category if there are many changes. Not implementation details, not commit hashes.

If the project has install or upgrade instructions (like `go install ...@vX.Y.Z`, `npm install`, `curl | bash`), include them at the bottom of the release notes.

## Step 7: Update Marketplace (if applicable)

If the project has a `.claude-plugin/plugin.json`, it may be distributed via a marketplace repo. Check if a marketplace exists by looking for a marketplace repo reference in the project's docs or CLAUDE.md.

If the project is listed in a marketplace (e.g., `markmdev/claude-plugins`):

1. Clone or pull the marketplace repo
2. Update the `version` field for this plugin in `.claude-plugin/marketplace.json`
3. Commit and push

**This step is critical.** Without updating the marketplace version, `/plugin update` will not pull the new release — it reads the version from the marketplace manifest, not from the plugin repo's tags.

## Edge Cases

- **No commits since last tag**: Tell the user there's nothing to release. Don't create an empty release.
- **Dirty working tree**: Ask whether to include uncommitted changes in the release or stash them first.
- **No changelog file**: Create one — don't skip changelog generation.
- **Multiple version files**: Update all of them to stay in sync.
- **Pre-1.0 projects**: Treat minor bumps as patch bumps (0.1.0 → 0.1.1 for features) unless the user says otherwise.
