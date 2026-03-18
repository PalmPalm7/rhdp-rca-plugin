---
name: incident-investigator
description: End-to-end incident investigation workflow that fetches logs and performs root cause analysis. Use when a user wants to investigate incidents, analyze job failures, fetch and analyze logs in one workflow, or debug infrastructure issues. Combines log-fetcher, root-cause-analysis and context-fetcher into a unified pipeline.
allowed-tools:
  - Bash
  - Read
  - Write
  - Grep
  - mcp__github__search_code
  - mcp__github__get_file_contents
  - mcp__github__search_repositories
  - mcp__atlassian__confluence_search
  - mcp__atlassian__confluence_get_page
  - mcp__slack__slack_get_channel_history
---

# Incident Investigator

End-to-end incident investigation workflow combining log fetching, root cause analysis, and context retrieval.

```
Phase 1   [logs-fetcher]      Fetch logs via SSH
Phase 2   [root-cause-analysis]   Analyze logs and correlate with Splunk
Phase 3   [context-fetcher]       Fetch additional context if needed
```

---

## Phase 1: Fetch Logs

Use log-fetcher skill /log-fetcher.

## Phase 2: Perform Root Cause Analysis

Use root-cause-analysis skill /root-cause-analysis.

## Phase 3: Fetch contexts

Use context-fetcher skill /context-fetcher.
