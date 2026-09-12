# Contributing Workflow

This document defines the Git workflow, branch naming, commit conventions, and Pull Request rules for this repository.

The goal is to keep the repository history clean, predictable, and easy for everyone on the team to understand.

## 1. Branch Strategy

`main` is the only long-lived branch.

All development must happen in a separate branch created from the latest `main`.

```text
main
 ├── feature/auth
 ├── fix/login-validation
 ├── hotfix/payment-error
 └── refactor/user-service
```

There are no permanent `develop`, `staging`, or developer-specific branches.

## 2. Main Branch Rules

`main` is protected by GitHub rulesets.

* Direct pushes to `main` are not allowed.
* Commits cannot be created directly on `main`.
* All changes must go through a Pull Request.
* Every PR requires at least one approval from another team member.
* The PR author cannot approve their own PR.
* Required checks must pass before merging.
* Once approval and checks are complete, GitHub automatically merges the PR into `main`.
* New branches must be created from the latest `main`.

## 3. Development Workflow

For new work:

```bash
git checkout main
git pull origin main
git checkout -b feature/my-feature
```

Work and commit on the branch:

```bash
git add .
git commit -m "feat: add my feature"
```

Push the branch:

```bash
git push -u origin feature/my-feature
```

Then create a Pull Request:

```text
feature/my-feature → main
```

After review, approval, and successful checks, the PR is automatically merged.

For the next piece of work, start again from the latest `main`.

```text
main
 ↓
feature/A
 ↓
PR → review → auto merge
 ↓
main
 ↓
feature/B
 ↓
PR → review → auto merge
 ↓
main
```

## 4. Branch Naming

Use:

```text
<type>/<short-description>
```

Rules:

* Use lowercase.
* Use hyphens between words.
* Describe the work, not the developer.
* Keep the name short and meaningful.

Good:

```text
feature/auth
feature/user-profile
fix/login-validation
hotfix/payment-failure
refactor/user-service
```

Avoid:

```text
Feature/UserProfile
feature/User_Profile
my-branch
john-branch
test
```

### Branch Types

| Prefix      | Use for                                     | Example                     |
| ----------- | ------------------------------------------- | --------------------------- |
| `feature/`  | New functionality                           | `feature/auth`              |
| `fix/`      | Normal bug fixes                            | `fix/login-validation`      |
| `hotfix/`   | Urgent production/critical fixes            | `hotfix/payment-failure`    |
| `refactor/` | Code restructuring without behavior changes | `refactor/user-service`     |
| `docs/`     | Documentation changes                       | `docs/api-guide`            |
| `test/`     | Test-only changes                           | `test/auth-service`         |
| `chore/`    | General maintenance                         | `chore/update-dependencies` |
| `build/`    | Build-related changes                       | `build/update-sdk`          |
| `ci/`       | CI/CD changes                               | `ci/github-actions`         |

For normal development, `feature/`, `fix/`, and `refactor/` will be used most often.

`hotfix/` should be reserved for urgent production or critical issues.

Do not introduce new branch prefixes unless there is a clear need.

## 5. Commits

A branch can contain multiple commits.

Use Conventional Commit format:

```text
<type>: <short description>
```

A scope can optionally be included:

```text
feat(auth): add login endpoint
fix(auth): handle expired token
refactor(user): simplify user service
```

Common types:

| Type       | Use for                  |
| ---------- | ------------------------ |
| `feat`     | New functionality        |
| `fix`      | Bug fixes                |
| `refactor` | Code restructuring       |
| `docs`     | Documentation            |
| `test`     | Tests                    |
| `chore`    | Maintenance              |
| `build`    | Build changes            |
| `ci`       | CI/CD changes            |
| `perf`     | Performance improvements |
| `style`    | Formatting-only changes  |
| `revert`   | Reverting a change       |

Examples:

```text
feat: add user authentication
fix: handle expired access token
refactor: simplify authentication service
docs: update authentication guide
test: add login tests
chore: update dependencies
```

Keep commits meaningful and avoid vague messages such as:

```text
update
changes
final
work
fix stuff
```

## 6. Pull Requests

Create PRs from the development branch into `main`.

```text
feature/auth → main
```

### PR Title

PR titles must follow the Conventional Commit format.

Examples:

```text
feat: add authentication
fix: resolve login validation issue
refactor: simplify user service
docs: update authentication documentation
```

The title should describe the overall change.

Avoid:

```text
Changes
Update
Final changes
My work
Bug fixes
```

### PR Description

The description should briefly explain what changed and how it was tested.

Recommended format:

```markdown
## Summary

- Added user authentication
- Added login endpoint
- Added authentication validation

## Testing

- Added authentication unit tests
- Verified login and logout flows
```

For larger changes, add relevant sections such as:

```markdown
## Changes
## Why
## Testing
## Screenshots
## Breaking Changes
## Notes
```

Do not add sections that are not relevant.

## 7. PR Review and Merge

Every PR must have at least one approval from another team member.

The author cannot approve their own PR.

```text
Developer A
    ↓
feature/auth
    ↓
Pull Request → main
    ↓
Developer B reviews
    ↓
Approval
    ↓
Checks pass
    ↓
GitHub auto-merges
    ↓
main
```

Reviewers should focus on:

* Correctness
* Code quality
* Tests
* Security
* Performance where relevant
* Consistency with the existing codebase
* Scope of the change

## 8. Keeping Branches Updated and Resolving Conflicts

If `main` has changed while working on your branch, your branch may need to be updated before the PR can be merged.

There are two valid approaches. Both are allowed in this repository.

### Option 1: Merge `main` into the Feature Branch

This is the simpler and recommended approach, especially when you are not comfortable with rebasing.

```bash
git checkout main
git pull origin main

git checkout feature/my-feature
git merge main
```

If there are conflicts, Git will identify the conflicting files.

Resolve the conflicts manually, then:

```bash
git add .
git commit
```

Run the relevant tests and push the updated branch:

```bash
git push
```

This approach preserves the existing branch history and is generally easier to understand.

### Option 2: Rebase the Feature Branch

You can also rebase your branch onto the latest `main`.

```bash
git checkout main
git pull origin main

git checkout feature/my-feature
git rebase main
```

If conflicts occur, resolve them and continue the rebase:

```bash
git add .
git rebase --continue
```

Repeat until the rebase is complete, then run the relevant tests.

Because rebasing rewrites commit history, pushing may require:

```bash
git push --force-with-lease
```

Use `--force-with-lease`, not `--force`, when a force push is necessary.

### Which Should You Use?

Both approaches are allowed:

| Approach                 | Recommendation | Notes                                                |
| ------------------------ | -------------- | ---------------------------------------------------- |
| Merge `main` into branch | Recommended    | Simpler and safer for most developers                |
| Rebase onto `main`       | Allowed        | Cleaner linear branch history but requires more care |

There is no requirement to rebase.

If you are unsure which approach to use, merge the latest `main` into your feature branch.

### Resolving Conflicts

Do not blindly choose "ours" or "theirs" when resolving conflicts.

Review each conflict and make sure the final code contains the intended behavior.

After resolving conflicts:

1. Complete the merge or rebase.
2. Run the relevant tests.
3. Push the updated branch.
4. Continue with the Pull Request.

Do not rebase a branch that other developers are actively working on without coordinating with them.

## 9. Keep Changes Focused

One branch should normally represent one logical piece of work.

For example:

```text
feature/auth
```

should focus on authentication rather than also containing unrelated dashboard, dependency, or UI changes.

Separate unrelated work into separate branches and PRs.

## 10. Basic Git Practices

### Start from the latest main

```bash
git checkout main
git pull origin main
```

### Review changes before committing

```bash
git status
git diff
```

### Never commit secrets

Do not commit:

```text
.env
API keys
passwords
access tokens
private certificates
credentials
```

Use environment variables or the project's approved secret-management solution.

### Keep PRs focused

Smaller PRs are easier to review, test, and maintain.

## 11. Quick Reference

```text
Create branch:
git checkout main
git pull origin main
git checkout -b feature/my-feature

Commit:
git add .
git commit -m "feat: add my feature"

Push:
git push -u origin feature/my-feature

PR:
feature/my-feature → main
```

### Final Rule

```text
Never push directly to main.

Create branch → Develop → Commit → Push → PR → Review → Approval → Checks → Auto Merge → main
```

`main` is the single source of truth for the repository.
