# SYNC.md — AXIOM-Mobile Repository Sync Guide

This guide explains how to keep your **fork** and **local clone** up to date with the **team organization repository**.

**Team repo (organization):** `AIML-Research-SFU/axiom-mobile`  
**Typical fork:** `{username}/axiom-mobile`

---

## Who needs this guide?

### ✅ You need this guide if you are working from a fork

If you cloned something like:

- `git@github.com:{username}/axiom-mobile.git`

…then you are working from a **fork**, and you should sync regularly.

### ⚠️ You likely do NOT need this guide if you work directly on the team repo

If you cloned:

- `git@github.com:AIML-Research-SFU/axiom-mobile.git`

…then your `origin` already points to the team repo, and you can just `git pull` normally.

---

## Remote Naming Convention (recommended)

- **origin** → your fork (`git@github.com:{username}/axiom-mobile.git`)
- **upstream** → team repo (`git@github.com:AIML-Research-SFU/axiom-mobile.git`)

You can confirm your remotes with:

```bash
git remote -v
```

Expected output (fork workflow):

```
origin   git@github.com:{username}/axiom-mobile.git (fetch)
origin   git@github.com:{username}/axiom-mobile.git (push)
upstream git@github.com:AIML-Research-SFU/axiom-mobile.git (fetch)
upstream git@github.com:AIML-Research-SFU/axiom-mobile.git (push)
```

---

## One-Time Setup (Fork Users Only)

If you do not have an `upstream` remote yet:

### 1) Add upstream

**SSH:**

```bash
git remote add upstream git@github.com:AIML-Research-SFU/axiom-mobile.git
```

**OR HTTPS:**

```bash
git remote add upstream https://github.com/AIML-Research-SFU/axiom-mobile.git
```

### 2) Confirm the default branch name

```bash
git remote show upstream
```

Look for:

```
HEAD branch: main
```

AXIOM-Mobile uses `main`.

---

## Flow 1: Pull Latest Changes from the Team Repo (Before you start work)

Do this **every time** before you begin new work.

### 1) Switch to main

```bash
git checkout main
```

### 2) Pull from upstream/main

```bash
git pull upstream main
```

### 3) Push the updated main to your fork

```bash
git push origin main
```

That keeps:

- Your local `main` up to date
- Your fork `main` up to date

---

## Flow 2: Keep Your Feature Branch Up to Date

If you already created a feature branch (example `feature/x`), sync it on top of the latest upstream changes.

### Option A (recommended): Rebase on upstream/main

```bash
git fetch upstream
git checkout feature/x
git rebase upstream/main
git push --force-with-lease origin feature/x
```

### Option B: Merge upstream/main into your branch

```bash
git fetch upstream
git checkout feature/x
git merge upstream/main
git push origin feature/x
```

---

## Viewing Ahead/Behind Status

### 1) Update tracking refs

```bash
git fetch upstream
```

### 2) See status

```bash
git status -b
```

Example:

```
main...upstream/main [behind 3]
```

### 3) More detail

```bash
git branch -vv
```

---

## Troubleshooting

### "fatal: 'upstream' does not appear to be a git repository"

You do not have `upstream` configured.

Check:

```bash
git remote -v
```

If upstream is missing, add it:

```bash
git remote add upstream git@github.com:AIML-Research-SFU/axiom-mobile.git
```

### "Permission denied (publickey)" when fetching upstream

Use HTTPS for upstream fetch (read access works without SSH org permissions):

```bash
git remote remove upstream
git remote add upstream https://github.com/AIML-Research-SFU/axiom-mobile.git
git fetch upstream
```

---

## Quick Reference

| Action | Command |
|---|---|
| Show remotes | `git remote -v` |
| Add upstream | `git remote add upstream git@github.com:AIML-Research-SFU/axiom-mobile.git` |
| Pull latest from team | `git pull upstream main` |
| Push updated main to fork | `git push origin main` |
| Rebase feature branch | `git rebase upstream/main` |
| Check ahead/behind | `git status -b` / `git branch -vv` |

---

## Recommended Habit

Before every work session:

```bash
git checkout main
git pull upstream main
git push origin main
```

Then create or continue your feature branch from the updated base.
