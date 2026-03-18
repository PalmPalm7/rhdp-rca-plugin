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

This skill uses automated Python scripts for data collection (Steps 1-4) and Claude for analysis (Step 5):

1. **Steps 1-3**: Parse job logs, query Splunk, build correlation timeline
2. **Step 4**: Automatically fetch AgnosticV configuration and AgnosticD workload code from GitHub
3. **Step 5**: Analyze root causes and generate recommendations

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
    "GITHUB_TOKEN": "your-github-token",
    "SPLUNK_HOST": "your-splunk-host",
    "SPLUNK_USERNAME": "your-username",
    "SPLUNK_PASSWORD": "your-password",
    "SPLUNK_INDEX": "your_splunk_index",
    "SPLUNK_OCP_APP_INDEX": "your_ocp_app_index",
    "SPLUNK_OCP_INFRA_INDEX": "your_ocp_infra_index",
    "SPLUNK_VERIFY_SSL": "false"
  }
}
```

Update the values:
- `JOB_LOGS_DIR` - Directory containing job log files (`job_<ID>.json.gz`, etc.)
- `GITHUB_TOKEN` - GitHub personal access token for fetching files via GitHub API
- `SPLUNK_HOST` - Your Splunk REST API endpoint
- `SPLUNK_USERNAME` / `SPLUNK_PASSWORD` - Your Splunk credentials
- `SPLUNK_INDEX` - Default index for AAP logs
- `SPLUNK_OCP_APP_INDEX` / `SPLUNK_OCP_INFRA_INDEX` - OCP log indices

### 3. Configure GitHub MCP Server (for 404 verification)

This skill uses GitHub MCP tools only for verifying 404 errors. Configure in your Claude Code settings:

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
- `mcp__github__get_file_contents` - Check parent directories and verify file existence
- `mcp__github__search_code` - Locate files when paths fail

## Usage

### Complete Analysis Workflow

```bash
# Step 1-3: Parse job log, query Splunk, build correlation
.venv/bin/python scripts/cli.py analyze --job-id 1234567

# Step 4: Automatically fetch GitHub files (AgnosticV configs and AgnosticD code)
.venv/bin/python scripts/step4_fetch_github.py --job-id 1234567

# Step 5: Claude analyzes the data and generates summary (automatic when skill is invoked)
```

### Analyze by Job ID

If `JOB_LOGS_DIR` is configured, you can analyze by job ID:

```bash
.venv/bin/python scripts/cli.py analyze --job-id 1234567
```

The skill will automatically find the log file matching `job_1234567.*` in `JOB_LOGS_DIR`.

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

### Steps 1-3: Automated Analysis (Python Scripts)

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

### Step 4: Fetch GitHub Files (Automated Python Script)

The `step4_fetch_github.py` script automatically:
- Parses job metadata to identify platform/catalog/environment
- Fetches AgnosticV configuration hierarchy from `rhpds/agnosticv`:
  - `common.yaml` (base defaults)
  - `{platform}/account.yaml` (platform-specific)
  - `{platform}/{catalog_item}/{env}.yaml` (environment-specific)
- Fetches AgnosticD workload code:
  - Role defaults (`roles/{role}/defaults/main.yml`)
  - Task files (`roles/{role}/tasks/{file}.yml`)
- Reports success/404 status for each file attempt

**Output**: `step4_github_fetch_history.json`

**GitHub MCP Verification for 404 Errors**:

When Step 4 reports `"error": "all_paths_failed"` or any `"status": "404"` in `paths_tried`, you **MUST** verify using MCP tools:

1. **Check parent directory first**: Use `mcp__github__get_file_contents` to list actual folder/file names (reveals case sensitivity, hyphens vs underscores)
2. **If parent check fails**: Use `mcp__github__search_code` to locate files by filename or partial path
3. **Document findings**: Wrong format → parser bug, missing → truly missing, empty → rare
4. **No assumptions**: "empty", "test", "demo" in names are just labels - always verify 404s before concluding files are missing

### Step 5: Analyze and Generate Summary (Claude)

**Input files** (read in order):
1. `step1_job_context.json` - Job metadata and failed task details
2. `step3_correlation.json` - Correlated timeline with relevant pod logs
3. `step4_github_fetch_history.json` - Configuration and code context
4. `step2_splunk_logs.json` - Only if step3 indicates errors needing deeper investigation

**Analysis Guidelines**:
- **Configuration Analysis**: Variable precedence (role defaults → common.yaml → platform/account.yaml → platform/catalog/env.yaml), check for conflicts, missing variables, secrets references
- **Task Analysis**: Task action patterns, duration analysis, time correlation, conditional execution checks
- **Root Cause**: Categorize as `configuration|infrastructure|workload_bug|credential|resource|dependency`

**Output**: `step5_analysis_summary.json` (or present directly to user)

## Output

Analysis results are saved to `.analysis/<job-id>/`:

| File | Description | Author |
|------|-------------|--------|
| `step1_job_context.json` | Parsed job metadata (GUID, namespace, failed tasks) | Python |
| `step2_splunk_logs.json` | Correlated Splunk pod logs | Python |
| `step3_correlation.json` | Unified timeline with correlation proof | Python |
| `step4_github_fetch_history.json` | GitHub fetch results (configs and workload code) | Python |
| `step5_analysis_summary.json` | Root cause summary with recommendations | Claude |

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

- **AgnosticV Configuration**: Automatically fetches configuration hierarchy from `rhpds/agnosticv` repository
  - Base defaults (`common.yaml`)
  - Platform-specific configs (`{platform}/account.yaml`)
  - Environment-specific overrides (`{platform}/{catalog_item}/{env}.yaml`)

- **AgnosticD Workload Code**: Automatically fetches workload code from AgnosticD repositories
  - Role defaults (`roles/{role}/defaults/main.yml`)
  - Task files (`roles/{role}/tasks/{file}.yml`)

- **Variable Precedence**: Analyzes variable override order to identify configuration conflicts

## Supported Log Formats

The skill can read job logs in these formats:
- `.json` - Plain JSON
- `.json.gz` - Gzipped JSON
- `.json.gz.transform-processed` - Transformed gzipped JSON
- `.json.transform-processed` - Transformed plain JSON

## Troubleshooting

### GitHub Token Issues
- Ensure `GITHUB_TOKEN` is set in environment variables
- Token must have `repo` scope for private repositories
- Check token expiration and regenerate if needed

### GitHub MCP Tools Not Available
- Ensure GitHub MCP server is configured in Claude Code settings
- Restart Claude Code after adding MCP servers
- Check that `mcp__github__*` tools appear in available tools
- **Note**: MCP tools are only used for 404 verification, not for fetching files

### Files Not Found (404 errors)
- Step 4 script handles path variations automatically
- If 404 errors occur, use GitHub MCP tools to verify (see Step 4 section above)
- Check parent directories first before doing wild searches
- Document findings to identify parser bugs vs truly missing files

### Splunk Connection Issues
- Verify Splunk credentials in environment variables
- Check network connectivity to Splunk API endpoint
- Ensure SSL certificate verification settings are correct
