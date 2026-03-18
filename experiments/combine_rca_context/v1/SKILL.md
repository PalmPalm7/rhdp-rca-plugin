---
name: root-cause-analysis
description: Perform root cause analysis and log analysis for failed jobs.Investigate AAP job failures using Splunk correlation and AgnosticD/AgnosticV configuration analysis. Correlates local Ansible/AAP job logs with Splunk OCP pod logs and retrieves relevant configuration from GitHub repositories.
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

### Step 4: Read outputs and analyze with AgnosticD/V context

After running the CLI, read the generated files from the `.analysis/` folder in this skill directory:

```
.analysis/<job-id>/step1_job_context.json
.analysis/<job-id>/step2_splunk_logs.json
.analysis/<job-id>/step3_correlation.json
```

Then perform enhanced analysis:
1. Parse job metadata to identify platform/demo/env from job_name pattern
2. Fetch AgnosticV configuration hierarchy from rhpds/agnosticv
3. Fetch AgnosticD workload code from redhat-cop/agnosticd
4. Apply investigation rules to identify root cause
5. Generate summary with actionable recommendations

Provide a summary to the user with:
1. **Job Details**: ID, status, GUID, namespace, platform, demo
2. **Failed Task(s)**: **IMPORTANT** - Preserve ALL fields from step1 failed_tasks:
   - Task: task name
   - Play: play name
   - Role: role name
   - Task Action: task_action (Ansible module)
   - Error: error_message
   - Task Duration: duration seconds
   - Location: Both original task_path AND derived GitHub path
     * Original: `/home/runner/.ansible/collections/...` (from task_path field)
     * GitHub: `repository:file_path:line` (parsed from original)
     * Example: `agnosticd/core_workloads:roles/ocp4_workload_gitops_bootstrap/tasks/workload.yml:74`
3. **Configuration Context**: Relevant variables, missing vars, secrets references
4. **Correlation**: How AAP logs link to Splunk pod logs (GUID, namespace, time overlap)
5. **Correlated Pods**: Pods found in Splunk during the job window
6. **Root Cause**: Analysis of why the job failed (configuration vs. infrastructure vs. workload bug)
7. **Recommendations**: Specific file changes with paths and suggested values
---

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

Create a `.env` file (see `.env.example`):

```bash
# Default directory to search for job log files
# The skill will look for files matching job_<ID>.* in this directory
JOB_LOGS_DIR=/path/to/extracted_logs

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
4. Identify causal chains (AAP task -> pod event -> error)

**Output**: `.analysis/<job-id>/step3_correlation.json`

---

## Step 4: Analyze with AgnosticD/V Context

**Input**: Read steps 1-3 outputs
**Output**: `.analysis/<job-id>/step4_summary.json`

### Your Task
Perform enhanced root cause analysis by combining correlation data with AgnosticD/AgnosticV configuration context.

### 4a. Parse Job Metadata

From `job_name` pattern: `RHPDS {platform}.{catalog_item}.{env}-{guid}-{action}`

Example: `RHPDS example_platform.example-catalog-item.dev-example-guid-provision`
- platform: `example_platform`
- catalog_item: `example-catalog-item`
- env: `dev`
- guid: `example-guid`

### 4b. Fetch AgnosticV Configuration Hierarchy

From **rhpds/agnosticv** repository, fetch configuration in override order using the GitHub MCP server:

Use `mcp__github__get_file_contents` to fetch each file:
1. `common.yaml` - Base configuration
2. `{platform}/account.yaml` - Platform defaults
   - Check for `includes/secrets` references
   - Note any `!vault` encrypted variables
3. `{platform}/{catalog_item}/{env}.yaml` - Environment-specific overrides

If files are not found at expected paths, use `mcp__github__search_code` to locate them.

Variables in later files override earlier ones.

#### Path Variations and Search Strategy

AgnosticV repositories use underscore naming convention consistently. When locating files:

1. **First attempt**: Direct path fetch
   ```
   {platform}/{catalog_item}/{env}.yaml
   ```
   Note: Platform names always use underscores (e.g., `example_platform`)

2. **If 404, try these strategies**:
   - Search for catalog item: `mcp__github__search_code` with query `repo:rhpds/agnosticv {catalog_item}`
   - Check parent directory structure: Fetch `{platform}/` directory listing to see available catalog items

3. **Check for related catalog items**:
   - Look for `{platform}/{catalog_item}/common.yaml` (catalog-level defaults)
   - Check for variant directories (e.g., `example-catalog` vs `example-catalog-rh1`)
   - Variants may share common configuration or have related settings

**Example**:
- Job name has catalog item: `{catalog_item}-rh1`
- Related directory may exist: `{catalog_item}/` (base version without suffix)
- Check both for shared configuration patterns

### 4c. Fetch AgnosticD Workload Code

From **agnosticd/core_workloads** or **redhat-cop/agnosticd** repository using the GitHub MCP server:

**IMPORTANT**: Check `failed_tasks[].task_path` to identify the correct repository:
- Path contains `agnosticd/core_workloads` → Use repo: `agnosticd/core_workloads`
- Path contains `/home/runner/.ansible/collections/` → Collection-based, check role name
- Path contains `redhat-cop/agnosticd` → Use repo: `redhat-cop/agnosticd`

**Fetch both role defaults AND task file:**

1. **Role defaults**: `roles/{role_name}/defaults/main.yml`
   - Contains default variable values
   - Critical for understanding variable precedence issues

2. **Task file**: `roles/{role_name}/{task_file}` at specific line number
   - Extract the full task definition, including `when` conditions
   - Check 10-20 lines before and after for context

3. **If repository is unclear or file fetch fails**:
   - If `task_path` doesn't clearly indicate repository, use `mcp__github__search_repositories` to find repositories containing the role:
     - Query: `org:agnosticd {role_name}` or `org:redhat-cop {role_name}` or `{role_name} agnosticd` or `agnosticd-v2`
     - This helps discover the correct repository when path parsing is ambiguous
   - Once repository is identified, use `mcp__github__search_code` with: `repo:{org}/{repo} {role_name}`
   - Try alternate repositories if not found

**Example**:
```
task_path: /home/runner/.ansible/collections/ansible_collections/agnosticd/core_workloads/roles/{role_name}/tasks/{task_file}.yml:{line}

→ Repository: agnosticd/core_workloads
→ Fetch: roles/{role_name}/defaults/main.yml
→ Fetch: roles/{role_name}/tasks/{task_file}.yml
→ Analyze: Line {line} task + its `when` condition
```

### 4d. Apply Investigation Rules

**Rule 1 - Variable Precedence Analysis**:
- Build precedence chain (later files override earlier ones): Role defaults → common.yaml → {platform}/account.yaml → {platform}/{catalog_item}/common.yaml → {platform}/{catalog_item}/{env}.yaml
  - **Override order**: Each file in the chain can override variables from previous files, with `{platform}/{catalog_item}/{env}.yaml` having the highest precedence (overrides all previous)
- Check for conflicts: Multiple files defining same variable, `__meta__.deployer` duplicates
- Conditional task analysis: If task has `when: var | bool` but executed when var=false → precedence failure
- Flag "testing only" or "must be removed for prod" comments as potential issues

**Rule 2 - Task Action Patterns**:
- `kubernetes.core.k8s_info` → Check API access, RBAC, resource existence
- `ansible.builtin.uri` → Check network, DNS, certificates, auth
- `ansible.builtin.command/shell` → Check binary paths, permissions
- `include_role/import_role` → Check role dependencies

**Rule 3 - Secrets**: If `account.yaml` has `includes/secrets` or `!vault`, flag potential credential issues

**Rule 4 - Time Correlation**: Match AAP timestamps with Splunk pod errors to determine if infrastructure issue (pod error BEFORE task) vs task-triggered error (DURING task)

**Rule 5 - Task Duration Analysis**:
- < 30s: Immediate failure (RBAC, missing resource)
- 30-300s: Short retry loop
- \> 300s: Long retry loop (health check timeout)
- Calculate retry count: `duration / (delay * retries)` and compare with role defaults

**Rule 6 - Conditional Execution**: Check if tasks with `when:` conditions executed when they should have been skipped (indicates variable precedence issues)

### Path Translation for Failed Tasks

**IMPORTANT**: Before generating the summary, parse the `task_path` field from each failed task in step1_job_context.json to create the `location` object.

**Pattern 1 - Collections Path**:
```
/home/runner/.ansible/collections/ansible_collections/{org}/{repo}/roles/{role}/tasks/{file}.yml:{line}
```
Example: `/home/runner/.ansible/collections/ansible_collections/agnosticd/core_workloads/roles/ocp4_workload_gitops_bootstrap/tasks/workload.yml:74`

Parsed as:
- repository: `agnosticd/core_workloads`
- file_path: `roles/ocp4_workload_gitops_bootstrap/tasks/workload.yml`
- line_number: `74`
- github_path: `agnosticd/core_workloads:roles/ocp4_workload_gitops_bootstrap/tasks/workload.yml:74`

**Pattern 2 - Project Path**:
```
/runner/project/{path}:{line}
```
Example: `/runner/project/ansible/roles-infra/infra-aws-dry-run/tasks/ec2.yml:2`

Parsed as:
- repository: `redhat-cop/agnosticd` (default for project paths)
- file_path: `ansible/roles-infra/infra-aws-dry-run/tasks/ec2.yml`
- line_number: `2`
- github_path: `redhat-cop/agnosticd:ansible/roles-infra/infra-aws-dry-run/tasks/ec2.yml:2`

**When displaying to users**: Show BOTH the original path and the GitHub path with an explanation:
```
Location: /runner/project/ansible/roles-infra/infra-aws-dry-run/tasks/ec2.yml:2
GitHub: redhat-cop/agnosticd:ansible/roles-infra/infra-aws-dry-run/tasks/ec2.yml:2
(Derived from the original AAP task path for code investigation)
```

### 4e. Generate Summary

Review the correlation timeline and produce a summary containing:

1. **Failed Tasks**: **PRESERVE ALL ORIGINAL FIELDS** from step1_job_context.json `failed_tasks` array
   - Copy all fields: task, play, role, task_action, error_message, duration, timestamp
   - Parse task_path using the patterns above to create the `location` object
   - This ensures no information is lost from the original AAP event

2. **Root Cause**: Primary reason for failure with configuration/workload context
3. **Evidence**: Key log entries and config findings supporting the conclusion

4. **Correlation Proof**: How AAP logs link to Splunk logs
   - Matching GUID/namespace
   - Overlapping timestamps
   - Referenced pod names

5. **Recommendations**: Actionable steps with specific file paths and changes

### Schema

See `schemas/summary.schema.json` for the complete output structure.

Example summary:

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

## Ad-hoc Splunk Queries

```python
from scripts.splunk_client import SplunkClient
from scripts.config import Config

config = Config.from_env()
client = SplunkClient(config)

# Query by namespace
results = client.query(
    'index=your_ocp_app_index kubernetes.namespace_name="$OCP_NAMESPACE"',
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
| 4 | `step4_summary.json` | You |

All files in `.analysis/<job-id>/`
