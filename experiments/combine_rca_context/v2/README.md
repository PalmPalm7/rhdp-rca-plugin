# Root Cause Analysis Skill

Investigate failed jobs by correlating Ansible Automation Platform (AAP) job logs with Splunk OCP pod logs and analyzing AgnosticD/AgnosticV configuration to identify root causes.

Use this skill when you need to:
- Investigate job failures
- Analyze logs for errors
- Find root causes of infrastructure issues
- Debug failed deployments
- Troubleshoot Kubernetes/OpenShift problems
- Analyze AgnosticD/AgnosticV configuration issues

## Overview

This skill combines automated Python scripts (Steps 1-4a) with GitHub MCP tool integration (Steps 4b-4e) to provide comprehensive root cause analysis:

1. **Automated Steps (Python scripts)**: Parse job logs, query Splunk, build correlation timeline, and parse GitHub paths
2. **Analysis Steps (Claude + GitHub MCP)**: Fetch AgnosticV configuration and AgnosticD workload code from GitHub, then analyze root causes

## Setup

### 1. Create virtual environment and install dependencies

```bash
cd root-cause-analysis
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Configure environment

Add the following environment variables to your Claude Code settings file:
- **Project-level**: `.claude/settings.local.json` in your project root
- **Or global**: `~/.claude/settings.json`

```json
{
  "env": {
    "JOB_LOGS_DIR": "/path/to/your/extracted_logs",
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

Update the values:
- `JOB_LOGS_DIR` - Directory containing job log files (`job_<ID>.json.gz`, etc.)
- `SPLUNK_HOST` - Your Splunk REST API endpoint (port 8089)
- `SPLUNK_USERNAME` / `SPLUNK_PASSWORD` - Your Splunk credentials
- `SPLUNK_INDEX` - Default index for AAP logs
- `SPLUNK_OCP_APP_INDEX` / `SPLUNK_OCP_INFRA_INDEX` - OCP log indices

### 3. Configure GitHub MCP Server

This skill requires GitHub MCP server access to fetch configuration and workload files. Configure in your Claude Code settings:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}
```

Required GitHub MCP tools:
- `mcp__github__search_code` - Search for code files
- `mcp__github__get_file_contents` - Fetch file contents
- `mcp__github__search_repositories` - Discover repositories

## Usage

### Analyze by Job ID

If `JOB_LOGS_DIR` is configured, you can analyze by job ID:

```bash
.venv/bin/python scripts/cli.py analyze --job-id 1234567
```

The skill will automatically:
1. Find the log file matching `job_1234567.*` in `JOB_LOGS_DIR`
2. Run Steps 1-4a (automated Python scripts)
3. Generate candidate GitHub paths for Steps 4b-4e

### Analyze by File Path

Alternatively, specify the log file directly:

```bash
.venv/bin/python scripts/cli.py analyze --job-log /path/to/job_1234567.json.gz
```

### Other Commands

```bash
# Parse job log only (Step 1)
.venv/bin/python scripts/cli.py parse --job-log /path/to/job.json.gz

# Run ad-hoc Splunk query
.venv/bin/python scripts/cli.py query 'index=$SPLUNK_OCP_APP_INDEX "example-guid"' --earliest=-24h

# Check analysis status for a job
.venv/bin/python scripts/cli.py status 1234567
```

## How It Works

### Automated Steps (Python Scripts)

**Step 1: Parse Job Log**
- Extract identifiers (GUID, namespace, time window, failed tasks)
- Parse job metadata (platform, catalog_item, environment)
- Output: `step1_job_context.json`

**Step 2: Query Splunk**
- Fetch OCP pod logs matching the namespace/GUID during job execution
- Filter for errors, failures, exceptions
- Output: `step2_splunk_logs.json`

**Step 3: Build Correlation Timeline**
- Merge AAP and Splunk events into a unified timeline
- Identify causal chains (AAP task → pod event → error)
- Output: `step3_correlation.json`

**Step 4a: Parse GitHub Paths**
- Parse job_name to extract platform/catalog/environment
- Parse task_path to extract repository/file/line information
- Generate candidate paths for AgnosticV configuration hierarchy
- Generate candidate paths for AgnosticD workload code
- **Note**: This step only generates candidate paths - files are NOT fetched yet
- Output: `step4a_github_paths.json`

### Analysis Steps (Claude + GitHub MCP)

**Step 4b: Fetch AgnosticV Configuration**
- Use GitHub MCP tools to fetch configuration files from `rhpds/agnosticv`
- Fetch in hierarchy order: `common.yaml` → `{platform}/account.yaml` → `{platform}/{catalog_item}/{env}.yaml`
- Handle path variations (underscores vs hyphens, case sensitivity)
- Check for secrets references and vault-encrypted variables

**Step 4c: Fetch AgnosticD Workload Code**
- Use GitHub MCP tools to fetch workload files from AgnosticD repositories
- Fetch role defaults and task files
- Extract context around failed task lines

**Step 4d: Apply Investigation Rules**
- Variable precedence analysis (role defaults → config hierarchy)
- Task action pattern matching
- Secrets detection
- Time correlation analysis
- Task duration analysis

**Step 4e: Generate Summary**
- Combine all evidence into root cause analysis
- Provide specific recommendations with file paths
- Output: `step4_summary.json`

## Output

Analysis results are saved to `.analysis/<job-id>/`:

| File | Description | Author |
|------|-------------|--------|
| `step1_job_context.json` | Parsed job metadata (GUID, namespace, failed tasks) | Python |
| `step2_splunk_logs.json` | Correlated Splunk pod logs | Python |
| `step3_correlation.json` | Unified timeline with correlation proof | Python |
| `step4a_github_paths.json` | Candidate GitHub paths for investigation (files NOT fetched) | Python |
| `step4_summary.json` | Root cause summary with AgnosticD/V context | Claude |

## Correlation Methods

The skill establishes correlation between AAP jobs and Splunk logs using:

- **Namespace Match** - `sandbox-<guid>-<env>` pattern in both sources
- **GUID Match** - 5-character deployment identifier (e.g., `example-guid`)
- **Time Overlap** - Splunk logs fall within job execution window

Confidence levels:
- **High** - Namespace + time overlap confirmed
- **Medium** - GUID match + time overlap
- **Low** - Only identifier match, no time confirmation

## AgnosticD/AgnosticV Integration

This skill specifically analyzes AgnosticD/AgnosticV deployments:

- **AgnosticV Configuration**: Fetches configuration hierarchy from `rhpds/agnosticv` repository
  - Base defaults (`common.yaml`)
  - Platform-specific configs (`{platform}/account.yaml`)
  - Environment-specific overrides (`{platform}/{catalog_item}/{env}.yaml`)

- **AgnosticD Workload Code**: Fetches workload code from AgnosticD repositories
  - Role defaults (`roles/{role}/defaults/main.yml`)
  - Task files (`roles/{role}/tasks/{file}.yml`)

- **Variable Precedence**: Analyzes variable override order to identify configuration conflicts

## Supported Log Formats

The skill can read job logs in these formats:
- `.json` - Plain JSON
- `.json.gz` - Gzipped JSON
- `.json.gz.transform-processed` - Transformed gzipped JSON
- `.json.transform-processed` - Transformed plain JSON
