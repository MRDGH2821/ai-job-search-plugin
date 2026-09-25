# Setup Guide

Step-by-step instructions for getting ai-job-search-plugin running.

## 1. Prerequisites

### Claude Code

Install Claude Code (Anthropic's CLI for Claude):

```bash
npm install -g @anthropic-ai/claude-code
```

You'll need an Anthropic API key or a Claude Pro/Team subscription. See the [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code) for details.

### Python

Python 3.10+ is required for the salary lookup tool. Check with:

```bash
python3 --version
```

On Windows, `py --version` is often the most reliable check. If your system exposes Python as `python` instead of `python3`, use `python` in the commands below.

### Bun (for job search tools)

The job portal CLIs (four Danish portals plus the country-agnostic `linkedin-search` and `freehire-search` tools) are written in TypeScript and run with Bun.

- macOS/Linux:

```bash
curl -fsSL https://bun.sh/install | bash
```

- Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://bun.sh/install.ps1 | iex"
```

If you prefer a package manager, `winget install Oven-sh.Bun` also works on Windows.

### LaTeX (for compiling CVs and cover letters)

Install a LaTeX distribution to compile the generated `.tex` files to PDF:

- **Windows:** [MiKTeX](https://miktex.org/download)
- **macOS:** [MacTeX](https://tug.org/mactex/)
- **Linux:** `sudo apt install texlive-full` or `sudo dnf install texlive-scheme-full`

The CV compiles with `lualatex` (pdflatex often fails on modern MiKTeX installs with `fontawesome5` font-expansion errors). The cover letter compiles with `xelatex` because `cover.cls` requires `fontspec` for its custom Lato/Raleway fonts.

#### Minimal TeX install: TinyTeX/BasicTeX

Full TeX distributions work out of the box, but minimal distributions need a few extra packages before the stock templates compile.

On macOS, a user-level TinyTeX install avoids a system-wide installer and does not require `sudo`:

```bash
curl -fsSL https://yihui.org/tinytex/install-bin-unix.sh -o /tmp/tinytex-install-bin-unix.sh
sh /tmp/tinytex-install-bin-unix.sh /tmp --no-path
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"
```

Then install the template dependencies:

```bash
tlmgr install \
  moderncv fontawesome5 fontawesome6 academicons import luatexbase pgf \
  titlesec textpos xltxtra xunicode cite realscripts needspace
```

For BasicTeX/MacTeX, make sure the TeX binary directory is on `PATH` first (for example via `/Library/TeX/texbin`), then run the same `tlmgr install ...` command.

Quick smoke tests after setup:

```bash
cd cv && lualatex -interaction=nonstopmode -halt-on-error main_example.tex && cd ..

SMOKE_DIR="$(mktemp -d /tmp/ai-job-cover-smoke.XXXXXX)"
cp -R cover_letters/cover.cls cover_letters/OpenFonts "$SMOKE_DIR/"
cat >"$SMOKE_DIR/cover_smoke.tex" <<'EOF'
\documentclass[]{cover}
\begin{document}
\namesection{Test}{Candidate}{test@example.com}
\companyname{Example Company}
\companyaddress{123 Hiring Street\\Example City}
\currentdate{\today}
\lettercontent{Dear Hiring Manager,}
\lettercontent{This smoke test verifies that xelatex can load cover.cls and the bundled fonts.}
\closing{Sincerely,}
\signature{Test Candidate}
\end{document}
EOF
(cd "$SMOKE_DIR" && xelatex -interaction=nonstopmode -halt-on-error cover_smoke.tex)
```

#### Windows: Basic MiKTeX

The full MiKTeX installer bundles every CTAN package and works out of the box, but the smaller [Basic MiKTeX](https://miktex.org/download) installer (`basic-miktex-*.exe`) only ships a minimal package set and needs a couple of one-time settings before the stock templates compile.

By default, MiKTeX installs missing packages on demand but pops up a GUI prompt for each one — which blocks non-interactive terminals (including Claude Code's Bash tool). Turn that into a silent auto-install instead:

```powershell
initexmf --admin --set-config-value=[MPM]AutoInstall=1
initexmf --set-config-value=[MPM]AutoInstall=1
```

(Run the first line from an elevated/Admin PowerShell if you installed MiKTeX for all users; the second line covers a per-user install. Only one will apply depending on how you installed it — running both is harmless.)

If you'd rather not rely on on-the-fly installs at all (for example, for a fully offline compile later), pre-install the same package set the macOS TinyTeX section above lists, using MiKTeX's package manager:

```powershell
mpm --admin --install=moderncv --install=fontawesome5 --install=fontawesome6 --install=academicons --install=import --install=luatexbase --install=pgf --install=titlesec --install=textpos --install=xltxtra --install=xunicode --install=cite --install=realscripts --install=needspace
```

Drop `--admin` if MiKTeX is installed for the current user only. If a package name doesn't resolve, `mpm --find=<name>` searches the repository for the correct name.

Quick smoke tests after setup (PowerShell):

```powershell
Set-Location cv; lualatex -interaction=nonstopmode -halt-on-error main_example.tex; Set-Location ..

$SmokeDir = New-Item -ItemType Directory -Path (Join-Path $env:TEMP "ai-job-cover-smoke-$(Get-Random)")
Copy-Item cover_letters\cover.cls, cover_letters\OpenFonts -Destination $SmokeDir -Recurse
@'
\documentclass[]{cover}
\begin{document}
\namesection{Test}{Candidate}{test@example.com}
\companyname{Example Company}
\companyaddress{123 Hiring Street\\Example City}
\currentdate{\today}
\lettercontent{Dear Hiring Manager,}
\lettercontent{This smoke test verifies that xelatex can load cover.cls and the bundled fonts.}
\closing{Sincerely,}
\signature{Test Candidate}
\end{document}
'@ | Set-Content (Join-Path $SmokeDir "cover_smoke.tex")
Push-Location $SmokeDir; xelatex -interaction=nonstopmode -halt-on-error cover_smoke.tex; Pop-Location
```

### Optional: ATS text extraction (pypdf, then pdftotext)

`/apply` runs an ATS parseability check on the compiled CV: it extracts the PDF's text layer and verifies contact details, reading order, and keyword coverage the way an applicant-tracking system sees them.

The default extractor is **pypdf** (BSD, `pip install pypdf`). Poppler `pdftotext` remains an optional fallback:

- **macOS:** `brew install poppler`
- **Debian/Ubuntu:** `sudo apt install poppler-utils`
- **Windows:** `choco install poppler`

If a command still uses `pdftotext -layout`, it must pass `-enc UTF-8` as well. If **neither** extractor is available, `/apply` skips the mechanical check with a warning and falls back to a visual keyword review — everything else works normally.

## 2. Install the plugin

Inside Claude Code:

```
/plugin marketplace add MRDGH2821/ai-job-search-plugin
/plugin install ai-job-search-plugin@ai-job-search-plugin
```

Job boards for Denmark (Jobbank, Jobdanmark, Jobindex, Jobnet) are a separate plugin, off by default. Install it if your market is Denmark (`/setup` offers it too):

```
/plugin install danish-job-portals@ai-job-search-plugin
```

The portal CLIs install their dependencies on first use. `linkedin-search` and `freehire-search` have zero runtime dependencies and run with plain `bun`. Outside Denmark, `/add-portal` generates a search skill for your local job board (see "Job search tools" in the README).

## 3. Create your workspace

Your workspace is an ordinary folder that holds your profile, CVs, cover letters and application history. Create an empty one, start Claude Code in it, and run:

```
/init-workspace
```

It lays out the CV and cover-letter sources, fonts, the `documents/` tree, state folders and a privacy `.gitignore`, writes `AGENTS.md` and `CLAUDE.md`, and offers `git init`. It copies only what is missing and never overwrites anything.

> **Keep this folder private.** `/setup` writes your personal data (name, contact details,
> employment history, salary expectations) into files here, and some of them are tracked
> by git. Keep the workspace local, or push it only to a **private** repository: anything
> pushed to a public repository is visible to anyone. `/setup` checks your `origin` and
> warns before writing if it is public.

## 4. Run the setup interview

Start Claude Code in your workspace folder:

```bash
claude
```

Then run the onboarding:

```
/setup
```

Claude will offer three paths:

- **Path A (documents folder):** Add your CV, LinkedIn export, diplomas, references, or past applications under `documents/`. Claude reads and cross-references them before proposing profile updates. This is best when you have several source files.
- **Path B (single CV import):** Share one CV/resume by mentioning the file with `@` or pasting the text. Claude extracts it and asks follow-up questions for anything missing.
- **Path C (interview mode):** Answer structured interview questions section by section.

All three paths produce the same result: fully populated profile files.

### What gets populated

| File | Content |
|------|---------|
| `profile/candidate.md` | Identity, contact details, education, experience, skills |
| `profile/behavioral.md` | Behavioral assessment |
| `profile/evaluation.md` | Personalized skill match areas, career goals, deal-breakers |
| `profile/cv.md` | Profile statements for your background |
| `profile/star.md` | STAR examples from your experience |
| `cv/main_example.tex` | Your LaTeX CV with actual details |
| `profile/search-queries.md` | Job search queries for `/scrape` |

### Re-running setup

You can update specific sections later:

```
/setup --section skills
/setup --section experience
/setup --section search
```

The `--section search` option is especially useful as your priorities evolve. It re-runs the search configuration interview and suggests role types you may not have considered based on your full profile.

## 5. Salary data

Optional. If you have salary data (from a union, salary survey, Glassdoor, or personal research), put `salary_data.json` in your workspace root:

1. **Option A:** Create it by hand. The format is in `plugins/ai-job-search-plugin/skills/job-tools/scripts/README_SALARY_TOOL.md`.
2. **Option B:** Convert it from Excel with the plugin's converter:
   ```bash
   pip install openpyxl
   python3 <plugin folder>/skills/job-tools/scripts/convert_salary_excel.py path/to/salary-data.xlsx --source "My Salary Data 2025"
   ```
   `<plugin folder>` is where Claude Code installed the plugin (`/plugin` shows it), or `plugins/ai-job-search-plugin` in a clone of this repository.

`/apply` uses it for salary benchmarking. Without it, the salary step is skipped.

## 6. Test the workflow

Find a job posting you're interested in, then:

```
/apply https://jobindex.dk/job/1234567
```

Or paste the job description directly:

```
/apply [paste job posting text here]
```

Claude will:
1. Evaluate the fit against your profile
2. Ask if you want to proceed
3. Draft a tailored CV and cover letter
4. Have a reviewer agent critique the drafts
5. Revise and present the final output

## 7. Compile your documents

After `/apply` creates the LaTeX files:

```bash
# Bash / zsh / Git Bash
cd cv && lualatex main_<company>_<role>.tex && cd ..
cd cover_letters && xelatex cover_<company>_<role>.tex && cd ..
```

```powershell
# PowerShell
Set-Location cv; lualatex main_<company>_<role>.tex; Set-Location ..
Set-Location cover_letters; xelatex cover_<company>_<role>.tex; Set-Location ..
```

These commands apply to the stock templates (moderncv CV, `cover.cls` cover letter). If you'd rather use your own LaTeX template, run `/add-template` — it captures the template's compile engine, fonts, style rules, and page limit, test-compiles it, and wires it into `/apply`. See "Custom templates" in the README.

## 8. Updating

Run `/plugin` and update `ai-job-search-plugin` (and `danish-job-portals` if installed), then run `/sync-instructions` in your workspace to refresh its `AGENTS.md` block. Your `profile/` and documents are never touched by an update.

## 9. Tracking the original project

This project was forked from [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search). Maintainers of this repository check it for improvements worth porting with `python3 tools/upstream_triage.py --remote upstream`, which maps upstream paths to the plugin layout. Ported and rejected commits are listed in `.github/upstream-handled.txt`. Users of the plugin don't need to do anything.

## Troubleshooting

### "salary_data.json not found"
This is expected if you haven't set up salary benchmarking. The `/apply` workflow skips this step automatically.

### Job search CLI tools not working
Make sure Bun is installed. Portal CLIs install their dependencies on first use. The tools require network access to fetch job listings.

### LaTeX compilation errors
- CV: uses `lualatex` (pdflatex often fails on modern MiKTeX with `fontawesome5` font-expansion errors; lualatex handles the same sources cleanly)
- Cover letter: uses `xelatex` (for custom fonts in `OpenFonts/fonts/`)
- Make sure your LaTeX distribution includes the `moderncv` package

### Fonts not found in cover letter
The cover letter template expects fonts in your workspace's `cover_letters/OpenFonts/fonts/`. If they are missing, run `/init-workspace` again: it restores missing files without overwriting anything.
