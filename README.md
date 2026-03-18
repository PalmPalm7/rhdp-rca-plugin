# AIOps Skills

A marketplace of skills for AI-powered operations tasks. Skills extend Claude's capabilities for specific operational domains.

## Available Skills


| Skill                                         | Description                                              |
| --------------------------------------------- | -------------------------------------------------------- |
| [logs-fetcher](./skills/logs-fetcher/)               | Fetch Ansible/AAP logs via SSH with time-based filtering |
| [root-cause-analysis](./skills/root-cause-analysis/) | Root cause analysis and log analysis for failed jobs     |
| [context-fetcher](./skills/context-fetcher/)         | Fetch job config and docs from GitHub/Confluence         |
| [feedback-capture](./skills/feedback-capture/)       | Capture and store user feedback                          |


### logs-fetcher

Fetch Ansible/AAP logs from remote servers via SSH with flexible filtering:

```bash
# Fetch logs from a specific time range
python -m scripts.fetch_logs_ssh \
  --start-time "2025-12-09 08:00:00" \
  --end-time "2025-12-10 17:00:00" \
  --mode processed

# Fetch logs by job number
python -m scripts.fetch_logs_by_job 1234567 1234568 1234569
```

Use this skill when you need to:

- Fetch logs from specific time windows (with minute/second precision)
- Retrieve logs for specific job numbers
- Download recent processed or ignored job logs
- Investigate incidents within a known timeframe

### root-cause-analysis

Investigate failed jobs by correlating Ansible/AAP logs with Splunk OCP pod logs:

```
Step 1   [Python]  Parse local job log (extract GUID, namespace, failed tasks)
Step 2   [Python]  Query Splunk for correlated pod logs
Step 3   [Python]  Build correlation timeline
Step 4   [Claude]  Analyze and summarize root cause
```

Use this skill when you need to:

- Investigate job failures
- Analyze logs for errors
- Find root causes of infrastructure issues
- Debug failed deployments
- Troubleshoot Kubernetes/OpenShift problems

**Configuration:** Add the following to your Claude Code settings file (`.claude/settings.local.json` in your project root, or `~/.claude/settings.json` for global):

```json
{
  "env": {
    "REMOTE_HOST":"<remote-host>",
    "REMOTE_DIR": "<remote-dir>",
    "DEFAULT_LOCAL_DIR":"Path.home() / "aiops_extracted_logs"",
    "JOB_LOGS_DIR": "/path/to/your/extracted_logs",
    "SPLUNK_HOST": "<your-remote-splunk>",
    "SPLUNK_USERNAME": "your-username",
    "SPLUNK_PASSWORD": "your-password",
    "SPLUNK_INDEX": "<your-splunk-index>",
    "SPLUNK_OCP_APP_INDEX": "<splunk-ocp-app-index>",
    "SPLUNK_OCP_INFRA_INDEX": "<splunk-ocp-infra-index>",
    "SPLUNK_VERIFY_SSL": "false"
  }
}
```

### context-fetcher

Fetch configuration and documentation context via MCP servers:

- GitHub: job configs, recent commits, CI workflows
- Confluence: runbooks, troubleshooting guides

### feedback-capture

Capture and store user feedback during an interaction:

- **Ask** the user if they want to provide feedback
- **Categorize** feedback into predefined categories (e.g., Complexity, Clarity, Accuracy)
- **Summarize** the context of the interaction
- **Record** structured feedback to a local file via a Python script

Feedback is appended with a timestamp and session ID to `~/feedback.txt` by default.

Use this skill when you need to:

- Collect feedback at the end of an interaction
- Track feedback across multiple skill invocations
- Categorize and store user sentiment or bug reports

## Installation

### SSH Credentials

Please setup your SSH connection to the server before invoking log fetching skills.

The current log fetcher skills assumed the current settings:
REMOTE_HOST = ""
REMOTE_DIR = ""
DEFAULT_LOCAL_DIR = Path.home() / "aiops_extracted_logs"

We encourage you to setup your profile under `~/.ssh/config`

An example will look like:

```
Host <remote-host>
    HostName <host-name>
    User <User>-redhat.com
    Port 22
    IdentityFile /Users/<User>/.ssh/<SSH_Public_Key>
```

### Claude Code

1. Add to your settings (`.claude/settings.json`):

```json
{
  "plugins": ["redhat-et/aiops-skills"]
}
```

1. On claude navigate to Plugins, type /plugin in terminal
2. Go to Browse and install plugins
3. Install the desired plugins
4. Restart Claude by exiting and starting again

Then invoke skills by name (e.g., "Analyze job 1234567 for root cause" or "Investigate why this job failed").

### Claude.ai

Upload the skill folder contents to a Claude project's knowledge base.

### Claude API

Include the skill's `SKILL.md` content in your system prompt.

## Contributing

Contributions welcome. Ensure your skill:

- Follows the [Agent Skills Spec](./agent_skills_spec.md)
- Includes clear, actionable instructions
- Is focused on a specific AIOps domain
- See [CONTRIBUTING.md](./CONTRIBUTING.md) for more details

## License

Individual skills may specify their own licenses in frontmatter.
