---
name: root_cause_analysis
description: Perform root cause analysis and log analysis for failed jobs. Investigate AAP job failures using Splunk correlation and AgnosticD/AgnosticV configuration analysis. Correlates local Ansible/AAP job logs with Splunk OCP pod logs and retrieves relevant configuration from GitHub repositories.
allowed-tools:
  - mcp__github__search_code
  - mcp__github__get_file_contents
  - mcp__github__search_repositories
  - Bash
  - Read
  - Write
---

# Root Cause Analysis

Investigate failed jobs by correlating Ansible Automation Platform (AAP) job logs with Splunk OCP pod logs and analyzing AgnosticD/AgnosticV configuration to identify root causes.

This version uses Python scripts to parse job metadata and build GitHub investigation paths (Steps 1-4a). Then, use GitHub MCP tools to fetch configuration and workload files from GitHub repositories.

## Automatic Execution

When a user asks to analyze a failed job, execute these steps automatically.

The skill's base path is provided when this skill is invoked. Run scripts relative to this folder.

### Setup (run once per session if .venv doesn't exist)

```bash
# Create virtual environment and install dependencies
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
```

### Step 1-4a: Run the analysis CLI

```bash
# Option 1: By job ID (searches JOB_LOGS_DIR automatically)
.venv/bin/python scripts/cli.py analyze --job-id <JOB_ID>

# Option 2: By explicit path
.venv/bin/python scripts/cli.py analyze --job-log <path-to-job-log>
```

The CLI automatically runs Steps 1-4a:
- **Step 1**: Parse job log → extract identifiers, failed tasks
- **Step 2**: Query Splunk → fetch correlated OCP pod logs
- **Step 3**: Build correlation timeline
- **Step 4a**: Parse GitHub paths → **ONLY generates candidate paths** (does NOT fetch files)

**Output files**:
- `.analysis/<job-id>/step1_job_context.json`
- `.analysis/<job-id>/step2_splunk_logs.json`
- `.analysis/<job-id>/step3_correlation.json`
- `.analysis/<job-id>/step4a_github_paths.json` (candidate paths only - files NOT fetched yet)

### Step 4b-4e: Analyze with AgnosticD/V context (You do this)

**Input**: Read the following files in order (optimized to avoid redundancy):
1. **REQUIRED**: `step1_job_context.json` - Job metadata and failed task details
2. **REQUIRED**: `step4a_github_paths.json` - Parsed GitHub paths and investigation targets
3. **REQUIRED**: `step3_correlation.json` - Correlated timeline with relevant pod logs (DO NOT read step2 unless needed)
4. **CONDITIONAL**: `step2_splunk_logs.json` - Only read if step3 indicates errors needing deeper investigation

Then perform enhanced analysis following these steps:

**Step 4b: Fetch AgnosticV Configuration using github mcp server**

Read `step4a_github_paths.json` and for EACH failed task, iterate through `investigation_targets.configuration.hierarchy`:

For EACH config in the hierarchy:

1. **If config has `path` (single path)**:
   - Use `mcp__github__get_file_contents(owner=config['owner'], repo=config['repo'], path=config['path'])`
   - If 404: Use GitHub MCP search tools (see below)

2. **If config has `paths_to_try` (multiple candidate paths)**:
   - Try ALL paths in the list using `mcp__github__get_file_contents`
   - **CRITICAL**: Don't stop after first 404 - try all variations (underscores vs hyphens, etc.)
   - If ALL paths return 404: Use GitHub MCP search tools

3. **When candidate paths fail, use GitHub MCP search**:
   - **Check parent directory first** (`mcp__github__get_file_contents`): List parent to see actual names/formats (reveals case sensitivity, hyphens vs underscores). Document findings: wrong format → parser bug, missing → truly missing, empty → rare.
   - **If parent check fails**: Use `mcp__github__search_code` to locate files by filename or partial path
   - **No assumptions**: "empty", "test", "demo" in names are just labels - always verify 404s

4. Store fetched content with metadata:
   - Which path worked (for recommendations later)
   - Order number (for precedence analysis)
   - Purpose (base_defaults, platform_config, env_overrides)
   - Any `check_for` hints (secrets, vault)

**Validation Checklist Before Step 4c:**
- [ ] All candidate paths from step4a were attempted (not just the first one)
- [ ] If candidate paths failed, GitHub MCP search tools were used to find actual paths
- [ ] Parent directory was checked first before doing wild searches
- [ ] All fetched configs stored with metadata (order, purpose, working path)

**Step 4c: Fetch AgnosticD Workload Code**

Read `investigation_targets.workload_code` from step4a for each failed task.

For EACH workload file:

1. **If file has `paths_to_try`** (role defaults with extension variations):
   ```
   Try each path until one succeeds
   ```

2. **If file has `path`** (task file - always direct):
   ```
   Fetch directly
   ```

3. Note any `warning` fields (e.g., "Could not extract role name")

Store fetched workload code with:
- File path that worked
- Purpose (role_defaults, failed_task_code)
- Line context information (target_line, context_before, context_after)

**Step 4d: Apply Investigation Rules**

Now you have ALL data:
- step1_job_context.json (basic failure info)
- step2_splunk_logs.json (pod logs, if available)
- step3_correlation.json (timeline)
- Fetched config files (from step 4b)
- Fetched workload files (from step 4c)

Apply these investigation rules:

1. **Variable Precedence Analysis**:
   - Use the config hierarchy ORDER from step4a (order 1 → 2 → 3)
   - Build precedence chain: role defaults → order 1 → order 2 → order 3
   - Last definition wins
   - Check for variables referenced in failed task but not defined anywhere

2. **Task Action Pattern Matching**:
   - `kubernetes.core.k8s_info` → Check API access, RBAC, resource existence
   - `ansible.builtin.uri` → Check network, DNS, certificates, auth
   - `ansible.builtin.command/shell` → Check binary paths, permissions
   - `include_role/import_role` → Check role dependencies

3. **Secrets Detection**:
   - Check `check_for` hints in config files from step4a
   - If `includes/secrets` found → Flag potential secret file issues
   - If `!vault` found → Flag potential vault decryption issues

4. **Time Correlation**:
   - Use step3 correlation data
   - Pod error BEFORE task → Infrastructure issue
   - Pod error DURING task → Task triggered the error
   - Pod error AFTER task timeout → Resource creation failed silently

5. **Task Duration Analysis**:
   - < 30s: Immediate failure (RBAC, missing resource)
   - 30-300s: Short retry loop
   - > 300s: Long retry loop (health check timeout)

**Step 4e: Generate Summary**

Combine ALL evidence and output to `.analysis/<job-id>/step4_summary.json` with this structure:

- parsing_status and warnings from step4a
- parsed_metadata from step4a
- Job details from step1
- Failed tasks with locations from step4a
- Config hierarchy showing which paths worked
- Workload code analysis
- Root cause with evidence
- Specific recommendations with file paths that worked

Provide a summary to the user with:
1. **Job Details**: ID, status, GUID, namespace, platform, demo
2. **Failed Tasks**: Task details with both original AAP path and parsed GitHub location
3. **Configuration Context**: Relevant variables, missing vars, secrets references
4. **Correlation**: How AAP logs link to Splunk pod logs
5. **Root Cause**: Analysis of why the job failed (configuration vs infrastructure vs workload bug)
6. **Recommendations**: Specific file changes with paths and suggested values

---

## Configuration

Create a `.env` file (see `.env.example`):

```bash
# Default directory to search for job log files
JOB_LOGS_DIR=~/aiops_extracted_logs
```

---

## Manual Usage

From this skill's directory:

```bash
# Setup virtual environment (one time)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run Steps 1-4a (all automated)
.venv/bin/python scripts/cli.py analyze --job-id 1234567

# Steps 4b-4e: Fetch GitHub files and analyze (done by Claude)
```

---

## Step 1: Parse Local Job Log

The script extracts key identifiers from the local AAP job log:

- **Job ID**: The AAP job number
- **GUID**: Unique deployment identifier
- **Namespace**: OCP namespace
- **Time Window**: Job start/end times for Splunk query filtering
- **Failed Tasks**: Tasks that failed with error messages
- **Pod References**: Any pod names mentioned in the job output

**Output**: `.analysis/<job-id>/step1_job_context.json`

---

## Step 2: Query Splunk for Pod Logs

Using the identifiers from Step 1, query Splunk for:

1. **OCP Application Logs**: Pod logs from the namespace
2. **Error Events**: Filtered for errors, failures, exceptions
3. **Time-Bounded**: Only logs within the job execution window

**Queries used**:
```spl
# Namespace-based search
index=your_ocp_app_index kubernetes.namespace_name="<namespace>"
  earliest=<job_start> latest=<job_end>

# Error-focused search
index=your_ocp_app_index kubernetes.namespace_name="<namespace>"
  (error OR failed OR fatal OR exception) | head 200
```

**Output**: `.analysis/<job-id>/step2_splunk_logs.json`

---

## Step 3: Build Correlation Timeline

Merge events from both sources into a unified timeline:

1. Extract timestamps from AAP job events
2. Extract timestamps from Splunk pod logs
3. Interleave by time
4. Identify causal chains (AAP task → pod event → error)

**Output**: `.analysis/<job-id>/step3_correlation.json`

---

## Step 4a: Parse GitHub Paths

**Script**: `scripts/parse_github_paths.py`
**Input**: `.analysis/<job-id>/step1_job_context.json`
**Output**: `.analysis/<job-id>/step4a_github_paths.json`

The script performs deterministic parsing:

1. **Parse job_name**: Extract platform, catalog_item, env, guid, action from RHPDS pattern
2. **Parse task_path**: Extract repository, file_path, line_number from each failed task
3. **Build config hierarchy**: Generate AgnosticV candidate paths (common → platform → demo)
4. **Build workload paths**: Generate AgnosticD candidate paths (role defaults, task file)

**The script outputs JSON with `path` or `paths_to_try` fields - these are CANDIDATE paths only. Actual file fetching must be done in Steps 4b-4e using GitHub MCP tools.**

**Output structure** (failure-centric):
```json
{
  "job_id": "{job_id}",
  "job_name": "RHPDS {platform}.{catalog_item}.{env}-{guid}-provision",
  "parsed_metadata": {
    "platform": "{platform}",
    "catalog_item": "{catalog_item}",
    "env": "{env}",
    "guid": "{guid}"
  },
  "failed_tasks": [
    {
      "task_name": "...",
      "role": "ocp4_workload_gitops_bootstrap",
      "error_message": "...",
      "location": {
        "original_path": "/home/runner/.ansible/...",
        "parsed": {
          "owner": "agnosticd",
          "repo": "core_workloads",
          "file_path": "roles/.../tasks/workload.yml",
          "line_number": 74
        }
      },
      "investigation_targets": {
        "workload_code": [...],
        "configuration": {
          "hierarchy": [...],
          "override_order": "Later files override earlier ones"
        }
      }
    }
  ]
}
```

---

## Step 4b-4e: Analyze with AgnosticD/V Context

**Input**: Read steps 1-3 and 4a outputs
**Output**: `.analysis/<job-id>/step4_summary.json`

### Investigation Strategy

**Variable Override Rules**:
- Order 1 (common.yaml) - Base defaults
- Order 2 (platform/account.yaml) - Platform overrides Order 1
- Order 3 (platform/catalog/env.yaml) - Environment overrides Order 2
- Role defaults are checked first, then configs in order

**When analyzing variables**:
1. Check if variable exists in role defaults
2. Check each config file in hierarchy order
3. Last definition wins
4. Flag if variable is undefined but required by task
5. Note if variable has "testing only" or "must remove for prod" comments

**Task Action Pattern Analysis**:
- `kubernetes.core.k8s_info` → Check API access, RBAC, resource existence
- `ansible.builtin.uri` → Check network, DNS, certificates, auth
- `ansible.builtin.command/shell` → Check binary paths, permissions
- `include_role/import_role` → Check role dependencies

**Secrets Detection**:
- If `account.yaml` has `includes/secrets` → Flag potential secret file issues
- If `!vault` found → Flag potential vault decryption issues

**Time Correlation**:
- Pod error BEFORE task → Infrastructure issue
- Pod error DURING task → Task triggered the error
- Pod error AFTER task timeout → Resource creation failed silently

### Schema

See `schemas/summary.schema.json` for the complete output structure.

---

## Ad-hoc Splunk Queries

```python
from scripts.splunk_client import SplunkClient
from scripts.config import Config

config = Config.from_env()
client = SplunkClient(config)

# Query by namespace
results = client.query(
    'index=federated:$SPLUNK_OCP_APP_INDEX kubernetes.namespace_name="$OCP_NAMESPACE"',
    earliest="-24h",
    max_results=100
)

# Query by GUID
results = client.query(
    'index=your_ocp_app_index "example-guid"',
    earliest="-24h"
)
```

---

## Files

| Step | File | Author |
|------|------|--------|
| 1 | `step1_job_context.json` | Python |
| 2 | `step2_splunk_logs.json` | Python |
| 3 | `step3_correlation.json` | Python |
| 4a | `step4a_github_paths.json` | Python (parse_github_paths.py) |
| 4e | `step4_summary.json` | You |

All files in `.analysis/<job-id>/`
