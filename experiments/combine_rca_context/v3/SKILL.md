---
name: root-cause-analysis
description: Perform root cause analysis and log analysis for failed jobs. Use when user wants to investigate job failures, analyze logs, find root causes, debug errors, troubleshoot infrastructure issues, or understand why a job failed. Investigate AAP job failures using Splunk correlation and AgnosticD/AgnosticV configuration analysis. Correlates local Ansible/AAP job logs with Splunk OCP pod logs and retrieves relevant configuration from GitHub repositories.
allowed-tools:
  - Bash
  - Read
  - Write
  - mcp__github__search_code
  - mcp__github__get_file_contents
---

# Root Cause Analysis

Investigate failed jobs by correlating Ansible Automation Platform (AAP) job logs with Splunk OCP pod logs and analyzing AgnosticD/AgnosticV configuration to identify root causes.

## Automatic Execution

When a user asks to analyze a failed job, execute these steps automatically.
The skill's base path is provided when this skill is invoked. Run scripts relative to this folder.

### Setup (run once per session if .venv doesn't exist)

```bash
# Create virtual environment and install dependencies
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
```

### Step 1-3: Run the analysis CLI

```bash
# Option 1: By job ID (searches JOB_LOGS_DIR automatically)
.venv/bin/python scripts/cli.py analyze --job-id <JOB_ID>

# Option 2: By explicit path
.venv/bin/python scripts/cli.py analyze --job-log <path-to-job-log>
```

The skill automatically searches for job logs in the configured `JOB_LOGS_DIR` (set in `.env`).

### Step 4: Fetch GitHub Data (Automated)

```bash
# Fetch all GitHub files automatically via GitHub API
.venv/bin/python scripts/step4_fetch_github.py --job-id <JOB_ID>
```

This script automatically parses job metadata, fetches AgnosticV configs and AgnosticD workload code, and reports success/404 status.

**Output**: `.analysis/<job-id>/step4_github_fetch_history.json`

**MANDATORY: GitHub MCP Tools for 404 Verification**:
- **ALWAYS check 404 files via MCP server** when step4 reports `"error": "all_paths_failed"` or any `"status": "404"` in `paths_tried`
- **DO NOT skip 404 verification** - the script may have incorrect path parsing
- **Process**:
  1. Check parent directory first using `mcp__github__get_file_contents` to list actual folder/file names (reveals case sensitivity, hyphens vs underscores)
  2. If parent check fails, use `mcp__github__search_code` to locate files by filename or partial path
  3. Document findings: wrong format → parser bug, missing → truly missing, empty → rare
  4. **No assumptions**: "empty", "test", "demo" in names are just labels - always verify 404s

### Step 5: Analyze and Generate Summary

Read outputs from `.analysis/<job-id>/` and perform root cause analysis. See Step 5 section below for detailed requirements.

## Manual Usage

From this skill's directory:

```bash
# Setup virtual environment (one time)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Analyze by job ID (uses JOB_LOGS_DIR to find the file)
.venv/bin/python scripts/cli.py analyze --job-id 1234567

# Or analyze with explicit path
.venv/bin/python scripts/cli.py analyze --job-log /path/to/job_123.json.gz
```

## Configuration

**IMPORTANT**: All credentials (GitHub token and Splunk credentials) should be set in `.claude/settings.json` (project-level) or `~/.claude/settings.json` (global), NOT in `.env` files.

Add the following environment variables to your Claude Code settings file:

**Project-level**: `.claude/settings.local.json` in your project root
**Or global**: `~/.claude/settings.json`

```json
{
  "env": {
    "JOB_LOGS_DIR": "/path/to/your/extracted_logs",
    "GITHUB_TOKEN": "your-github-token",
    "SPLUNK_HOST": "host-url",
    "SPLUNK_USERNAME": "your-username",
    "SPLUNK_PASSWORD": "your-password",
    "SPLUNK_INDEX": "your_aap_index",
    "SPLUNK_OCP_APP_INDEX": "your_ocp_app_index",
    "SPLUNK_OCP_INFRA_INDEX": "your_ocp_infra_index",
    "SPLUNK_VERIFY_SSL": "false"
  }
}
```

---

## Steps 1-3: Automated Analysis (Python Scripts)

**Step 1**: Parse job log → Extract job ID, GUID, namespace, failed tasks, time window
**Step 2**: Query Splunk → Fetch pod logs from namespace within job time window
**Step 3**: Correlate → Merge AAP and Splunk events into unified timeline

**Outputs**: `.analysis/<job-id>/step1_job_context.json`, `step2_splunk_logs.json`, `step3_correlation.json`

---

## Step 4: Fetch GitHub Files (Automated)

Script `step4_fetch_github.py` automatically parses job metadata, fetches AgnosticV configs and AgnosticD workload code, and reports success/404 status.

**Output**: `.analysis/<job-id>/step4_github_fetch_history.json`


**GitHub MCP Verification for 404 Errors**:

When step4 reports `"error": "all_paths_failed"` or any `"status": "404"` in `paths_tried`, you **MUST** verify using MCP tools:

2. **If parent check fails**: Use `mcp__github__search_code` to locate files by filename or partial path. Use `mcp__github__search_repositories` only if task_path parsing failed.

4. **No assumptions**: "empty", "test", "demo" in names are just labels - always verify 404s before concluding files are missing.

---

## Step 5: Analyze and Generate Summary (your task)

**Input**: Read the following files in order (optimized to avoid redundancy):
1. **REQUIRED**: `step1_job_context.json` - Job metadata and failed task details
2. **REQUIRED**: `step3_correlation.json` - Correlated timeline with relevant pod logs (DO NOT read step2 unless needed)
3. **REQUIRED**: `step4_github_fetch_history.json` - Configuration and code context
4. **CONDITIONAL**: `step2_splunk_logs.json` - Only read if step3 indicates errors needing deeper investigation

**Output**: `.analysis/<job-id>/step5_analysis_summary.json` (optional, or present directly to user)

### Analysis Guidelines

**Configuration Analysis**:
- Variable precedence: Role defaults → common.yaml → {platform}/account.yaml → {platform}/{catalog_item}/{env}.yaml (later overrides earlier)
- Check for conflicts, missing variables, secrets references (`includes/secrets`, `!vault`)

**Task Analysis**:
- Task action patterns: `kubernetes.core.k8s_info` (RBAC/resource), `ansible.builtin.uri` (network/auth), `command/shell` (paths/permissions)
- Duration: <30s (immediate failure), 30-300s (short retry), >300s (long retry/timeout)
- Time correlation: Pod error before/during/after task indicates infrastructure vs task-triggered issue
- Conditional execution: Check if `when:` conditions executed incorrectly (variable precedence issue)

### Summary Requirements

1. **Job Details**: ID, status, GUID, namespace, platform, catalog, environment
2. **Failed Tasks**: **PRESERVE ALL FIELDS** from step1 (task, play, role, task_action, error_message, duration, timestamp, location with both original path and GitHub path)
3. **Configuration Analysis**: Which configs found, variable precedence, missing vars, secrets
4. **Correlation**: How AAP logs link to Splunk (GUID, namespace, timestamps, pod names)
5. **Root Cause**: Category (`configuration|infrastructure|workload_bug|credential|resource|dependency`), summary, confidence, evidence
6. **Recommendations**: Specific file changes with paths, actions, and reasons

### Schema

See `schemas/summary.schema.json` for complete structure. Example:

```json
{
  "job_id": "{job_id}",
  "job_metadata": {
    "platform": "{platform}",
    "catalog_item": "{catalog_item}",
    "environment": "{env}",
    "guid": "{guid}"
  },
  "failed_tasks": [
    {
      "task": "Get caller identity",
      "play": "Destroy playbook",
      "role": "infra-aws-dry-run",
      "task_action": "command",
      "error_message": "'aws_access_key_id' is undefined",
      "duration": 0.008,
      "timestamp": "2025-01-15T10:30:45Z",
      "location": {
        "original_path": "/runner/project/ansible/roles-infra/infra-aws-dry-run/tasks/ec2.yml:2",
        "repository": "redhat-cop/agnosticd",
        "file_path": "ansible/roles-infra/infra-aws-dry-run/tasks/ec2.yml",
        "line_number": 2,
        "github_path": "redhat-cop/agnosticd:ansible/roles-infra/infra-aws-dry-run/tasks/ec2.yml:2"
      }
    }
  ],
  "agnosticv_config": {
    "hierarchy": [
      {
        "file": "rhpds/agnosticv:common.yaml",
        "relevant_vars": {}
      },
      {
        "file": "rhpds/agnosticv:{platform}/account.yaml",
        "secrets_referenced": ["includes/secrets/{platform}.yml"]
      },
      {
        "file": "rhpds/agnosticv:{platform}/{catalog_item}/{env}.yaml",
        "missing_vars": ["variable_name"],
        "critical_finding": "Description of important finding"
      }
    ]
  },
  "agnosticd_workloads": [
    {
      "role": "{role_name}",
      "task_file": "tasks/{task_file}.yml",
      "task_line": 123,
      "task_action": "module.name"
    }
  ],
  "root_cause": {
    "summary": "Brief description of root cause",
    "category": "configuration|infrastructure|workload_bug|credential|resource|dependency",
    "subcategory": "specific_type",
    "confidence": "high|medium|low",
    "primary_evidence": ["Evidence point 1", "Evidence point 2"],
    "contributing_factors": ["Factor 1", "Factor 2"],
    "alternative_hypothesis": "Other possible explanation"
  },
  "recommendations": [
    {
      "priority": "critical|high|medium|low",
      "action": "What to do",
      "file": "rhpds/agnosticv:{platform}/{catalog_item}/{env}.yaml",
      "change": "Specific change to make"
    }
  ]
}
```

---

## Files

| Step | File | Author |
|------|------|--------|
| 1 | `step1_job_context.json` | Python |
| 2 | `step2_splunk_logs.json` | Python |
| 3 | `step3_correlation.json` | Python |
| 4 | `step4_github_fetch_history.json` | Python |
| 5 | `step5_analysis_summary.json` | You |

All files in `.analysis/<job-id>/`
