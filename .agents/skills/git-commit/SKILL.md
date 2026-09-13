---
name: git-commit
description: "Execute intelligent Git commits using Conventional Commits. Use when the user asks to commit changes, create a git commit, or mentions /commit. Analyze all current changes, intelligently group files by logical change, and automatically create one or more commits as needed."
license: MIT
allowed-tools: Bash
---

# Git Commit with Conventional Commits

## Overview

Create clean, semantic Git commits using the Conventional Commits specification.

When invoked, this skill must inspect the repository's current Git state and all relevant uncommitted changes. It must intelligently determine whether the changes represent one logical change or multiple independent logical changes.

The goal is:

* Analyze the complete current working state.
* Identify all relevant uncommitted changes.
* Group related files into logical changes.
* Create separate commits for separate logical changes.
* Ensure every intended change is committed unless explicitly excluded.
* Never require the user to manually specify which files belong to each commit when the grouping can be determined from the changes.

## Important Behavior

### No Continuous Monitoring

This skill does **not** continuously monitor or watch the repository.

It only analyzes the repository state when the skill is explicitly invoked.

When invoked, it must analyze the changes that exist at that point in time.

---

# Conventional Commit Format

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Commit Types

| Type       | Purpose                                       |
| ---------- | --------------------------------------------- |
| `feat`     | New feature                                   |
| `fix`      | Bug fix                                       |
| `docs`     | Documentation only                            |
| `style`    | Formatting/style changes with no logic change |
| `refactor` | Code refactor with no feature/fix             |
| `perf`     | Performance improvement                       |
| `test`     | Add/update tests                              |
| `build`    | Build system/dependency changes               |
| `ci`       | CI/configuration changes                      |
| `chore`    | Maintenance/miscellaneous                     |
| `revert`   | Revert a previous commit                      |

---

# Workflow

When the skill is invoked, follow this workflow completely.

## 1. Inspect Repository State

Always begin by checking the repository status.

```bash
git status --short
```

Then inspect both unstaged and staged changes:

```bash
git diff
git diff --staged
```

Also inspect untracked files:

```bash
git status --porcelain
```

Do not assume that only modified tracked files matter.

The analysis must consider:

* Modified files
* Deleted files
* Renamed files
* Added files
* Untracked files
* Already staged files
* Partially staged files

---

# 2. Analyze ALL Changes

Analyze the complete set of current uncommitted changes.

Determine:

* What changed?
* Why did it change?
* Which files belong together?
* Which changes represent the same feature?
* Which changes represent a bug fix?
* Which changes are documentation?
* Which changes are tests?
* Which changes are configuration/build changes?
* Are there unrelated changes mixed together?

Use the actual diff and file contents where necessary.

Do not generate commit messages based only on filenames.

---

# 3. Detect Logical Commit Groups

The skill must intelligently divide changes into logical groups.

A **logical commit** should represent one coherent change that can be understood and reverted independently.

For example, if the repository contains:

```text
src/auth/login.ts
src/auth/login.test.ts
docs/auth.md

src/payment/payment.ts
src/payment/payment.test.ts
```

and the changes indicate two independent features, create separate commits:

```text
feat(auth): add login functionality
feat(payment): add payment processing
```

The test files belonging to each feature should remain with their corresponding feature commit.

---

# 4. Multiple Features in One Working Section

If the user has made multiple independent features or changes before invoking the skill, do NOT assume everything should be one commit.

For example:

```text
Feature A:
  src/auth/*
  tests/auth/*

Feature B:
  src/dashboard/*
  tests/dashboard/*
```

The skill should identify the two logical groups and create:

```text
feat(auth): add authentication
feat(dashboard): add dashboard
```

in separate commits.

---

# 5. Intelligent File Staging

If multiple logical changes are detected, stage only the files belonging to the current logical group.

Example:

```bash
git add src/auth/login.ts
git add src/auth/login.test.ts
```

Then commit that group.

After the commit succeeds, continue with the remaining changes.

Do not commit unrelated files together merely because they were modified at the same time.

---

# 6. Repeat Until All Intended Changes Are Handled

When multiple logical groups exist, repeat the following process:

```text
Analyze remaining changes
        ↓
Identify next logical group
        ↓
Stage only that group's files
        ↓
Generate commit message
        ↓
Commit
        ↓
Inspect remaining changes
        ↓
Repeat
```

Continue until all intended committable changes have been processed.

For example:

```text
Working tree:
  Feature A
  Feature B
  Documentation update
  Bug fix
```

The skill should be capable of producing:

```text
feat(...): ...
feat(...): ...
docs(...): ...
fix(...): ...
```

as separate commits when the changes are logically independent.

---

# 7. Preserve Already-Staged Changes

If the user has already staged changes, inspect them carefully.

Do not blindly reset or unstage user changes.

If staged changes clearly represent one logical commit, commit them appropriately.

If staged and unstaged changes are separate logical changes, preserve the user's staged state as much as possible and handle the remaining changes independently.

Never discard user work.

---

# 8. Partially Staged Files

A single file may contain changes belonging to different logical commits.

When this occurs, do not automatically commit the entire file if doing so would mix unrelated changes.

Use interactive or patch-based staging when appropriate:

```bash
git add -p
```

The goal is to stage only the hunks belonging to the current logical commit.

---

# 9. Untracked Files

Inspect untracked files before committing.

Determine whether they belong to an existing logical change.

For example:

```text
src/auth/service.ts
src/auth/service.test.ts
```

may belong to the same feature even if both are currently untracked.

Add them to the appropriate logical commit.

Do not automatically commit files that appear to contain secrets or sensitive configuration.

---

# 10. Secret and Sensitive File Protection

Never commit secrets.

Do not stage or commit files such as:

```text
.env
.env.*
*.pem
*.key
credentials.json
service-account.json
```

or other files containing:

* API keys
* Access tokens
* Passwords
* Private keys
* Cloud credentials
* Database credentials
* Authentication secrets

If a potentially sensitive file is detected, leave it uncommitted and clearly report that it was excluded.

Do not expose secret values in the response.

---

# 11. Generate Commit Message

For each logical commit, analyze its staged diff and determine:

### Type

Choose the most appropriate Conventional Commit type.

### Scope

Use a scope when a meaningful module, component, domain, or subsystem can be identified.

Examples:

```text
feat(auth): add login flow
fix(api): handle invalid requests
docs(readme): update setup instructions
test(payment): add refund tests
```

### Description

The description must:

* Clearly describe the actual change.
* Use imperative/present tense.
* Be concise.
* Prefer fewer than 72 characters.
* Avoid vague descriptions such as `update code` or `changes`.

Prefer:

```text
feat(auth): add token refresh flow
```

over:

```text
feat(auth): update authentication files
```

---

# 12. Breaking Changes

Use the Conventional Commits breaking-change syntax when appropriate.

Examples:

```text
feat!: remove deprecated endpoint
```

or:

```text
feat(api): change authentication response format

BREAKING CHANGE: authentication responses no longer include token metadata
```

Only mark a change as breaking when the actual change is incompatible with existing behavior.

---

# 13. Commit Execution

For each logical group, execute the commit only after verifying the staged diff.

Before committing:

```bash
git diff --staged
```

Then commit:

```bash
git commit -m "<type>[scope]: <description>"
```

For commits requiring a body/footer:

```bash
git commit -m "$(cat <<'EOF'
<type>[scope]: <description>

<body>

<footer>
EOF
)"
```

---

# 14. Verify After Every Commit

After each successful commit, inspect the repository again:

```bash
git status --short
```

and inspect the remaining changes:

```bash
git diff
git diff --staged
```

This is required when multiple commits are being created.

Never assume that the first commit handled all changes.

Continue processing remaining logical changes until the intended changes are committed.

---

# 15. Final Verification

After processing all logical commit groups, run:

```bash
git status --short
```

Confirm that:

* All intended changes were committed.
* No unrelated changes were accidentally committed.
* Sensitive files remain uncommitted.
* No unexpected changes were discarded.
* Multiple logical changes were separated into multiple commits where appropriate.

If unrelated changes remain, leave them untouched and explain why they were not included.

---

# Git Safety Protocol

## Never

* Never update Git configuration.
* Never modify global Git configuration.
* Never modify user identity/configuration.
* Never use `git reset --hard`.
* Never use destructive commands to discard user changes.
* Never use `git clean -fd` or similar destructive cleanup.
* Never force push.
* Never force push to `main` or `master`.
* Never skip Git hooks using `--no-verify` unless explicitly requested.
* Never amend an existing commit unless explicitly requested.
* Never rewrite existing commit history unless explicitly requested.
* Never commit secrets.
* Never discard unrelated user changes.

## Commit Hook Failures

If a commit fails because of a Git hook:

1. Inspect the failure.
2. Determine whether the failure can safely be fixed.
3. Make the necessary correction if appropriate.
4. Re-stage the affected changes.
5. Create a **new commit**.

Do not use `--no-verify` unless the user explicitly requests it.

Do not amend the previous commit merely to bypass the failure.

---

# Commit Grouping Principles

Prefer:

```text
One logical change = One commit
```

Examples:

```text
Feature + its tests
→ one commit

Bug fix + regression test
→ one commit

Two unrelated features
→ two commits

Feature + unrelated README change
→ separate commits

Refactor unrelated to feature
→ separate commit
```

When uncertain whether two changes belong together, use the actual dependency and purpose of the changes rather than simply grouping by directory.

---

# Important Final Rule

When invoked, this skill must treat the repository's current uncommitted state as the complete input for the commit operation.

It must:

1. Inspect all current changes.
2. Understand the changes.
3. Detect logical groups.
4. Stage appropriate files/hunks.
5. Create one commit per logical change.
6. Re-inspect the repository after every commit.
7. Continue until all intended committable changes have been handled.
8. Leave unrelated or sensitive changes untouched.
9. Never continuously monitor the repository between invocations.