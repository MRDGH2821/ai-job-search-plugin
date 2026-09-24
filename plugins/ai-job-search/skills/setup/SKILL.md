---
name: setup
description: "Profile Onboarding. Use when the user runs /setup."
argument-hint: "[--section <name>]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py:*), Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py:*)
---
# /setup - Profile Onboarding

`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, read paths as relative to the folder containing this SKILL.md.

You are running the onboarding setup for the AI Job Search framework. Your goal is to collect the user's professional information and populate all profile files so the `/apply` workflow works out of the box.

There are three paths into setup. Step 0 picks the right one; all three converge on Step 3 (file generation) and Step 4 (confirmation).

---

## Step 0: Welcome & Choose Path

### Step 0a: Prepare the profile folder

Your candidate data lives in `profile/` at the workspace root. Before anything else:

1. Lay out the workspace: run `python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py` exactly as written, as one command from the current directory (no `cd`, no `&&`). It copies only what is missing (CV and cover-letter sources, fonts, the `documents/` tree, a privacy `.gitignore`) and never overwrites anything. Mention in one line what it created, if anything. If it exits 2, show its message and continue.
2. Create `profile/` if it does not exist.
3. If `profile/` did not exist before step 2, run **Legacy fork migration** below first. Then, for each file in `${CLAUDE_SKILL_DIR}/../job-application-assistant/profile-templates/`, copy it to `profile/<same name>` **only if that file is missing**. Copy only the missing files and never overwrite an existing profile file: it may hold the user's data.
4. Tell the user in one line which files were created, if any.
5. Refresh this workspace's instructions: run `python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py` exactly as written, as one command from the current directory (no `cd`, no `&&`). It writes the framework's block into `AGENTS.md` and makes `CLAUDE.md` import it, leaving everything else in both files alone. Mention its result in one line. If it exits 2 (broken markers in `AGENTS.md`, an unreadable file or broken symlink), show its message and continue with setup.

Every write below goes to `profile/`. Framework files in the plugin are never edited by this command.

#### Legacy fork migration

Before this change, `/setup` wrote candidate data into framework files. A fork that merged the change still has that data in its git history. Find it:

1. Find the legacy ref. Check these candidates in order, reading `.claude/skills/job-application-assistant/01-candidate-profile.md` from each (`git show <candidate>:<path>`, or the file itself for the working tree). The first candidate where that file exists and does **not** contain `[YOUR_EMAIL]` is the legacy profile; call it `<ref>`.
   a. The working tree.
   b. `ORIG_HEAD` (set by the merge that brought this change in).
   c. The fork's side of the upgrade merge: for each merge commit from `git log --no-show-signature --merges --format=%H` (newest first), try `<merge>^1`, then `<merge>^2`. When a fork merges upstream, `^1` is the fork's own pre-merge tip, so every legacy file is read as it was just before the upgrade.
   d. Last resort: each commit from `git log --no-show-signature --full-history --format=%H -- .claude/skills/job-application-assistant/01-candidate-profile.md`. Keep `--full-history`: without it git follows the merge's upstream side and never reaches the fork's commits.

   Always pass `--no-show-signature` to `git log`: with `log.showSignature` set, signature lines end up in the list of commit ids.

   If no candidate qualifies, tell the user "No legacy profile found in git history; starting a fresh setup." and continue with a fresh setup.
2. Read these from `<ref>` with `git show <ref>:<path>` (skip any that do not exist there): `.claude/skills/job-application-assistant/01-candidate-profile.md` through `07-interview-prep.md`, `.claude/skills/job-scraper/search-queries.md`, and `CLAUDE.md`. If `<ref>` came from step 1d, it is only the last commit that touched `01`: tell the user the other files are read as of that commit and may miss later edits (for example a template registered with `/add-template` afterwards), so they check each proposed file.
3. Build the new files with this mapping:

   | Legacy region | New home |
   |---|---|
   | `01-candidate-profile.md` (all) | `profile/candidate.md` |
   | `02-behavioral-profile.md` (all) | `profile/behavioral.md` |
   | `03-writing-style.md` `## Patterns Observed in Past Applications` | `profile/writing-patterns.md` |
   | `04-job-evaluation.md` match areas, experience lines, career goals, energizing/draining tasks, life-situation lines, permit second gate, `## Calibration from Past Applications` | `profile/evaluation.md` (Skill Match Areas, Experience Areas, Career Goals, Motivation, Life Situation, Eligibility Constraints, Calibration) |
   | `05-cv-templates.md` profile statements (incl. `[Used for: ...]`), `ACTIVE-TEMPLATE` block | `profile/cv.md` (Profile Statements, Active Template) |
   | `06-cover-letter-templates.md` extracted patterns, `ACTIVE-TEMPLATE` block | `profile/cover-letter.md` (Patterns From Past Letters, Active Template) |
   | `07-interview-prep.md` `## Ready-Made STAR Examples`, `## STAR Candidates (Complete Manually)` | `profile/star.md` |
   | `job-scraper/search-queries.md` (all) | `profile/search-queries.md` |
   | `CLAUDE.md` Identity fields `LinkedIn headline`, `CV language`; `## Certifications`; What Excites You, Target Sectors, Deal-breakers | `profile/candidate.md` (Identity, Certifications); `profile/evaluation.md` (What Excites You, Target Sectors, Deal-breakers) |

   The contact details in the legacy `05`/`06` LaTeX blocks and the rest of the legacy `CLAUDE.md` summary are used only to cross-check `profile/candidate.md`. Report every conflict (for example a different job title or email) and ask the user which to keep. Never silently pick one.
4. Show every proposed `profile/*.md` file in full and write them only after the user confirms.
5. Check the templates. If `${CLAUDE_SKILL_DIR}/../job-application-assistant/profile-templates/candidate.md` no longer contains `[YOUR_EMAIL]`, `behavioral.md` no longer contains `[PROFILE_TYPE]`, or `search-queries.md` no longer contains `[YOUR_JOB_BOARD]`, git's rename detection carried the old data into the template files during the merge. Build the profile from `<ref>` as above (never from a polluted template), then tell the user to restore the templates from the remote they merged, for example `git checkout upstream/master -- plugins/ai-job-search/skills/job-application-assistant/profile-templates/`, and commit.
6. Tell the user: "Your data is now in `profile/`. If git still shows merge conflicts in files under `plugins/`, `.claude/skills/` or in `CLAUDE.md`, resolve them by taking the upstream version, for example `git checkout --theirs plugins/ai-job-search/skills/job-application-assistant/04-job-evaluation.md`; for a file upstream deleted, use `git rm <path>`. Your old data stays in git history." Migration deletes nothing.

### Step 0b: Choose a path

If `$ARGUMENTS` contains `--section <name>`, skip directly to that section in Path C for an update-only flow. Do not run the path-selection prompt below.

Otherwise, first check where this working copy would publish to — **before anything is
written, not after** (the Step 4 privacy note fires only once every file is already on
disk, which is too late to inform the decision). Run `git remote get-url origin`; if the
command fails (no remote, or not a git checkout), skip this check silently. If there is
a GitHub `origin`, check it with `gh repo view <owner/repo> --json visibility,isFork`
when `gh` is available. If the origin is a **public fork** of the template — or its
visibility cannot be determined — warn now and wait:

> **Heads-up before we start:** your `origin` points at `<owner/repo>`, which is a
> public GitHub fork. This setup writes your personal data (name, contact details,
> employment history, salary expectations) into **tracked** files, and anything you
> commit *and push* to that fork is visible to anyone. Two safe options: keep your
> profile commits local and never push them, or push to a **private** repository
> instead — SETUP.md section 8 has the two-minute private-remote recipe. Want to
> continue with the setup?

Wait for the user's confirmation before showing the path prompt. A private origin, no
origin, or a non-fork remote needs no warning — continue silently.

Then, before greeting the user, scan the `documents/` folder. Use Glob with `documents/**/*` and count files per subfolder (`cv/`, `linkedin/`, `diplomas/`, `references/`, `projects/`, `applications/`).

Then welcome the user with a single message that lists three paths. The wording changes based on what was found.

**If `documents/` has files** in one or more subfolders, lead with Path A:

> **Welcome to the AI Job Search setup!**
>
> I'll help you build your professional profile so Claude can evaluate job postings, tailor CVs, write cover letters, and prepare you for interviews.
>
> I see files in your `documents/` folder: [list per subfolder, e.g. "2 in cv/, 1 in linkedin/, 3 in references/"]. Three ways to start:
>
> **Path A: Read my documents folder** (recommended for what you have) - I'll read everything in `documents/`, cross-reference for consistency, and build your profile from real source materials. Idempotent and safe to re-run as you add more documents.
>
> **Path B: Single CV import** - Paste or @-mention a single CV/resume here. I'll extract it and ask follow-up questions for what's missing.
>
> **Path C: Interview mode** - I'll walk you through structured questions section by section.
>
> Which would you like?

**If `documents/` is empty or missing**, surface Path A as a "do this if you have materials" option:

> **Welcome to the AI Job Search setup!**
>
> I'll help you build your professional profile so Claude can evaluate job postings, tailor CVs, write cover letters, and prepare you for interviews.
>
> Three ways to start:
>
> **Path A: Documents folder** (best signal if you have several materials) - Drop your CV / LinkedIn export / diplomas / reference letters / project summaries in the `documents/` folder, then say "go". I'll read everything and build your profile from it. See `documents/README.md` for the folder layout.
>
> **Path B: Single CV import** - Paste or @-mention a single CV/resume here. I'll extract it and ask follow-up questions for what's missing.
>
> **Path C: Interview mode** - I'll walk you through structured questions section by section. Good if you're starting from scratch.
>
> Which would you like?

Wait for the user's choice. If they pick A but the folder is still empty, tell them what to add (point at `documents/README.md`) and stop.

---

## Path A: Documents Folder

Reads structured documents in `documents/`, cross-references them for consistency, and merges extracted data into the profile files in `profile/`. Read-before-write and idempotent: changes already present will not be proposed again.

Follow these steps **exactly in order**.

### Step A1: Inventory

Use Glob with `documents/**/*` to scan the full tree. Print:

```
## Documents Found

**cv/**: [list files, or "(empty)"]
**linkedin/**: [list files, or "(empty)"]
**diplomas/**: [list files, or "(empty)"]
**references/**: [list files, or "(empty)"]
**projects/**: [list files, or "(empty)"]
**applications/**: [list subfolders with their files, or "(empty)"]

I will read these and cross-reference before proposing any changes.
```

If every subfolder is empty, stop and tell the user to populate the folder. Point at `documents/README.md` for the layout.

### Step A2: Read Existing Profile Files

Read these in parallel before extracting anything. You must know what is already there to make the merge intelligent.

- `profile/candidate.md`
- `profile/behavioral.md`
- `profile/writing-patterns.md`
- `profile/evaluation.md`
- `profile/cv.md`
- `profile/cover-letter.md`
- `profile/star.md`

Hold this content in context throughout Path A. Do not re-read.

### Step A3: Parse Documents

Read each document found in Step A1. Process subfolders in this order: `cv/`, `linkedin/`, `diplomas/`, `references/`, `projects/`, `applications/`.

**`cv/` documents:** name, contact (email, phone, LinkedIn, GitHub), education (degree, institution, dates, thesis), work experience (title, company, dates, location, bullets), skills, languages (with any stated proficiency), publications, awards, profile/summary.

**`linkedin/` documents:** About/summary section (full text, used for behavioral inference), work experience, education, skills and endorsements, **Languages section** (language name + self-rated proficiency level, e.g. "Spanish - Native or bilingual proficiency" - a high-confidence structured source, feeds the Language Gate in `04-job-evaluation.md`), certifications, volunteer work, publications, recommendations received (full text). If multiple LinkedIn exports are present, use the most recently modified file.

**`diplomas/` documents:** official degree title and level, institution name (official spelling), graduation date, grade or distinction or GPA if visible.

**`references/` documents:** referee name, title, organization; full text of the letter (extract specific quotes); competency language used.

**`projects/` documents:** project name, summary/description, problem domain, tech stack (languages, frameworks, tools), key technical challenges and architectural decisions, measurable outcomes/metrics (e.g. users, performance, stars, impact).

**`applications/<company>_<role>/` subfolders:**
- `job_posting.md`: role title, company, required skills, experience level, sector, role type
- `cover_letter.tex`: opening structure, body structure, bullet style, closing, recurring phrases
- `cv_draft.tex`: profile statement, section ordering, framing for this role type
- `outcome.md`: status (in_progress/hired/offer_declined/rejected/no_response/interview_only), interview stages, notes. Skip `in_progress` applications for calibration — they have no final signal yet.

After reading, proceed to Step A4 without intermediate output. The user sees a complete picture in Step A6.

### Step A4: Cross-Reference Check

Before mapping anything to profile files, check for inconsistencies:

- Date mismatches between CV / LinkedIn / diploma
- Title mismatches across documents for the same role
- Education mismatches (degree name, graduation date)
- Employer name variations

If inconsistencies are found, present them as a numbered list and wait for the user to resolve each one before continuing:

```
## Cross-Reference Issues Found

These need to be resolved before I continue. For each one, tell me which version is correct.

1. **Role title mismatch - [COMPANY]:**
   CV says: "[TITLE_A]"
   LinkedIn says: "[TITLE_B]"
   Which is correct?

2. ...
```

If no inconsistencies, state "No cross-reference issues found." and continue.

### Step A5: Build Change Sets

For each profile file, compare extracted document content against the current file content from Step A2. Build two buckets.

**Additive changes:** entirely new content not in the profile file in any form. Examples: a certification not in `profile/candidate.md`, a new independent project not in `profile/candidate.md`, a new endorsement skill, a referee not yet listed, a new behavioral quote from a reference letter, a new award.

**Conflicting changes:** content that touches something already in a profile file but disagrees. Examples: a different date range for an existing job, a different job title for the same role, a different graduation date than what is recorded.

**Inference rules** (apply when populating from inferred sources):

- **`profile/candidate.md` (`## Independent Projects`):** Source is `projects/` documents. Extract structured project entries formatted as `- **[PROJECT_NAME]**: [DESCRIPTION with tech stack and measurable outcome]`. Ground all claims in the document text.
- **`profile/behavioral.md`:** Source is LinkedIn About + recommendation letters. Extract recurring themes, adjectives, phrases about how the candidate works. Add only to "Strongest Behavioral Traits", "How [Candidate] Works Best", or "Management Style Preferences" sections. Do not overwrite existing scored assessments. Always label inferred additions: *[Inferred from LinkedIn About / Reference letter - review before relying on this]*
- **`profile/writing-patterns.md`:** Source is `cover_letter.tex` files. Extract recurring patterns. Add as observations under "## Patterns Observed in Past Applications". Only add if 2+ cover letters show a genuine pattern.
- **`profile/evaluation.md`:** Source is `job_posting.md` + `outcome.md` pairs. If an application reached interview or offer: note role type and sector as a confirmed strong-fit signal. If 2+ applications repeat a no-response or rejection pattern: note it. Add findings under "## Calibration".
- **`profile/cv.md` (`## Profile Statements`):** Source is `cv_draft.tex` files. Extract any profile statement that does not already appear in templates. Label with: *[Used for: <company>_<role>]*. **Ground before extracting:** archived drafts are tailored outputs, not source documents - verify every factual claim in an extracted statement (titles, employers, metrics, technologies) against `profile/candidate.md` and drop or correct any claim the profile does not support, keeping only the framing. A tailored draft that drifted must never become a template future applications start from.
- **`profile/cover-letter.md` (`## Patterns From Past Letters`):** Source is `cover_letter.tex` files. Extract opening patterns, bullet structures, closing formulations. Add only what is structurally distinct from existing templates.
- **`profile/star.md`:** Source is CV bullets, LinkedIn descriptions, reference letter quotes. Identify achievements not yet covered by an existing STAR example. Do NOT draft full STAR examples. Add stubs under "## STAR Candidates (Complete Manually)":

```markdown
### [Achievement title]
**Source:** [CV / LinkedIn / Reference letter - role/company]
**What happened:** [one sentence]
**Why it matters:** [interview question types this could answer]
**S/T/A/R stub:**
- Situation:
- Task:
- Action:
- Result:
```

### Step A6: Present and Confirm Changes

Present the full change set before writing anything.

**Additive changes** (single grouped list, organized by target file):

```
## Proposed Additive Changes

### profile/candidate.md
- [ ] New certification: [title], [issuer], [date] - extracted from LinkedIn
- [ ] New independent project: [PROJECT_NAME] - [description, tech stack, key outcome]
- [ ] New reference: [name, title, company]
  Quote: "[relevant quote]"

### profile/behavioral.md
- [ ] New behavioral observation [labeled as inference]: "[phrase]"

[and so on per file]
```

Then ask:

> **Apply all additive changes?** These add new content without touching anything already in the files.
> Reply **yes** to apply all, or list the numbers you want to skip.

Wait for the response. Apply only the confirmed items.

**Conflicting changes** (one at a time):

```
## Conflict 1 of [N]: Job title - [COMPANY]

**Current in profile/candidate.md:**
[TITLE_A] - [COMPANY] ([START]-[END])

**Proposed (from LinkedIn export):**
[TITLE_B] - [COMPANY] ([START]-[END])

Options:
  [keep] Keep the existing text
  [replace] Replace with the version from the document
  [manual] I'll edit this myself - skip for now
```

Wait for the user's choice on each conflict. If no conflicts, state "No conflicting changes found." and skip this section.

### Step A7: Write Confirmed Changes and Fill Gaps

Apply the confirmed changes with the Edit tool. Make targeted edits only. Do not rewrite entire files. State which changes were applied per file. If a file has no confirmed changes, state "No changes made to [filename]."

Documents cover skills, experience, education, references, and behavioral signal. They do not cover everything `/apply` and `/scrape` need. After the writes, ask follow-up questions for gaps:

- Career goals and target role types
- What excites the user in their next role
- Deal-breakers and must-haves
- Languages you work in professionally, with proficiency levels (only if not already extracted from `cv/` or `linkedin/` above) - this feeds the Language Gate in `04-job-evaluation.md`, so ask directly rather than skipping it
- Salary expectations / baseline (optional)
- Commute or location constraints (if not visible from CV)
- Job search configuration (use the questions from Path C Section 9 below)

Then proceed to Step 3 to populate the remaining profile files. Step 3 detects which profile files Path A already populated and skips those substeps.

---

## Path B: Single CV Import

If the user provides a single CV/resume:

1. Read the document thoroughly.
2. Extract all structured information: name, contact, education, experience, skills, languages, publications, awards.
3. Present a summary of what was extracted.
4. Ask follow-up questions for gaps (behavioral profile, career goals, deal-breakers, languages and proficiency levels if not already extracted, salary expectations, references).
5. Proceed to Step 3 (file generation).

---

## Path C: Interview Mode

Walk through each section conversationally. Ask questions naturally, not as a form. Let the user answer in their own words and you'll structure the data.

### Section 1: Identity & Contact
Ask about:
- Full name
- Location (city, country)
- Phone, email, LinkedIn, GitHub
- What languages they work in professionally, and roughly what level in each (native, fluent, conversational, a CEFR letter like B2 - whatever's natural for them to describe, doesn't need to be precise). Worth explaining why: a posting requiring a language they don't list at all gets auto-excluded later by the Language Gate, while one asking for a higher level in a language they do list gets flagged for their own judgment instead of silently passed or rejected - so it's worth being honest here rather than optimistic.
- Current employment status
- Family/commute constraints (if any)

### Section 2: Education
For each degree:
- Level (PhD, MSc, BSc, etc.), field, institution, years
- Thesis topic (if applicable)
- Key coursework or topics

Also ask about certifications (online courses, professional certs).

### Section 3: Professional Experience
For each role (most recent first):
- Job title, company, dates, location
- Key responsibilities (3-5 bullets)
- Key achievements or projects
- Technologies/tools used

Also ask about independent projects, freelance work, or side projects.

### Section 4: Technical Skills
- Programming languages + proficiency level
- ML/AI frameworks and tools
- Domain expertise
- Software tools and platforms
- Any other technical skills

### Section 5: Publications & Awards (optional)
- Peer-reviewed papers, conference presentations
- Hackathons, competitions, awards
- Skip if not applicable

### Section 6: Behavioral Profile (optional)
If they have a formal assessment (PI, DISC, Myers-Briggs, StrengthsFinder):
- Ask them to describe or share the results

If not, ask behavioral questions:
- "What work environments do you thrive in?"
- "What drains your energy at work?"
- "How do you prefer to work in teams?"
- "How do you make decisions, quickly or deliberately?"
- "What's your communication style?"
- Synthesize answers into a behavioral profile

### Section 7: Career Goals & Preferences
- Target roles and industries
- What excites you in work
- Deal-breakers and must-haves
- Salary expectations/baseline (optional)
- What environments to avoid
- Commute/location constraints

### Section 8: References (optional)
For each reference:
- Name, title, company, email, phone
- Relationship to the user

### Section 9: Job Search Configuration
This section generates the search queries that power `/scrape`. Use the information from Sections 1, 4, and 7 to build targeted queries.

Ask about:
- **Role titles to search for:** Job titles for the same underlying work vary a lot across companies and markets - a "Data Scientist" role at one employer may be called "Insights Analyst" or "Data Consultant" at another. Ask about the function first: "What kind of work do you actually want to be doing day-to-day?" Then translate that into concrete search terms: "Given that, what job titles should I search for? For example: Data Scientist, ML Engineer, Geophysicist." Collect 3-8 specific titles, but keep the underlying function in mind - it feeds the category naming in `profile/search-queries.md` and the Experience Match dimension in `04-job-evaluation.md`.
- **Key skills as search terms:** "Which of your skills are most likely to appear in job postings?" Pick 3-5 that are distinctive and searchable.
- **Target companies (optional):** "Are there specific companies you'd like to monitor for openings?"
- **Geographic scope:** "Which cities or regions should I search in? How far are you willing to commute?" Use this to define the location filter tiers (ideal, acceptable, borderline, too far).
- **Job portals:** "The framework ships country-agnostic search CLIs (`linkedin-search`, `freehire-search`) in the `ai-job-search` plugin, plus Danish portals (Jobindex, Jobbank, Jobdanmark, Jobnet) in a separate `danish-job-portals` plugin that is **off by default**. `/scrape` uses every installed portal skill, plus your own from `/add-portal` in `.agents/skills/`, and skips any listed under Disabled Portals in `profile/search-queries.md`. Which portals fit your market?" **Then act on the answer:** if the user's market is Denmark (or they ask for the Danish boards), turn the Danish plugin on: in a clone of the repository, add `{"enabledPlugins": {"danish-job-portals@ai-job-search": true}}` to `.claude/settings.local.json` (merge it into any existing content); otherwise tell them to run `/plugin install danish-job-portals@ai-job-search`. Either way, the portals load in the next session. If the user needs a local board that is not shipped, guide them to `/add-portal`. WebSearch/`site:` queries remain the fallback for portals without a CLI skill.
- **CV language:** "Should your CVs be written in English (the default, accepted in most markets), or in your market's language?" Record the answer as a `CV language: <language>` line in the Identity section of `profile/candidate.md`. Cover letters always match each posting's language automatically; this setting governs the CV only. If the user is unsure, keep English and note they can re-run `/setup --section search` to change it.

**Important:** Also suggest role types the user may not have considered, based on their skill profile. For example:
- If they have strong Python + domain expertise: "Have you considered roles like 'Technical Consultant' or 'Solutions Engineer' in your domain?"
- If they have ML + a specific industry: "Companies in adjacent industries also hire for these skills. Should I include searches for [adjacent sector]?"
- If they have project management experience alongside technical skills: "Would you also want to search for 'Technical Project Manager' or 'Team Lead' roles?"

This proactive suggestion step helps users discover career paths they might not have considered.

---

## Step 3: Generate Profile Files

Once data collection is complete, generate or finish populating the files below. **For Path A**, several profile files are already populated by Step A7; check each before writing and skip it if its content is no longer placeholder text. All targets are under `profile/`.

### 1. Populate `profile/candidate.md`
Identity (including LinkedIn headline, **CV language**, and Languages with levels), Education, Professional Experience, Independent Projects, Technical Skills, Certifications, Publications, Awards, References. The contact details here are the only copy: `/apply` fills the CV and cover-letter templates from them when drafting.

### 2. Populate `profile/behavioral.md`
The behavioral profile, based on assessment results or synthesized answers.

### 3. Populate `profile/evaluation.md`
Skill Match Areas (strong, moderate, weak), Experience Areas, Career Goals, What Excites You, Target Sectors, Deal-breakers, Motivation, Life Situation. Record a permit hours/start-date limit under Eligibility Constraints.

### 4. Populate `profile/cv.md`
Two or three role-specific profile statements under Profile Statements. Leave Active Template empty (only `/add-template` writes it).

### 5. Populate `profile/cover-letter.md`
Nothing to ask here for Path B and C: leave both sections empty. Path A fills Patterns From Past Letters.

### 6. Populate `profile/writing-patterns.md`
Nothing to ask here for Path B and C. Path A fills it from past cover letters.

### 7. Populate `profile/star.md`
At least 3-4 STAR examples from the candidate's actual experience. Path A leaves stubs under STAR Candidates (Complete Manually) instead; mention them in Step 4.

### 8. Update `cv/main_example.tex`
Replace placeholder personal data with the candidate's actual name, contact info, and add their education and most recent experience entries.

### 9. Populate `profile/search-queries.md`
Replace all placeholder tokens in the search queries file with the user's actual information from Section 9 (or the equivalent follow-up questions in Path A's Step A7):
- Replace `[YOUR_PRIMARY_ROLE_TYPE]`, `[YOUR_PRIMARY_JOB_TITLE]`, etc. with actual role titles
- Replace `[YOUR_KEY_SKILL]`, `[YOUR_DOMAIN_KEYWORD_1]`, etc. with actual skills and domain terms
- Replace `[YOUR_CITY]`, `[YOUR_COUNTRY]`, `[YOUR_REGION]` with actual location
- Fill in the location filter tiers (ideal, acceptable, borderline, too far) based on commute constraints
- Organize queries into priority categories matching the user's career direction:
  - Priority 1: Their strongest/most desired role direction
  - Priority 2: Their domain expertise
  - Priority 3: Adjacent roles they could pivot into
  - Priority 4: Broader roles (wider net)

---

## Step 4: Confirm & Next Steps

Present a summary:

> **Setup complete!** Here's what was generated:
>
> - `profile/candidate.md` - Your candidate profile (identity, contact details, experience, skills)
> - `profile/behavioral.md` - Behavioral assessment
> - `profile/evaluation.md` - Personalized evaluation inputs
> - `profile/cv.md` - Your profile statements
> - `profile/star.md` - STAR examples from your experience
> - `profile/search-queries.md` - Job search queries for `/scrape`
> - `cv/main_example.tex` - Your LaTeX CV template
>
> **Privacy note:** the files above now contain your personal data. `profile/` and `cv/main_example.tex` are *tracked by git* in your repository.
> A GitHub fork of the template is always public (forks of public repos cannot be made
> private), so do not push these commits to a fork. Keep them local, or push to a private
> repository instead - see SETUP.md section 8 for the private-remote setup.
>
> **Try it out:**
> - Run `/scrape` to search for matching jobs right now
> - Run `/apply` with a job posting URL to see the full application workflow
> - Run `/setup --section search` later to update your search queries as your priorities evolve

If Path A left any STAR stubs in `profile/star.md`, also note:

> Path A flagged [N] STAR candidate stubs in `profile/star.md` that need your situation/task/action/result details before you use them in interviews.

---

## Design Principles

- Three onboarding paths converge on the same profile files. Step 0 picks the right path based on what's in `documents/`. Steps 3 and 4 are shared.
- Path A is read-before-write and idempotent. Re-running it as documents are added does not duplicate or overwrite existing content; conflicts are surfaced for explicit resolution.
- Path A labels inferred behavioral or style additions so the user can review them critically before relying on them.
- Each section in Path C is a natural conversation, not a form. The user can skip optional sections.
- Synthesize answers into structured formats (the user does not need to know markdown or LaTeX).
- Can be re-run with `--section <name>` to update specific sections (e.g., `/setup --section search` to reconfigure job search queries without re-doing the full profile).
- Section 9 (search) in Path C, and the equivalent follow-up questions in Path A, proactively suggest role types the user may not have considered.
- At the end, suggest running `/scrape` and `/apply` with a test job posting.
