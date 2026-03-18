# Root Cause Analysis Skill

Investigate failed jobs by correlating Ansible Automation Platform (AAP) job logs with Splunk OCP pod logs to identify root causes.

Use this skill when you need to:
- Investigate job failures
- Analyze logs for errors
- Find root causes of infrastructure issues
- Debug failed deployments
- Troubleshoot Kubernetes/OpenShift problems

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

## Usage

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

## Output

Analysis results are saved to `.analysis/<job-id>/`:

| File | Description |
|------|-------------|
| `step1_job_context.json` | Parsed job metadata (GUID, namespace, failed tasks) |
| `step2_splunk_logs.json` | Correlated Splunk pod logs |
| `step3_correlation.json` | Unified timeline with correlation proof |
| `step4_summary.json` | Root cause summary (created by Claude) |

## How It Works

1. **Parse Job Log** - Extract identifiers (GUID, namespace, time window, failed tasks)
2. **Query Splunk** - Fetch OCP pod logs matching the namespace/GUID during job execution
3. **Build Correlation** - Merge AAP and Splunk events into a unified timeline
4. **Summarize** - Claude analyzes the correlation and provides root cause analysis

## Correlation Methods

The skill establishes correlation between AAP jobs and Splunk logs using:

- **Namespace Match** - `sandbox-<guid>-<env>` pattern in both sources
- **GUID Match** - 5-character deployment identifier (e.g., `example-guid`)
- **Time Overlap** - Splunk logs fall within job execution window

Confidence levels:
- **High** - Namespace + time overlap confirmed
- **Medium** - GUID match + time overlap
- **Low** - Only identifier match, no time confirmation

## Supported Log Formats

The skill can read job logs in these formats:
- `.json` - Plain JSON
- `.json.gz` - Gzipped JSON
- `.json.gz.transform-processed` - Transformed gzipped JSON
- `.json.transform-processed` - Transformed plain JSON
