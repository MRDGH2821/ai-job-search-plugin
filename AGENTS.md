---
framework_version: 1.2.0
---

# Agent Guidelines: AI Job Search

This workspace is structured to manage job search activities, scraper tools, CVs, cover letters, and interview preparation.

## Thin-Pointer Design (Single Source of Truth)

To prevent duplication and configuration drift across different AI agent frameworks (Claude Code, Google Antigravity, Codex, Cursor, Gemini CLI, etc.), this workspace uses a unified thin-pointer design. All agent runtimes should load the canonical specifications and candidate profiles from the files and directories below:

1. **Personal Candidate Profile:**
   - All candidate data lives in [profile/](profile/) (created by `/setup` from `plugins/ai-job-search/skills/job-application-assistant/profile-templates/`). [CLAUDE.md](CLAUDE.md) holds the role and pointers only.
2. **Canonical Workflow Specifications:**
   - The step-by-step instructions and triggers for tasks (setup, scrape, rank, apply, upskill, interview) are defined as skills in [plugins/ai-job-search/skills/](plugins/ai-job-search/skills/), one folder per command or workflow.
   - Do not duplicate these rules or specifications. Treat the plugin skills as the single source of truth.
3. **Portal Search Skills:**
   - Job-portal search skills ship inside the plugins (`plugins/*/skills/*-search/`) in the portable Agent Skills format. Other runtimes can install them, and the whole workflow, through capa (`capa registry add MadsLorentzen/ai-job-search`). Your own portals from `/add-portal` live in [.agents/skills/](.agents/skills/). The `/scrape` workflow ([plugins/ai-job-search/skills/job-scraper/](plugins/ai-job-search/skills/job-scraper/)) orchestrates both.
