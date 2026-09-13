---
name: create-branch
description: Create and switch to a new Git branch for the user's upcoming work, always based on the latest remote main and following the repository's branch conventions. Use this skill whenever the user asks to create or start a new branch, "make a branch for X", wants to set up a work branch before starting a feature, fix, refactor, docs change, test change, chore, or CI change — even if they don't explicitly say "branch". Also use it when they mention starting work on something and a new branch would be needed. Do not use for committing, pushing, merging, or rebasing.
---

# Create Branch

Create and switch to a new Git branch for the user's upcoming work while strictly following the repository's branch conventions.

This skill is responsible **only for branch creation and checkout**. Do not commit, push, merge, rebase, or modify project files unless explicitly requested by the user.

## Required input

Determine a **brief description of the work the user is about to do**. The description is required because it drives a meaningful branch name.

- If the user already gave a description, use it directly. Do not ask them to repeat it.
- If no description was given, ask for a short description of the feature, bug fix, refactor, documentation change, test change, or other work they're about to do. For example:
  > What are you going to work on? Give me a brief description so I can create a meaningful branch name.

Do **not** create a generic branch such as `feature/work`, `feature/update`, or `feature/my-feature` merely because the description is missing, and do not proceed until a meaningful description is available.

## Branch naming

Follow the repository's branch convention:

```text
<type>/<short-description>
```

Allowed branch types:

```text
feature/
fix/
hotfix/
refactor/
docs/
test/
chore/
build/
ci/
```

Choose the type that best matches the user's intended work. Build the branch name from the description using these rules:

- Lowercase only.
- Use hyphens between words.
- Remove unnecessary words.
- Describe the work, not the developer.
- Keep it concise.
- Do not use usernames, personal names, ticket-like identifiers, or vague names unless explicitly required by the repository.
- Do not invent a new prefix when an existing allowed prefix fits.

Examples:

```text
"Add JWT authentication" → feature/jwt-authentication
"Fix login validation" → fix/login-validation
"Refactor the user service" → refactor/user-service
"Update API documentation" → docs/api-documentation
"Add authentication tests" → test/authentication
"Update GitHub Actions workflow" → ci/github-actions
```

If the user's description clearly indicates an existing branch type, preserve that intent.

## Repository state safety

The new branch **must always be created from the latest remote `main`**, never from whatever branch happens to be currently checked out. This matters because a branch based on an old or divergent base silently inherits stale work and makes the eventual PR noisy.

Before creating the branch:

1. Inspect the current Git state.
2. Determine the current branch.
3. Check for local changes.
4. Fetch the latest remote state.
5. Synchronize the local `main` reference with `origin/main`.
6. Create the new branch from `main`.
7. Switch to the newly created branch.

### Do not assume `git pull` is sufficient

`git pull` on your current branch updates that branch, not `main`. The invariant you need is:

```text
new branch
    ↓
latest local main
    ↓
origin/main
```

Get the latest remote state with `git fetch origin`, then update local `main` from `origin/main`.

## Local changes

Before switching away from the current branch, inspect `git status --short`.

If there are uncommitted changes, **do not blindly discard, stash, commit, or move them**. Explain to the user that the working tree contains local changes and that proceeding requires a decision about those changes.

Never use destructive commands such as `git reset --hard`, `git clean -fd`, or `git checkout -- .` unless the user explicitly requests the destructive operation.

If the current branch is already `main` with local changes, do not overwrite or reset those changes merely to synchronize `main`.

## Synchronization workflow

When the working tree is clean:

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
git checkout -b <type>/<short-description>
```

The branch must **never** be based on the user's current feature branch. For example, if the user is on `feature/old-work` and wants to start `feature/new-work`, do **not** run `git checkout -b feature/new-work` — that would branch from `feature/old-work`. Run the full synchronization workflow above instead.

## Remote synchronization

Use the repository's configured remote, normally `origin`. Check with `git remote -v` when necessary, then fetch:

```bash
git fetch origin
```

Fetch updates all remote-tracking references (`origin/main`, `origin/feature/...`), not just the current branch. The new branch must ultimately be based on the latest `origin/main`.

## Updating `main`

Prefer a fast-forward-only update:

```bash
git checkout main
git pull --ff-only origin main
```

This prevents the workflow from silently creating an unexpected merge commit on `main`.

If local `main` cannot be fast-forwarded because it has diverged from `origin/main`, **stop before creating the branch**. Do not auto-resolve divergence with `git reset --hard origin/main` — that can discard local commits. Report the situation and ask the user how to handle the divergent local `main`.

## Branch already exists

Before creating the branch, determine whether the intended name already exists locally.

- If `<type>/<short-description>` exists locally, do **not** recreate it. Report that it exists and ask whether the user wants to switch to it. Never delete or overwrite it automatically.
- Also check the remote. If the branch exists remotely but not locally, don't blindly create an unrelated branch with the same name — determine whether the user intends to continue the existing remote branch.

## Branch creation

Once all prerequisites are satisfied, create the branch explicitly from `main`:

```bash
git checkout -b <type>/<short-description>
```

Immediately verify the result:

```bash
git branch --show-current
```

The result must be the newly created branch. Optionally verify its starting point with `git log -1 --oneline` — it must point at the updated local `main`.

## Failure handling

If any Git operation fails:

- Stop the workflow.
- Do not continue blindly.
- Do not use destructive recovery commands automatically.
- Explain the Git operation that failed.
- Preserve the user's existing work.
- Ask for intervention only when necessary.

Examples of situations that require a stop: uncommitted changes prevent checkout, `main` has diverged from `origin/main`, fetch fails, authentication is required, a merge/rebase state is already in progress, unresolved conflicts, the requested branch already exists, or the directory isn't a Git repository.

Never hide Git errors from the user.

## Existing Git operations in progress

Before creating the branch, detect whether the repository is mid-operation (merge, rebase, cherry-pick, revert). If so, do not create or switch branches automatically — stop and report the state, and do not abort the operation automatically.

## No automatic development actions

After successfully creating and switching to the branch, stop. Do not automatically run `git add`, `git commit`, `git push`, `git merge`, `git rebase`, `git stash`, `git reset`, or `git clean` unless the user explicitly asks.

The expected successful workflow:

```text
Understand work
      ↓
Get brief description if missing
      ↓
Determine branch type
      ↓
Generate meaningful branch name
      ↓
Inspect Git state
      ↓
Ensure working tree is safe
      ↓
git fetch origin
      ↓
checkout main
      ↓
git pull --ff-only origin main
      ↓
create branch from main
      ↓
switch to new branch
      ↓
verify branch
      ↓
STOP
```

## Final response

After successful creation, report:

- The branch name.
- That it was created from the latest synchronized `main`.
- That the working directory is now switched to the new branch.

Example:

```text
Created and switched to:

feature/jwt-authentication

The branch was created from the latest synchronized main.
```

Do not claim the branch is synchronized with the remote unless the required fetch/update operations actually succeeded.

## Core invariant

The new branch must always originate from the latest successfully synchronized `main`, never from the branch currently checked out.

```text
User's current branch
        ✕
        │
        │  never use as branch base
        │
        ▼
      main
        ▲
        │
 latest origin/main
        │
   git fetch origin
        │
        ▼
new branch
```