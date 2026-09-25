# Profile Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all candidate data out of framework skill files into a workspace `profile/` folder created from framework-owned templates, and give existing personalized forks a `/setup` migration.

**Architecture:** Eight pristine templates live in `.claude/skills/job-application-assistant/profile-templates/`. `/setup` copies any missing ones into `profile/` (not tracked upstream) and writes candidate data only there. Framework files keep only rules and point at profile data with `` `profile/<file>.md#<anchor>` `` links that a test resolves. `CLAUDE.md` keeps no personal data; the workflow and verification checklist move to a framework file, `10-verification.md`.

**Tech Stack:** Markdown command/skill specs (the spec *is* the implementation), Python 3 stdlib `unittest` tests, GitHub Actions CI, LaTeX (lualatex/xelatex) smoke compiles.

**Spec:** `docs/superpowers/specs/2026-09-24-plugin-profile-separation-design.md` — sections "Branch 1 design: profile separation" and "Planning clarifications (branch 1)". Read both before starting.

## Global Constraints

- Work on branch `plugin/1-profile-separation`, created from `master`. Never commit the uncommitted thin-wrapper files (`.claude-plugin/`, `README.md` and `CHANGELOG.md` edits from before this plan) — stash them first: `git stash push -m thin-wrapper -- .claude-plugin README.md CHANGELOG.md`.
- Framework dir: `.claude/skills/job-application-assistant/` (below: `FW/`). Templates dir: `FW/profile-templates/` (below: `TPL/`).
- The 8 template names, exactly: `candidate.md`, `behavioral.md`, `evaluation.md`, `cv.md`, `cover-letter.md`, `writing-patterns.md`, `star.md`, `search-queries.md`.
- Pointer syntax, exactly: `` `profile/<name>.md#<anchor>` `` where `<anchor>` is the GitHub slug of a heading in `TPL/<name>.md` (lowercase, spaces → `-`, drop characters other than letters, digits, `-`, `_`).
- `[YOUR_*]`, `[FIRST_NAME]`, `[LAST_NAME]` tokens may appear only in templates, `cv/main_example.tex`, `cover_letters/cover_example.tex`, and in commands that *describe* those tokens. Framework files `FW/03`–`FW/10` and `FW/SKILL.md` contain none of them.
- Draft-time contact tokens in `05`/`06`, exactly: `[CANDIDATE_NAME]`, `[CANDIDATE_FIRST_NAME]`, `[CANDIDATE_LAST_NAME]`, `[CANDIDATE_ADDRESS]`, `[CANDIDATE_PHONE]`, `[CANDIDATE_EMAIL]`, `[CANDIDATE_LINKEDIN_URL]`, `[CANDIDATE_GITHUB_URL]`.
- Every file under `FW/*.md`, `TPL/*.md` and `AGENTS.md` carries `framework_version` frontmatter. Each such file edited on this branch is bumped **once** relative to `master` (minor bump; new files start at `1.0.0`). Target versions: `03` 1.3.0, `04` 1.3.0, `05` 1.5.0, `06` 1.1.0, `07` 1.1.0, `08` 1.1.0, `SKILL.md` 1.4.0, `AGENTS.md` 1.1.0, `10-verification.md` 1.0.0, all templates 1.0.0.
- Tests use stdlib `unittest` only. Run one file with `python3 -m unittest tests.<module> -v`, the suite with `python3 -m unittest discover -s tests -t . -v`.
- Writing rules for all new prose (repo style): no em-dashes in candidate-facing text; plain, direct sentences; keep command specs' existing heading structure.
- Commit messages: conventional commits; end every message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **`profile/` partially exists** (user created some files by hand, or an earlier `/setup` was interrupted) → `/setup` must copy only the *missing* templates and never overwrite an existing profile file. Pinned in Task 4 (`test_step0a_copies_only_missing_templates`).
2. **Fresh clone after this branch, user runs `/apply` or `/rank` before `/setup`** → the profile guard stops and says "run `/setup`"; nothing is scored against placeholders. Pinned in Task 2 (`test_skill_defines_profile_guard`) and Task 3 (`test_apply_runs_profile_guard_first`).
3. **Legacy fork with a custom template active** (an `ACTIVE-TEMPLATE` block inside old `05`/`06`) → migration must carry it into `profile/cv.md` / `profile/cover-letter.md`, otherwise `/apply` silently falls back to the stock template. Pinned in Task 5 (`test_migration_carries_active_template`).
4. **`/reset profile` with a custom template active** → the Active Template section survives the reset, as it does today. Pinned in Task 4 (`test_reset_preserves_active_template`).
5. **Legacy `CLAUDE.md` summary disagrees with legacy `01`** (common: users edited one and not the other) → migration reports each conflict and asks; it never silently picks one. Pinned in Task 5 (`test_migration_reports_conflicts`).

---

### Task 1: Profile templates

**Files:**
- Create: `TPL/candidate.md`, `TPL/behavioral.md`, `TPL/evaluation.md`, `TPL/cv.md`, `TPL/cover-letter.md`, `TPL/writing-patterns.md`, `TPL/star.md`, `TPL/search-queries.md`
- Create: `tests/test_profile_separation.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the 8 templates and their headings, which later pointers target. Required headings (exact text):
  - `candidate.md`: `## Identity`, `### Languages`, `## Education`, `## Professional Experience`, `## Independent Projects`, `## Technical Skills`, `## Certifications`, `## Publications`, `## Awards`, `## References`
  - `evaluation.md`: `## Skill Match Areas`, `## Experience Areas`, `## Career Goals`, `## What Excites You`, `## Target Sectors`, `## Deal-breakers`, `## Motivation`, `## Life Situation`, `## Eligibility Constraints`, `## Calibration`
  - `cv.md`: `## Active Template`, `## Profile Statements`
  - `cover-letter.md`: `## Active Template`, `## Patterns From Past Letters`
  - `writing-patterns.md`: `## Patterns Observed in Past Applications`
  - `star.md`: `## Ready-Made STAR Examples`, `## STAR Candidates (Complete Manually)`
- Produces in `tests/test_profile_separation.py`: constants `REPO`, `FW`, `TPL`, `TEMPLATES` and helper `slug(heading: str) -> str`, `headings(path: Path) -> set[str]` (set of slugs), reused by Tasks 2, 3, 6, 7.

The originals (`FW/01-candidate-profile.md`, `FW/02-behavioral-profile.md`, `.claude/skills/job-scraper/search-queries.md`) stay in place until Task 7, so every existing test keeps passing.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_profile_separation.py`:

```python
"""Guards for the profile/ separation (spec: docs/superpowers/specs/
2026-09-24-plugin-profile-separation-design.md, branch 1).

Candidate data lives in a workspace profile/ folder created from the
framework-owned templates in profile-templates/. Framework files hold rules
only and point at profile data with `profile/<file>.md#<anchor>` links.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FW = REPO / ".claude" / "skills" / "job-application-assistant"
TPL = FW / "profile-templates"
TEMPLATES = (
    "candidate.md",
    "behavioral.md",
    "evaluation.md",
    "cv.md",
    "cover-letter.md",
    "writing-patterns.md",
    "star.md",
    "search-queries.md",
)
# A token /setup fills. Each template must still carry its sentinel.
SENTINELS = {
    "candidate.md": "[YOUR_EMAIL]",
    "behavioral.md": "[PROFILE_TYPE]",
    "evaluation.md": "[YOUR_PRIMARY_SKILLS]",
    "cv.md": "[YOUR_PROFILE_STATEMENT_TEMPLATE_1]",
    "cover-letter.md": "## Patterns From Past Letters",
    "writing-patterns.md": "## Patterns Observed in Past Applications",
    "star.md": "[PROJECT_NAME]",
    "search-queries.md": "[YOUR_JOB_BOARD]",
}
REQUIRED_HEADINGS = {
    "candidate.md": ["Identity", "Languages", "Education", "Professional Experience",
                     "Independent Projects", "Technical Skills", "Certifications",
                     "Publications", "Awards", "References"],
    "evaluation.md": ["Skill Match Areas", "Experience Areas", "Career Goals",
                      "What Excites You", "Target Sectors", "Deal-breakers",
                      "Motivation", "Life Situation", "Eligibility Constraints",
                      "Calibration"],
    "cv.md": ["Active Template", "Profile Statements"],
    "cover-letter.md": ["Active Template", "Patterns From Past Letters"],
    "writing-patterns.md": ["Patterns Observed in Past Applications"],
    "star.md": ["Ready-Made STAR Examples", "STAR Candidates (Complete Manually)"],
}


def slug(heading: str) -> str:
    """GitHub-style anchor for a markdown heading."""
    text = heading.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def headings(path: Path) -> set[str]:
    """Slugs of every ATX heading in a markdown file."""
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            found.add(slug(m.group(1)))
    return found


def frontmatter_version(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    v = re.search(r"^framework_version:\s*(\S+)", m.group(1), re.MULTILINE)
    return v.group(1) if v else None


class TestTemplates(unittest.TestCase):
    def test_every_template_exists_with_framework_version(self):
        for name in TEMPLATES:
            path = TPL / name
            self.assertTrue(path.is_file(), f"missing template {path}")
            self.assertIsNotNone(frontmatter_version(path), f"{name}: no framework_version")

    def test_templates_carry_their_setup_sentinel(self):
        for name, sentinel in SENTINELS.items():
            self.assertIn(sentinel, (TPL / name).read_text(encoding="utf-8"), name)

    def test_templates_have_required_headings(self):
        for name, wanted in REQUIRED_HEADINGS.items():
            have = headings(TPL / name)
            missing = [h for h in wanted if slug(h) not in have]
            self.assertEqual(missing, [], f"{name} lacks headings {missing}")

    def test_candidate_template_holds_fields_that_lived_in_claude_md(self):
        text = (TPL / "candidate.md").read_text(encoding="utf-8")
        self.assertIn("**CV language:**", text)
        self.assertIn("**LinkedIn headline:**", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_profile_separation -v`
Expected: FAIL — `missing template .../profile-templates/candidate.md` (and the other three tests error the same way).

- [ ] **Step 3: Create the copied templates**

```bash
mkdir -p .claude/skills/job-application-assistant/profile-templates
FW=.claude/skills/job-application-assistant
cp $FW/01-candidate-profile.md $FW/profile-templates/candidate.md
cp $FW/02-behavioral-profile.md $FW/profile-templates/behavioral.md
cp .claude/skills/job-scraper/search-queries.md $FW/profile-templates/search-queries.md
```

Then edit them:

`TPL/candidate.md`:
- Frontmatter → `framework_version: 1.0.0`.
- Replace the two `<!-- SETUP: ... -->` comment lines with:
  ```markdown
  <!-- Your profile. /setup creates profile/candidate.md from this template and fills it. Edit freely. -->
  ```
- In `## Identity`, after the `- **Status:** [YOUR_EMPLOYMENT_STATUS]` line, insert:
  ```markdown
  - **LinkedIn headline:** "[YOUR_LINKEDIN_HEADLINE]"
  - **CV language:** [YOUR_CV_LANGUAGE] <!-- English unless your market expects otherwise; /setup asks -->
  ```
- In the `### Languages` comment, replace `Used by the\nLanguage Gate in 04-job-evaluation.md and by job-scraper/search-queries.md's query-language\ngeneration.` with `Used by the\nLanguage Gate in 04-job-evaluation.md and by profile/search-queries.md's query-language\ngeneration.`
- Insert a new section between `## Technical Skills` (and its subsections) and `## Publications`:
  ```markdown
  ## Certifications
  - **[CERTIFICATION_NAME]** - [HOURS]h - completed [DATE]

  ```

`TPL/behavioral.md`: frontmatter → `framework_version: 1.0.0`; replace the first `<!-- SETUP: ... -->` line with `<!-- Your behavioral profile. /setup creates profile/behavioral.md from this template. -->` (keep the PI/DISC comment line).

`TPL/search-queries.md`: prepend frontmatter

```markdown
---
framework_version: 1.0.0
---

```

and replace `<!-- SETUP: Customize these queries based on your skills, target roles, and location -->` with `<!-- Your search queries. /setup creates profile/search-queries.md from this template and fills it; /scrape reads it. -->`.

- [ ] **Step 4: Create the new templates**

`TPL/evaluation.md` (tokens copied from today's `04-job-evaluation.md` and `CLAUDE.md`):

```markdown
---
framework_version: 1.0.0
---

# Evaluation Inputs

<!-- Your personal inputs to the scoring framework in 04-job-evaluation.md. /setup creates profile/evaluation.md from this template and fills it. -->

## Skill Match Areas
**Strong match areas:** [YOUR_PRIMARY_SKILLS]
**Moderate match areas:** [YOUR_SECONDARY_SKILLS]
**Weak match areas:** [SKILLS_YOU_LACK]

## Experience Areas
**Strong:** [YOUR_DIRECT_EXPERIENCE_DOMAINS]
**Moderate:** [YOUR_ADJACENT_EXPERIENCE]
**Entry-level:** [ROLES_WITH_LIMITED_EXPERIENCE]

## Career Goals
- [YOUR_CAREER_GOAL_1]
- [YOUR_CAREER_GOAL_2]
- [YOUR_CAREER_GOAL_3]

## What Excites You
- [PASSION_1]
- [PASSION_2]

## Target Sectors
- [SECTOR_1]: [EXAMPLE_COMPANIES]
- [SECTOR_2]: [EXAMPLE_COMPANIES]

## Deal-breakers
- [DEALBREAKER_1]
- [DEALBREAKER_2]

## Motivation
- Tasks that energize: [YOUR_ENERGIZING_TASKS]
- Tasks that drain: [YOUR_DRAINING_TASKS]

## Life Situation
- **Security**: [YOUR_FINANCIAL_SITUATION_CONTEXT]
- **Flexibility**: [YOUR_SCHEDULE_CONSTRAINTS]
- **Professional development**: [YOUR_GROWTH_PRIORITIES]

## Eligibility Constraints
<!-- A permit that limits hours or start date (e.g. a student visa with a term-time cap), with the specific dates. /setup records it here. Leave empty if none. -->

## Calibration
<!-- /setup Path A records confirmed strong-fit signals and repeated rejection patterns from your resolved applications here. Empty until then. -->
```

`TPL/cv.md`:

```markdown
---
framework_version: 1.0.0
---

# CV Inputs

<!-- Your CV-specific inputs. /setup creates profile/cv.md from this template. Tailoring rules stay in 05-cv-templates.md. -->

## Active Template
<!-- /add-template writes the BEGIN/END ACTIVE-TEMPLATE block here. Empty means the stock moderncv template. -->

## Profile Statements
**For [YOUR_PRIMARY_ROLE_TYPE] roles:**
> [YOUR_PROFILE_STATEMENT_TEMPLATE_1]

**For [YOUR_SECONDARY_ROLE_TYPE] roles:**
> [YOUR_PROFILE_STATEMENT_TEMPLATE_2]

Statements labeled *[Used for: <company>_<role>]* were extracted from archived application drafts by `/setup` Path A. They are **phrasing references, never fact sources**: every factual claim still comes from `profile/candidate.md`.
```

`TPL/cover-letter.md`:

```markdown
---
framework_version: 1.0.0
---

# Cover Letter Inputs

<!-- Your cover-letter inputs. /setup creates profile/cover-letter.md from this template. Structure rules stay in 06-cover-letter-templates.md. -->

## Active Template
<!-- /add-template writes the BEGIN/END ACTIVE-TEMPLATE block here. Empty means the stock cover.cls template. -->

## Patterns From Past Letters
<!-- /setup Path A adds opening, bullet and closing patterns extracted from your submitted cover letters. Empty until then. -->
```

`TPL/writing-patterns.md`:

```markdown
---
framework_version: 1.0.0
---

# Writing Patterns

<!-- Observations from your own past applications. The rules in 03-writing-style.md win on any conflict. -->

## Patterns Observed in Past Applications
<!-- /setup Path A adds a pattern here only when 2+ of your past cover letters show it. Empty until then. -->
```

`TPL/star.md`: frontmatter `framework_version: 1.0.0`, H1 `# STAR Examples`, the comment `<!-- Your STAR examples. /setup creates profile/star.md from this template and fills it; /interview appends approved answers. -->`, then the **entire** `## Ready-Made STAR Examples` section copied verbatim from `FW/07-interview-prep.md` (from that heading down to, not including, `## Common Tough Questions`), then:

```markdown
## STAR Candidates (Complete Manually)
<!-- /setup Path A adds stubs here for achievements not yet covered by a STAR example. -->
```

- [ ] **Step 5: Run to verify it passes**

Run: `python3 -m unittest tests.test_profile_separation -v`
Expected: 4 tests PASS. Then `python3 -m unittest discover -s tests -t . -v` — all PASS (nothing else changed).

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/job-application-assistant/profile-templates tests/test_profile_separation.py
git commit -m "feat(profile): add profile templates for workspace profile/ folder

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Framework files hold rules only

**Files:**
- Modify: `FW/03-writing-style.md`, `FW/04-job-evaluation.md`, `FW/05-cv-templates.md`, `FW/06-cover-letter-templates.md`, `FW/07-interview-prep.md`, `FW/08-application-forms.md`, `FW/SKILL.md`
- Modify: `tests/test_profile_separation.py`, `tests/test_setup_command.py` (class `TemplatesStillCarryThePlaceholders`)

**Interfaces:**
- Consumes: `TPL` headings from Task 1; helpers `slug`, `headings`, `REPO`, `FW`, `TPL`, `TEMPLATES`.
- Produces: the profile guard text in `FW/SKILL.md` under heading `## Profile Guard` (Task 3 and Task 6 reference it by that heading); `[CANDIDATE_*]` tokens in `05`/`06` (Task 3's `/apply` fills them).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_profile_separation.py` (before the `if __name__` block):

```python
SETUP_TOKEN = re.compile(r"\[(?:YOUR_[A-Z0-9_]+|FIRST_NAME|LAST_NAME)\]")
FRAMEWORK_FILES = [
    "03-writing-style.md", "04-job-evaluation.md", "05-cv-templates.md",
    "06-cover-letter-templates.md", "07-interview-prep.md",
    "08-application-forms.md", "09-web-research.md", "SKILL.md",
]
POINTER = re.compile(r"`profile/([\w-]+\.md)(?:#([\w-]+))?`")


def pointer_sources():
    """Every markdown file that may point into profile/."""
    files = sorted((REPO / ".claude").rglob("*.md"))
    files = [f for f in files if TPL not in f.parents]
    for extra in ("CLAUDE.md", "AGENTS.md"):
        if (REPO / extra).exists():
            files.append(REPO / extra)
    return files


class TestFrameworkFilesHoldRulesOnly(unittest.TestCase):
    def test_framework_files_have_no_setup_tokens(self):
        offenders = {}
        for name in FRAMEWORK_FILES:
            path = FW / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            if name == "SKILL.md" and "## Profile Guard" in text:
                # The guard names the [YOUR_EMAIL] sentinel it checks for.
                head, tail = text.split("## Profile Guard", 1)
                text = head + ("\n## " + tail.split("\n## ", 1)[1] if "\n## " in tail else "")
            hits = sorted(set(SETUP_TOKEN.findall(text)))
            if hits:
                offenders[name] = hits
        self.assertEqual(offenders, {}, "framework files must not carry /setup slots")

    def test_draft_time_tokens_use_candidate_prefix(self):
        cv = (FW / "05-cv-templates.md").read_text(encoding="utf-8")
        cover = (FW / "06-cover-letter-templates.md").read_text(encoding="utf-8")
        for token in ("[CANDIDATE_FIRST_NAME]", "[CANDIDATE_LAST_NAME]",
                      "[CANDIDATE_EMAIL]", "[CANDIDATE_PHONE]"):
            self.assertIn(token, cv)
        self.assertIn("\\signature{[CANDIDATE_NAME]}", cover)
        self.assertIn("profile/candidate.md#identity", cv)
        self.assertIn("profile/candidate.md#identity", cover)

    def test_every_profile_pointer_resolves(self):
        broken = []
        for path in pointer_sources():
            for name, anchor in POINTER.findall(path.read_text(encoding="utf-8")):
                tpl = TPL / name
                if name not in TEMPLATES or not tpl.exists():
                    broken.append(f"{path.relative_to(REPO)}: profile/{name}")
                elif anchor and anchor not in headings(tpl):
                    broken.append(f"{path.relative_to(REPO)}: profile/{name}#{anchor}")
        self.assertEqual(broken, [], "pointers into profile/ must hit a real template heading")

    def test_skill_defines_profile_guard(self):
        text = (FW / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Profile Guard", text)
        guard = text.split("## Profile Guard", 1)[1].split("\n## ", 1)[0]
        self.assertIn("profile/candidate.md", guard)
        self.assertIn("[YOUR_EMAIL]", guard)
        self.assertIn("/setup", guard)
```

In `tests/test_setup_command.py`, replace the two methods of `TemplatesStillCarryThePlaceholders` with:

```python
    def test_cv_templates_contact_block_tokens(self):
        text = CV_TEMPLATES.read_text(encoding="utf-8")
        for token in ("[CANDIDATE_FIRST_NAME]", "[CANDIDATE_LAST_NAME]", "[CANDIDATE_EMAIL]", "[CANDIDATE_PHONE]"):
            self.assertIn(token, text)

    def test_cover_letter_templates_contact_and_signature_tokens(self):
        text = COVER_TEMPLATES.read_text(encoding="utf-8")
        for token in ("[CANDIDATE_NAME]", "[CANDIDATE_EMAIL]", "[CANDIDATE_PHONE]", "[CANDIDATE_LINKEDIN_URL]"):
            self.assertIn(token, text)
        self.assertIn("\\signature{[CANDIDATE_NAME]}", text)
```

(Leave `SetupStep3ContactBlocks` alone here; Task 4 rewrites it.)

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_profile_separation tests.test_setup_command -v`
Expected: FAIL — `framework files must not carry /setup slots` listing `05-cv-templates.md` and `06-cover-letter-templates.md` and `04-job-evaluation.md`; `## Profile Guard` missing; `[CANDIDATE_FIRST_NAME]` missing.

- [ ] **Step 3: Edit `04-job-evaluation.md`**

- Frontmatter → `framework_version: 1.3.0`.
- Replace `<!-- SETUP: Skill match areas and career goals are personalized by running /setup -->` with:
  ```markdown
  The candidate's personal inputs (match areas, goals, sectors, deal-breakers, constraints, calibration) live in `profile/evaluation.md`. This file holds the framework only. Apply any findings in `profile/evaluation.md#calibration` when scoring.
  ```
- Replace the paragraph starting `If the candidate's permit also constrains *hours* or *start date*` so its sentence reads: `...record that as a second gate in \`profile/evaluation.md#eligibility-constraints\` during \`/setup\`, with the specific dates.` (rest of paragraph unchanged).
- In the Language Gate, replace `compare it against your Languages table in CLAUDE.md / \`01-candidate-profile.md\`:` with `compare it against the Languages table in \`profile/candidate.md#languages\`:`.
- Replace the three `**Strong/Moderate/Weak match areas:**` lines with `Score against the candidate's match areas in \`profile/evaluation.md#skill-match-areas\`.`
- Replace the three `**Strong:** / **Moderate:** / **Entry-level:**` lines with `Score against the candidate's experience areas in \`profile/evaluation.md#experience-areas\`.`
- Replace the `**Career goals:**` heading line and its three bullets with `**Career goals:** read \`profile/evaluation.md#career-goals\`, \`profile/evaluation.md#what-excites-you\` and \`profile/evaluation.md#target-sectors\`.`
- In the Motivation filter list, replace the two lines `- Tasks that energize: [YOUR_ENERGIZING_TASKS]` / `- Tasks that drain: [YOUR_DRAINING_TASKS]` with one line `- The candidate's energizing and draining tasks: \`profile/evaluation.md#motivation\``.
- Replace the three `**Security**/**Flexibility**/**Professional development**` bullets with `- The candidate's constraints: \`profile/evaluation.md#life-situation\``.
- Under `### 4. Location & Logistics`, append the bullet `- Anything listed in \`profile/evaluation.md#deal-breakers\`: FAIL (deal-breaker)`.

- [ ] **Step 4: Edit `05-cv-templates.md`**

- Frontmatter → `framework_version: 1.5.0`.
- Replace `<!-- SETUP: Profile statements and section ordering are personalized by running /setup -->` with:
  ```markdown
  If `profile/cv.md#active-template` holds an `ACTIVE-TEMPLATE` block (written by `/add-template`), that block wins wherever it conflicts with the stock guidance below.
  ```
- In the LaTeX template block: `pdftitle={[YOUR_NAME] - CV}` → `pdftitle={[CANDIDATE_NAME] - CV}`; `\name{[FIRST_NAME]}{[LAST_NAME]}` → `\name{[CANDIDATE_FIRST_NAME]}{[CANDIDATE_LAST_NAME]}`; `[YOUR_ADDRESS]` → `[CANDIDATE_ADDRESS]`; `[YOUR_PHONE]` → `[CANDIDATE_PHONE]`; `[YOUR_EMAIL]` → `[CANDIDATE_EMAIL]`; `[YOUR_LINKEDIN_URL]` → `[CANDIDATE_LINKEDIN_URL]`; `[YOUR_GITHUB_URL]` → `[CANDIDATE_GITHUB_URL]`.
- Directly after the closing ```` ``` ```` of that LaTeX block, add:
  ```markdown
  Fill every `[CANDIDATE_*]` token from `profile/candidate.md#identity` when drafting a CV. Never edit the tokens in this file.
  ```
- Replace everything from `<!-- SETUP: These are populated based on your background -->` through the sentence ending `a past tailored draft does not vouch for its own accuracy.` with:
  ```markdown
  Start from the candidate's own statements in `profile/cv.md#profile-statements`. Statements labeled *[Used for: <company>_<role>]* are phrasing references, never fact sources: every factual claim still comes from `profile/candidate.md`.
  ```

- [ ] **Step 5: Edit `06-cover-letter-templates.md`**

- Frontmatter → `framework_version: 1.1.0`.
- After the H1, insert:
  ```markdown
  If `profile/cover-letter.md#active-template` holds an `ACTIVE-TEMPLATE` block (written by `/add-template`), that block wins wherever it conflicts with the stock guidance below. Reuse the candidate's own openings and closings from `profile/cover-letter.md#patterns-from-past-letters` where they fit.
  ```
- In the LaTeX block: `[YOUR_NAME]` → `[CANDIDATE_NAME]` (both places), `[YOUR_EMAIL]` → `[CANDIDATE_EMAIL]` (both), `[YOUR_PHONE]` → `[CANDIDATE_PHONE]`, `[YOUR_LINKEDIN_URL]` → `[CANDIDATE_LINKEDIN_URL]`.
- After that LaTeX block's closing fence, add: `Fill every \`[CANDIDATE_*]\` token from \`profile/candidate.md#identity\` when drafting a letter. Never edit the tokens in this file.`

- [ ] **Step 6: Edit `03`, `07`, `08`**

`03-writing-style.md`: frontmatter → `1.3.0`; after the H1 insert `Also apply the candidate's own observed patterns in \`profile/writing-patterns.md#patterns-observed-in-past-applications\`, if any. The rules in this file win on any conflict.`

`07-interview-prep.md`: frontmatter → `1.1.0`; replace the whole `## Ready-Made STAR Examples` section (heading through the line before `## Common Tough Questions`) with:

```markdown
## Ready-Made STAR Examples

The candidate's STAR examples live in `profile/star.md#ready-made-star-examples`. Unfinished stubs from `/setup` Path A are in `profile/star.md#star-candidates-complete-manually`; never present a stub as a finished answer.
```

Also replace the `<!-- SETUP: STAR examples are personalized ... -->` line under the H1 with nothing (delete it).

`08-application-forms.md`: frontmatter → `1.1.0`; in the "rule that governs everything" paragraph replace `the union of \`01-candidate-profile.md\`, the master CV (\`cv/main_example.tex\`), and \`CLAUDE.md\`'s Candidate Profile section, with a claim grounded if ANY of the three supports it` with `the union of \`profile/candidate.md\` and the master CV (\`cv/main_example.tex\`), with a claim grounded if EITHER supports it`; replace the checklist line `- [ ] Every factual claim traces to the union of \`01-candidate-profile.md\`, the master CV (\`cv/main_example.tex\`), and \`CLAUDE.md\`'s Candidate Profile section` with `- [ ] Every factual claim traces to \`profile/candidate.md\` or the master CV (\`cv/main_example.tex\`)`.

- [ ] **Step 7: Edit `SKILL.md`**

- Frontmatter `framework_version: 1.3.4` → `1.4.0`.
- Insert directly after the `# Job Application Assistant` H1 (before the first `---`):

```markdown
## Profile Guard

Run this before any evaluation, ranking, drafting or interview prep. If `profile/` does not exist, or `profile/candidate.md` still contains `[YOUR_EMAIL]`, stop and tell the user: "Your profile isn't set up yet. Run `/setup` first." Never score, rank or draft against placeholder data.
```

- In Workflow Step 1, replace `using the framework in \`04-job-evaluation.md\`` with `using the framework in \`04-job-evaluation.md\` and the candidate's inputs in \`profile/evaluation.md\``.
- Replace the `## Reference Files` table with two tables:

```markdown
## Reference Files

Framework (rules, shipped with the framework):

| File | Purpose |
|------|---------|
| `03-writing-style.md` | Tone, structure, do's and don'ts |
| `04-job-evaluation.md` | Scoring framework for job fit |
| `05-cv-templates.md` | LaTeX CV structure and tailoring rules |
| `06-cover-letter-templates.md` | LaTeX cover letter structure and tailoring rules |
| `07-interview-prep.md` | STAR format, tough questions, roleplay guidelines |
| `08-application-forms.md` | Portal free-text fields: self-introduction, project entries, character-limited pitches |
| `09-web-research.md` | Fetching postings and company pages: trust boundary, the WebFetch 403 fallback, escalation order, claim verification |
| `profile-templates/` | Pristine templates `/setup` copies into `profile/` |

Candidate data (workspace `profile/`, created by `/setup`):

| File | Purpose |
|------|---------|
| `profile/candidate.md` | Identity, CV language, languages, education, experience, skills, certifications, publications, awards, references |
| `profile/behavioral.md` | Behavioral assessment, strengths, ideal environments |
| `profile/evaluation.md` | Match areas, career goals, target sectors, deal-breakers, constraints, calibration |
| `profile/cv.md` | Active CV template, profile statements |
| `profile/cover-letter.md` | Active cover-letter template, patterns from past letters |
| `profile/writing-patterns.md` | Writing patterns observed in past applications |
| `profile/star.md` | STAR examples and unfinished STAR stubs |
| `profile/search-queries.md` | Job search queries for `/scrape` |
```

- [ ] **Step 7b: Verify no stray tokens remain**

Run: `grep -nE '\[(YOUR_[A-Z0-9_]+|FIRST_NAME|LAST_NAME)\]' .claude/skills/job-application-assistant/0[3-9]-*.md .claude/skills/job-application-assistant/SKILL.md`
Expected: exactly one line, the Profile Guard sentence in `SKILL.md` that names `[YOUR_EMAIL]`.

- [ ] **Step 8: Run to verify it passes**

Run: `python3 -m unittest tests.test_profile_separation tests.test_setup_command tests.test_latex_guidance tests.test_apply_page_count tests.test_company_research_cache tests.test_rank_command -v`
Expected: PASS. If `test_latex_guidance` or `test_rank_command` fail, they assert on text you replaced: restore that text's meaning in the new wording rather than editing the test, unless the test asserts a `[YOUR_*]` token or a `01`/`02` path (then update the test to the new token/path).

- [ ] **Step 9: Commit**

```bash
git add .claude/skills/job-application-assistant tests/test_profile_separation.py tests/test_setup_command.py
git commit -m "refactor(skills): framework files point at profile/ instead of holding candidate data

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Verification checklist moves out of CLAUDE.md; /apply reads profile/

**Files:**
- Create: `FW/10-verification.md`
- Modify: `CLAUDE.md`, `.claude/commands/apply.md`
- Modify: `tests/test_profile_separation.py` (add `10-verification.md` to `FRAMEWORK_FILES`, new test class)

**Interfaces:**
- Consumes: `## Profile Guard` (Task 2), `[CANDIDATE_*]` tokens (Task 2), templates (Task 1).
- Produces: `FW/10-verification.md` with headings `## Workflow for New Job Applications` and `## Verification Checklist` (Task 8 docs reference it).

- [ ] **Step 1: Write the failing tests**

In `tests/test_profile_separation.py`, add `"10-verification.md",` to `FRAMEWORK_FILES`, then append:

```python
APPLY = REPO / ".claude" / "commands" / "apply.md"


class TestClaudeMdAndApply(unittest.TestCase):
    def test_verification_file_holds_workflow_and_checklist(self):
        text = (FW / "10-verification.md").read_text(encoding="utf-8")
        self.assertIn("## Workflow for New Job Applications", text)
        self.assertIn("## Verification Checklist", text)
        self.assertIn("### Compiled PDF verification (MANDATORY - never skip)", text)

    def test_claude_md_holds_no_personal_data(self):
        text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIsNone(SETUP_TOKEN.search(text), "CLAUDE.md must hold no /setup slots")
        self.assertNotIn("## Candidate Profile", text)
        self.assertNotIn("## Verification Checklist", text)
        self.assertIn("10-verification.md", text)
        self.assertIn("profile/", text)

    def test_apply_runs_profile_guard_first(self):
        text = APPLY.read_text(encoding="utf-8")
        step1 = text.split("## Step 1", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Profile Guard", step1)

    def test_apply_no_longer_reads_claude_md_for_facts(self):
        text = APPLY.read_text(encoding="utf-8")
        self.assertNotIn("Candidate Profile section", text)
        self.assertNotIn("checklist from `CLAUDE.md`", text)
        self.assertIn("10-verification.md", text)
        self.assertIn("`profile/candidate.md#identity`", text)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_profile_separation -v`
Expected: FAIL — `10-verification.md` missing; CLAUDE.md contains `[YOUR_NAME]`; apply.md lacks `Profile Guard`.

- [ ] **Step 3: Create `FW/10-verification.md`**

Frontmatter `framework_version: 1.0.0`, H1 `# Application Workflow and Verification`, then the `## Workflow for New Job Applications` section, the `**Important:** ... Claude Code ...` line, and the whole `## Verification Checklist` section (with all subsections through the end of `### ATS & keyword verification (CV)`) copied **verbatim** from `CLAUDE.md`, with exactly these edits:
- `4. **Verify both documents** (see Verification Checklist below)` stays as is.
- `- [ ] All claims match actual profile (CLAUDE.md / candidate profile) - no fabricated skills, experience, or achievements` → `- [ ] All claims match the candidate's profile (\`profile/candidate.md\` and \`cv/main_example.tex\`) - no fabricated skills, experience, or achievements`.
- `- [ ] Contact details are correct` → `- [ ] Contact details match \`profile/candidate.md#identity\``.

- [ ] **Step 4: Rewrite `CLAUDE.md`**

Replace the whole file with:

```markdown
# Job Application Assistant

## Role
This repo is a job application workspace. Claude acts as a career advisor and application assistant for the candidate, helping with:
1. **Job fit evaluation** - Assess job postings against the candidate's profile (skills, experience, behavioral traits)
2. **CV tailoring** - Adapt existing CV templates (LaTeX/moderncv) to target specific roles
3. **Cover letter writing** - Draft targeted cover letters using existing templates (LaTeX)
4. **Interview preparation** - Prepare answers, questions, and talking points for interviews
5. **Career strategy** - Advise on positioning and personal branding

## Candidate Data
All personal data lives in `profile/`, which `/setup` creates and fills. Read candidate facts from there and never invent them:
- `profile/candidate.md` - identity, CV language, languages, education, experience, skills
- `profile/behavioral.md` - behavioral profile
- `profile/evaluation.md` - match areas, goals, target sectors, deal-breakers
- `profile/cv.md`, `profile/cover-letter.md`, `profile/writing-patterns.md`, `profile/star.md`, `profile/search-queries.md`

If `profile/` is missing, ask the user to run `/setup`.

## Repo Structure
- `profile/` - Your candidate data (created by `/setup`)
- `cv/` - LaTeX CV variants (moderncv template, banking style)
- `cover_letters/` - LaTeX cover letters (custom cover.cls template)
- `.claude/skills/` - AI skill definitions for the application workflow
- `.agents/skills/` - Job search CLI tools

## Workflow and Verification
Follow `.claude/skills/job-application-assistant/10-verification.md` for the application workflow and the mandatory verification checklist.

**Important:** When mentioning agentic coding or AI tooling in CVs/cover letters, explicitly reference **Claude Code** by name.
```

- [ ] **Step 5: Edit `.claude/commands/apply.md`**

Apply these exact replacements (each `old` occurs once; verify with `grep -c` before editing):

| Old | New |
|---|---|
| ``a fact that is not already in `01-candidate-profile.md` — a metric`` | ``a fact that is not already in `profile/candidate.md` — a metric`` |
| ``- `.claude/skills/job-application-assistant/04-job-evaluation.md`\n- `.claude/skills/job-application-assistant/01-candidate-profile.md`\n`` (lines 36-37) | ``- `.claude/skills/job-application-assistant/04-job-evaluation.md`\n- `profile/evaluation.md`\n- `profile/candidate.md`\n`` |
| ``You already have `01-candidate-profile.md` and `04-job-evaluation.md` in context from Step 1.`` | ``You already have `profile/candidate.md`, `profile/evaluation.md` and `04-job-evaluation.md` in context from Step 1.`` |
| ``if `05-cv-templates.md` or `06-cover-letter-templates.md` opens with an `ACTIVE-TEMPLATE` managed block (inserted by `/add-template`)`` | ``if `profile/cv.md#active-template` or `profile/cover-letter.md#active-template` holds an `ACTIVE-TEMPLATE` managed block (inserted by `/add-template`)`` |
| ``*The master candidate profile (`01-candidate-profile.md`), the master CV (`cv/main_example.tex`), and CLAUDE.md's Candidate Profile section are the sole source of truth for facts;`` | ``*The candidate profile (`profile/candidate.md`) and the master CV (`cv/main_example.tex`) are the sole source of truth for facts;`` |
| ``(the `CV language:` line in CLAUDE.md's Identity section)`` | ``(the `CV language:` line in `profile/candidate.md#identity`)`` |
| ``against the union of three sources: `.claude/skills/job-application-assistant/01-candidate-profile.md` + the master CV (`cv/main_example.tex`) + `CLAUDE.md`'s Candidate Profile section to verify`` | ``against the union of two sources: `profile/candidate.md` + the master CV (`cv/main_example.tex`) to verify`` |
| ``- `.claude/skills/job-application-assistant/01-candidate-profile.md`\n- `.claude/skills/job-application-assistant/02-behavioral-profile.md` —`` (reviewer read list) | ``- `profile/candidate.md`\n- `profile/behavioral.md` —`` |
| ``- The workspace root `CLAUDE.md` file (specifically the Candidate Profile section)\n`` | *(delete the line)* |
| ``against the union of three sources: `.claude/skills/job-application-assistant/01-candidate-profile.md` + the master CV baseline template (`cv/main_example.tex`) + `CLAUDE.md`'s Candidate Profile section. A claim is grounded if ANY of these sources supports it. Mismatches between these three sources themselves`` | ``against the union of two sources: `profile/candidate.md` + the master CV baseline template (`cv/main_example.tex`). A claim is grounded if EITHER source supports it. Mismatches between these two sources themselves`` |
| ``check against `03-writing-style.md` AND `02-behavioral-profile.md`.`` | ``check against `03-writing-style.md` AND `profile/behavioral.md`.`` |
| ``Run the full verification checklist from `CLAUDE.md` now`` | ``Run the full verification checklist from `.claude/skills/job-application-assistant/10-verification.md` now`` |
| ``Report pass/fail for each item in the CLAUDE.md verification checklist`` | ``Report pass/fail for each item in the `10-verification.md` checklist`` |

Then, as the first paragraph under the `## Step 1` heading, insert:

```markdown
**Run the Profile Guard first** (`job-application-assistant/SKILL.md`, section Profile Guard). If it stops, stop here too.
```

And in the drafting read list (the one containing `05-cv-templates.md`/`06-cover-letter-templates.md`), add the lines `- \`profile/cv.md\``, `- \`profile/cover-letter.md\``, `- \`profile/writing-patterns.md\``. After the "Resolve the active template" paragraph, add: `Fill the \`[CANDIDATE_*]\` contact tokens in the stock templates from \`profile/candidate.md#identity\`.`

- [ ] **Step 6: Run to verify it passes**

Run: `grep -nE "01-candidate-profile|02-behavioral-profile|Candidate Profile section|CLAUDE\.md" .claude/commands/apply.md`
Expected: no output.
Run: `python3 -m unittest discover -s tests -t . -v`
Expected: all PASS (`tests.test_placeholder_integrity` reads only `ci.yml` and the templates it names, never `CLAUDE.md`). On any failure: fix the text, not the test.

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md .claude/commands/apply.md .claude/skills/job-application-assistant/10-verification.md tests/test_profile_separation.py
git commit -m "refactor(apply): move workflow and checklist to 10-verification.md, read facts from profile/

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Writers move to profile/ (/setup, /reset, /expand, /add-template)

**Files:**
- Modify: `.claude/commands/setup.md`, `.claude/commands/reset.md`, `.claude/commands/expand.md`, `.claude/commands/add-template.md`
- Modify: `tests/test_setup_command.py`, `tests/test_reset_command.py`

**Interfaces:**
- Consumes: templates (Task 1), pointer anchors (Task 2).
- Produces: `/setup` `### Step 0a: Prepare the profile folder` heading (Task 5 extends it); Step 3 substeps named `### <n>. <Verb> \`profile/<name>.md\`` (tests derive targets from these).

- [ ] **Step 1: Write the failing tests**

In `tests/test_setup_command.py`: add `TPL = SKILL_DIR / "profile-templates"` after `COVER_TEMPLATES`, and replace class `SetupStep3ContactBlocks` with:

```python
class SetupWritesOnlyToProfile(unittest.TestCase):
    def setUp(self):
        self.text = COMMAND.read_text(encoding="utf-8")
        self.sections = _sections(self.text)
        self.step3 = self.sections["Step 3: Generate Profile Files"]

    def test_step3_targets_are_profile_files_with_templates(self):
        import re
        targets = re.findall(r"^###\s+\d+\.\s+\w+\s+`([^`]+)`", self.step3, re.MULTILINE)
        profile_targets = [t for t in targets if t.startswith("profile/")]
        self.assertGreaterEqual(len(profile_targets), 7, targets)
        for t in profile_targets:
            self.assertTrue((TPL / t.split("/", 1)[1]).exists(), f"no template for {t}")
        for t in targets:
            self.assertFalse(t.startswith(".claude/"), f"Step 3 still writes framework file {t}")

    def test_step3_never_edits_framework_latex_blocks(self):
        self.assertNotIn("05-cv-templates.md", self.step3)
        self.assertNotIn("06-cover-letter-templates.md", self.step3)

    def test_step0a_copies_only_missing_templates(self):
        step0 = self.sections["Step 0: Welcome & Choose Path"]
        self.assertIn("### Step 0a: Prepare the profile folder", step0)
        block = step0.split("### Step 0a: Prepare the profile folder", 1)[1]
        self.assertIn("profile-templates/", block)
        self.assertIn("only the missing", block.lower())
        self.assertIn("never overwrite", block.lower())

    def test_step0a_runs_before_section_shortcut(self):
        step0 = self.sections["Step 0: Welcome & Choose Path"]
        self.assertLess(step0.index("Step 0a"), step0.index("--section <name>"))

    def test_completion_summary_lists_profile_files(self):
        summary = self.sections["Step 4: Confirm & Next Steps"].split("**Privacy note:**")[0]
        for name in ("profile/candidate.md", "profile/evaluation.md", "profile/search-queries.md"):
            self.assertIn(name, summary)
        self.assertNotIn(".claude/skills/", summary)
```

In `tests/test_reset_command.py`, replace `setup_step3_skill_files` and class `TestResetCoversEveryPersonalizedSkillFile` with:

```python
TPL = REPO / ".claude" / "skills" / "job-application-assistant" / "profile-templates"


def setup_step3_profile_files():
    """profile/ files /setup Step 3 populates, derived from its own headings."""
    step3 = section(SETUP.read_text(encoding="utf-8"), "## Step 3:", "## Step 4:")
    targets = re.findall(r"^###\s+\d+\.\s+\w+\s+`([^`]+)`", step3, re.MULTILINE)
    return {t.split("/", 1)[1] for t in targets if t.startswith("profile/")}


class TestResetRestoresProfileFromTemplates(unittest.TestCase):
    def setUp(self):
        self.text = RESET.read_text(encoding="utf-8")
        self.files = setup_step3_profile_files()
        self.assertGreaterEqual(len(self.files), 7, self.files)

    def test_preview_lists_every_profile_file(self):
        preview = section(self.text, "### If scope includes `profile`:", "### If scope includes `documents`:")
        missing = sorted(f for f in self.files if f"profile/{f}" not in preview)
        self.assertEqual(missing, [], f"reset preview omits profile files /setup writes: {missing}")

    def test_execution_copies_templates(self):
        execution = section(self.text, "### Profile reset", "### Documents reset")
        self.assertIn("profile-templates/", execution)
        self.assertNotIn("| Line to restore | Token |", execution, "token-restore tables must be gone")

    def test_reset_preserves_active_template(self):
        execution = section(self.text, "### Profile reset", "### Documents reset")
        self.assertIn("Active Template", execution)
        self.assertIn("keep", execution.lower())

    def test_every_template_is_a_setup_target(self):
        templates = {p.name for p in TPL.glob("*.md")}
        self.assertEqual(sorted(templates - self.files), [], "a template /setup never fills")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_setup_command tests.test_reset_command -v`
Expected: FAIL — Step 0a missing, Step 3 targets still `.claude/...`/bare `0N-*.md`, reset preview lacks `profile/`.

- [ ] **Step 3: Edit `/setup` (`.claude/commands/setup.md`)**

1. Directly under `## Step 0: Welcome & Choose Path`, **before** the `--section <name>` paragraph, insert:

   ```markdown
   ### Step 0a: Prepare the profile folder

   Your candidate data lives in `profile/` at the workspace root. Before anything else:

   1. Create `profile/` if it does not exist.
   2. For each file in `.claude/skills/job-application-assistant/profile-templates/`, copy it to `profile/<same name>` **only if that file is missing**. Copy only the missing files and never overwrite an existing profile file: it may hold the user's data.
   3. Tell the user in one line which files were created, if any.

   Every write below goes to `profile/`. Framework files under `.claude/skills/` are never edited by this command.

   ### Step 0b: Choose a path
   ```

   The new `### Step 0b: Choose a path` heading sits directly above the existing `--section <name>` paragraph, so the rest of today's Step 0 (the `--section` shortcut, the public-fork check, the `documents/` scan and the welcome) now lives under Step 0b.

2. Step A2 read list → replace the seven `.claude/skills/job-application-assistant/0N-*.md` bullets with:
   ```markdown
   - `profile/candidate.md`
   - `profile/behavioral.md`
   - `profile/writing-patterns.md`
   - `profile/evaluation.md`
   - `profile/cv.md`
   - `profile/cover-letter.md`
   - `profile/star.md`
   ```
   and change the heading `### Step A2: Read Existing Skill Files` → `### Step A2: Read Existing Profile Files`.
3. Step A5 inference-rule bullets: rename targets — `01-candidate-profile.md` → `profile/candidate.md`; `02-behavioral-profile.md` → `profile/behavioral.md`; `03-writing-style.md` bullet → `profile/writing-patterns.md` (keep "Add as observations under `## Patterns Observed in Past Applications`"; drop "Do not modify existing rules"); `04-job-evaluation.md` bullet → `profile/evaluation.md`, "Add findings under `## Calibration`"; `05-cv-templates.md` bullet → `profile/cv.md` (under `## Profile Statements`); `06-cover-letter-templates.md` bullet → `profile/cover-letter.md` (under `## Patterns From Past Letters`); `07-interview-prep.md` bullet → `profile/star.md`. Apply the same renames in Step A5's first paragraph examples and in the Step A6 example blocks (`### 01-candidate-profile.md` → `### profile/candidate.md`, `### 02-behavioral-profile.md` → `### profile/behavioral.md`, `**Current in 01-candidate-profile.md:**` → `**Current in profile/candidate.md:**`).
4. Step A7: in the Languages bullet, `this feeds the Language Gate in \`04-job-evaluation.md\`` stays; replace the last paragraph with: `Then proceed to Step 3 to populate the remaining profile files. Step 3 detects which profile files Path A already populated and skips those substeps.`
5. Replace the whole `## Step 3: Generate Profile Files` body with (keep the heading):

   ```markdown
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
   ```
   followed by the **existing** Step 3.9 bullet list verbatim (the `Replace [YOUR_PRIMARY_ROLE_TYPE]...` bullets and the Priority 1-4 list).
6. Step 4 summary: replace the file bullet list with:
   ```markdown
   > - `profile/candidate.md` - Your candidate profile (identity, contact details, experience, skills)
   > - `profile/behavioral.md` - Behavioral assessment
   > - `profile/evaluation.md` - Personalized evaluation inputs
   > - `profile/cv.md` - Your profile statements
   > - `profile/star.md` - STAR examples from your experience
   > - `profile/search-queries.md` - Job search queries for `/scrape`
   > - `cv/main_example.tex` - Your LaTeX CV template
   ```
   and in the Privacy note replace `the files above now contain your personal data and are *tracked by git*` with `the files above now contain your personal data. \`profile/\` and \`cv/main_example.tex\` are *tracked by git* in your repository`. Replace both occurrences of `07-interview-prep.md` in the STAR-stub note with `profile/star.md`.
7. Design Principles: `converge on the same skill files` → `converge on the same profile files`.
8. Step 0 private-remote warning text: `writes your personal data ... into **tracked** files` stays.
9. Any remaining `search-queries.md` reference that points at `.claude/skills/job-scraper/` → `profile/search-queries.md`. Check: `grep -n "\.claude/skills" .claude/commands/setup.md` must print only the `profile-templates/` line in Step 0a.

- [ ] **Step 4: Edit `/reset` (`.claude/commands/reset.md`)**

1. Step 0 prompt: `Clears candidate data from the skill files (...)` → `Restores every file in \`profile/\` to its blank template (profile, behavioral, evaluation inputs, profile statements, STAR examples, search queries). Framework files are never touched.` (keep the rest of that bullet).
2. Replace the `### If scope includes \`profile\`:` block (from its heading down to, not including, `### If scope includes \`documents\`:`) with:

   ````markdown
   ### If scope includes `profile`:

   Read each of these and report whether it holds data or is already blank (still matches its template in `.claude/skills/job-application-assistant/profile-templates/`):

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
   ````

3. Replace the `### Profile reset` block (from its heading down to, not including, `### Documents reset`) with:

   ```markdown
   ### Profile reset

   For each file listed in Step 1, copy `.claude/skills/job-application-assistant/profile-templates/<name>` over `profile/<name>`.

   **Exception, keep the Active Template section:** before overwriting `profile/cv.md` and `profile/cover-letter.md`, read the text between `<!-- BEGIN ACTIVE-TEMPLATE` and `<!-- END ACTIVE-TEMPLATE -->` if present. After copying the template, put that block back under `## Active Template`. A reset clears data, not the user's template registration.
   ```
4. Step 4 "If profile was reset" message → `> Your \`profile/\` files are back to blank templates. Run \`/setup\` to repopulate them. ... \n>\n> \`cv/main_example.tex\` is outside the \`profile\` scope and still holds your personal data. If you are handing this repository over or making it public, clear it by hand.` (keep the middle sentence about auto-detecting `documents/`).
5. Check: `grep -nE "0[1-7]-[a-z-]+\.md|job-scraper/search-queries|CLAUDE\.md" .claude/commands/reset.md` → no output.

- [ ] **Step 5: Edit `/expand` and `/add-template`**

`.claude/commands/expand.md`: replace every `.claude/skills/job-application-assistant/01-candidate-profile.md` and bare `01-candidate-profile.md` with `profile/candidate.md`; every `.claude/skills/job-application-assistant/02-behavioral-profile.md` and bare `02-behavioral-profile.md` with `profile/behavioral.md`. Add as the first line of its first step: `Run the Profile Guard (\`job-application-assistant/SKILL.md\`) first.` Check: `grep -nE "0[12]-" .claude/commands/expand.md` → no output.

`.claude/commands/add-template.md`:
- Line 30: ``A template is **active** if `05-cv-templates.md` (CV) or `06-cover-letter-templates.md` (cover letter) contains`` → ``A template is **active** if `profile/cv.md` (CV) or `profile/cover-letter.md` (cover letter) contains``.
- Step 5 first paragraph: ``adding a **managed block** to the top of the relevant guidance file — `05-cv-templates.md` for CVs, `06-cover-letter-templates.md` for cover letters. `/apply` reads these files`` → ``adding a **managed block** under the `## Active Template` heading of the relevant profile file — `profile/cv.md` for CVs, `profile/cover-letter.md` for cover letters. `/apply` reads these files``.
- ``Insert (or replace, if one exists) this block immediately after the file's H1 title:`` → ``Insert (or replace, if one exists) this block directly under the file's `## Active Template` heading. If `profile/` or that file is missing, tell the user to run `/setup` first and stop:``.
- In the managed block template, ``Where this block conflicts with the stock guidance below, this block wins.`` → ``Where this block conflicts with the stock guidance in 05-cv-templates.md / 06-cover-letter-templates.md, this block wins.`` and ``(not the command named in the stock guidance below`` → ``(not the command named in the stock guidance``.
- ``Exactly **one** managed block per guidance file.`` → ``Exactly **one** managed block per profile file.``
- `templates/README.md` line 23: ``adds a managed block to `05-cv-templates.md` or `06-cover-letter-templates.md` `` → ``adds a managed block to `profile/cv.md` or `profile/cover-letter.md` ``.
- Check: `grep -nE "0[56]-" .claude/commands/add-template.md` prints only lines that describe stock guidance, never a write target.

- [ ] **Step 6: Run to verify it passes**

Run: `python3 -m unittest tests.test_setup_command tests.test_reset_command tests.test_profile_separation -v`
Expected: PASS. Then the whole suite: `python3 -m unittest discover -s tests -t . -v` — all PASS.

- [ ] **Step 7: Commit**

```bash
git add .claude/commands/setup.md .claude/commands/reset.md .claude/commands/expand.md .claude/commands/add-template.md templates/README.md tests/test_setup_command.py tests/test_reset_command.py
git commit -m "refactor(setup,reset): write candidate data to profile/ only

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Legacy-fork migration in /setup

**Files:**
- Modify: `.claude/commands/setup.md` (extend Step 0a)
- Modify: `tests/test_setup_command.py`

**Interfaces:**
- Consumes: `### Step 0a: Prepare the profile folder` (Task 4), template headings (Task 1).
- Produces: `#### Legacy fork migration` subsection inside Step 0a. It is the only place in `.claude/` allowed to name `01-candidate-profile.md`, `02-behavioral-profile.md` and `job-scraper/search-queries.md` after Task 7.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_setup_command.py` (before `if __name__`):

```python
class SetupLegacyMigration(unittest.TestCase):
    def setUp(self):
        text = COMMAND.read_text(encoding="utf-8")
        step0 = _sections(text)["Step 0: Welcome & Choose Path"]
        self.assertIn("#### Legacy fork migration", step0)
        self.block = step0.split("#### Legacy fork migration", 1)[1].split("\n### ", 1)[0]

    def test_detection_uses_git_history_and_the_sentinel(self):
        self.assertIn("git show", self.block)
        self.assertIn("ORIG_HEAD", self.block)
        self.assertIn("[YOUR_EMAIL]", self.block)
        self.assertIn("01-candidate-profile.md", self.block)

    def test_mapping_covers_every_legacy_region(self):
        for legacy in ("01-candidate-profile.md", "02-behavioral-profile.md", "03-writing-style.md",
                       "04-job-evaluation.md", "05-cv-templates.md", "06-cover-letter-templates.md",
                       "07-interview-prep.md", "search-queries.md", "CLAUDE.md"):
            self.assertIn(legacy, self.block, f"migration mapping omits {legacy}")

    def test_migration_carries_active_template(self):
        self.assertIn("ACTIVE-TEMPLATE", self.block)
        self.assertIn("profile/cv.md", self.block)
        self.assertIn("profile/cover-letter.md", self.block)

    def test_migration_reports_conflicts(self):
        self.assertIn("conflict", self.block.lower())
        self.assertIn("never silently", self.block.lower())

    def test_migration_confirms_and_never_deletes(self):
        low = self.block.lower()
        self.assertIn("confirm", low)
        self.assertIn("deletes nothing", low)
        self.assertIn("git checkout --theirs", self.block)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_setup_command.SetupLegacyMigration -v`
Expected: FAIL — `#### Legacy fork migration` not found.

- [ ] **Step 3: Add the migration subsection**

In `.claude/commands/setup.md`, inside Step 0a, replace step "2." with:

```markdown
2. If `profile/` did not exist before step 1, run **Legacy fork migration** below first. Then, for each file in `.claude/skills/job-application-assistant/profile-templates/`, copy it to `profile/<same name>` **only if that file is missing**. Copy only the missing files and never overwrite an existing profile file: it may hold the user's data.
```

and insert, at the end of Step 0a (directly above the `### Step 0b: Choose a path` heading):

````markdown
#### Legacy fork migration

Before this change, `/setup` wrote candidate data into framework files. A fork that merged the change still has that data in its git history. Find it:

1. Check, in order: the working tree, `ORIG_HEAD`, then each commit from `git log --format=%H -- .claude/skills/job-application-assistant/01-candidate-profile.md`. Use `git show <ref>:.claude/skills/job-application-assistant/01-candidate-profile.md`. The first version that exists and does **not** contain `[YOUR_EMAIL]` is the legacy profile; call its ref `<ref>`. If none is found, skip migration and continue with a fresh setup.
2. Read these from `<ref>` with `git show <ref>:<path>` (skip any that do not exist there): `.claude/skills/job-application-assistant/01-candidate-profile.md` through `07-interview-prep.md`, `.claude/skills/job-scraper/search-queries.md`, and `CLAUDE.md`.
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
5. Tell the user: "Your data is now in `profile/`. If git still shows merge conflicts in files under `.claude/skills/`, resolve them by taking the upstream version, for example `git checkout --theirs .claude/skills/job-application-assistant/04-job-evaluation.md`. Your old data stays in git history." Migration deletes nothing.
````

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_setup_command -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/setup.md tests/test_setup_command.py
git commit -m "feat(setup): migrate a personalized fork's legacy profile into profile/

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Remaining readers use profile/

**Files:**
- Modify: `.claude/commands/interview.md`, `.claude/commands/rank.md`, `.claude/commands/outcome.md`, `.claude/commands/add-portal.md`, `.claude/skills/job-scraper/SKILL.md`, `.claude/skills/upskill/SKILL.md`, `documents/README.md`
- Modify: `tests/test_profile_separation.py`

**Interfaces:**
- Consumes: `## Profile Guard` (Task 2), templates (Task 1), `#### Legacy fork migration` (Task 5).
- Produces: the invariant "outside `/setup`'s migration subsection, nothing under `.claude/` names the legacy files" (Task 7 then deletes them).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_profile_separation.py`:

```python
LEGACY_NAMES = ("01-candidate-profile.md", "02-behavioral-profile.md", "job-scraper/search-queries.md")


def strip_setup_migration(text: str) -> str:
    """Remove /setup's Legacy fork migration subsection, the one allowed mention."""
    marker = "#### Legacy fork migration"
    if marker not in text:
        return text
    head, tail = text.split(marker, 1)
    rest = tail.split("\n### ", 1)
    return head + ("\n### " + rest[1] if len(rest) > 1 else "")


class TestNoLegacyReferences(unittest.TestCase):
    def test_claude_tree_names_no_legacy_profile_files(self):
        offenders = []
        files = list((REPO / ".claude").rglob("*.md")) + [REPO / "CLAUDE.md", REPO / "documents" / "README.md"]
        for path in files:
            if path.name.startswith(("01-", "02-")):  # TEMPORARY: legacy files, deleted in Task 7
                continue
            text = strip_setup_migration(path.read_text(encoding="utf-8"))
            for name in LEGACY_NAMES:
                if name in text:
                    offenders.append(f"{path.relative_to(REPO)}: {name}")
        self.assertEqual(offenders, [], "legacy profile paths still referenced")

    def test_search_queries_read_from_profile(self):
        scraper = (REPO / ".claude" / "skills" / "job-scraper" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("profile/search-queries.md", scraper)
        self.assertNotIn("`search-queries.md` (this directory)", scraper)
```

Note: the legacy `01-candidate-profile.md` still exists until Task 7 and names `job-scraper/search-queries.md` in its Languages comment, hence the marked TEMPORARY skip. `.claude/skills/job-scraper/search-queries.md` names none of the legacy files, so it needs no skip.

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_profile_separation.TestNoLegacyReferences -v`
Expected: FAIL listing `interview.md`, `rank.md`, `upskill/SKILL.md`, `job-scraper/SKILL.md`, `add-portal.md`, `documents/README.md`, and `outcome.md` if it names them.

- [ ] **Step 3: Edit each reader**

Mechanical renames in these files (`interview.md`, `rank.md`, `outcome.md`, `add-portal.md`, `job-scraper/SKILL.md`, `upskill/SKILL.md`, `documents/README.md`):
- `.claude/skills/job-application-assistant/01-candidate-profile.md` and bare `01-candidate-profile.md` → `profile/candidate.md`
- `.claude/skills/job-application-assistant/02-behavioral-profile.md` and bare `02-behavioral-profile.md` → `profile/behavioral.md`
- `.claude/skills/job-scraper/search-queries.md` → `profile/search-queries.md`

Then the non-mechanical edits:
- `interview.md`: in the read list add `- \`profile/star.md\`` and `- \`profile/evaluation.md\`` after the `07-interview-prep.md` line. `Match the ready-made STAR examples in \`07-interview-prep.md\`` → `Match the ready-made STAR examples in \`profile/star.md\``. `remind them those were appended to \`07-interview-prep.md\`` → `remind them those were appended to \`profile/star.md\``. `except appending user-approved STAR examples to \`07-interview-prep.md\`` → `except appending user-approved STAR examples to \`profile/star.md\``. First line of the first step: `Run the Profile Guard (\`job-application-assistant/SKILL.md\`) first.`
- `rank.md`: in its read list (lines 38-39) replace the `01` line with `- \`profile/candidate.md\`` and add `- \`profile/evaluation.md\``. First line of its first step: `Run the Profile Guard (\`job-application-assistant/SKILL.md\`) first.`
- `outcome.md`: `that \`/setup\` Path A mines to calibrate \`04-job-evaluation.md\`` → `that \`/setup\` Path A mines to calibrate \`profile/evaluation.md\``; `Do **not** write anything into \`04-job-evaluation.md\` or other skill files yourself.` → `Do **not** write anything into \`profile/\` or framework files yourself.`
- `job-scraper/SKILL.md`: both `Read \`search-queries.md\` (this directory)` → `Read \`profile/search-queries.md\``; the other bare `search-queries.md` mentions → `profile/search-queries.md`; `a required language you haven't declared at all in your CLAUDE.md Languages table` → `a required language you haven't declared at all in \`profile/candidate.md#languages\``. Add as the first line of its first step: `Run the Profile Guard (\`job-application-assistant/SKILL.md\`) first.`
- `add-portal.md` line 126: ``in `.claude/skills/job-scraper/search-queries.md` (use the `[YOUR_JOB_BOARD]` style placeholders already there)`` → ``in `profile/search-queries.md` (use the `[YOUR_JOB_BOARD]` style placeholders from its template)``.
- `documents/README.md`: `05-cv-templates.md` → `profile/cv.md` (line 159), `06-cover-letter-templates.md` → `profile/cover-letter.md` (line 157), `04-job-evaluation.md` → `profile/evaluation.md` (lines 155, 189).

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest discover -s tests -t . -v`
Expected: all PASS. `tests.test_upskill_skill`, `tests.test_scrape_contract`, `tests.test_scrape_provenance`, `tests.test_rank_command` must pass: if one asserts an old path, update that assertion to the new `profile/` path and nothing else.

- [ ] **Step 5: Commit**

```bash
git add .claude documents/README.md tests/test_profile_separation.py
git commit -m "refactor(commands): read candidate data from profile/

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Remove legacy files; tools and CI

**Files:**
- Delete: `FW/01-candidate-profile.md`, `FW/02-behavioral-profile.md`, `.claude/skills/job-scraper/search-queries.md`
- Modify: `tools/check_framework_version.py`, `tools/check_upstream_updates.py`, `.github/workflows/ci.yml`
- Modify: `tests/test_placeholder_integrity.py`, `tests/test_check_upstream_updates.py`, `tests/test_profile_separation.py`

**Interfaces:**
- Consumes: everything above.
- Produces: final file set; CI placeholder-integrity targets templates.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_profile_separation.py`:

```python
class TestLegacyFilesRemoved(unittest.TestCase):
    def test_legacy_profile_files_are_gone(self):
        for path in (FW / "01-candidate-profile.md", FW / "02-behavioral-profile.md",
                     REPO / ".claude" / "skills" / "job-scraper" / "search-queries.md"):
            self.assertFalse(path.exists(), f"{path.relative_to(REPO)} should be deleted")

    def test_version_guard_covers_templates(self):
        src = (REPO / "tools" / "check_framework_version.py").read_text(encoding="utf-8")
        self.assertIn("profile-templates", src)
```

Also delete the line marked `# TEMPORARY: legacy files, deleted in Task 7` (and the `continue` under it) from `TestNoLegacyReferences`.

In `tests/test_placeholder_integrity.py`: change `PROFILE` to `REPO / ".claude" / "skills" / "job-application-assistant" / "profile-templates" / "candidate.md"`; in `test_ci_checks_a_data_placeholder_not_the_header_comment` change the expected string to `"check .claude/skills/job-application-assistant/profile-templates/candidate.md '\\[YOUR_EMAIL\\]'"` and the message to `"candidate.md's sentinel must sit in the Identity data /setup fills"`; update the module docstring's `01-candidate-profile.md` mention to `profile-templates/candidate.md`. Add to class `TestProfileSentinelIsDataLocated`:

```python
    def test_ci_forbids_a_tracked_profile_folder(self):
        ci = CI.read_text(encoding="utf-8")
        self.assertIn("profile/ must not be committed to the upstream template", ci)

    def test_ci_no_longer_checks_claude_md_for_a_name(self):
        ci = CI.read_text(encoding="utf-8")
        self.assertNotIn("check CLAUDE.md", ci)
```

In `tests/test_check_upstream_updates.py`, set the `FRAMEWORK_FILES` list to:

```python
FRAMEWORK_FILES = [
    ".claude/skills/job-application-assistant/03-writing-style.md",
    ".claude/skills/job-application-assistant/04-job-evaluation.md",
    ".claude/skills/job-application-assistant/05-cv-templates.md",
    ".claude/skills/job-application-assistant/06-cover-letter-templates.md",
    ".claude/skills/job-application-assistant/07-interview-prep.md",
    ".claude/skills/job-application-assistant/08-application-forms.md",
    ".claude/skills/job-application-assistant/09-web-research.md",
    ".claude/skills/job-application-assistant/10-verification.md",
    ".claude/skills/job-application-assistant/SKILL.md",
    ".claude/skills/job-application-assistant/profile-templates/behavioral.md",
    ".claude/skills/job-application-assistant/profile-templates/candidate.md",
    ".claude/skills/job-application-assistant/profile-templates/cover-letter.md",
    ".claude/skills/job-application-assistant/profile-templates/cv.md",
    ".claude/skills/job-application-assistant/profile-templates/evaluation.md",
    ".claude/skills/job-application-assistant/profile-templates/search-queries.md",
    ".claude/skills/job-application-assistant/profile-templates/star.md",
    ".claude/skills/job-application-assistant/profile-templates/writing-patterns.md",
    "AGENTS.md",
]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_profile_separation tests.test_placeholder_integrity tests.test_check_upstream_updates -v`
Expected: FAIL — legacy files exist; tool lacks `profile-templates`; CI lacks the new check; upstream list mismatch.

- [ ] **Step 3: Delete legacy files**

```bash
git rm .claude/skills/job-application-assistant/01-candidate-profile.md \
       .claude/skills/job-application-assistant/02-behavioral-profile.md \
       .claude/skills/job-scraper/search-queries.md
```

- [ ] **Step 4: Update tools**

`tools/check_framework_version.py`: replace

```python
FRAMEWORK_FILES = sorted(SKILL_DIR.glob("*.md"))
```

with

```python
FRAMEWORK_FILES = sorted(SKILL_DIR.glob("*.md")) + sorted(SKILL_DIR.glob("profile-templates/*.md"))
```

and change the docstring's first sentence to `Fails if any markdown file under .claude/skills/job-application-assistant/ (including profile-templates/) is`.

`tools/check_upstream_updates.py`: set its `FRAMEWORK_FILES` to exactly the list in Step 1's test, and update the docstring line `3. Compares the 'framework_version' in your local files under\n   .claude/skills/job-application-assistant/ with those in the upstream remote.` to mention `(including profile-templates/)`. If the script's "missing upstream" branch reports newly added files as errors, confirm it treats a file missing **upstream** as informational (read the loop after `for rel_path in FRAMEWORK_FILES:`); if it errors, leave behavior unchanged and note it in the PR, because upstream will have the files once merged.

- [ ] **Step 5: Update CI**

In `.github/workflows/ci.yml` job `placeholder-integrity`, replace the `check` lines with:

```yaml
          check cv/main_example.tex '\\name{\[First\]}{\[Last\]}'
          check cv/main_example.tex '\\email{\[your\.email@example\.com\]}'
          check cover_letters/cover_example.tex '\[YOUR NAME\]'
          check .claude/skills/job-application-assistant/profile-templates/candidate.md '\[YOUR_EMAIL\]'
          check .claude/skills/job-application-assistant/profile-templates/evaluation.md '\[YOUR_PRIMARY_SKILLS\]'
          if [ -e profile ]; then
            echo "::error file=profile::profile/ must not be committed to the upstream template - personal data may have been committed"
            fail=1
          fi
```

(i.e. the `CLAUDE.md` and the two `01`/`04` lines are removed.) Also update the header comment at the top of `ci.yml`: `forks personalize CLAUDE.md, the skill files, and cv/main_example.tex via /setup` → `forks personalize profile/ and cv/main_example.tex via /setup`.

- [ ] **Step 6: Run to verify it passes**

Run: `python3 -m unittest discover -s tests -t . -v`
Expected: all PASS (no exceptions left).
Run: `python3 tools/lint_skills.py && python3 tools/security_guards.py`
Expected: both exit 0.
Run: `GITHUB_BASE_REF=master python3 tools/check_framework_version.py`
Expected: `Framework Version Check: OK`. If it names a file "modified without bumping", bump that file's `framework_version` to the target in Global Constraints and re-run.

- [ ] **Step 7: Commit**

```bash
git add -A .claude tools .github/workflows/ci.yml tests
git commit -m "refactor(ci): drop legacy profile files, guard templates and untracked profile/

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Docs, AGENTS.md and CHANGELOG

**Files:**
- Modify: `README.md`, `SETUP.md`, `AGENTS.md`, `CHANGELOG.md`
- Modify: `tests/test_profile_separation.py`

**Interfaces:**
- Consumes: final layout from Tasks 1-7.
- Produces: user-facing docs; `SETUP.md` heading `## 9. Merging the profile-separation change into a personalized fork` (README links it).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_profile_separation.py`:

```python
class TestDocs(unittest.TestCase):
    def test_docs_name_no_legacy_profile_files_outside_migration(self):
        setup_md = (REPO / "SETUP.md").read_text(encoding="utf-8")
        migration = "## 9. Merging the profile-separation change into a personalized fork"
        self.assertIn(migration, setup_md)
        before, after = setup_md.split(migration, 1)
        rest = after.split("\n## ", 1)
        outside = before + (rest[1] if len(rest) > 1 else "")
        for text, where in ((outside, "SETUP.md"), ((REPO / "README.md").read_text(encoding="utf-8"), "README.md"),
                            ((REPO / "AGENTS.md").read_text(encoding="utf-8"), "AGENTS.md")):
            for name in ("01-candidate-profile.md", "02-behavioral-profile.md"):
                self.assertNotIn(name, text, f"{where} still names {name}")

    def test_changelog_flags_the_fork_break(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = text.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("BREAKING (personalized forks)", unreleased)
        self.assertIn("profile/", unreleased)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_profile_separation.TestDocs -v`
Expected: FAIL — SETUP.md section 9 missing.

- [ ] **Step 3: Edit docs**

`README.md`:
- File structure tree: change `├── CLAUDE.md  # Main candidate profile + workflow rules` → `├── CLAUDE.md                          # Role and pointers (no personal data)`; add `├── profile/                           # Your candidate data (created by /setup, not in the template)`; in the `job-application-assistant/` subtree replace the `01`–`07` lines with:
  ```
  │   │   │   ├── 03-writing-style.md    # Tone, structure, do's and don'ts
  │   │   │   ├── 04-job-evaluation.md   # Scoring framework for job fit
  │   │   │   ├── 05-cv-templates.md     # LaTeX CV structure + tailoring rules
  │   │   │   ├── 06-cover-letter-templates.md # LaTeX cover letter templates
  │   │   │   ├── 07-interview-prep.md   # Interview framework
  │   │   │   ├── 10-verification.md     # Application workflow + verification checklist
  │   │   │   └── profile-templates/     # Blank templates /setup copies into profile/
  ```
- "Which files to edit manually" table: replace rows `CLAUDE.md` … `search-queries.md` with rows for `profile/candidate.md`, `profile/behavioral.md`, `profile/evaluation.md`, `profile/cv.md`, `profile/star.md`, `profile/search-queries.md` (purposes as in `FW/SKILL.md`'s candidate-data table).
- Line 311: `update the guidance in \`05-cv-templates.md\` and \`06-cover-letter-templates.md\`` → `add your own block to \`profile/cv.md\` and \`profile/cover-letter.md\` under Active Template`.
- Under "Staying up to date", add one sentence: `Upgrading a personalized fork across the profile-separation change needs one extra step: see [SETUP.md section 9](SETUP.md#9-merging-the-profile-separation-change-into-a-personalized-fork).`

`SETUP.md`:
- The files table at lines ~233-240: same replacement as README's table.
- Section 8, item 1: `\`/setup\` edits CLAUDE.md and the profile skill files in place` → `\`/setup\` writes your data into \`profile/\``; add after item 3 (merge): `Because your data lives in \`profile/\` and upstream never ships that folder, upstream merges no longer touch your personalization.`
- Append a new section at the end:

  ```markdown
  ## 9. Merging the profile-separation change into a personalized fork

  Older versions stored your profile inside framework files (`.claude/skills/job-application-assistant/01-candidate-profile.md` and its neighbours). Newer versions keep it in `profile/`. Upgrading across that change:

  1. `git merge upstream/master`. Expect conflicts in files under `.claude/skills/`.
  2. Resolve every conflict under `.claude/skills/` by taking upstream's version: `git checkout --theirs <path>` for each, then `git add` them. Your data is not lost; it is still in your git history.
  3. Commit the merge, then run `/setup`. It finds your old profile in git history, shows you the new `profile/` files built from it, and writes them only after you confirm.
  4. Commit `profile/` to your own (private) repository.
  ```

`AGENTS.md`: frontmatter `framework_version: 1.0.0` → `1.1.0`; pointer 1 → `1. **Personal Candidate Profile:**\n   - All candidate data lives in [profile/](profile/) (created by \`/setup\` from \`.claude/skills/job-application-assistant/profile-templates/\`). [CLAUDE.md](CLAUDE.md) holds the role and pointers only.`

`CHANGELOG.md`: under the existing `## [Unreleased]` → `### Changed` heading (add `### Changed` below `### Added`'s entries only if none exists; there must be exactly one), add:

```markdown
- **BREAKING (personalized forks): candidate data moves to `profile/`**
  (`.claude/skills/job-application-assistant/profile-templates/`, `.claude/commands/setup.md`,
  `.claude/commands/reset.md`, `CLAUDE.md`, `10-verification.md`) - `/setup` now writes
  every personal detail into a workspace `profile/` folder created from framework-owned
  templates, and framework files hold rules only. Upstream merges stop conflicting with
  your personalization. `01-candidate-profile.md`, `02-behavioral-profile.md` and
  `job-scraper/search-queries.md` are removed; the workflow and verification checklist
  move from `CLAUDE.md` to `10-verification.md`. Upgrading a personalized fork: see
  SETUP.md section 9; `/setup` migrates your old profile from git history.
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_profile_separation tests.test_changelog_structure -v`
Expected: PASS. Then `GITHUB_BASE_REF=master python3 tools/check_framework_version.py` → OK (AGENTS.md bumped).

- [ ] **Step 5: Commit**

```bash
git add README.md SETUP.md AGENTS.md CHANGELOG.md tests/test_profile_separation.py
git commit -m "docs: document profile/ and the fork upgrade path

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Full local verification (upstream-only CI jobs skip in forks)

**Files:** none changed unless a check fails.

- [ ] **Step 1: Run everything CI runs**

```bash
python3 -m unittest discover -s tests -t . -v
python3 tools/lint_skills.py
python3 tools/security_guards.py
GITHUB_BASE_REF=master python3 tools/check_framework_version.py
```
Expected: all pass / exit 0.

- [ ] **Step 2: Run the upstream-only placeholder block by hand**

```bash
fail=0
check() { if ! grep -q "$2" "$1"; then echo "MISSING $2 in $1"; fail=1; fi; }
check cv/main_example.tex '\\name{\[First\]}{\[Last\]}'
check cv/main_example.tex '\\email{\[your\.email@example\.com\]}'
check cover_letters/cover_example.tex '\[YOUR NAME\]'
check .claude/skills/job-application-assistant/profile-templates/candidate.md '\[YOUR_EMAIL\]'
check .claude/skills/job-application-assistant/profile-templates/evaluation.md '\[YOUR_PRIMARY_SKILLS\]'
[ -e profile ] && { echo "profile/ exists"; fail=1; }
echo "fail=$fail"
```
Expected: `fail=0`.

- [ ] **Step 3: LaTeX smoke compiles**

```bash
(cd cv && lualatex -interaction=nonstopmode main_example.tex >/dev/null) && python3 tools/verify_pdf.py cv/main_example.pdf --pages 2
(cd cover_letters && xelatex -interaction=nonstopmode cover_example.tex >/dev/null) && python3 tools/verify_pdf.py cover_letters/cover_example.pdf --pages 1
git status --short cv cover_letters   # delete generated .pdf/.aux/.log if they show up untracked
```
Expected: both page checks pass. (The `.tex` files were not edited; this confirms nothing else broke.)

- [ ] **Step 4: End-to-end in a scratch clone (manual, report results in the PR)**

```bash
S=$(mktemp -d) && git clone -q --branch plugin/1-profile-separation . "$S/ws" && cd "$S/ws"
```
In that clone, start Claude Code and:
1. Run `/apply` with any public posting URL before `/setup` → expect the Profile Guard message, nothing drafted.
2. Run `/setup`, choose Path C, answer with made-up data (name "Test Person", email `test@example.com`). Confirm `profile/` has all 8 files and `git diff --stat .claude` is empty.
3. Run `/apply` on a sample posting. Confirm the generated CV `.tex` contains `test@example.com` and no `[CANDIDATE_` token.
4. Run `/reset profile`, confirm `profile/*.md` match the templates again (`diff -r profile .claude/skills/job-application-assistant/profile-templates`).

- [ ] **Step 5: Migration end-to-end (manual)**

```bash
S=$(mktemp -d) && git clone -q . "$S/fork" && cd "$S/fork" && git checkout -q master
sed -i 's/\[YOUR_EMAIL\]/legacy@example.com/; s/\[YOUR_NAME\]/Legacy Person/' .claude/skills/job-application-assistant/01-candidate-profile.md
git commit -qam "personalize (test)"
git merge plugin/1-profile-separation   # expect conflicts under .claude/skills/
```
Follow SETUP.md section 9 exactly. Expected: `/setup` finds the legacy profile, proposes `profile/candidate.md` containing `legacy@example.com` and `Legacy Person`, writes it after confirmation, and `git log` still holds the old file.

- [ ] **Step 6: Final commit only if a fix was needed**

```bash
git add -A && git commit -m "fix: address local verification findings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
