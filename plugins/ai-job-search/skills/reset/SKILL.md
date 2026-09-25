---
name: reset
description: "Reset Candidate Profile Data. Use when the user runs /reset."
argument-hint: "[profile | documents | all]"
disable-model-invocation: true
---
# /reset - Reset Candidate Profile Data

`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, read paths as relative to the folder containing this SKILL.md.

You are resetting parts of the job search framework back to a blank state so the user can start fresh with `/setup`.

**This command is destructive.** Nothing is deleted until the user explicitly confirms. Follow these steps exactly in order.

---

## Step 0: Parse Scope from Arguments

Check `$ARGUMENTS` for a scope keyword:

- `profile` — restores every file in `profile/` to its blank template
- `documents` — deletes user-provided files from the `documents/` folder only
- `all` — both of the above

If `$ARGUMENTS` is empty or does not contain a recognized scope keyword, ask:

> **What would you like to reset?**
>
> - **`profile`** — Restores every file in `profile/` to its blank template (profile, behavioral, evaluation inputs, profile statements, STAR examples, search queries). Framework files are never touched. Use this to re-run `/setup` from scratch.
>
> - **`documents`** — Deletes all files you've placed in the `documents/` folder (CV PDFs, LinkedIn export, diplomas, references, project summaries, pasted job postings, past applications). The folder structure and `README.md` are preserved.
>
> - **`all`** — Both of the above.
>
> Reply with `profile`, `documents`, or `all`.

Wait for the user's response before continuing.

---

## Step 1: Show Exactly What Will Be Cleared

Before doing anything, show the user precisely what will be wiped.

### If scope includes `profile`:

Read each of these and report whether it holds data or is already blank (still matches its template in `${CLAUDE_SKILL_DIR}/../job-application-assistant/profile-templates/`):

- `profile/candidate.md`
- `profile/behavioral.md`
- `profile/evaluation.md`
- `profile/cv.md` *(profile statements only — an active custom template is kept)*
- `profile/cover-letter.md` *(extracted patterns only — an active custom template is kept)*
- `profile/writing-patterns.md`
- `profile/star.md`
- `profile/search-queries.md`

This list must match the files `/setup` Step 3 populates.

Present as:

```
## Profile reset will clear:

- profile/<file> — [has data / already blank]
  (one line per file above)

An active custom CV or cover-letter template (the Active Template section) is kept.

Also still holding your personal data: cv/main_example.tex. This scope does not touch it.
```

### If scope includes `documents`:

Use Glob to list all files present in `documents/cv/`, `documents/linkedin/`, `documents/diplomas/`, `documents/references/`, `documents/projects/`, `documents/postings/`, and `documents/applications/`. Present as:

```
## Documents reset will delete:

documents/cv/
  - [filename] or "(empty)"

documents/linkedin/
  - [filename] or "(empty)"

documents/diplomas/
  - [filename] or "(empty)"

documents/references/
  - [filename] or "(empty)"

documents/projects/
  - [filename] or "(empty)"

documents/postings/
  - [filename] or "(empty)"

documents/applications/
  - [subfolder/filename] or "(empty)"

documents/README.md — NOT deleted (instructions file)
```

If all document subfolders are already empty, state "All document subfolders are already empty — nothing to delete." and skip the confirmation step for this scope.

---

## Step 2: Require Explicit Confirmation

Present the confirmation prompt:

> **This cannot be undone.**
>
> Type **`RESET`** (all caps) to confirm, or anything else to cancel.

Wait for the user's response.

- If the user types exactly `RESET`: proceed to Step 3.
- If the user types anything else: abort and tell them "Reset cancelled. Nothing was changed."

---

## Step 3: Execute the Reset

### Profile reset

For each file listed in Step 1, copy `${CLAUDE_SKILL_DIR}/../job-application-assistant/profile-templates/<name>` over `profile/<name>`.

**Exception, keep the Active Template section:** before overwriting `profile/cv.md` and `profile/cover-letter.md`, read the text between `<!-- BEGIN ACTIVE-TEMPLATE` and `<!-- END ACTIVE-TEMPLATE -->` if present. After copying the template, put that block back under `## Active Template`. A reset clears data, not the user's template registration.

### Documents reset

For each non-empty document subfolder, delete all files within it using Bash `rm`. Do not delete the folder itself, and do not delete `documents/README.md`.

```bash
rm -f documents/cv/*
rm -f documents/linkedin/*
rm -f documents/diplomas/*
rm -f documents/references/*
rm -f documents/projects/*
rm -f documents/postings/*
rm -rf documents/applications/*/
```

---

## Step 4: Confirm What Was Done and Next Steps

After the reset is complete, report:

```
## Reset complete

### Cleared
[List each file/folder that was actually modified or cleared]

### Unchanged
[List anything that was already empty or was intentionally preserved]
```

Then tell the user what to do next based on what was reset:

**If profile was reset:**
> Your `profile/` files are back to blank templates. Run `/setup` to repopulate them. The command auto-detects any files in your `documents/` folder and offers to read from there; otherwise it walks you through a CV import or interactive interview.
>
> `cv/main_example.tex` is outside the `profile` scope and still holds your personal data. If you are handing this repository over or making it public, clear it by hand.

**If documents were reset:**
> The `documents/` folder is now empty. Add your career documents and run `/setup` to populate your profile. See `documents/README.md` for instructions on what to put where.

**If both were reset:**
> Both your profile files and documents folder are now empty. Add documents to `documents/` (or skip and use the CV import / interview path), then run `/setup`.
