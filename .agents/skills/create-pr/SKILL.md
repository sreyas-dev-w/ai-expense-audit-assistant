---
name: create-pr
description: Create a GitHub Pull Request from the current development branch into main using the GitHub CLI (gh), while enforcing repository contribution rules, validating authentication, handling errors interactively, inspecting branch commits, and generating a meaningful Conventional Commit PR title and description.
---

# Create GitHub Pull Request

## Purpose

Create a Pull Request for the user's current development branch into `main` using the GitHub CLI (`gh`).

This skill must:

* Use `gh` for GitHub operations.
* Follow the repository's `CONTRIBUTING.md` rules.
* Ensure the PR is created from the current feature/development branch into `main`.
* Verify GitHub CLI installation and authentication.
* Handle authentication failures interactively.
* Detect and handle HTTP `403` authentication/account problems.
* Inspect all commits on the branch before generating the PR title and description.
* Generate a meaningful Conventional Commit PR title.
* Generate a concise, accurate PR description based on the actual commits and changes.
* Never invent changes, tests, or behavior.
* Stop and ask the user when an interactive decision is required.
* Provide a clear resolution path for every recoverable failure.
* Never bypass repository rules or protected-branch restrictions.

---

# Operating Principles

1. **Be interactive when interaction is required.**
2. **Never silently make potentially destructive Git operations.**
3. **Never assume the GitHub account is correct.**
4. **Never create a PR before validating the branch and repository state.**
5. **Never create a PR without inspecting the branch commits.**
6. **Never invent PR content.**
7. **Never target a branch other than `main` for this workflow.**
8. **Never push directly to `main`.**
9. **Never use `--force`; if a force push is genuinely required elsewhere, use `--force-with-lease`.**
10. **After every important command, inspect the result and handle failures before continuing.**

---

# Required Workflow

Execute the following workflow in order.

```text
Understand feature
      ↓
Verify gh installed
      ↓
Verify Git repository
      ↓
Verify current branch
      ↓
Verify branch is not main
      ↓
Verify gh authentication
      ↓
Verify repository/account access
      ↓
Inspect main
      ↓
Inspect feature branch
      ↓
Determine whether branch is up to date
      ↓
Inspect commits
      ↓
Inspect diff
      ↓
Check for obvious secrets
      ↓
Push feature branch if required
      ↓
Generate PR title
      ↓
Generate PR description
      ↓
Show proposed PR details
      ↓
Create PR with gh
      ↓
Verify PR creation
      ↓
Report PR URL
```

Do not skip validation steps merely because a previous command appears successful.

---

# Step 0 — Understand the Work

Before creating the PR, determine what feature, fix, refactor, documentation change, or other work the branch represents.

Use the current conversation context first.

If the purpose of the branch is not clear from the conversation, inspect:

```bash
git log --oneline --decorate --no-merges main..HEAD
git diff --stat main...HEAD
git diff main...HEAD
```

If the work still cannot be understood confidently, ask the user for a brief description.

Do not create a PR with an ambiguous purpose.

The description should be short, for example:

```text
This branch adds the expense document upload workflow.
```

---

# Step 1 — Verify GitHub CLI Installation

Run:

```bash
gh --version
```

## Success

Continue.

## Failure: `gh` command not found

Tell the user:

> GitHub CLI (`gh`) is not installed. This workflow uses `gh` to authenticate with GitHub, inspect repository information, push/create the Pull Request, and verify the resulting PR. Please install GitHub CLI and then run this skill again.

Do not attempt to continue with GitHub operations without `gh`.

Do not install `gh` automatically unless the user explicitly asks the agent to install it.

Provide the official installation guidance if available.

---

# Step 2 — Verify Git Repository

Run:

```bash
git rev-parse --is-inside-work-tree
```

## Failure

If this is not a Git repository:

> The current directory is not a Git repository, so a Pull Request cannot be created from here.

Ask the user to move to the repository directory.

Stop.

---

# Step 3 — Determine Current Branch

Run:

```bash
git branch --show-current
```

Store the result as:

```text
CURRENT_BRANCH
```

If the command fails or returns an empty branch name, stop and explain the problem.

---

# Step 4 — Never Create a PR From `main`

If:

```text
CURRENT_BRANCH == main
```

stop.

Tell the user:

> You are currently on `main`. This workflow creates PRs from a development branch into `main`, and direct PR work from `main` is not allowed by the repository workflow.

Do not automatically create a new branch because the actual feature branch and its commits would be unknown.

Ask the user to switch to the appropriate development branch.

---

# Step 5 — Validate Branch Naming

Check:

```bash
git branch --show-current
```

The branch should follow:

```text
<type>/<short-description>
```

Allowed prefixes:

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

Examples:

```text
feature/auth
feature/user-profile
fix/login-validation
refactor/user-service
```

Check that:

* The prefix is lowercase.
* The description is lowercase.
* Words are separated by hyphens.
* The branch describes the work.
* The branch is not a developer-specific name.
* The branch is reasonably short.

If the branch violates the convention, inform the user.

Do not rename the branch automatically.

Ask whether they want to rename it before continuing.

---

# Step 6 — Verify GitHub Authentication

Run:

```bash
gh auth status
```

## Success

Continue.

## Not authenticated

Tell the user:

> GitHub CLI is installed, but you are not authenticated with GitHub. Authentication is required so `gh` can access the repository and create the Pull Request.

Start the interactive GitHub authentication flow:

```bash
gh auth login
```

Prefer:

```text
GitHub.com
HTTPS
Authenticate via web browser
```

when those options are available.

After login completes, verify again:

```bash
gh auth status
```

Do not continue until authentication succeeds.

## Authentication failure

Explain the failure and ask the user to resolve/retry authentication.

Do not fabricate authentication success.

---

# Step 7 — Determine GitHub Repository

Determine the repository associated with the current Git repository.

Prefer:

```bash
gh repo view --json nameWithOwner,url,defaultBranchRef
```

Also inspect the Git remote if necessary:

```bash
git remote -v
```

The repository must be identifiable.

Confirm that the default/target branch for this workflow is:

```text
main
```

Even if GitHub reports another default branch, this skill must follow the repository contribution requirement supplied for this workflow and target `main`.

If `main` does not exist, stop and inform the user.

---

# Step 8 — Verify GitHub Account Has Access

Use:

```bash
gh repo view --json nameWithOwner
```

and, where appropriate:

```bash
gh api user
```

Determine the authenticated GitHub account.

Do not expose unnecessary personal information.

The purpose is to verify that the authenticated account can access the repository.

---

# Step 9 — Handle HTTP 403 Explicitly

A `403` response must be treated as a possible GitHub account/permission mismatch.

If any GitHub operation returns:

```text
HTTP 403
```

do not repeatedly retry blindly.

Tell the user:

> GitHub returned HTTP 403. The authenticated GitHub account may be different from the account that has permission to access this repository.

Then show the user the currently authenticated account using:

```bash
gh auth status
```

Ask:

```text
Would you like to re-authenticate with the correct GitHub account, or end the PR creation process?
```

The user must explicitly choose.

### If user chooses re-authentication

Run:

```bash
gh auth logout --hostname github.com
```

Then:

```bash
gh auth login --hostname github.com
```

After authentication:

```bash
gh auth status
```

Then retry the failed operation once.

### If the retry succeeds

Continue the workflow.

### If the retry still returns 403

Explain that the authenticated account still does not have the required repository permission.

Ask whether the user wants to:

1. Re-authenticate again.
2. End the process.

Never loop indefinitely.

### If user chooses to end

Stop without creating the PR.

---

# Step 10 — Fetch Remote Information

Fetch the latest remote state:

```bash
git fetch origin
```

## Failure handling

If fetching fails:

* Inspect the error.
* Determine whether the problem is network access, remote configuration, authentication, or repository access.
* Explain the likely cause.
* Provide the specific corrective action.
* Ask the user to retry when interaction is required.

Do not continue using stale remote information when the latest `main` state is required.

---

# Step 11 — Verify `main`

Verify that `origin/main` exists:

```bash
git rev-parse --verify origin/main
```

If it does not exist, stop and report that `origin/main` could not be found.

Inspect the latest main commit:

```bash
git log -1 --oneline origin/main
```

---

# Step 12 — Inspect Feature Branch Relationship With Main

Determine the branch relationship:

```bash
git rev-list --left-right --count origin/main...HEAD
```

Interpret the result as:

```text
BEHIND AHEAD
```

For example:

```text
0 5
```

means the branch is 5 commits ahead and 0 commits behind.

If the branch is behind `main`, inform the user:

> Your branch is behind `main`. The repository requires development branches to be based on the latest `main`.

Ask the user whether to update the branch.

The repository permits both:

### Recommended — merge main

```bash
git merge origin/main
```

### Alternative — rebase

```bash
git rebase origin/main
```

Prefer merge when the user has not specified a preference.

---

# Step 13 — Conflict Handling

If merge/rebase produces conflicts:

Do not blindly resolve conflicts.

Do not use:

```bash
git checkout --ours .
git checkout --theirs .
```

as a blanket resolution.

Inspect:

```bash
git status
git diff
```

Explain which files are conflicted.

Ask the user to resolve the conflicts unless the correct resolution is unambiguous and the user has explicitly authorized the agent to resolve them.

After resolution:

### Merge

```bash
git add <resolved-files>
git commit
```

### Rebase

```bash
git add <resolved-files>
git rebase --continue
```

After conflict resolution:

```bash
git status
```

Then run the relevant project tests.

Only continue when the merge/rebase is complete.

---

# Step 14 — Inspect All Commits on the Branch

This is mandatory.

Run:

```bash
git log --reverse --format="%H%n%s%n%b%n---" origin/main..HEAD
```

Also inspect a compact version:

```bash
git log --oneline --decorate origin/main..HEAD
```

The PR title and description must be based on the actual work represented by these commits.

Do not simply use the latest commit message.

Analyze:

* Commit types.
* Commit scopes.
* Overall feature.
* Bug fixes.
* Refactors.
* Documentation.
* Tests.
* Configuration changes.
* Dependency changes.
* Any mixed concerns.

---

# Step 15 — Inspect the Actual Changes

Run:

```bash
git diff --stat origin/main...HEAD
```

Then inspect the complete diff when necessary:

```bash
git diff origin/main...HEAD
```

Use the diff to validate that the commits accurately represent the work.

The PR description must reflect the actual code changes, not assumptions based only on commit messages.

---

# Step 16 — Check for Uncommitted Changes

Run:

```bash
git status --short
```

If there are uncommitted changes:

Do not silently include them in the PR.

Tell the user:

> There are uncommitted changes in the working tree. The PR should be based on committed branch changes only.

Ask whether they want to:

1. Commit the changes first.
2. Leave them uncommitted and continue with the existing branch commits.
3. End the process.

Do not automatically commit changes unless explicitly authorized.

---

# Step 17 — Check for Obvious Secrets

Before pushing, inspect the changed files for obvious credentials/secrets.

Look for patterns such as:

```text
.env
*.pem
*.key
password=
api_key=
apikey=
access_token=
client_secret=
connection string credentials
private keys
```

Do not print secret values into the conversation.

If an obvious secret is detected:

> A potentially sensitive credential or secret appears to be included in the changes. It should not be committed or pushed.

Stop and ask the user to remove it or confirm the intended safe handling.

Never expose the secret value.

---

# Step 18 — Validate Commit Conventions

Each commit should follow:

```text
<type>: <description>
```

or:

```text
<type>(scope): <description>
```

Allowed types:

```text
feat
fix
refactor
docs
test
chore
build
ci
perf
style
revert
```

Inspect commits with:

```bash
git log --format="%h %s" origin/main..HEAD
```

If commit messages clearly violate the convention, inform the user.

Do not rewrite commit history automatically.

The PR title must still follow Conventional Commit format even if existing commits are imperfect.

---

# Step 19 — Decide Whether the Branch Needs Pushing

Determine whether the remote branch exists:

```bash
git ls-remote --heads origin "$CURRENT_BRANCH"
```

If the branch does not exist remotely, push it:

```bash
git push -u origin "$CURRENT_BRANCH"
```

If it already exists, determine whether the local branch is ahead:

```bash
git status -sb
```

Push when required:

```bash
git push
```

## Push failure handling

### Authentication / permission error

Inspect the error.

If it is HTTP 403, follow the dedicated 403 procedure above.

### Non-fast-forward error

Do not force push.

Fetch:

```bash
git fetch origin
```

Determine why the remote branch contains commits not present locally.

Ask the user whether to merge/rebase those changes.

### Network failure

Report the failure and ask the user to retry once connectivity is restored.

### Any other failure

Explain the actual error and resolution rather than blindly retrying.

---

# Step 20 — Generate PR Title

The PR title must follow:

```text
<type>: <overall change>
```

or:

```text
<type>(scope): <overall change>
```

Examples:

```text
feat: add expense document auditing
feat(auth): add user authentication
fix: resolve expense validation errors
refactor: simplify audit processing workflow
```

The title must describe the **overall purpose of the PR**, not simply copy the latest commit.

Determine the dominant change from:

1. Feature/branch purpose.
2. All commits.
3. Actual diff.
4. Tests and supporting changes.

Avoid:

```text
Changes
Update
Final changes
My work
Fix stuff
Various updates
```

---

# Step 21 — Generate PR Description

Use this structure by default:

```markdown
## Summary

- <meaningful change>
- <meaningful change>
- <meaningful change>

## Testing

- <test or validation actually performed>
- <test or validation actually performed>
```

Only include sections supported by the actual work.

For example, if applicable:

```markdown
## Changes

- ...

## Why

- ...

## Testing

- ...

## Breaking Changes

- ...

## Notes

- ...
```

Do not claim tests were run if they were not run.

If testing was not performed, say so honestly:

```markdown
## Testing

- Not run locally; CI validation is expected to run with the PR.
```

Only use this statement if it accurately reflects the situation.

---

# Step 22 — Review Proposed PR Information With User

Before creating the PR, show:

```text
PR target:
<current branch> → main

Title:
<generated title>

Description:
<generated description>
```

If the title and description are clearly correct based on the branch commits and diff, creation may proceed.

If the task requires user confirmation, ask:

```text
Create this Pull Request?
```

Do not ask unnecessary confirmation when the user has already explicitly requested PR creation and all required information is valid.

---

# Step 23 — Create the Pull Request

Use `gh pr create`.

Preferred structure:

```bash
gh pr create \
  --base main \
  --head "$CURRENT_BRANCH" \
  --title "<PR_TITLE>" \
  --body "<PR_BODY>"
```

The important requirement is:

```text
HEAD = current development branch
BASE = main
```

Never accidentally reverse them.

Never create:

```text
main → feature/...
```

for this workflow.

---

# Step 24 — Handle PR Creation Errors

Inspect the command result.

## HTTP 403

Follow the dedicated 403 re-authentication workflow.

## Authentication failure

Run:

```bash
gh auth status
```

Re-authenticate interactively if necessary.

## Branch does not exist remotely

Push the branch and retry:

```bash
git push -u origin "$CURRENT_BRANCH"
```

## No commits between branches

Inform the user:

> There are no commits between the development branch and `main`, so there is nothing to create a PR for.

Stop.

## PR already exists

Check:

```bash
gh pr list --head "$CURRENT_BRANCH" --base main
```

If an existing PR is found, do not create a duplicate.

Report the existing PR.

## Validation/check failure

If GitHub rejects the PR because of repository rules, explain the exact reported requirement.

Do not bypass the repository rules.

## Unknown error

Show the relevant non-sensitive error message and provide a resolution path.

Never claim that the PR was created unless `gh` confirms it.

---

# Step 25 — Verify the Created PR

After `gh pr create` succeeds, verify the PR:

```bash
gh pr view "$CURRENT_BRANCH" --json number,title,state,baseRefName,headRefName,url
```

Verify:

```text
baseRefName == main
headRefName == CURRENT_BRANCH
```

If the values are incorrect, do not claim successful completion.

---

# Step 26 — Final Result

Only after successful verification report:

```text
Pull Request created successfully.

Branch:
<feature branch>

Target:
<feature branch> → main

Title:
<PR title>

PR:
<GitHub PR URL>
```

Do not claim approval, checks, or auto-merge unless those states have actually been verified.

---

# Important Safety Rules

## Never push directly to main

Never execute:

```bash
git push origin main
```

as part of this workflow.

---

## Never create a PR with the wrong base

Always explicitly specify:

```bash
--base main
```

and:

```bash
--head "$CURRENT_BRANCH"
```

---

## Never invent PR content

Every statement in the PR description must be supported by:

* Conversation context.
* Branch commits.
* Git diff.
* Tests actually executed.
* Repository information.

---

## Never claim tests were run when they were not

Bad:

```text
Testing:
- All tests passed
```

when tests were not executed.

Correct:

```text
Testing:
- Not run locally.
```

---

## Never expose secrets

Do not print:

* Tokens.
* Passwords.
* API keys.
* Private keys.
* Connection strings containing credentials.

---

## Never blindly resolve conflicts

Always inspect the conflict.

---

## Never use `--force`

This workflow must not use:

```bash
git push --force
```

If a history rewrite was explicitly authorized and is genuinely required, use:

```bash
git push --force-with-lease
```

and only after verifying the remote branch state.

---

# Error Handling Matrix

| Failure                   | Action                                                          |
| ------------------------- | --------------------------------------------------------------- |
| `gh` missing              | Tell user to install GitHub CLI and stop                        |
| Not a Git repo            | Tell user to enter repository directory and stop                |
| Current branch is `main`  | Ask user to switch to development branch                        |
| Invalid branch name       | Ask whether to rename it                                        |
| `gh` not authenticated    | Run interactive `gh auth login`                                 |
| GitHub `403`              | Explain account/permission mismatch and ask re-authenticate/end |
| Re-authentication fails   | Explain failure and ask retry/end                               |
| `git fetch` fails         | Diagnose remote/network/auth issue                              |
| Branch behind `main`      | Ask whether to merge/rebase                                     |
| Merge conflict            | Inspect and interactively resolve                               |
| Uncommitted changes       | Ask whether to commit, leave, or stop                           |
| Potential secret detected | Stop and ask user to remove/resolve                             |
| Push fails                | Diagnose; never blindly force push                              |
| No branch commits         | Stop; nothing to PR                                             |
| Existing PR               | Do not create duplicate                                         |
| PR creation `403`         | Re-authentication workflow                                      |
| Wrong PR base/head        | Do not report success                                           |
| Unknown `gh` error        | Explain actual error and resolution                             |
| PR created                | Verify with `gh pr view`                                        |

---

# Command Reference

## Git state

```bash
git status --short
git branch --show-current
git remote -v
git fetch origin
git rev-list --left-right --count origin/main...HEAD
```

## Commit inspection

```bash
git log --oneline --decorate origin/main..HEAD
git log --reverse --format="%H%n%s%n%b%n---" origin/main..HEAD
```

## Change inspection

```bash
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

## GitHub CLI

```bash
gh --version
gh auth status
gh auth login
gh auth logout --hostname github.com
gh repo view --json nameWithOwner,url,defaultBranchRef
gh api user
```

## Branch push

```bash
git push -u origin "$CURRENT_BRANCH"
git push
```

## Existing PR detection

```bash
gh pr list --head "$CURRENT_BRANCH" --base main
```

## PR creation

```bash
gh pr create \
  --base main \
  --head "$CURRENT_BRANCH" \
  --title "<PR_TITLE>" \
  --body "<PR_BODY>"
```

## PR verification

```bash
gh pr view "$CURRENT_BRANCH" \
  --json number,title,state,baseRefName,headRefName,url
```

---

# Completion Criteria

The skill is complete only when all of the following are true:

* `gh` is installed.
* The user is authenticated.
* The authenticated account can access the repository.
* No unresolved `403` exists.
* The repository is identified.
* The current branch is a valid development branch.
* The current branch is not `main`.
* `main` exists remotely.
* The branch relationship with `main` has been checked.
* Required branch updates have been completed.
* No unresolved conflicts exist.
* Relevant commits have been inspected.
* Relevant changes have been inspected.
* No obvious secret is being introduced.
* The feature branch has been pushed to GitHub.
* The PR title follows Conventional Commit format.
* The PR description accurately represents the branch.
* The PR targets `main`.
* The PR originates from the current development branch.
* `gh` confirms that the PR was created.
* The created PR has been verified with `gh pr view`.

Only then should the workflow report successful completion.

---

# Expected End State

```text
feature/fix/etc.
       │
       │ commits inspected
       │ changes inspected
       │
       ▼
origin/feature/...
       │
       │ gh pr create
       ▼
Pull Request
       │
       ├── HEAD → feature/...
       └── BASE → main
                │
                ▼
          Review + Checks
                │
                ▼
            Auto Merge
                │
                ▼
               main
```