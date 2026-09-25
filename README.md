<p align="center">
  <img src="assets/mascot/pip_flight_loop.gif" alt="Pip, the courier bird" width="200">
</p>

# ai-job-search-plugin

*The job search that runs on your machine, as a Claude Code plugin.*

[![CI](https://github.com/MRDGH2821/ai-job-search-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/MRDGH2821/ai-job-search-plugin/actions/workflows/ci.yml)

An AI-powered job application workflow for [Claude Code](https://claude.com/claude-code). Install the plugin, lay out a private workspace folder, fill in your profile, and let Claude evaluate job postings, tailor your CV, write cover letters, and prepare you for interviews.

> Note: This is an independent open-source project and is not affiliated with, endorsed by, sponsored by, or maintained by Anthropic. Anthropic and Claude Code are referenced only to describe the toolchain this workflow uses.
>
> This project has **no affiliated cryptocurrency, token, or paid sponsorship program**. Anything claiming otherwise is unauthorized and should be treated as a scam.

## What this is

A structured workflow that turns Claude Code into a full-stack job application assistant. The core workflow (self-profiling, fit evaluation, and the drafter-reviewer application pipeline) is **language- and country-agnostic**. Job-portal search skills ship for LinkedIn and freehire.me in the core plugin, and for the Danish market (Jobindex, Jobnet, Akademikernes Jobbank, Jobdanmark) in an optional second plugin; `/add-portal` builds one for your own local job board.

```
/init-workspace   /setup          /scrape              /apply <url>
  |                 |                |                     |
  v                 v                v                     v
Lay out a       Fill in         Search job           Evaluate fit
workspace       your profile    portals              Score & recommend
                  |                |                     |
                  v                v                     v
                Profile         Present matches      Draft CV + Cover Letter
                files ready     with fit ratings     (LaTeX, tailored)
                                   |                     |
                                   v                     v
                               Pick a match         Reviewer agent critiques
                               -> /apply            -> Revise -> Final output
```

The workflow encodes career guidance best practices, including structured evaluation criteria, forward-looking cover letter framing, and optional salary benchmarking.

## Prerequisites

- [Claude Code](https://claude.com/claude-code) (CLI). Claude Code has no free tier: you need a Claude Pro/Max/Team subscription or Anthropic API credits.
- Python 3.10+
- [Bun](https://bun.sh) (for the job-portal search CLIs)
- A LaTeX distribution with `lualatex` and `xelatex`: [TeX Live](https://tug.org/texlive/), [MacTeX](https://tug.org/mactex/), [TinyTeX](https://yihui.org/tinytex/), or [MiKTeX](https://miktex.org/). The CV compiles with `lualatex`; the cover letter compiles with `xelatex` because `cover.cls` requires `fontspec`. For a minimal TeX install, see [SETUP.md](SETUP.md#minimal-tex-install-tinytexbasictex).
- Optional: `pip install pypdf` for `/apply`'s ATS parseability check. Poppler `pdftotext` is a fallback.

## Install

Inside Claude Code:

```
/plugin marketplace add MRDGH2821/ai-job-search-plugin
/plugin install ai-job-search-plugin@ai-job-search-plugin
/plugin install danish-job-portals@ai-job-search-plugin   # optional, Danish job boards
```

## First run

1. Create an empty folder for your job search and start Claude Code in it. This folder will hold your personal data: keep it local, or push it only to a **private** repository.
2. Run `/init-workspace`. It lays out the CV and cover-letter sources, fonts, the `documents/` tree, state folders and a privacy `.gitignore`, writes the workspace's `AGENTS.md`/`CLAUDE.md`, and offers `git init`. It never overwrites anything.
3. Run `/setup`. It offers three paths: read your `documents/` folder (CV PDF, LinkedIn export, diplomas, reference letters, past applications), import a single CV pasted in chat, or walk through an interview. Your data goes into `profile/`.
4. Run `/scrape` to search job portals, then `/apply <url>` on a match:

```
/apply https://jobindex.dk/job/1234567
/apply <paste the full job description here>
```

`/apply` evaluates fit, drafts a CV and cover letter, has a second agent review them, revises, and presents the final output. When a scrape returns more jobs than you want to read, `/rank` batch-scores them first.

Postings are treated as untrusted input (the workflow follows no instructions embedded in them and fetches no links from their body), but agentic defenses are instruction-level, not a sandbox. On an unfamiliar job board, skim what was fetched and written before you hit send. Details in [SECURITY.md](SECURITY.md).

## Commands

`/init-workspace`, `/setup`, `/scrape` and `/apply` form the core workflow. Every command also works with the plugin prefix, for example `/ai-job-search-plugin:apply`.

- **`/interview`** preps you for a scheduled interview on a tracked application: a stage-specific prep pack from the application's archive, company and interviewer research with a verify-before-use rule, likely questions mapped to your STAR examples, and an optional mock interview. Gaps get honest bridge answers, never invented experience.
- **`/outcome`** records what happened to an application (interview stages, offers, rejections, silence), archives the submitted materials into `documents/applications/<company>_<role>/`, and updates the tracker. `/outcome followup` drafts follow-ups for applications that have gone quiet (drafts only, never sends).
- **`/rank`** batch-scores newly scraped postings against the fit framework and returns a ranked shortlist with per-job strengths and gaps.
- **`/expand`** enriches your profile from public sources you've linked (GitHub, portfolio, Kaggle, Google Scholar) and course syllabi, tagging each discovered competency with its source.
- **`/upskill`** analyzes the gap between your profile and your tracked or ranked postings (or one posting via `/upskill <URL>`) and produces a prioritized learning plan.
- **`/html-report`** generates a self-contained, offline HTML dashboard from `job_search_tracker.csv` and the application archives.
- **`/notion-sync`** publishes a one-way, read-only view of the pipeline into a Notion database via the official Notion MCP server. Documents sync as filenames only.
- **`/gmail-sync`** reads your Gmail (via the Gmail connector) for status signals on open applications and proposes tracker updates for you to approve.
- **`/add-template`** registers your own CV or cover letter template (LaTeX, Typst, or another toolchain), with a mandatory test compile. See [Custom templates](#custom-templates).
- **`/add-portal`** generates a job-portal search skill for a job board in your market. See [Job search tools](#job-search-tools).
- **`/sync-instructions`** writes the workflow's standing instructions into your workspace's `AGENTS.md` (one managed block) and makes `CLAUDE.md` import it. Run it after updating the plugin.
- **`/reset`** wipes profile data and/or documents after a typed `RESET` confirmation. See [Starting over](#starting-over).

## Your workspace

```
my-job-search/                     # any folder; /init-workspace lays it out
├── AGENTS.md, CLAUDE.md           # standing instructions (/sync-instructions)
├── profile/                       # your candidate data (/setup)
├── cv/main_example.tex            # moderncv LaTeX CV
├── cover_letters/                 # cover.cls, example letter, Lato + Raleway fonts
├── templates/                     # custom templates from /add-template
├── documents/                     # source materials for /setup and /expand, application archive
├── .agents/skills/                # your own portal skills from /add-portal
├── job_scraper/ company_research/ upskill/   # state and reports
├── job_search_tracker.csv         # application tracker
└── .gitignore                     # keeps personal data out of git
```

## How `/apply` works

The `/apply` command runs a **drafter-reviewer workflow** with mandatory PDF compilation:

1. **Parse** the job posting (URL or text)
2. **Evaluate fit** against your profile (skills, experience, culture, location, career alignment)
3. **Draft** a tailored CV and cover letter in LaTeX
4. **Spawn a reviewer agent** that researches the company and critiques the drafts
5. **Revise** based on the reviewer's feedback
6. **Compile and inspect** both PDFs: lualatex for the CV, xelatex for the cover letter. Claude reads the rendered pages and iterates until the CV is exactly 2 pages with no orphaned entry titles, and the cover letter is exactly 1 page with the signature visible.
7. **ATS-check the CV**: extract the PDF's text layer and verify it the way an ATS parser sees it, then score the posting's keyword coverage. Keywords the profile genuinely supports get added; genuine gaps stay visible, never stuffed.
8. **Present** the final output with a verification checklist

All claims in the CV and cover letter are verified against your actual profile. The workflow never fabricates skills or experience.

## Customization

### Editing your profile by hand

| File | What to change |
|------|---------------|
| `profile/candidate.md` | Identity, CV language, languages, education, experience, skills, certifications, publications, awards, references |
| `profile/behavioral.md` | Behavioral assessment, strengths, ideal environments |
| `profile/evaluation.md` | Match areas, career goals, target sectors, deal-breakers, constraints |
| `profile/cv.md` | Profile statements for your main role types |
| `profile/star.md` | STAR examples from your actual experience |
| `profile/search-queries.md` | Job search queries for your skills and location |

To reconfigure only the job search, run `/setup --section search`.

### Custom templates

The CV uses [moderncv](https://ctan.org/pkg/moderncv) (banking style). The cover letter uses a custom `cover.cls` with Lato/Raleway fonts. To use your own template (LaTeX, [Typst](https://typst.app/), or any toolchain that compiles to PDF from the command line), run `/add-template`. It stores the template under `templates/` with `[PLACEHOLDER]` tokens instead of personal data, runs a test compile, and activates it for `/apply`.

- `/add-template --list` shows registered templates
- `/add-template --use <name>` switches between them
- `/add-template --use default` reverts to the stock templates

### Job search tools

Portal skills share one contract (a `search`/`detail` CLI, `--format json|table|plain` output, an `enabled:` flag in its `SKILL.md`, its own tests), and `/scrape` discovers every installed one.

- **`linkedin-search`** uses LinkedIn's public, unauthenticated `jobs-guest` endpoints; any market via `-l "<location>"`. **Personal use only**: automated access is against LinkedIn's Terms of Service, so keep volume low.
- **`freehire-search`** queries the [freehire.me](https://freehire.me) aggregator's public REST API: tech-focused, multi-market, zero runtime dependencies.
- **`danish-job-portals`** (optional plugin): Jobbank, Jobdanmark, Jobindex, Jobnet.

For another market, run `/add-portal` with your local job board's URL. It investigates the portal (search URL pattern, result structure, robots.txt), scaffolds a CLI skill in your workspace's `.agents/skills/`, and test-runs a live query before registering it. Before running a portal skill someone else wrote, read its code: these CLIs run pre-approved on your machine.

### Salary benchmarking

The salary tool works with any salary data you provide. Put `salary_data.json` in your workspace root; see [SETUP.md](SETUP.md#5-salary-data) for the format. Without it, the salary step is skipped.

### Starting over

```
/reset profile    # clears profile data, preserves workflow rules
/reset documents  # deletes files from documents/
/reset all        # both
```

`/reset` shows exactly what will be deleted and requires you to type `RESET` to confirm.

## Tips for better results

- **Profile depth matters.** Describe what you actually did in each role (projects, tools, responsibilities, measurable achievements), not just titles. Richer input produces sharper output on every onboarding path.
- **Skills in context.** "Built ML pipelines for customer churn prediction in Python using scikit-learn" gives the workflow far more to work with than "Python, machine learning."
- **Say what energizes and drains you** during `/setup`: it shapes fit evaluation and the roles `/scrape` surfaces, including career paths you haven't considered.

## Other harnesses (capa)

[capa](https://capa.sh) installs Claude plugins into other coding agents (Cursor, Codex, and more):

```
capa registry add MRDGH2821/ai-job-search-plugin
capa add ai-job-search-plugin:ai-job-search-plugin
```

This is untested outside Claude Code: capa copies the skills into your harness, and each skill falls back to paths relative to its own folder. Run `/sync-instructions` (or its script) in your workspace to get the standing instructions into `AGENTS.md`.

## Developing the plugin

```bash
git clone https://github.com/MRDGH2821/ai-job-search-plugin
cd ai-job-search-plugin
claude
```

Accept the folder-trust prompt: `.claude/settings.json` loads both plugins in place from `plugins/`. This repository is plugin source, not a workspace; try changes with `/init-workspace` in a separate folder. The layout, checks and conventions are in [AGENTS.md](AGENTS.md), and [CONTRIBUTING.md](CONTRIBUTING.md) covers pull requests.

## Tracking the original project

This project was forked from MadsLorentzen/ai-job-search and keeps an eye on it for improvements worth porting:

```bash
git remote add upstream https://github.com/MadsLorentzen/ai-job-search.git
git fetch upstream
python3 tools/upstream_triage.py --remote upstream
```

The report maps each upstream path to where the file lives here (`tools/upstream_paths.py`) and prints a `git show` line per commit to read before porting by hand. Record every ported or rejected commit in `.github/upstream-handled.txt`. A weekly workflow (`.github/workflows/upstream-watch.yml`) posts the same report to a rolling issue.

## Credits

- Forked from [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search) (MIT) by Mads Lorentzen, who built the original workflow for his own job search.
- [Mikkel Krogsholm](https://github.com/mikkelkrogsholm) ([skills repo](https://github.com/mikkelkrogsholm/skills)) for the job search CLI skills.
- Built with [Claude Code](https://claude.com/claude-code) by [Anthropic](https://anthropic.com).

## License

MIT. See [LICENSE](LICENSE).
