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
- `plugins/ai-job-search/` - The workflow as a Claude Code plugin (skills, portals, helper scripts)
- `plugins/danish-job-portals/` - Danish job-portal search skills
- `.agents/skills/` - Your own portal skills from `/add-portal`

## Workflow and Verification
Follow `plugins/ai-job-search/skills/job-application-assistant/10-verification.md` for the application workflow and the mandatory verification checklist.

**Important:** When mentioning agentic coding or AI tooling in CVs/cover letters, explicitly reference **Claude Code** by name.
