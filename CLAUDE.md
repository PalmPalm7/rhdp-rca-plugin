# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIOps Skills marketplace - a collection of skills for AI-powered operations tasks. Skills extend Claude's capabilities for specific operational domains like monitoring, incident management, infrastructure automation, and security operations.

## Repository Structure

```
aiops-skills/
├── skills/              # All skills live here
│   ├── template-skill/
│   ├── logs-fetcher/
│   ├── root-cause-analysis/
│   ├── context-fetcher/
│   └── feedback-capture/
├── docs/                # Project documentation and spec
├── experiments/         # Experimental skill prototypes
└── pyproject.toml
```

## Creating Skills

Each skill requires a `SKILL.md` file with:
1. YAML frontmatter (`name`, `description`, optional `license`, `allowed-tools`, `metadata`)
2. Markdown body with instructions

The `name` field must match the directory name (lowercase, hyphen-separated).

## logs-fetcher Skill

Fetch Ansible/AAP logs from remote servers with time-based filtering:

```bash
# Fetch logs within a specific time range (minute/second precision)
python skills/logs-fetcher/scripts/fetch_logs_ssh.py \
  --start-time "2025-12-09 08:00:00" \
  --end-time "2025-12-10 17:00:00" \
  --mode processed \
  --local-dir ~/incident-logs

# Fetch logs from a specific day
python skills/logs-fetcher/scripts/fetch_logs_ssh.py \
  --start-time "2025-12-10" \
  --end-time "2025-12-10" \
  --mode all

# Fetch logs by job number
python skills/logs-fetcher/scripts/fetch_logs_by_job.py 1234567 1234568 1234569
```

Supports:
- Time-based filtering with formats: `YYYY-MM-DD HH:MM:SS`, `YYYY-MM-DD HH:MM`, or `YYYY-MM-DD`
- Job number-based fetching (with or without 'job_' prefix)
- Mode filtering: `processed`, `ignored`, or `all`
- Sorting: `desc` (newest first) or `asc` (oldest first)
- Limit on number of files fetched

Both scripts default `--local-dir` to `JOB_LOGS_DIR` from settings.json (shared with root-cause-analysis).

## Environment Variables

All skills share these environment variables (configured via `.claude/settings.local.json`):

| Variable | Used by | Description |
|----------|---------|-------------|
| `REMOTE_HOST` | logs-fetcher, root-cause-analysis (`--fetch`) | SSH host alias |
| `REMOTE_DIR` | logs-fetcher, root-cause-analysis (`--fetch`) | Remote log directory |
| `JOB_LOGS_DIR` | logs-fetcher, root-cause-analysis | Local directory for job logs |
| `GITHUB_TOKEN` | root-cause-analysis | GitHub personal access token |
| `SPLUNK_*` | root-cause-analysis | Splunk connection settings |

## Skill Categories

- Monitoring & Observability
- Incident Management
- Infrastructure & Automation
- Security Operations
- Cost Optimization
